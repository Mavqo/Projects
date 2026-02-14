"""FastAPI application for Ralph Dashboard."""

from __future__ import annotations

import asyncio
import json
import logging
import shutil
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from . import __version__
from .config import get_projects_dir, load_config, save_config
from .log_manager import ProjectLogManager
from .models import (
    ApiResponse,
    DashboardConfig,
    LaunchOptions,
    ProjectStatus,
    TaskCreate,
    TaskUpdate,
)
from .process_manager import ProcessManager
from .ralph_integration import (
    build_run_command,
    build_resume_command,
    discover_projects,
    find_log_files,
    is_ralph_tui_available,
    load_project_config,
    save_project_config,
)
from .system_monitor import SystemMonitor

logger = logging.getLogger(__name__)

# Global state
config = load_config()
monitor = SystemMonitor()
process_mgr = ProcessManager()
log_mgr = ProjectLogManager(max_lines=config.log_max_lines)

# Wire process output to log buffers
process_mgr.on_output(lambda project, line: log_mgr.add_line(project, line))

# WebSocket connection sets
ws_metrics_clients: set[WebSocket] = set()
ws_log_clients: dict[str, set[WebSocket]] = {}

# Background task handle
_metrics_task: asyncio.Task | None = None


async def broadcast_metrics() -> None:
    """Background task: collect and broadcast system metrics."""
    while True:
        try:
            metrics = monitor.collect()
            data = json.dumps({
                "type": "metrics",
                "data": metrics.model_dump(mode="json"),
            })
            dead: list[WebSocket] = []
            for ws in ws_metrics_clients:
                try:
                    await ws.send_text(data)
                except Exception:
                    dead.append(ws)
            for ws in dead:
                ws_metrics_clients.discard(ws)
        except Exception as exc:
            logger.debug("Metrics broadcast error: %s", exc)
        await asyncio.sleep(config.refresh_interval_ms / 1000)


