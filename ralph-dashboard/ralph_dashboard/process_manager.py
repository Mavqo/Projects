"""Process management for Ralph-TUI instances."""

from __future__ import annotations

import logging
import os
import signal
import subprocess
import threading
from datetime import datetime
from pathlib import Path
from typing import Callable

import psutil

from .models import ProjectStatus

logger = logging.getLogger(__name__)


class ManagedProcess:
    """Wrapper around a subprocess with output capture."""

    def __init__(
        self,
        project_name: str,
        command: list[str],
        cwd: Path,
        on_output: Callable[[str, str], None] | None = None,
        on_exit: Callable[[str, int], None] | None = None,
        auto_respond: list[str] | None = None,
    ) -> None:
        self.project_name = project_name
        self.command = command
        self.cwd = cwd
        self.process: subprocess.Popen | None = None
        self.status = ProjectStatus.IDLE
        self.start_time: datetime | None = None
        self.exit_code: int | None = None
        self._on_output = on_output
        self._on_exit = on_exit
        self._output_thread: threading.Thread | None = None
        self._stderr_thread: threading.Thread | None = None
        self._auto_respond = auto_respond or []

    @property
    def pid(self) -> int | None:
        return self.process.pid if self.process else None

    @property
    def is_running(self) -> bool:
        if self.process is None:
            return False
        return self.process.poll() is None

    def start(self) -> None:
        """Start the subprocess."""
        logger.info("Starting process for %s: %s", self.project_name, " ".join(self.command))
        try:
            # Use a sanitized environment: set TERM=dumb to suppress TUI rendering,
            # and disable colors/interactive prompts in child processes.
            env = os.environ.copy()
            env["TERM"] = "dumb"
            env["NO_COLOR"] = "1"
            env["FORCE_COLOR"] = "0"
            # NOTE: Do NOT set CI=1 here – agents (opencode, claude, etc.)
            # treat CI mode as "dry run / non-interactive" and skip work.

            self.process = subprocess.Popen(
                self.command,
                cwd=str(self.cwd),
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                env=env,
            )
            self.status = ProjectStatus.RUNNING
            self.start_time = datetime.now()

            # Auto-respond to interactive prompts (e.g. auto-commit selection)
            if self._auto_respond and self.process.stdin:
                threading.Thread(
                    target=self._write_auto_responses,
                    daemon=True,
                ).start()

            # Start output reader threads
            self._output_thread = threading.Thread(
                target=self._read_stream,
                args=(self.process.stdout, "stdout"),
                daemon=True,
            )
            self._output_thread.start()

            self._stderr_thread = threading.Thread(
                target=self._read_stream,
                args=(self.process.stderr, "stderr"),
                daemon=True,
            )
            self._stderr_thread.start()

            # Start wait thread
            threading.Thread(target=self._wait_for_exit, daemon=True).start()

        except FileNotFoundError as exc:
            self.status = ProjectStatus.ERROR
            logger.error("Failed to start process: %s", exc)
            raise
        except PermissionError as exc:
            self.status = ProjectStatus.ERROR
            logger.error("Permission denied: %s", exc)
            raise

    def _write_auto_responses(self) -> None:
        """Write pre-canned responses to stdin for interactive prompts."""
        import time
        stdin = self.process.stdin
        if not stdin:
            return
        try:
            for response in self._auto_respond:
                # Small delay to let the process initialize and show the prompt
                time.sleep(1.5)
                if not self.is_running:
                    break
                logger.debug("Auto-responding '%s' to %s", response.strip(), self.project_name)
                stdin.write(response)
                stdin.flush()
        except (BrokenPipeError, OSError) as exc:
            logger.debug("Auto-respond pipe closed: %s", exc)

    def _read_stream(self, stream, stream_name: str) -> None:
        """Read lines from a stream and forward to callback."""
        try:
            for line in stream:
                line = line.rstrip("\n")
                if self._on_output:
                    self._on_output(self.project_name, line)
        except (ValueError, OSError):
            pass  # Stream closed

    def _wait_for_exit(self) -> None:
        """Wait for process to exit and update status."""
        if self.process is None:
            return
        self.exit_code = self.process.wait()
        if self.exit_code == 0:
            self.status = ProjectStatus.COMPLETED
        else:
            self.status = ProjectStatus.ERROR
        logger.info(
            "Process %s (pid=%s) exited with code %d",
            self.project_name,
            self.pid,
            self.exit_code,
        )
        if self._on_exit:
            self._on_exit(self.project_name, self.exit_code)

    def stop(self) -> None:
        """Stop the subprocess gracefully, then forcefully."""
        if not self.is_running or self.process is None:
            return
        logger.info("Stopping process %s (pid=%s)", self.project_name, self.pid)
        try:
            self.process.send_signal(signal.SIGTERM)
            try:
                self.process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                logger.warning("Process %s did not stop gracefully, killing", self.project_name)
                self.process.kill()
                self.process.wait(timeout=5)
        except (ProcessLookupError, OSError) as exc:
            logger.debug("Process already gone: %s", exc)
        self.status = ProjectStatus.IDLE

    def pause(self) -> None:
        """Pause (SIGSTOP) the subprocess."""
        if self.is_running and self.process:
            try:
                self.process.send_signal(signal.SIGSTOP)
                self.status = ProjectStatus.PAUSED
            except (ProcessLookupError, OSError) as exc:
                logger.warning("Failed to pause: %s", exc)

    def resume(self) -> None:
        """Resume (SIGCONT) the subprocess."""
        if self.process and self.status == ProjectStatus.PAUSED:
            try:
                self.process.send_signal(signal.SIGCONT)
                self.status = ProjectStatus.RUNNING
            except (ProcessLookupError, OSError) as exc:
                logger.warning("Failed to resume: %s", exc)


