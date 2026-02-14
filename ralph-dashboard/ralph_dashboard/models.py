"""Pydantic models for Ralph Dashboard API."""

from __future__ import annotations

import enum
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


# --- System Metrics ---

class CpuMetrics(BaseModel):
    percent: float = Field(description="Overall CPU usage percentage")
    per_core: list[float] = Field(default_factory=list, description="Per-core usage percentages")
    frequency_mhz: float | None = None
    temperature_c: float | None = None
    core_count: int = 0
    thread_count: int = 0


class MemoryMetrics(BaseModel):
    total_gb: float = 0.0
    used_gb: float = 0.0
    available_gb: float = 0.0
    percent: float = 0.0
    swap_total_gb: float = 0.0
    swap_used_gb: float = 0.0
    swap_percent: float = 0.0


class GpuMetrics(BaseModel):
    name: str = "N/A"
    load_percent: float = 0.0
    memory_total_mb: float = 0.0
    memory_used_mb: float = 0.0
    memory_percent: float = 0.0
    temperature_c: float | None = None
    available: bool = False


class DiskMetrics(BaseModel):
    total_gb: float = 0.0
    used_gb: float = 0.0
    free_gb: float = 0.0
    percent: float = 0.0
    read_bytes_sec: float = 0.0
    write_bytes_sec: float = 0.0


class SystemMetrics(BaseModel):
    timestamp: datetime = Field(default_factory=datetime.now)
    cpu: CpuMetrics = Field(default_factory=CpuMetrics)
    memory: MemoryMetrics = Field(default_factory=MemoryMetrics)
    gpu: GpuMetrics = Field(default_factory=GpuMetrics)
    disk: DiskMetrics = Field(default_factory=DiskMetrics)
    uptime_seconds: float = 0.0


class ProcessInfo(BaseModel):
    pid: int
    name: str = ""
    cpu_percent: float = 0.0
    memory_mb: float = 0.0
    status: str = ""
    create_time: datetime | None = None
    command: str = ""


# --- Project Management ---

class ProjectStatus(str, enum.Enum):
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    ERROR = "error"
    COMPLETED = "completed"


class ProjectConfig(BaseModel):
    issue_tracker: str = "json"
    agent: str = "opencode"
    model: str = "qwen2.5-coder:7b"
    max_iterations: int = 50
    headless: bool = False
    project_dir: str = ""
    raw_toml: str = ""


class Project(BaseModel):
    name: str
    path: str
    status: ProjectStatus = ProjectStatus.IDLE
    config: ProjectConfig = Field(default_factory=ProjectConfig)
    pid: int | None = None
    last_activity: datetime | None = None
    task_count: int = 0
    completed_tasks: int = 0


class LaunchOptions(BaseModel):
    max_iterations: int = 50
    headless: bool = False
    model: str | None = None
    agent: str | None = None


# --- Task Management ---

class TaskStatus(str, enum.Enum):
    PENDING = "pending"
    IN_PROGRESS = "in-progress"
    COMPLETED = "completed"
    BLOCKED = "blocked"
    CANCELLED = "cancelled"
    DEFERRED = "deferred"


class TaskPriority(str, enum.Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class Task(BaseModel):
    id: str | int
    title: str
    description: str = ""
    status: TaskStatus = TaskStatus.PENDING
    priority: TaskPriority = TaskPriority.MEDIUM
    dependencies: list[str | int] = Field(default_factory=list)
    subtasks: list[Task] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class TaskUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    status: TaskStatus | None = None
    priority: TaskPriority | None = None
    dependencies: list[str | int] | None = None


class TaskCreate(BaseModel):
    title: str
    description: str = ""
    priority: TaskPriority = TaskPriority.MEDIUM
    dependencies: list[str | int] = Field(default_factory=list)


# --- Log Management ---

class LogLevel(str, enum.Enum):
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class LogEntry(BaseModel):
    timestamp: datetime | None = None
    level: LogLevel = LogLevel.INFO
    message: str = ""
    source: str = ""
    line_number: int = 0


class LogFilter(BaseModel):
    keyword: str | None = None
    level: LogLevel | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None


# --- Dashboard Config ---

class DashboardConfig(BaseModel):
    ralph_tui_command: str = "ralph-tui"
    projects_dir: str = "~/Projects"
    refresh_interval_ms: int = 1000
    theme: str = "dark"
    log_max_lines: int = 10000
    host: str = "127.0.0.1"
    port: int = 8420
    alert_cpu_threshold: float = 90.0
    alert_memory_threshold: float = 85.0
    alert_gpu_threshold: float = 95.0
    alert_disk_threshold: float = 90.0


# --- API Response Wrappers ---

class ApiResponse(BaseModel):
    success: bool = True
    message: str = ""
    data: Any = None


class MetricsHistory(BaseModel):
    timestamps: list[str] = Field(default_factory=list)
    cpu: list[float] = Field(default_factory=list)
    memory: list[float] = Field(default_factory=list)
    gpu: list[float] = Field(default_factory=list)
    disk_read: list[float] = Field(default_factory=list)
    disk_write: list[float] = Field(default_factory=list)


# --- Chat Models ---

class ChatMessage(BaseModel):
    role: str = Field(description="Message role: user, assistant, or system")
    content: str = Field(description="Message content")


class ChatRequest(BaseModel):
    model: str = "qwen2.5-coder:7b"
    messages: list[ChatMessage] = Field(default_factory=list)


class ProjectFromPrompt(BaseModel):
    name: str = Field(description="Project name (used as directory name)")
    prompt: str = Field(description="User prompt describing what to build")
    model: str = "qwen2.5-coder:7b"
    max_iterations: int = 50