async def broadcast_logs(project: str) -> None:
    """Send new log lines to subscribed WebSocket clients."""
    clients = ws_log_clients.get(project, set())
    if not clients:
        return
    buffer = log_mgr.get_buffer(project)
    lines = buffer.get_recent(1)
    if not lines:
        return
    data = json.dumps({"type": "log", "project": project, "lines": lines})
    dead: list[WebSocket] = []
    for ws in clients:
        try:
            await ws.send_text(data)
        except Exception:
            dead.append(ws)
    for ws in dead:
        clients.discard(ws)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown."""
    global _metrics_task
    logger.info("Ralph Dashboard v%s starting up", __version__)
    # Start metrics broadcast
    _metrics_task = asyncio.create_task(broadcast_metrics())
    # Initial CPU measurement (first call returns 0)
    monitor.collect()
    yield
    # Shutdown
    logger.info("Ralph Dashboard shutting down")
    if _metrics_task:
        _metrics_task.cancel()
    process_mgr.shutdown_all()
    log_mgr.shutdown()


app = FastAPI(
    title="Ralph Dashboard",
    version=__version__,
    description="GUI Dashboard for Ralph-TUI AI Agent Orchestrator",
    lifespan=lifespan,
)

# Mount static files
STATIC_DIR = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


# --- HTML Entry Point ---

@app.get("/", response_class=HTMLResponse)
async def index():
    """Serve the main dashboard HTML."""
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file), media_type="text/html")
    return HTMLResponse("<h1>Ralph Dashboard</h1><p>Static files not found.</p>")


# --- System Endpoints ---

@app.get("/api/system/status")
async def system_status():
    """Get overall system status."""
    return ApiResponse(data={
        "version": __version__,
        "ralph_tui_available": is_ralph_tui_available(),
        "active_processes": len(process_mgr.list_active()),
        "uptime": monitor.collect().uptime_seconds,
        "timestamp": datetime.now().isoformat(),
    })


@app.get("/api/system/metrics")
async def system_metrics():
    """Get current system metrics."""
    return monitor.collect()


@app.get("/api/system/metrics/history")
async def metrics_history(seconds: int = Query(default=300, ge=60, le=3600)):
    """Get historical metrics for the given time window."""
    return monitor.get_history(seconds)


@app.get("/api/system/processes")
async def ralph_processes():
    """List all detected ralph-tui processes."""
    return monitor.list_ralph_processes()


# --- Configuration Endpoints ---

@app.get("/api/config")
async def get_config():
    """Get dashboard configuration."""
    return config


@app.put("/api/config")
async def update_config(new_config: DashboardConfig):
    """Update dashboard configuration."""
    global config
    config = new_config
    save_config(config)
    return ApiResponse(message="Configuration updated")


# --- Project Endpoints ---

@app.get("/api/projects")
async def list_projects():
    """List all Ralph-TUI projects."""
    projects_dir = get_projects_dir(config)
    projects = discover_projects(projects_dir)
    # Update statuses from process manager
    for proj in projects:
        status = process_mgr.get_status(proj.name)
        if status != ProjectStatus.IDLE:
            proj.status = status
            proc = process_mgr.get_process(proj.name)
            if proc:
                proj.pid = proc.pid
    return projects


@app.get("/api/projects/{name}")
async def get_project(name: str):
    """Get details about a specific project."""
    projects_dir = get_projects_dir(config)
    project_path = projects_dir / name
    if not project_path.exists() or not (project_path / ".ralph-tui").exists():
        raise HTTPException(404, f"Project '{name}' not found")

    proj_config = load_project_config(project_path)
    status = process_mgr.get_status(name)
    proc = process_mgr.get_process(name)

    from .task_manager import TaskManager
    tm = TaskManager(project_path)
    tasks = tm.list_tasks()

    return {
        "name": name,
        "path": str(project_path),
        "status": status.value,
        "config": proj_config.model_dump(),
        "pid": proc.pid if proc else None,
        "task_count": len(tasks),
        "completed_tasks": sum(1 for t in tasks if t.status.value == "completed"),
        "log_files": [str(f) for f in find_log_files(project_path)],
    }


@app.post("/api/projects/{name}/launch")
async def launch_project(name: str, options: LaunchOptions | None = None):
    """Launch a Ralph-TUI execution loop for a project."""
    if not is_ralph_tui_available():
        raise HTTPException(503, "ralph-tui is not installed or not in PATH")

    projects_dir = get_projects_dir(config)
    project_path = projects_dir / name
    if not project_path.exists():
        raise HTTPException(404, f"Project '{name}' not found")

    opts = options or LaunchOptions()
    # Always force headless when launching from the dashboard -
    # Ralph-TUI's own TUI interface cannot work inside a subprocess pipe
    cmd = build_run_command(
        project_name=name,
        max_iterations=opts.max_iterations,
        headless=True,
        model=opts.model,
        agent=opts.agent,
    )

    proc = process_mgr.launch(name, cmd, project_path)

    # Start watching log files
    for log_file in find_log_files(project_path):
        log_mgr.watch_file(name, log_file)

    return ApiResponse(
        message=f"Project '{name}' launched (PID: {proc.pid})",
        data={"pid": proc.pid, "command": " ".join(cmd)},
    )


@app.post("/api/projects/{name}/stop")
async def stop_project(name: str):
    """Stop a running project."""
    if process_mgr.stop(name):
        log_mgr.stop_watchers(name)
        return ApiResponse(message=f"Project '{name}' stopped")
    raise HTTPException(400, f"Project '{name}' is not running")


@app.post("/api/projects/{name}/pause")
async def pause_project(name: str):
    """Pause a running project."""
    if process_mgr.pause(name):
        return ApiResponse(message=f"Project '{name}' paused")
    raise HTTPException(400, f"Project '{name}' is not running")


@app.post("/api/projects/{name}/resume")
async def resume_project(name: str):
    """Resume a paused project."""
    if process_mgr.resume(name):
        return ApiResponse(message=f"Project '{name}' resumed")

    # If not paused, try ralph-tui resume command
    if is_ralph_tui_available():
        projects_dir = get_projects_dir(config)
        project_path = projects_dir / name
        cmd = build_resume_command(name)
        proc = process_mgr.launch(name, cmd, project_path)
        return ApiResponse(
            message=f"Project '{name}' resumed via ralph-tui (PID: {proc.pid})",
            data={"pid": proc.pid},
        )

    raise HTTPException(400, f"Project '{name}' is not paused")


@app.delete("/api/projects/{name}")
async def delete_project(name: str, confirm: bool = Query(default=False)):
    """Delete a project directory."""
    if not confirm:
        raise HTTPException(400, "Must confirm deletion with ?confirm=true")

    projects_dir = get_projects_dir(config)
    project_path = projects_dir / name
    if not project_path.exists():
        raise HTTPException(404, f"Project '{name}' not found")

    # Stop if running
    process_mgr.stop(name)
    log_mgr.stop_watchers(name)

    shutil.rmtree(project_path)
    return ApiResponse(message=f"Project '{name}' deleted")


@app.get("/api/projects/{name}/config")
async def get_project_config(name: str):
    """Get a project's Ralph-TUI configuration."""
    projects_dir = get_projects_dir(config)
    project_path = projects_dir / name
    if not project_path.exists():
        raise HTTPException(404, f"Project '{name}' not found")
    return load_project_config(project_path)


@app.put("/api/projects/{name}/config")
async def update_project_config(name: str, raw_toml: str):
    """Update a project's Ralph-TUI configuration (raw TOML)."""
    projects_dir = get_projects_dir(config)
    project_path = projects_dir / name
    if not project_path.exists():
        raise HTTPException(404, f"Project '{name}' not found")
    save_project_config(project_path, raw_toml)
    return ApiResponse(message="Configuration updated")


# --- Task Endpoints ---

@app.get("/api/projects/{name}/tasks")
async def list_tasks(name: str):
    """List all tasks for a project."""
    from .task_manager import TaskManager
    projects_dir = get_projects_dir(config)
    project_path = projects_dir / name
    if not project_path.exists():
        raise HTTPException(404, f"Project '{name}' not found")
    tm = TaskManager(project_path)
    return tm.list_tasks()


