"""System performance monitoring using psutil and nvidia-smi."""

from __future__ import annotations

import logging
import shutil
import subprocess
import time
from collections import deque
from datetime import datetime
from typing import TYPE_CHECKING

import psutil

from .models import (
    CpuMetrics,
    DiskMetrics,
    GpuMetrics,
    MemoryMetrics,
    MetricsHistory,
    ProcessInfo,
    SystemMetrics,
)

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

# History length: 3600 samples at 1s interval = 60 minutes
MAX_HISTORY = 3600


class SystemMonitor:
    """Collects and stores system performance metrics."""

    def __init__(self) -> None:
        self._history: deque[SystemMetrics] = deque(maxlen=MAX_HISTORY)
        self._prev_disk_io: tuple[int, int] | None = None
        self._prev_disk_time: float | None = None
        self._gpu_available = False
        self._try_init_gpu()

    def _try_init_gpu(self) -> None:
        """Try to initialize GPU monitoring via nvidia-smi."""
        if shutil.which("nvidia-smi"):
            try:
                result = subprocess.run(
                    ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
                    capture_output=True, text=True, timeout=5,
                )
                if result.returncode == 0 and result.stdout.strip():
                    self._gpu_available = True
                    logger.info("GPU monitoring enabled (nvidia-smi): %s", result.stdout.strip())
                    return
            except Exception as exc:
                logger.warning("nvidia-smi failed: %s", exc)
        logger.info("No NVIDIA GPU detected via nvidia-smi, GPU monitoring disabled")

    def collect_cpu(self) -> CpuMetrics:
        """Collect CPU metrics."""
        freq = psutil.cpu_freq()
        temp = None
        try:
            temps = psutil.sensors_temperatures()
            if temps:
                # Try common sensor names
                for key in ("coretemp", "k10temp", "cpu_thermal", "cpu-thermal"):
                    if key in temps and temps[key]:
                        temp = temps[key][0].current
                        break
                # Fallback: use first available
                if temp is None:
                    first_key = next(iter(temps))
                    if temps[first_key]:
                        temp = temps[first_key][0].current
        except (AttributeError, StopIteration):
            pass

        return CpuMetrics(
            percent=psutil.cpu_percent(interval=0),
            per_core=psutil.cpu_percent(interval=0, percpu=True),
            frequency_mhz=freq.current if freq else None,
            temperature_c=temp,
            core_count=psutil.cpu_count(logical=False) or 0,
            thread_count=psutil.cpu_count(logical=True) or 0,
        )

    def collect_memory(self) -> MemoryMetrics:
        """Collect memory metrics."""
        vm = psutil.virtual_memory()
        sw = psutil.swap_memory()
        return MemoryMetrics(
            total_gb=round(vm.total / (1024**3), 2),
            used_gb=round(vm.used / (1024**3), 2),
            available_gb=round(vm.available / (1024**3), 2),
            percent=vm.percent,
            swap_total_gb=round(sw.total / (1024**3), 2),
            swap_used_gb=round(sw.used / (1024**3), 2),
            swap_percent=sw.percent,
        )

    def collect_gpu(self) -> GpuMetrics:
        """Collect GPU metrics via nvidia-smi (no GPUtil dependency)."""
        if not self._gpu_available:
            return GpuMetrics(available=False)
        try:
            result = subprocess.run(
                [
                    "nvidia-smi",
                    "--query-gpu=name,utilization.gpu,memory.total,memory.used,temperature.gpu",
                    "--format=csv,noheader,nounits",
                ],
                capture_output=True, text=True, timeout=5,
            )
            if result.returncode != 0:
                return GpuMetrics(available=False)
            parts = [p.strip() for p in result.stdout.strip().split(",")]
            if len(parts) < 5:
                return GpuMetrics(available=False)
            name = parts[0]
            load = float(parts[1]) if parts[1] not in ("[N/A]", "") else 0.0
            mem_total = float(parts[2]) if parts[2] not in ("[N/A]", "") else 0.0
            mem_used = float(parts[3]) if parts[3] not in ("[N/A]", "") else 0.0
            temp = float(parts[4]) if parts[4] not in ("[N/A]", "") else None
            mem_pct = (mem_used / mem_total * 100) if mem_total > 0 else 0.0
            return GpuMetrics(
                name=name,
                load_percent=round(load, 1),
                memory_total_mb=round(mem_total, 1),
                memory_used_mb=round(mem_used, 1),
                memory_percent=round(mem_pct, 1),
                temperature_c=temp,
                available=True,
            )
        except Exception as exc:
            logger.debug("GPU collection error: %s", exc)
            return GpuMetrics(available=False)

    def collect_disk(self) -> DiskMetrics:
        """Collect disk metrics with I/O rates."""
        usage = psutil.disk_usage("/")
        now = time.time()
        read_rate = 0.0
        write_rate = 0.0

        try:
            dio = psutil.disk_io_counters()
            if dio and self._prev_disk_io and self._prev_disk_time:
                dt = now - self._prev_disk_time
                if dt > 0:
                    read_rate = (dio.read_bytes - self._prev_disk_io[0]) / dt
                    write_rate = (dio.write_bytes - self._prev_disk_io[1]) / dt
            if dio:
                self._prev_disk_io = (dio.read_bytes, dio.write_bytes)
                self._prev_disk_time = now
        except (AttributeError, RuntimeError):
            pass

        return DiskMetrics(
            total_gb=round(usage.total / (1024**3), 2),
            used_gb=round(usage.used / (1024**3), 2),
            free_gb=round(usage.free / (1024**3), 2),
            percent=usage.percent,
            read_bytes_sec=round(read_rate, 0),
            write_bytes_sec=round(write_rate, 0),
        )

    def collect(self) -> SystemMetrics:
        """Collect all system metrics and store in history."""
        metrics = SystemMetrics(
            timestamp=datetime.now(),
            cpu=self.collect_cpu(),
            memory=self.collect_memory(),
            gpu=self.collect_gpu(),
            disk=self.collect_disk(),
            uptime_seconds=time.time() - psutil.boot_time(),
        )
        self._history.append(metrics)
        return metrics

    def get_history(self, seconds: int = 300) -> MetricsHistory:
        """Get metrics history for the specified time window.

        Args:
            seconds: Number of seconds of history to return (default 300 = 5 min).
        """
        cutoff = datetime.now().timestamp() - seconds
        timestamps: list[str] = []
        cpu: list[float] = []
        memory: list[float] = []
        gpu: list[float] = []
        disk_read: list[float] = []
        disk_write: list[float] = []

        for m in self._history:
            if m.timestamp.timestamp() >= cutoff:
                timestamps.append(m.timestamp.strftime("%H:%M:%S"))
                cpu.append(m.cpu.percent)
                memory.append(m.memory.percent)
                gpu.append(m.gpu.load_percent)
                disk_read.append(m.disk.read_bytes_sec)
                disk_write.append(m.disk.write_bytes_sec)

        return MetricsHistory(
            timestamps=timestamps,
            cpu=cpu,
            memory=memory,
            gpu=gpu,
            disk_read=disk_read,
            disk_write=disk_write,
        )

    def get_process_info(self, pid: int) -> ProcessInfo | None:
        """Get info about a specific process."""
        try:
            proc = psutil.Process(pid)
            with proc.oneshot():
                return ProcessInfo(
                    pid=proc.pid,
                    name=proc.name(),
                    cpu_percent=proc.cpu_percent(),
                    memory_mb=round(proc.memory_info().rss / (1024**2), 1),
                    status=proc.status(),
                    create_time=datetime.fromtimestamp(proc.create_time()),
                    command=" ".join(proc.cmdline()),
                )
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return None

    def list_ralph_processes(self) -> list[ProcessInfo]:
        """Find all running ralph-tui processes."""
        results = []
        for proc in psutil.process_iter(["pid", "name", "cmdline"]):
            try:
                cmdline = " ".join(proc.info.get("cmdline") or [])
                if "ralph-tui" in cmdline or "ralph_tui" in cmdline:
                    info = self.get_process_info(proc.pid)
                    if info:
                        results.append(info)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return results
