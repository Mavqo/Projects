"""Task management for Ralph-TUI project task trackers."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from .models import Task, TaskCreate, TaskPriority, TaskStatus, TaskUpdate

logger = logging.getLogger(__name__)


class TaskManager:
    """Manages tasks within Ralph-TUI project task tracker files."""

    def __init__(self, project_path: Path) -> None:
        self.project_path = project_path
        self._tasks_file = self._find_tasks_file()

    def _find_tasks_file(self) -> Path | None:
        """Locate the task tracker file for this project."""
        candidates = [
            self.project_path / "tasks" / "tasks.json",
            self.project_path / "tasks.json",
            self.project_path / "prd.json",
            self.project_path / ".ralph-tui" / "tasks.json",
        ]
        for path in candidates:
            if path.exists():
                return path

        # Check for any .json in tasks/ directory
        tasks_dir = self.project_path / "tasks"
        if tasks_dir.is_dir():
            json_files = list(tasks_dir.glob("*.json"))
            if json_files:
                return json_files[0]

        return None

    def _load_raw(self) -> dict:
        """Load raw JSON data from the tasks file."""
        if self._tasks_file is None or not self._tasks_file.exists():
            return {"tasks": []}
        try:
            return json.loads(self._tasks_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            logger.error("Failed to load tasks from %s: %s", self._tasks_file, exc)
            return {"tasks": []}

    def _save_raw(self, data: dict) -> None:
        """Save raw JSON data to the tasks file."""
        if self._tasks_file is None:
            # Create default tasks file
            tasks_dir = self.project_path / "tasks"
            tasks_dir.mkdir(parents=True, exist_ok=True)
            self._tasks_file = tasks_dir / "tasks.json"

        self._tasks_file.write_text(
            json.dumps(data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def _parse_task(self, raw: dict) -> Task:
        """Parse a raw dict into a Task model."""
        # Handle various field naming conventions
        task_id = raw.get("id", raw.get("task_id", ""))
        title = raw.get("title", raw.get("name", raw.get("summary", "")))
        description = raw.get("description", raw.get("details", ""))
        raw_status = str(raw.get("status", "pending")).lower().replace(" ", "-")

        # Map status strings
        status_map = {
            "pending": TaskStatus.PENDING,
            "todo": TaskStatus.PENDING,
            "not-started": TaskStatus.PENDING,
            "in-progress": TaskStatus.IN_PROGRESS,
            "in_progress": TaskStatus.IN_PROGRESS,
            "active": TaskStatus.IN_PROGRESS,
            "running": TaskStatus.IN_PROGRESS,
            "completed": TaskStatus.COMPLETED,
            "done": TaskStatus.COMPLETED,
            "complete": TaskStatus.COMPLETED,
            "blocked": TaskStatus.BLOCKED,
            "waiting": TaskStatus.BLOCKED,
            "cancelled": TaskStatus.CANCELLED,
            "canceled": TaskStatus.CANCELLED,
            "deferred": TaskStatus.DEFERRED,
            "skipped": TaskStatus.DEFERRED,
        }
        status = status_map.get(raw_status, TaskStatus.PENDING)

        # Parse priority
        raw_priority = str(raw.get("priority", "medium")).lower()
        priority_map = {
            "high": TaskPriority.HIGH,
            "critical": TaskPriority.HIGH,
            "urgent": TaskPriority.HIGH,
            "medium": TaskPriority.MEDIUM,
            "normal": TaskPriority.MEDIUM,
            "low": TaskPriority.LOW,
            "minor": TaskPriority.LOW,
        }
        priority = priority_map.get(raw_priority, TaskPriority.MEDIUM)

        # Parse dependencies
        deps = raw.get("dependencies", raw.get("depends_on", []))
        if isinstance(deps, str):
            deps = [d.strip() for d in deps.split(",") if d.strip()]

        # Parse subtasks
        subtasks = [self._parse_task(st) for st in raw.get("subtasks", [])]

        return Task(
            id=task_id,
            title=title,
            description=description,
            status=status,
            priority=priority,
            dependencies=deps,
            subtasks=subtasks,
            metadata={k: v for k, v in raw.items() if k not in (
                "id", "task_id", "title", "name", "summary", "description",
                "details", "status", "priority", "dependencies", "depends_on",
                "subtasks",
            )},
        )

    def _task_to_raw(self, task: Task) -> dict:
        """Convert a Task model back to raw dict."""
        raw = {
            "id": task.id,
            "title": task.title,
            "description": task.description,
            "status": task.status.value,
            "priority": task.priority.value,
            "dependencies": task.dependencies,
        }
        if task.subtasks:
            raw["subtasks"] = [self._task_to_raw(st) for st in task.subtasks]
        raw.update(task.metadata)
        return raw

    def list_tasks(self) -> list[Task]:
        """Get all tasks from the tracker file."""
        data = self._load_raw()
        raw_tasks = data.get("tasks", data if isinstance(data, list) else [])
        if isinstance(raw_tasks, list):
            return [self._parse_task(t) for t in raw_tasks if isinstance(t, dict)]
        return []

    def get_task(self, task_id: str | int) -> Task | None:
        """Get a specific task by ID."""
        for task in self.list_tasks():
            if str(task.id) == str(task_id):
                return task
        return None

    def update_task(self, task_id: str | int, update: TaskUpdate) -> Task | None:
        """Update a task's fields."""
        data = self._load_raw()
        raw_tasks = data.get("tasks", data if isinstance(data, list) else [])

        for raw_task in raw_tasks:
            if str(raw_task.get("id", raw_task.get("task_id", ""))) == str(task_id):
                if update.title is not None:
                    raw_task["title"] = update.title
                if update.description is not None:
                    raw_task["description"] = update.description
                if update.status is not None:
                    raw_task["status"] = update.status.value
                if update.priority is not None:
                    raw_task["priority"] = update.priority.value
                if update.dependencies is not None:
                    raw_task["dependencies"] = update.dependencies

                if isinstance(data, dict) and "tasks" in data:
                    data["tasks"] = raw_tasks
                self._save_raw(data if isinstance(data, dict) else {"tasks": raw_tasks})
                return self._parse_task(raw_task)

        return None

    def create_task(self, create: TaskCreate) -> Task:
        """Create a new task."""
        data = self._load_raw()
        raw_tasks = data.get("tasks", []) if isinstance(data, dict) else data if isinstance(data, list) else []

        # Generate new ID
        existing_ids = [t.get("id", 0) for t in raw_tasks if isinstance(t, dict)]
        numeric_ids = [int(i) for i in existing_ids if str(i).isdigit()]
        new_id = max(numeric_ids, default=0) + 1

        new_task_raw = {
            "id": new_id,
            "title": create.title,
            "description": create.description,
            "status": TaskStatus.PENDING.value,
            "priority": create.priority.value,
            "dependencies": create.dependencies,
        }
        raw_tasks.append(new_task_raw)

        if isinstance(data, dict):
            data["tasks"] = raw_tasks
        else:
            data = {"tasks": raw_tasks}
        self._save_raw(data)
        return self._parse_task(new_task_raw)

    def delete_task(self, task_id: str | int) -> bool:
        """Delete a task by ID."""
        data = self._load_raw()
        raw_tasks = data.get("tasks", data if isinstance(data, list) else [])

        original_len = len(raw_tasks)
        raw_tasks = [
            t for t in raw_tasks
            if str(t.get("id", t.get("task_id", ""))) != str(task_id)
        ]

        if len(raw_tasks) == original_len:
            return False

        if isinstance(data, dict) and "tasks" in data:
            data["tasks"] = raw_tasks
        else:
            data = {"tasks": raw_tasks}
        self._save_raw(data)
        return True

    @property
    def tasks_file_path(self) -> str:
        """Get the path to the tasks file."""
        return str(self._tasks_file) if self._tasks_file else ""