class ProcessManager:
    """Manages multiple Ralph-TUI process instances."""

    def __init__(self) -> None:
        self._processes: dict[str, ManagedProcess] = {}
        self._lock = threading.Lock()
        self._output_callbacks: list[Callable[[str, str], None]] = []
        self._exit_callbacks: list[Callable[[str, int], None]] = []

    def on_output(self, callback: Callable[[str, str], None]) -> None:
        """Register a callback for process output."""
        self._output_callbacks.append(callback)

    def on_exit(self, callback: Callable[[str, int], None]) -> None:
        """Register a callback for process exit."""
        self._exit_callbacks.append(callback)

    def _handle_output(self, project: str, line: str) -> None:
        for cb in self._output_callbacks:
            try:
                cb(project, line)
            except Exception as exc:
                logger.debug("Output callback error: %s", exc)

    def _handle_exit(self, project: str, code: int) -> None:
        for cb in self._exit_callbacks:
            try:
                cb(project, code)
            except Exception as exc:
                logger.debug("Exit callback error: %s", exc)

    def launch(
        self,
        project_name: str,
        command: list[str],
        cwd: Path,
        auto_respond: list[str] | None = None,
    ) -> ManagedProcess:
        """Launch a new Ralph-TUI process for a project."""
        with self._lock:
            # Stop existing process if running
            if project_name in self._processes and self._processes[project_name].is_running:
                self._processes[project_name].stop()

            proc = ManagedProcess(
                project_name=project_name,
                command=command,
                cwd=cwd,
                on_output=self._handle_output,
                on_exit=self._handle_exit,
                auto_respond=auto_respond,
            )
            proc.start()
            self._processes[project_name] = proc
            return proc

    def stop(self, project_name: str) -> bool:
        """Stop a running project process."""
        with self._lock:
            proc = self._processes.get(project_name)
            if proc and proc.is_running:
                proc.stop()
                return True
            return False

    def pause(self, project_name: str) -> bool:
        """Pause a running project process."""
        with self._lock:
            proc = self._processes.get(project_name)
            if proc and proc.is_running:
                proc.pause()
                return True
            return False

    def resume(self, project_name: str) -> bool:
        """Resume a paused project process."""
        with self._lock:
            proc = self._processes.get(project_name)
            if proc and proc.status == ProjectStatus.PAUSED:
                proc.resume()
                return True
            return False

    def get_process(self, project_name: str) -> ManagedProcess | None:
        """Get the managed process for a project."""
        return self._processes.get(project_name)

    def get_status(self, project_name: str) -> ProjectStatus:
        """Get the status of a project's process."""
        proc = self._processes.get(project_name)
        if proc is None:
            return ProjectStatus.IDLE
        if proc.is_running:
            return proc.status
        return proc.status

    def list_active(self) -> dict[str, ManagedProcess]:
        """List all active (running/paused) processes."""
        return {
            name: proc
            for name, proc in self._processes.items()
            if proc.is_running or proc.status == ProjectStatus.PAUSED
        }

    def shutdown_all(self) -> None:
        """Stop all running processes."""
        with self._lock:
            for proc in self._processes.values():
                if proc.is_running:
                    proc.stop()
