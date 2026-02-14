# Ralph Dashboard - Architecture

## Technology Stack

| Layer      | Technology                     | Rationale                                    |
|------------|--------------------------------|----------------------------------------------|
| Backend    | FastAPI (Python 3.10+)         | Async, WebSocket support, auto-docs, typing  |
| Frontend   | Vanilla JS + CSS (no build)    | Zero build step, served by FastAPI directly   |
| Server     | Uvicorn                        | ASGI server for FastAPI                       |
| Monitoring | psutil + GPUtil (optional)     | Cross-platform system metrics                 |
| Real-time  | WebSocket (native)             | Low-latency metrics and log streaming         |
| Charts     | Canvas 2D API                  | Lightweight, no external chart library needed |

## System Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                        Browser (Frontend)                        │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────────────┐  │
│  │ Projects  │  │  Tasks   │  │   Logs   │  │  Performance   │  │
│  │ Sidebar   │  │  Panel   │  │  Panel   │  │  Metrics Panel │  │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └───────┬────────┘  │
│       │              │             │                 │           │
│       │    REST API (fetch)        │    WebSocket    │           │
└───────┼──────────────┼─────────────┼─────────────────┼───────────┘
        │              │             │                 │
┌───────┴──────────────┴─────────────┴─────────────────┴───────────┐
│                    FastAPI Application (app.py)                    │
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────────┐  │
│  │  REST Routes   │  │   WebSocket    │  │   Static Files     │  │
│  │  /api/*        │  │  /ws/metrics   │  │   /static/*        │  │
│  │                │  │  /ws/logs/*    │  │   / (index.html)   │  │
│  └───────┬────────┘  └───────┬────────┘  └────────────────────┘  │
└──────────┼───────────────────┼────────────────────────────────────┘
           │                   │
┌──────────┴───────────────────┴────────────────────────────────────┐
│                        Core Services                              │
│  ┌──────────────────┐  ┌──────────────────┐  ┌────────────────┐  │
│  │  SystemMonitor   │  │  ProcessManager  │  │  LogManager    │  │
│  │  (psutil/GPUtil) │  │  (subprocess)    │  │  (file watch)  │  │
│  └──────────────────┘  └──────────────────┘  └────────────────┘  │
│  ┌──────────────────┐  ┌──────────────────┐  ┌────────────────┐  │
│  │  TaskManager     │  │  RalphIntegration│  │  Config        │  │
│  │  (JSON tracker)  │  │  (CLI wrapper)   │  │  (TOML parser) │  │
│  └──────────────────┘  └──────────────────┘  └────────────────┘  │
└───────────────────────────────────────────────────────────────────┘
           │                        │
           ▼                        ▼
┌────────────────────┐  ┌───────────────────────┐
│   Ralph-TUI CLI    │  │   File System          │
│   (subprocess)     │  │   - .ralph-tui/        │
│                    │  │   - tasks/*.json       │
│   run, resume,     │  │   - logs/              │
│   status, logs     │  │   - config.toml        │
└────────────────────┘  └───────────────────────┘
```

## Component Responsibilities

### Backend Modules

| Module                | File                    | Purpose                                       |
|-----------------------|-------------------------|-----------------------------------------------|
| Models                | `models.py`             | Pydantic data models for API and internal use  |
| Config                | `config.py`             | Dashboard config load/save                     |
| System Monitor        | `system_monitor.py`     | CPU, RAM, GPU, disk metrics collection         |
| Process Manager       | `process_manager.py`    | Launch/stop/pause Ralph-TUI subprocesses       |
| Ralph Integration     | `ralph_integration.py`  | CLI command building, config parsing, project discovery |
| Task Manager          | `task_manager.py`       | Read/write task tracker JSON files             |
| Log Manager           | `log_manager.py`        | Log buffering, file watching, streaming        |
| App                   | `app.py`                | FastAPI routes, WebSocket handlers, lifecycle  |
| Main                  | `__main__.py`           | CLI entry point                                |

### Frontend Modules

| Module          | File               | Purpose                              |
|-----------------|--------------------|--------------------------------------|
| API Client      | `js/api.js`        | REST API communication               |
| WebSocket       | `js/websocket.js`  | Real-time connection management      |
| App             | `js/app.js`        | Main orchestrator, state management  |
| Projects        | `js/projects.js`   | Project sidebar and actions          |
| Tasks           | `js/tasks.js`      | Task table, CRUD, dependency tree    |
| Logs            | `js/logs.js`       | Log viewer, streaming, export        |
| Performance     | `js/performance.js`| Metrics display, mini charts         |
| Config          | `js/config.js`     | Config editor                        |

## Data Flow

### Metrics Streaming
1. `SystemMonitor.collect()` runs every N ms (configurable)
2. Metrics stored in circular buffer (deque, max 3600 samples)
3. Serialized to JSON and broadcast to all `/ws/metrics` WebSocket clients
4. Frontend `Performance` module updates DOM and redraws charts

### Log Streaming
1. `ProcessManager` captures stdout/stderr from Ralph-TUI subprocesses
2. Lines forwarded to `LogManager.add_line(project, line)`
3. `LogFileWatcher` threads also tail log files on disk
4. `LogBuffer` stores lines in thread-safe deque
5. `/ws/logs/{project}` WebSocket polls buffer for new lines every 300ms
6. Frontend `Logs` module appends lines to log viewer DOM

### Project Lifecycle
1. User clicks "Launch" → REST `POST /api/projects/{name}/launch`
2. Backend builds CLI command via `ralph_integration.build_run_command()`
3. `ProcessManager.launch()` starts subprocess with stdout/stderr pipes
4. Output captured by reader threads → forwarded to `LogManager`
5. Process status tracked; exit code captured on completion
6. Frontend polls project list or receives WebSocket updates

## File Structure

```
ralph-dashboard/
├── pyproject.toml              # Package configuration
├── requirements.txt            # Dependencies
├── ralph_dashboard/
│   ├── __init__.py
│   ├── __main__.py             # CLI entry point
│   ├── app.py                  # FastAPI application
│   ├── config.py               # Dashboard config management
│   ├── models.py               # Pydantic models
│   ├── system_monitor.py       # System metrics collection
│   ├── process_manager.py      # Subprocess management
│   ├── ralph_integration.py    # Ralph-TUI CLI wrapper
│   ├── task_manager.py         # Task tracker file management
│   ├── log_manager.py          # Log buffering and streaming
│   └── static/
│       ├── index.html          # Main dashboard HTML
│       ├── css/style.css       # Styles with dark/light themes
│       └── js/
│           ├── api.js          # REST API client
│           ├── websocket.js    # WebSocket manager
│           ├── app.js          # Main app orchestrator
│           ├── projects.js     # Project management UI
│           ├── tasks.js        # Task management UI
│           ├── logs.js         # Log viewer UI
│           ├── performance.js  # Metrics display UI
│           └── config.js       # Config editor UI
├── tests/
│   ├── test_system_monitor.py
│   ├── test_task_manager.py
│   ├── test_ralph_integration.py
│   └── test_api.py
└── docs/
    ├── ARCHITECTURE.md
    ├── INSTALLATION.md
    └── USAGE.md
```