@app.get("/api/projects/{name}/tasks/{task_id}")
async def get_task(name: str, task_id: str):
    """Get a specific task."""
    from .task_manager import TaskManager
    projects_dir = get_projects_dir(config)
    tm = TaskManager(projects_dir / name)
    task = tm.get_task(task_id)
    if not task:
        raise HTTPException(404, f"Task '{task_id}' not found")
    return task


@app.put("/api/projects/{name}/tasks/{task_id}")
async def update_task(name: str, task_id: str, update: TaskUpdate):
    """Update a task."""
    from .task_manager import TaskManager
    projects_dir = get_projects_dir(config)
    tm = TaskManager(projects_dir / name)
    task = tm.update_task(task_id, update)
    if not task:
        raise HTTPException(404, f"Task '{task_id}' not found")
    return task


@app.post("/api/projects/{name}/tasks")
async def create_task(name: str, create: TaskCreate):
    """Create a new task."""
    from .task_manager import TaskManager
    projects_dir = get_projects_dir(config)
    project_path = projects_dir / name
    if not project_path.exists():
        raise HTTPException(404, f"Project '{name}' not found")
    tm = TaskManager(project_path)
    return tm.create_task(create)


@app.delete("/api/projects/{name}/tasks/{task_id}")
async def delete_task(name: str, task_id: str):
    """Delete a task."""
    from .task_manager import TaskManager
    projects_dir = get_projects_dir(config)
    tm = TaskManager(projects_dir / name)
    if tm.delete_task(task_id):
        return ApiResponse(message=f"Task '{task_id}' deleted")
    raise HTTPException(404, f"Task '{task_id}' not found")


# --- Log Endpoints ---

@app.get("/api/projects/{name}/logs")
async def get_logs(
    name: str,
    count: int = Query(default=200, ge=1, le=10000),
    keyword: str | None = None,
    level: str | None = None,
):
    """Get log lines for a project."""
    from .models import LogLevel
    log_level = None
    if level:
        try:
            log_level = LogLevel(level.lower())
        except ValueError:
            pass
    lines = log_mgr.get_logs(name, count=count, keyword=keyword, level=log_level)
    return {"project": name, "count": len(lines), "lines": lines}


@app.get("/api/projects/{name}/log-files")
async def list_log_files(name: str):
    """List available log files for a project."""
    projects_dir = get_projects_dir(config)
    project_path = projects_dir / name
    if not project_path.exists():
        raise HTTPException(404, f"Project '{name}' not found")
    files = find_log_files(project_path)
    return [{"path": str(f), "name": f.name, "size": f.stat().st_size} for f in files]


@app.get("/api/projects/{name}/log-files/read")
async def read_log_file(
    name: str,
    path: str,
    max_lines: int = Query(default=1000, ge=1, le=50000),
    offset: int = Query(default=0, ge=0),
):
    """Read contents of a specific log file."""
    file_path = Path(path)
    if not file_path.exists():
        raise HTTPException(404, "Log file not found")
    # Security: ensure file is within project directory
    projects_dir = get_projects_dir(config)
    try:
        file_path.resolve().relative_to(projects_dir.resolve())
    except ValueError:
        raise HTTPException(403, "Access denied: file outside projects directory")
    lines = log_mgr.read_log_file(file_path, max_lines=max_lines, offset=offset)
    return {"path": str(file_path), "count": len(lines), "offset": offset, "lines": lines}


@app.post("/api/projects/{name}/logs/clear")
async def clear_logs(name: str):
    """Clear the log buffer for a project (doesn't delete files)."""
    log_mgr.clear_buffer(name)
    return ApiResponse(message=f"Log buffer cleared for '{name}'")


# --- WebSocket Endpoints ---

@app.websocket("/ws/metrics")
async def ws_metrics(websocket: WebSocket):
    """WebSocket: real-time system metrics stream."""
    await websocket.accept()
    ws_metrics_clients.add(websocket)
    try:
        while True:
            # Keep connection alive, listen for commands
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text(json.dumps({"type": "pong"}))
    except WebSocketDisconnect:
        pass
    finally:
        ws_metrics_clients.discard(websocket)


@app.websocket("/ws/logs/{project}")
async def ws_logs(websocket: WebSocket, project: str):
    """WebSocket: real-time log streaming for a project."""
    await websocket.accept()
    clients = ws_log_clients.setdefault(project, set())
    clients.add(websocket)

    # Send existing buffer
    existing = log_mgr.get_logs(project, count=200)
    if existing:
        await websocket.send_text(json.dumps({
            "type": "log_history",
            "project": project,
            "lines": existing,
        }))

    try:
        buffer = log_mgr.get_buffer(project)
        last_count = buffer.count
        while True:
            await asyncio.sleep(0.3)
            current_count = buffer.count
            if current_count > last_count:
                new_lines = buffer.get_recent(current_count - last_count)
                last_count = current_count
                await websocket.send_text(json.dumps({
                    "type": "log",
                    "project": project,
                    "lines": new_lines,
                }))
    except WebSocketDisconnect:
        pass
    finally:
        clients.discard(websocket)
