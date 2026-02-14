"""Integration layer with Ralph-TUI CLI and configuration files."""

from __future__ import annotations

import json
import logging
import shutil
import subprocess
from pathlib import Path

from .models import Project, ProjectConfig, ProjectStatus

logger = logging.getLogger(__name__)

# Ralph-TUI config file name within project directories
RALPH_CONFIG_DIR = ".ralph-tui"
RALPH_CONFIG_FILE = "config.toml"


def find_ralph_tui() -> str | None:
    """Find the ralph-tui executable on the system."""
    return shutil.which("ralph-tui")


def is_ralph_tui_available() -> bool:
    """Check if ralph-tui CLI is available."""
    return find_ralph_tui() is not None


def run_ralph_command(args: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess:
    """Execute a ralph-tui CLI command and return the result."""
    cmd = [find_ralph_tui() or "ralph-tui"] + args
    logger.debug("Running: %s", " ".join(cmd))
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=str(cwd) if cwd else None,
        timeout=30,
    )


def parse_toml_config(config_path: Path) -> dict:
    """Parse a TOML configuration file.

    Uses tomllib (Python 3.11+) or falls back to basic parsing.
    """
    try:
        import tomllib
        with open(config_path, "rb") as f:
            return tomllib.load(f)
    except ImportError:
        pass

    # Fallback: basic TOML parsing for simple key=value files
    result: dict = {}
    current_section = result
    try:
        for line in config_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("[") and line.endswith("]"):
                section_name = line[1:-1].strip()
                result[section_name] = {}
                current_section = result[section_name]
            elif "=" in line:
                key, _, value = line.partition("=")
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                # Try to convert to appropriate types
                if value.lower() in ("true", "false"):
                    current_section[key] = value.lower() == "true"
                elif value.isdigit():
                    current_section[key] = int(value)
                else:
                    try:
                        current_section[key] = float(value)
                    except ValueError:
                        current_section[key] = value
    except Exception as exc:
        logger.warning("Failed to parse TOML %s: %s", config_path, exc)
    return result


def load_project_config(project_path: Path) -> ProjectConfig:
    """Load Ralph-TUI project configuration."""
    config_file = project_path / RALPH_CONFIG_DIR / RALPH_CONFIG_FILE
    if not config_file.exists():
        return ProjectConfig(project_dir=str(project_path))

    raw_toml = config_file.read_text(encoding="utf-8")
    parsed = parse_toml_config(config_file)

    def _get_nested(d: dict, key: str, sub_key: str, default):
        """Safely get a value that may be top-level or in a nested section."""
        val = d.get(key)
        if val is not None and not isinstance(val, dict):
            return val
        section = val if isinstance(val, dict) else d.get(key, {})
        if isinstance(section, dict):
            return section.get(sub_key, default)
        return default

    return ProjectConfig(
        issue_tracker=_get_nested(parsed, "issue_tracker", "type",
                                  _get_nested(parsed, "tracker", "type", "json")),
        agent=_get_nested(parsed, "agent", "type", "opencode"),
        model=_get_nested(parsed, "model", "model",
                          _get_nested(parsed, "agent", "model", "qwen2.5-coder:7b")),
        max_iterations=_get_nested(parsed, "max_iterations", "max_iterations",
                                   _get_nested(parsed, "execution", "max_iterations", 50)),
        headless=_get_nested(parsed, "headless", "headless",
                             _get_nested(parsed, "execution", "headless", False)),
        project_dir=str(project_path),
        raw_toml=raw_toml,
    )


def save_project_config(project_path: Path, raw_toml: str) -> None:
    """Save raw TOML content to project config file."""
    config_dir = project_path / RALPH_CONFIG_DIR
    config_dir.mkdir(parents=True, exist_ok=True)
    config_file = config_dir / RALPH_CONFIG_FILE
    config_file.write_text(raw_toml, encoding="utf-8")
    logger.info("Saved config for project at %s", project_path)


