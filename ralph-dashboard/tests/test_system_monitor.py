"""Tests for the system monitoring module."""

from ralph_dashboard.system_monitor import SystemMonitor


class TestSystemMonitor:
    def setup_method(self):
        self.monitor = SystemMonitor()

    def test_collect_cpu(self):
        cpu = self.monitor.collect_cpu()
        assert 0 <= cpu.percent <= 100
        assert cpu.core_count >= 0
        assert cpu.thread_count >= 0
        assert isinstance(cpu.per_core, list)

    def test_collect_memory(self):
        mem = self.monitor.collect_memory()
        assert mem.total_gb > 0
        assert mem.used_gb >= 0
        assert mem.available_gb >= 0
        assert 0 <= mem.percent <= 100

    def test_collect_disk(self):
        disk = self.monitor.collect_disk()
        assert disk.total_gb > 0
        assert disk.used_gb >= 0
        assert disk.free_gb >= 0
        assert 0 <= disk.percent <= 100

    def test_collect_gpu(self):
        gpu = self.monitor.collect_gpu()
        # GPU may or may not be available
        assert isinstance(gpu.available, bool)

    def test_collect_all(self):
        metrics = self.monitor.collect()
        assert metrics.timestamp is not None
        assert metrics.cpu.percent >= 0
        assert metrics.memory.total_gb > 0
        assert metrics.disk.total_gb > 0

    def test_history(self):
        # Collect a few samples
        for _ in range(5):
            self.monitor.collect()
        history = self.monitor.get_history(seconds=3600)
        assert len(history.timestamps) >= 5
        assert len(history.cpu) == len(history.timestamps)
        assert len(history.memory) == len(history.timestamps)

    def test_list_ralph_processes(self):
        # Should return empty list (no ralph-tui running)
        procs = self.monitor.list_ralph_processes()
        assert isinstance(procs, list)
