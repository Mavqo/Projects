"""Tests for the Ralph-TUI integration module."""

import json
import tempfile
from pathlib import Path

from ralph_dashboard.ralph_integration import (
    build_run_command,
    build_resume_command,
    discover_projects,
    load_project_config,
    parse_toml_config,
)


class TestTomlParsing:
    def test_parse_simple(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            f.write('issue_tracker = "json"\nmax_iterations = 50\nheadless = true\n')
            f.flush()
            result = parse_toml_config(Path(f.name))
        assert result["issue_tracker"] == "json"
        assert result["max_iterations"] == 50
        assert result["headless"] is True

    def test_parse_sections(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            f.write('[agent]\ntype = "opencode"\nmodel = "qwen2.5-coder:7b"\n')
            f.flush()
            result = parse_toml_config(Path(f.name))
        assert "agent" in result
        assert result["agent"]["type"] == "opencode"
        assert result["agent"]["model"] == "qwen2.5-coder:7b"


class TestProjectDiscovery:
    def test_discover_projects(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            projects_dir = Path(tmpdir)

            # Create project with .ralph-tui
            p1 = projects_dir / "project-a"
            p1.mkdir()
            (p1 / ".ralph-tui").mkdir()
            (p1 / ".ralph-tui" / "config.toml").write_text('agent = "opencode"\n')

            # Create non-ralph project (should be ignored)
            p2 = projects_dir / "not-ralph"
            p2.mkdir()

            projects = discover_projects(projects_dir)
            assert len(projects) == 1
            assert projects[0].name == "project-a"

    def test_discover_empty_dir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            projects = discover_projects(Path(tmpdir))
            assert projects == []

    def test_discover_nonexistent_dir(self):
        projects = discover_projects(Path("/tmp/nonexistent_ralph_dir_12345"))
        assert projects == []


class TestProjectConfig:
    def test_load_config(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            (project / ".ralph-tui").mkdir()
            (project / ".ralph-tui" / "config.toml").write_text(
                'issue_tracker = "json"\nagent = "opencode"\nmodel = "qwen2.5-coder:7b"\n'
            )
            config = load_project_config(project)
            assert config.issue_tracker == "json"
            assert config.project_dir == str(project)

    def test_load_config_missing(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config = load_project_config(Path(tmpdir))
            assert config.project_dir == str(Path(tmpdir))


class TestCommandBuilding:
    def test_build_run_command(self):
        cmd = build_run_command("my-project", max_iterations=100, headless=True)
        assert "run" in cmd
        assert "--project" in cmd
        assert "my-project" in cmd
        assert "--max-iterations" in cmd
        assert "100" in cmd
        assert "--headless" in cmd

    def test_build_run_with_model(self):
        cmd = build_run_command("proj", model="qwen2.5-coder:7b")
        assert "--model" in cmd
        assert "qwen2.5-coder:7b" in cmd

    def test_build_resume_command(self):
        cmd = build_resume_command("my-project")
        assert "resume" in cmd
        assert "--project" in cmd
        assert "my-project" in cmd
