/**
 * Ralph Dashboard - Performance Monitoring Module
 * Renders real-time system metrics and mini charts.
 */

const Performance = {
    _history: { timestamps: [], cpu: [], memory: [], gpu: [], disk_read: [], disk_write: [] },
    _canvases: {},

    updateMetrics(metrics) {
        if (!metrics) return;

        // CPU
        this._updateCard('cpu', {
            value: metrics.cpu?.percent ?? 0,
            unit: '%',
            sub: `${metrics.cpu?.core_count ?? 0} cores / ${metrics.cpu?.thread_count ?? 0} threads` +
                 (metrics.cpu?.frequency_mhz ? ` @ ${Math.round(metrics.cpu.frequency_mhz)} MHz` : '') +
                 (metrics.cpu?.temperature_c ? ` | ${metrics.cpu.temperature_c.toFixed(0)}°C` : ''),
        });

        // Memory
        const mem = metrics.memory || {};
        this._updateCard('memory', {
            value: mem.percent ?? 0,
            unit: '%',
            sub: `${mem.used_gb?.toFixed(1) ?? 0} / ${mem.total_gb?.toFixed(1) ?? 0} GB` +
                 (mem.swap_percent > 0 ? ` | Swap: ${mem.swap_percent.toFixed(0)}%` : ''),
        });

        // GPU
        const gpu = metrics.gpu || {};
        if (gpu.available) {
            this._updateCard('gpu', {
                value: gpu.load_percent ?? 0,
                unit: '%',
                sub: `${gpu.name}` +
                     ` | VRAM: ${gpu.memory_used_mb?.toFixed(0) ?? 0}/${gpu.memory_total_mb?.toFixed(0) ?? 0} MB` +
                     (gpu.temperature_c ? ` | ${gpu.temperature_c.toFixed(0)}°C` : ''),
            });
            document.getElementById('metric-gpu')?.classList.remove('hidden');
        } else {
            const gpuCard = document.getElementById('metric-gpu');
            if (gpuCard) {
                gpuCard.querySelector('.metric-value').textContent = 'N/A';
                gpuCard.querySelector('.metric-sub').textContent = 'No GPU detected';
                gpuCard.querySelector('.metric-bar-fill')?.style.setProperty('width', '0%');
            }
        }

        // Disk
        const disk = metrics.disk || {};
        this._updateCard('disk', {
            value: disk.percent ?? 0,
            unit: '%',
            sub: `${disk.used_gb?.toFixed(1) ?? 0} / ${disk.total_gb?.toFixed(1) ?? 0} GB` +
                 ` | R: ${this._formatBytes(disk.read_bytes_sec ?? 0)}/s` +
                 ` W: ${this._formatBytes(disk.write_bytes_sec ?? 0)}/s`,
        });

        // Per-core display
        if (metrics.cpu?.per_core?.length) {
            this._renderCoreGrid(metrics.cpu.per_core);
        }
    },

    _updateCard(name, { value, unit, sub }) {
        const card = document.getElementById(`metric-${name}`);
        if (!card) return;

        const valueEl = card.querySelector('.metric-value');
        const subEl = card.querySelector('.metric-sub');
        const barFill = card.querySelector('.metric-bar-fill');

        const rounded = Math.round(value);
        if (valueEl) {
            valueEl.textContent = `${rounded}${unit}`;
            valueEl.className = `metric-value ${this._getLevel(rounded)}`;
        }
        if (subEl) subEl.textContent = sub;
        if (barFill) {
            barFill.style.width = `${Math.min(rounded, 100)}%`;
            barFill.className = `metric-bar-fill ${this._getLevel(rounded)}`;
        }
    },

    _getLevel(percent) {
        if (percent >= 90) return 'danger';
        if (percent >= 70) return 'warning';
        return 'good';
    },

    _formatBytes(bytes) {
        if (bytes === 0) return '0 B';
        const units = ['B', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(1024));
        return `${(bytes / Math.pow(1024, i)).toFixed(1)} ${units[i] || 'TB'}`;
    },

    _renderCoreGrid(cores) {
        const container = document.getElementById('core-grid');
        if (!container) return;

        container.innerHTML = cores.map((pct, i) => {
            const level = this._getLevel(pct);
            const bgColor = level === 'danger' ? 'var(--danger-dim)' :
                           level === 'warning' ? 'var(--warning-dim)' : 'var(--success-dim)';
            const color = level === 'danger' ? 'var(--danger)' :
                         level === 'warning' ? 'var(--warning)' : 'var(--success)';
            return `<div class="core-cell" style="background: ${bgColor}; color: ${color};">${Math.round(pct)}</div>`;
        }).join('');
    },

    updateHistory(history) {
        if (!history) return;
        this._history = history;
        this._drawChart('chart-cpu', history.cpu, 'var(--accent)');
        this._drawChart('chart-memory', history.memory, 'var(--success)');
        this._drawChart('chart-gpu', history.gpu, 'var(--warning)');
    },

    _drawChart(canvasId, data, color) {
        const canvas = document.getElementById(canvasId);
        if (!canvas || !data?.length) return;

        const ctx = canvas.getContext('2d');
        const w = canvas.width = canvas.offsetWidth * (window.devicePixelRatio || 1);
        const h = canvas.height = canvas.offsetHeight * (window.devicePixelRatio || 1);
        ctx.scale(window.devicePixelRatio || 1, window.devicePixelRatio || 1);

        const dw = canvas.offsetWidth;
        const dh = canvas.offsetHeight;

        ctx.clearRect(0, 0, dw, dh);

        // Resolve CSS variable color
        const computedColor = getComputedStyle(document.documentElement)
            .getPropertyValue(color.replace('var(', '').replace(')', '')).trim() || '#6c8cff';

        // Draw area
        const max = 100;
        const step = dw / Math.max(data.length - 1, 1);

        ctx.beginPath();
        ctx.moveTo(0, dh);
        data.forEach((v, i) => {
            const x = i * step;
            const y = dh - (Math.min(v, max) / max) * dh;
            if (i === 0) ctx.lineTo(x, y);
            else ctx.lineTo(x, y);
        });
        ctx.lineTo(dw, dh);
        ctx.closePath();
        ctx.fillStyle = computedColor + '20';
        ctx.fill();

        // Draw line
        ctx.beginPath();
        data.forEach((v, i) => {
            const x = i * step;
            const y = dh - (Math.min(v, max) / max) * dh;
            if (i === 0) ctx.moveTo(x, y);
            else ctx.lineTo(x, y);
        });
        ctx.strokeStyle = computedColor;
        ctx.lineWidth = 1.5;
        ctx.stroke();
    },
};