def discover_projects(projects_dir: Path) -> list[Project]:
    """Discover all Ralph-TUI projects in the projects directory."""
    projects = []
    if not projects_dir.exists():
        logger.warning("Projects directory does not exist: %s", projects_dir)
        return projects

    for item in sorted(projects_dir.iterdir()):
        if not item.is_dir():
            continue
        # A Ralph-TUI project has a .ralph-tui directory
        ralph_dir = item / RALPH_CONFIG_DIR
        if not ralph_dir.exists():
            continue

        config = load_project_config(item)
        task_count, completed = _count_tasks(item)

        projects.append(Project(
            name=item.name,
            path=str(item),
            status=ProjectStatus.IDLE,
            config=config,
            task_count=task_count,
            completed_tasks=completed,
        ))

    return projects


def _count_tasks(project_path: Path) -> tuple[int, int]:
    """Count total and completed tasks in a project."""
    total = 0
    completed = 0

    # Check for tasks.json
    tasks_file = project_path / "tasks" / "tasks.json"
    if tasks_file.exists():
        try:
            data = json.loads(tasks_file.read_text(encoding="utf-8"))
            tasks = data.get("tasks", data if isinstance(data, list) else [])
            total = len(tasks)
            completed = sum(
                1 for t in tasks
                if t.get("status", "").lower() in ("completed", "done", "complete")
            )
        except (json.JSONDecodeError, AttributeError) as exc:
            logger.debug("Failed to parse tasks.json: %s", exc)

    # Check for prd.json that may contain tasks
    prd_file = project_path / "prd.json"
    if prd_file.exists() and total == 0:
        try:
            data = json.loads(prd_file.read_text(encoding="utf-8"))
            tasks = data.get("tasks", [])
            total = len(tasks)
            completed = sum(
                1 for t in tasks
                if t.get("status", "").lower() in ("completed", "done", "complete")
            )
        except (json.JSONDecodeError, AttributeError):
            pass

    return total, completed


def build_run_command(
    project_name: str,
    project_path: Path | None = None,
    max_iterations: int = 50,
    headless: bool = False,
    model: str | None = None,
    agent: str | None = None,
) -> list[str]:
    """Build the ralph-tui run command with options.

    Note: We run from the project directory (cwd), so ralph-tui should
    pick up .ralph-tui/config.toml automatically. We also pass
    --tracker json explicitly to override any defaults and --prd
    to point at the tasks file so the json tracker finds them.
    """
    cmd = [find_ralph_tui() or "ralph-tui", "run"]
    cmd.extend(["--project", project_name])
    cmd.extend(["--max-iterations", str(max_iterations)])
    cmd.extend(["--tracker", "json"])

    # Pass --prd so the json tracker finds the tasks file
    if project_path:
        prd_candidates = [
            project_path / "tasks" / "tasks.json",
            project_path / ".ralph-tui" / "tasks.json",
            project_path / "prd.json",
        ]
        for prd_file in prd_candidates:
            if prd_file.exists():
                cmd.extend(["--prd", str(prd_file)])
                break

    if headless:
        cmd.append("--headless")
    if model:
        cmd.extend(["--model", model])
    if agent:
        cmd.extend(["--agent", agent])
    return cmd


def build_resume_command(project_name: str) -> list[str]:
    """Build the ralph-tui resume command."""
    return [find_ralph_tui() or "ralph-tui", "resume", "--project", project_name]


def get_ralph_status() -> dict:
    """Get ralph-tui global status if available."""
    if not is_ralph_tui_available():
        return {"available": False, "message": "ralph-tui not found in PATH"}
    try:
        result = run_ralph_command(["status"])
        return {
            "available": True,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode,
        }
    except subprocess.TimeoutExpired:
        return {"available": True, "message": "ralph-tui status command timed out"}
    except Exception as exc:
        return {"available": True, "message": str(exc)}


def find_log_files(project_path: Path) -> list[Path]:
    """Find all log files for a Ralph-TUI project."""
    log_files = []

    # Common log locations
    candidates = [
        project_path / ".ralph-tui" / "logs",
        project_path / "logs",
        project_path / ".ralph-tui",
    ]

    for candidate in candidates:
        if candidate.is_dir():
            log_files.extend(sorted(candidate.glob("*.log"), reverse=True))
            log_files.extend(sorted(candidate.glob("*.txt"), reverse=True))

    # Also check for iteration logs
    iteration_dir = project_path / ".ralph-tui" / "iterations"
    if iteration_dir.is_dir():
        log_files.extend(sorted(iteration_dir.glob("*"), reverse=True))

    return log_files
