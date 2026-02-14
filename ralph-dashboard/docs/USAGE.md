# Ralph Dashboard - Usage Guide

## Dashboard Layout

The dashboard uses a three-column layout:

```
┌───────────────────────────────────────────────────────────┐
│                       Header Bar                          │
├──────────┬──────────────────────────────┬─────────────────┤
│          │        Tab Bar               │                 │
│ Projects │ ┌──────────────────────────┐ │  System Metrics │
│ Sidebar  │ │                          │ │  - CPU          │
│          │ │   Main Content Area      │ │  - Memory       │
│ - proj1  │ │   (Tasks / Logs / Config)│ │  - GPU          │
│ - proj2  │ │                          │ │  - Disk         │
│ - proj3  │ │                          │ │                 │
│          │ └──────────────────────────┘ │                 │
│ [Launch] │                              │                 │
├──────────┴──────────────────────────────┴─────────────────┤
│                       Status Bar                          │
└───────────────────────────────────────────────────────────┘
```

## Project Management

### Viewing Projects

The left sidebar lists all detected Ralph-TUI projects. Each project shows:
- Project name
- Task progress (completed/total)
- Status indicator (colored dot):
  - Gray = Idle
  - Green (pulsing) = Running
  - Yellow = Paused
  - Red = Error
  - Blue = Completed

Click a project to select it and load its data.

### Launching a Project

1. Select a project in the sidebar
2. Click the **Launch** button
3. Configure launch options in the modal:
   - **Model**: AI model to use (default: qwen2.5-coder:7b)
   - **Max Iterations**: Maximum execution cycles (default: 50)
   - **Headless**: Run without interactive prompts
4. Click **Launch** to start execution

The dashboard will automatically switch to the Logs tab to show real-time output.

### Stopping/Pausing Projects

Use the buttons at the bottom of the sidebar:
- **Pause**: Suspend execution (SIGSTOP)
- **Resume**: Continue paused execution (SIGCONT)
- **Stop**: Terminate execution (SIGTERM, then SIGKILL)

## Task Management

### Viewing Tasks

The Tasks tab shows all tasks from the project's tracker file in a table with:
- ID, Title, Status, Priority, Dependencies, Actions

### Filtering Tasks

Use the toolbar above the task table:
- **Search box**: Filter by title, description, or ID
- **Status dropdown**: Filter by task status
- **Priority dropdown**: Filter by priority level

### Adding Tasks

1. Click **+ Add Task**
2. Fill in the form:
   - Title (required)
   - Description
   - Priority (High/Medium/Low)
   - Dependencies (comma-separated task IDs)
3. Click **Create Task**

### Editing Tasks

Click the pencil icon on any task row to open the edit modal.
You can change title, description, status, priority, and dependencies.

### Marking Tasks Complete

Click the checkmark icon to toggle a task between completed and pending.

### Dependency Tree

Click **Dependency Tree** to view a visual tree of task dependencies:
- Root tasks (no dependencies) appear at the top
- Dependent tasks are indented below their parents
- Status icons show completion state

## Log Viewer

### Real-time Streaming

When you select a project and switch to the Logs tab, the dashboard connects
via WebSocket to stream logs in real-time.

### Features

- **Auto-scroll**: Automatically follows new output (toggle with button)
- **Search**: Filter logs by keyword (press Enter to search)
- **Clear**: Clear the log view (does not delete log files)
- **Export TXT**: Download logs as plain text
- **Export JSON**: Download logs as structured JSON

### Log Highlighting

Log lines are color-coded by severity:
- Red: ERROR / CRITICAL
- Yellow: WARNING
- Gray: DEBUG
- White: INFO (default)

## Configuration Editor

The Config tab shows:
1. **Parsed Configuration**: Read-only summary of key settings
2. **TOML Editor**: Editable raw config.toml content

Click **Save** to write changes. Click **Revert** to discard edits.

## System Metrics

The right panel shows real-time system performance:

### CPU
- Overall usage percentage with color coding
- Per-core grid showing individual core loads
- Frequency and temperature (if available)
- 5-minute history chart

### Memory
- RAM usage percentage
- Used/Total GB breakdown
- Swap usage

### GPU
- Load percentage (requires GPUtil + NVIDIA GPU)
- VRAM usage
- Temperature
- Shows "N/A" if no GPU detected

### Disk
- Disk usage percentage
- Used/Total GB
- Read/Write I/O rates

### Color Coding
- Green: < 70% (healthy)
- Yellow: 70-90% (warning)
- Red: > 90% (critical)

## Theme

Click the moon/sun icon in the header to toggle between dark and light themes.
Your preference is saved in the browser.

## Keyboard Shortcuts

| Key            | Action                        |
|----------------|-------------------------------|
| Enter (in log search) | Execute search        |
| Escape         | Close modal dialogs           |

## API Endpoints

The dashboard exposes a RESTful API at `/api/`:

### System
| Method | Endpoint                        | Description                |
|--------|---------------------------------|----------------------------|
| GET    | `/api/system/status`            | Overall system status      |
| GET    | `/api/system/metrics`           | Current system metrics     |
| GET    | `/api/system/metrics/history`   | Historical metrics         |
| GET    | `/api/system/processes`         | Ralph-TUI processes        |

### Configuration
| Method | Endpoint        | Description              |
|--------|-----------------|--------------------------|
| GET    | `/api/config`   | Get dashboard config     |
| PUT    | `/api/config`   | Update dashboard config  |

### Projects
| Method | Endpoint                           | Description         |
|--------|------------------------------------|---------------------|
| GET    | `/api/projects`                    | List all projects   |
| GET    | `/api/projects/{name}`             | Project details     |
| POST   | `/api/projects/{name}/launch`      | Launch project      |
| POST   | `/api/projects/{name}/stop`        | Stop project        |
| POST   | `/api/projects/{name}/pause`       | Pause project       |
| POST   | `/api/projects/{name}/resume`      | Resume project      |
| DELETE | `/api/projects/{name}?confirm=true`| Delete project      |

### Tasks
| Method | Endpoint                                   | Description     |
|--------|--------------------------------------------|-----------------|
| GET    | `/api/projects/{name}/tasks`               | List tasks      |
| GET    | `/api/projects/{name}/tasks/{id}`          | Get task        |
| POST   | `/api/projects/{name}/tasks`               | Create task     |
| PUT    | `/api/projects/{name}/tasks/{id}`          | Update task     |
| DELETE | `/api/projects/{name}/tasks/{id}`          | Delete task     |

### Logs
| Method | Endpoint                                   | Description       |
|--------|--------------------------------------------|-------------------|
| GET    | `/api/projects/{name}/logs`                | Get log lines     |
| GET    | `/api/projects/{name}/log-files`           | List log files    |
| GET    | `/api/projects/{name}/log-files/read`      | Read log file     |
| POST   | `/api/projects/{name}/logs/clear`          | Clear log buffer  |

### WebSocket
| Endpoint                 | Description                    |
|--------------------------|--------------------------------|
| `/ws/metrics`            | Real-time system metrics       |
| `/ws/logs/{project}`     | Real-time log streaming        |

Interactive API docs available at: `http://127.0.0.1:8420/docs`
