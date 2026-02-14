"""Tests for the task manager module."""

import json
import tempfile
from pathlib import Path

import pytest

from ralph_dashboard.models import TaskPriority, TaskStatus
from ralph_dashboard.task_manager import TaskManager


@pytest.fixture
def project_dir():
    with tempfile.TemporaryDirectory() as tmpdir:
        project = Path(tmpdir)
        # Create .ralph-tui dir
        (project / ".ralph-tui").mkdir()
        (project / ".ralph-tui" / "config.toml").write_text('[agent]\ntype = "opencode"\n')
        # Create tasks dir with sample tasks
        (project / "tasks").mkdir()
        tasks_data = {
            "tasks": [
                {
                    "id": 1,
                    "title": "Setup database",
                    "description": "Initialize the database schema",
                    "status": "completed",
                    "priority": "high",
                    "dependencies": [],
                },
                {
                    "id": 2,
                    "title": "Create auth module",
                    "description": "Implement user authentication",
                    "status": "in-progress",
                    "priority": "high",
                    "dependencies": [1],
                },
                {
                    "id": 3,
                    "title": "Build API endpoints",
                    "description": "REST API implementation",
                    "status": "pending",
                    "priority": "medium",
                    "dependencies": [1, 2],
                },
            ]
        }
        (project / "tasks" / "tasks.json").write_text(json.dumps(tasks_data, indent=2))
        yield project


class TestTaskManager:
    def test_list_tasks(self, project_dir):
        tm = TaskManager(project_dir)
        tasks = tm.list_tasks()
        assert len(tasks) == 3

    def test_task_parsing(self, project_dir):
        tm = TaskManager(project_dir)
        tasks = tm.list_tasks()
        t1 = tasks[0]
        assert t1.id == 1
        assert t1.title == "Setup database"
        assert t1.status == TaskStatus.COMPLETED
        assert t1.priority == TaskPriority.HIGH

    def test_task_dependencies(self, project_dir):
        tm = TaskManager(project_dir)
        tasks = tm.list_tasks()
        t3 = tasks[2]
        assert len(t3.dependencies) == 2
        assert 1 in t3.dependencies
        assert 2 in t3.dependencies

    def test_get_task(self, project_dir):
        tm = TaskManager(project_dir)
        task = tm.get_task(2)
        assert task is not None
        assert task.title == "Create auth module"

    def test_get_task_not_found(self, project_dir):
        tm = TaskManager(project_dir)
        task = tm.get_task(999)
        assert task is None

    def test_create_task(self, project_dir):
        tm = TaskManager(project_dir)
        from ralph_dashboard.models import TaskCreate
        new_task = tm.create_task(TaskCreate(
            title="New feature",
            description="A new feature",
            priority=TaskPriority.LOW,
            dependencies=[1],
        ))
        assert new_task.id == 4
        assert new_task.title == "New feature"

        # Verify persisted
        tasks = tm.list_tasks()
        assert len(tasks) == 4

    def test_update_task(self, project_dir):
        tm = TaskManager(project_dir)
        from ralph_dashboard.models import TaskUpdate
        updated = tm.update_task(2, TaskUpdate(status=TaskStatus.COMPLETED))
        assert updated is not None
        assert updated.status == TaskStatus.COMPLETED

        # Verify persisted
        task = tm.get_task(2)
        assert task.status == TaskStatus.COMPLETED

    def test_delete_task(self, project_dir):
        tm = TaskManager(project_dir)
        result = tm.delete_task(3)
        assert result is True
        tasks = tm.list_tasks()
        assert len(tasks) == 2

    def test_delete_nonexistent(self, project_dir):
        tm = TaskManager(project_dir)
        result = tm.delete_task(999)
        assert result is False

    def test_no_tasks_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tm = TaskManager(Path(tmpdir))
            tasks = tm.list_tasks()
            assert tasks == []
