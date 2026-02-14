/**
 * Ralph Dashboard - Logs Module
 * Manages real-time log streaming and log viewer.
 */

const Logs = {
    _autoScroll: true,
    _currentProject: null,
    _lineCount: 0,
    _maxLines: 10000,

    connect(project) {
        if (this._currentProject === project && wsManager.isConnected(`logs-${project}`)) {
            return;
        }

        this.disconnect();
        this._currentProject = project;
        this._lineCount = 0;

        const output = document.getElementById('log-output');
        if (output) output.innerHTML = '';

        wsManager.connect(`logs-${project}`, `/ws/logs/${encodeURIComponent(project)}`, (data) => {
            if (data.type === 'log_history' || data.type === 'log') {
                this.appendLines(data.lines || []);
            }
        });

        this.updateStatus('Connecting...');
    },

    disconnect() {
        if (this._currentProject) {
            wsManager.disconnect(`logs-${this._currentProject}`);
            this._currentProject = null;
        }
    },

    appendLines(lines) {
        const output = document.getElementById('log-output');
        if (!output) return;

        const fragment = document.createDocumentFragment();

        for (const line of lines) {
            if (this._lineCount >= this._maxLines) {
                // Remove oldest lines
                const firstChild = output.firstChild;
                if (firstChild) output.removeChild(firstChild);
            }

            const div = document.createElement('div');
            div.className = `log-line ${this._getLogLevel(line)}`;
            div.textContent = line;
            fragment.appendChild(div);
            this._lineCount++;
        }

        output.appendChild(fragment);

        if (this._autoScroll) {
            output.scrollTop = output.scrollHeight;
        }

        this.updateStatus(`${this._lineCount} lines`);
    },

    _getLogLevel(line) {
        const upper = line.toUpperCase();
        if (upper.includes('[ERROR]') || upper.includes('ERROR:') || upper.includes('TRACEBACK')) return 'error';
        if (upper.includes('[CRITICAL]') || upper.includes('CRITICAL:')) return 'critical';
        if (upper.includes('[WARNING]') || upper.includes('[WARN]') || upper.includes('WARNING:')) return 'warning';
        if (upper.includes('[DEBUG]') || upper.includes('DEBUG:')) return 'debug';
        return '';
    },

    toggleAutoScroll() {
        this._autoScroll = !this._autoScroll;
        const btn = document.getElementById('log-autoscroll-btn');
        if (btn) {
            btn.textContent = this._autoScroll ? '&#8615; Auto-scroll ON' : '&#8615; Auto-scroll OFF';
            btn.classList.toggle('btn-primary', this._autoScroll);
        }
        if (this._autoScroll) {
            const output = document.getElementById('log-output');
            if (output) output.scrollTop = output.scrollHeight;
        }
    },

    clear() {
        const output = document.getElementById('log-output');
        if (output) output.innerHTML = '';
        this._lineCount = 0;
        this.updateStatus('Cleared');

        if (this._currentProject) {
            api.clearLogs(this._currentProject).catch(() => {});
        }
    },

    async search() {
        const keyword = document.getElementById('log-search').value.trim();
        const project = this._currentProject || App.state.selectedProject;
        if (!project) return;

        if (!keyword) {
            // Reload all logs
            this.connect(project);
            return;
        }

        try {
            const result = await api.getLogs(project, 5000, keyword);
            const output = document.getElementById('log-output');
            if (output) {
                output.innerHTML = '';
                this._lineCount = 0;
                this.appendLines(result.lines || []);
                this.updateStatus(`${result.count} matches for "${keyword}"`);
            }
        } catch (e) {
            App.showToast(`Log search failed: ${e.message}`, 'error');
        }
    },

    async exportLogs(format = 'txt') {
        const project = this._currentProject || App.state.selectedProject;
        if (!project) return;

        try {
            const result = await api.getLogs(project, 50000);
            const lines = result.lines || [];

            let content, filename, mimeType;
            if (format === 'json') {
                content = JSON.stringify({ project, exported: new Date().toISOString(), lines }, null, 2);
                filename = `${project}-logs.json`;
                mimeType = 'application/json';
            } else {
                content = lines.join('\n');
                filename = `${project}-logs.txt`;
                mimeType = 'text/plain';
            }

            const blob = new Blob([content], { type: mimeType });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = filename;
            a.click();
            URL.revokeObjectURL(url);
            App.showToast(`Logs exported as ${filename}`, 'success');
        } catch (e) {
            App.showToast(`Export failed: ${e.message}`, 'error');
        }
    },

    updateStatus(text) {
        const el = document.getElementById('log-status');
        if (el) el.textContent = text;
    },
};
