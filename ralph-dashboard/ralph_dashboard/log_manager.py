"""Log management: parsing, streaming, and searching Ralph-TUI logs."""

from __future__ import annotations

import logging
import re
import threading
import time
from collections import deque
from datetime import datetime
from pathlib import Path

from .models import LogEntry, LogLevel

logger = logging.getLogger(__name__)

# Common log line patterns
LOG_PATTERNS = [
    # Standard: 2024-01-15 10:30:45 [INFO] message
    re.compile(
        r"^(?P<timestamp>\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}(?:\.\d+)?)\s+"
        r"\[(?P<level>\w+)]\s+(?P<message>.*)$"
    ),
    # ISO format: 2024-01-15T10:30:45.123Z INFO message
    re.compile(
        r"^(?P<timestamp>\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z?)\s+"
        r"(?P<level>DEBUG|INFO|WARN(?:ING)?|ERROR|CRITICAL)\s+(?P<message>.*)$"
    ),
    # Simple: [INFO] message
    re.compile(
        r"^\[(?P<level>DEBUG|INFO|WARN(?:ING)?|ERROR|CRITICAL)]\s+(?P<message>.*)$"
    ),
]

LEVEL_MAP = {
    "debug": LogLevel.DEBUG,
    "info": LogLevel.INFO,
    "warn": LogLevel.WARNING,
    "warning": LogLevel.WARNING,
    "error": LogLevel.ERROR,
    "critical": LogLevel.CRITICAL,
    "fatal": LogLevel.CRITICAL,
}


def parse_log_line(line: str, line_number: int = 0, source: str = "") -> LogEntry:
    """Parse a single log line into a LogEntry."""
    for pattern in LOG_PATTERNS:
        match = pattern.match(line)
        if match:
            groups = match.groupdict()
            level_str = groups.get("level", "info").lower()
            timestamp = None
            ts_str = groups.get("timestamp")
            if ts_str:
                for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M:%S.%f",
                            "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%S.%fZ"):
                    try:
                        timestamp = datetime.strptime(ts_str, fmt)
                        break
                    except ValueError:
                        continue
            return LogEntry(
                timestamp=timestamp,
                level=LEVEL_MAP.get(level_str, LogLevel.INFO),
                message=groups.get("message", line),
                source=source,
                line_number=line_number,
            )

    # No pattern matched - treat as INFO
    return LogEntry(
        message=line,
        level=LogLevel.INFO,
        source=source,
        line_number=line_number,
    )


class LogBuffer:
    """Thread-safe buffer for log lines with max capacity."""

    def __init__(self, max_lines: int = 10000) -> None:
        self._lines: deque[str] = deque(maxlen=max_lines)
        self._lock = threading.Lock()
        self._new_line_event = threading.Event()

    def append(self, line: str) -> None:
        with self._lock:
            self._lines.append(line)
        self._new_line_event.set()

    def get_all(self) -> list[str]:
        with self._lock:
            return list(self._lines)

    def get_recent(self, count: int = 100) -> list[str]:
        with self._lock:
            items = list(self._lines)
            return items[-count:] if len(items) > count else items

    def clear(self) -> None:
        with self._lock:
            self._lines.clear()

    def wait_for_new(self, timeout: float = 5.0) -> bool:
        """Wait for new lines. Returns True if new line arrived."""
        result = self._new_line_event.wait(timeout=timeout)
        self._new_line_event.clear()
        return result

    @property
    def count(self) -> int:
        return len(self._lines)


class LogFileWatcher(threading.Thread):
    """Watches a log file for new content and streams to a buffer."""

    def __init__(self, file_path: Path, buffer: LogBuffer) -> None:
        super().__init__(daemon=True)
        self.file_path = file_path
        self.buffer = buffer
        self._stop_event = threading.Event()

    def run(self) -> None:
        """Watch the file and push new lines to the buffer."""
        try:
            if not self.file_path.exists():
                self.buffer.append(f"[LOG] Waiting for log file: {self.file_path}")
                # Wait for file to appear
                while not self._stop_event.is_set() and not self.file_path.exists():
                    time.sleep(0.5)

            if self._stop_event.is_set():
                return

            with open(self.file_path, "r", encoding="utf-8", errors="replace") as f:
                # Seek to end for real-time tailing
                f.seek(0, 2)
                while not self._stop_event.is_set():
                    line = f.readline()
                    if line:
                        self.buffer.append(line.rstrip("\n"))
                    else:
                        time.sleep(0.1)
        except Exception as exc:
            self.buffer.append(f"[LOG ERROR] Failed to watch {self.file_path}: {exc}")

    def stop(self) -> None:
        self._stop_event.set()


class ProjectLogManager:
    """Manages log buffers and watchers for projects."""

    def __init__(self, max_lines: int = 10000) -> None:
        self._buffers: dict[str, LogBuffer] = {}
        self._watchers: dict[str, list[LogFileWatcher]] = {}
        self._max_lines = max_lines

    def get_buffer(self, project_name: str) -> LogBuffer:
        """Get or create a log buffer for a project."""
        if project_name not in self._buffers:
            self._buffers[project_name] = LogBuffer(max_lines=self._max_lines)
        return self._buffers[project_name]

    def add_line(self, project_name: str, line: str) -> None:
        """Add a log line to a project's buffer (from process output)."""
        self.get_buffer(project_name).append(line)

    def watch_file(self, project_name: str, file_path: Path) -> None:
        """Start watching a log file for a project."""
        buffer = self.get_buffer(project_name)
        watcher = LogFileWatcher(file_path, buffer)
        watcher.start()
        self._watchers.setdefault(project_name, []).append(watcher)

    def get_logs(
        self,
        project_name: str,
        count: int = 100,
        keyword: str | None = None,
        level: LogLevel | None = None,
    ) -> list[str]:
        """Get filtered log lines for a project."""
        buffer = self._buffers.get(project_name)
        if not buffer:
            return []

        lines = buffer.get_all() if count <= 0 else buffer.get_recent(count)

        if keyword:
            keyword_lower = keyword.lower()
            lines = [l for l in lines if keyword_lower in l.lower()]

        if level:
            level_str = level.value.upper()
            lines = [l for l in lines if level_str in l.upper()]

        return lines

    def read_log_file(
        self,
        file_path: Path,
        max_lines: int = 1000,
        offset: int = 0,
    ) -> list[str]:
        """Read lines from a log file."""
        if not file_path.exists():
            return []
        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()
            return [l.rstrip("\n") for l in lines[offset:offset + max_lines]]
        except OSError as exc:
            logger.error("Failed to read log file %s: %s", file_path, exc)
            return []

    def clear_buffer(self, project_name: str) -> None:
        """Clear the log buffer for a project (doesn't delete files)."""
        if project_name in self._buffers:
            self._buffers[project_name].clear()

    def stop_watchers(self, project_name: str) -> None:
        """Stop all file watchers for a project."""
        for watcher in self._watchers.pop(project_name, []):
            watcher.stop()

    def shutdown(self) -> None:
        """Stop all watchers."""
        for name in list(self._watchers.keys()):
            self.stop_watchers(name)
