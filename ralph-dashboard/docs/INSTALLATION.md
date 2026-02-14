# Ralph Dashboard - Installation Guide

## Prerequisites

- **Python 3.10+** (3.11 or 3.12 recommended)
- **pip** or **pipx** for package installation
- **Ralph-TUI** installed and configured (for full functionality)
- **Ollama** with a Qwen model pulled (for AI agent execution)

## Installation

### Option 1: Install from source (development)

```bash
# Clone or navigate to the ralph-dashboard directory
cd ralph-dashboard

# Create a virtual environment (recommended)
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate   # Windows

# Install in development mode
pip install -e ".[dev]"

# Optional: Install GPU monitoring support
pip install -e ".[gpu]"
```

### Option 2: Install from requirements.txt

```bash
cd ralph-dashboard
pip install -r requirements.txt

# Then run directly
python -m ralph_dashboard
```

### Option 3: pipx (isolated install)

```bash
pipx install ./ralph-dashboard
```

## Configuration

### Initial Setup

On first launch, Ralph Dashboard creates its config at `~/.ralph-dashboard/config.json`.

Default configuration:
```json
{
  "ralph_tui_command": "ralph-tui",
  "projects_dir": "~/Projects",
  "refresh_interval_ms": 1000,
  "theme": "dark",
  "log_max_lines": 10000,
  "host": "127.0.0.1",
  "port": 8420,
  "alert_cpu_threshold": 90.0,
  "alert_memory_threshold": 85.0,
  "alert_gpu_threshold": 95.0,
  "alert_disk_threshold": 90.0
}
```

### Connecting to Ralph-TUI

1. Ensure `ralph-tui` is in your PATH:
   ```bash
   which ralph-tui
   ralph-tui --help
   ```

2. Set `projects_dir` to match where your Ralph-TUI projects are:
   ```bash
   ralph-dashboard --projects-dir ~/Projects
   ```

3. Each project must have a `.ralph-tui/` directory to be detected.

## Running

### Start the dashboard

```bash
# Using the installed command
ralph-dashboard

# Or using Python module
python -m ralph_dashboard

# With custom options
ralph-dashboard --host 0.0.0.0 --port 8420 --projects-dir ~/Projects

# Development mode (auto-reload)
ralph-dashboard --reload --log-level debug
```

### Access the dashboard

Open your browser to: **http://127.0.0.1:8420**

## Verifying Installation

### Run the test suite

```bash
cd ralph-dashboard
pip install -e ".[dev]"
pytest tests/ -v
```

### Check system metrics

```bash
# The /api/system/metrics endpoint should return current metrics
curl http://127.0.0.1:8420/api/system/metrics | python -m json.tool
```

### Check project discovery

```bash
curl http://127.0.0.1:8420/api/projects | python -m json.tool
```

## Troubleshooting

### Dashboard won't start

- **Port in use**: Try `--port 8421` or kill the existing process
- **Module not found**: Ensure you installed with `pip install -e .`
- **Python version**: Verify `python --version` shows 3.10+

### No projects showing

- Verify `projects_dir` in config points to correct directory
- Each project needs a `.ralph-tui/` subdirectory
- Check file permissions

### ralph-tui not found

- Dashboard works without ralph-tui for monitoring and task management
- Launch/run features require ralph-tui to be installed and in PATH
- Install ralph-tui: `bun install -g ralph-tui`

### GPU metrics showing N/A

- Install GPU support: `pip install GPUtil`
- Ensure NVIDIA drivers are installed
- Check `nvidia-smi` works from terminal

### WebSocket disconnections

- Check for firewall/proxy blocking WebSocket connections
- Try accessing directly (not through reverse proxy)
- Check browser console for error messages
