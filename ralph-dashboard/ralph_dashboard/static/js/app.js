/**
 * Ralph Dashboard - Main Application
 * Orchestrates all dashboard components and manages state.
 */

const App = {
    state: {
        projects: [],
        selectedProject: null,
        activeMode: 'chat',      // 'chat' or 'ralph'
        activeProjectTab: 'tasks',
        theme: localStorage.getItem('ralph-theme') || 'dark',
        connected: false,
        ralphAvailable: false,
        ollamaAvailable: false,
    },

    init() {
        document.documentElement.setAttribute('data-theme', this.state.theme);

        // Start WebSocket for metrics
        wsManager.connect('metrics', '/ws/metrics', (data) => {
            if (data.type === 'metrics') {
                Performance.updateMetrics(data.data);
            }
        });

        wsManager.on('connected', (name) => {
            if (name === 'metrics') {
                this.state.connected = true;
                this.updateConnectionStatus(true);
            }
        });

        wsManager.on('disconnected', (name) => {
            if (name === 'metrics') {
                this.state.connected = false;
                this.updateConnectionStatus(false);
            }
        });

        // Load initial data
        this.loadSystemStatus();
        this.loadProjects();
        this.checkOllama();

        // Periodic refreshes
        setInterval(() => this.loadProjects(), 10000);
        setInterval(() => this.checkOllama(), 30000);

        // Theme toggle
        document.getElementById('theme-toggle')?.addEventListener('click', () => this.toggleTheme());

        // Load metrics history for charts
        this.loadMetricsHistory();
        setInterval(() => this.loadMetricsHistory(), 30000);
    },

    switchMode(mode) {
        this.state.activeMode = mode;

        // Update sidebar mode buttons
        document.querySelectorAll('.mode-btn').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.mode === mode);
        });

        // Switch sidebar panels
        document.querySelectorAll('.sidebar-panel').forEach(p => {
            p.classList.toggle('active', p.id === `sidebar-${mode}`);
        });

        // Switch main panels
        document.querySelectorAll('.main-panel').forEach(p => {
            p.classList.toggle('active', p.id === `main-${mode}`);
        });

        // When switching to ralph, refresh projects
        if (mode === 'ralph') {
            this.loadProjects();
        }
    },

    switchProjectTab(tabName) {
        this.state.activeProjectTab = tabName;
        const detail = document.getElementById('ralph-detail');
        if (!detail) return;

        detail.querySelectorAll('.tab').forEach(t =>
            t.classList.toggle('active', t.dataset.tab === tabName)
        );
        detail.querySelectorAll('.tab-panel').forEach(p =>
            p.classList.toggle('active', p.id === `panel-${tabName}`)
        );

        if (this.state.selectedProject) {
            if (tabName === 'tasks') Tasks.loadTasks(this.state.selectedProject);
            else if (tabName === 'logs') Logs.connect(this.state.selectedProject);
            else if (tabName === 'config') Config.loadConfig(this.state.selectedProject);
        }
    },

    async checkOllama() {
        try {
            const status = await api.getOllamaStatus();
            this.state.ollamaAvailable = status.available;
            const el = document.getElementById('ollama-status');
            if (el) {
                el.textContent = status.available ? 'Ollama: online' : 'Ollama: offline';
                el.style.color = status.available ? 'var(--success)' : 'var(--danger)';
            }
            if (status.available) {
                Chat.loadModels();
            }
        } catch (e) {
            console.warn('Ollama check failed:', e);
        }
    },

    async loadSystemStatus() {
        try {
            const status = await api.getSystemStatus();
            this.state.ralphAvailable = status.data?.ralph_tui_available || false;
            this.updateStatusBar(status.data);
        } catch (e) {
            console.error('Failed to load system status:', e);
        }
    },

    async loadProjects() {
        try {
            const projects = await api.listProjects();
            this.state.projects = projects;
            Projects.renderList(projects);
            this.updateStatusBar();
        } catch (e) {
            console.error('Failed to load projects:', e);
        }
    },

    async loadMetricsHistory() {
        try {
            const history = await api.getMetricsHistory(300);
            Performance.updateHistory(history);
        } catch (e) {
            console.error('Failed to load metrics history:', e);
        }
    },

    selectProject(name) {
        this.state.selectedProject = name;

        // Update sidebar
        document.querySelectorAll('.project-item').forEach(item => {
            item.classList.toggle('active', item.dataset.project === name);
        });

        // Disconnect previous log stream
        Logs.disconnect();

        // Show project detail
        document.getElementById('ralph-empty')?.classList.add('hidden');
        const detail = document.getElementById('ralph-detail');
        if (detail) detail.classList.remove('hidden');

        // Update header
        const nameEl = document.getElementById('project-detail-name');
        if (nameEl) nameEl.textContent = name;

        // Update folder link
        const proj = this.state.projects.find(p => p.name === name);
        const folderLink = document.getElementById('project-folder-link');
        if (folderLink && proj) {
            folderLink.href = `file://${proj.path}`;
            folderLink.title = proj.path;
        }

        // Update status badge
        const statusBadge = document.getElementById('project-detail-status');
        if (statusBadge && proj) {
            statusBadge.textContent = proj.status;
            statusBadge.className = `badge badge-${proj.status}`;
        }

        // Load active tab data
        if (this.state.activeProjectTab === 'tasks') {
            Tasks.loadTasks(name);
        } else if (this.state.activeProjectTab === 'logs') {
            Logs.connect(name);
        } else if (this.state.activeProjectTab === 'config') {
            Config.loadConfig(name);
        }
    },

    toggleTheme() {
        this.state.theme = this.state.theme === 'dark' ? 'light' : 'dark';
        document.documentElement.setAttribute('data-theme', this.state.theme);
        localStorage.setItem('ralph-theme', this.state.theme);
        const btn = document.getElementById('theme-toggle');
        if (btn) btn.textContent = this.state.theme === 'dark' ? '\u2600' : '\u263E';
    },

    updateConnectionStatus(connected) {
        const dot = document.getElementById('connection-dot');
        const text = document.getElementById('connection-text');
        if (dot) dot.className = `status-dot ${connected ? '' : 'offline'}`;
        if (text) text.textContent = connected ? 'Connesso' : 'Disconnesso';
    },

    updateStatusBar() {
        const activeCount = document.getElementById('status-active-count');
        const ralphStatus = document.getElementById('status-ralph');
        const timestamp = document.getElementById('status-timestamp');

        if (activeCount) {
            const running = this.state.projects.filter(p => p.status === 'running').length;
            activeCount.textContent = `${running} agent${running !== 1 ? 'i' : 'e'} attiv${running !== 1 ? 'i' : 'o'}`;
        }
        if (ralphStatus) {
            ralphStatus.textContent = this.state.ralphAvailable ? 'ralph-tui: pronto' : 'ralph-tui: non trovato';
            ralphStatus.style.color = this.state.ralphAvailable ? 'var(--success)' : 'var(--warning)';
        }
        if (timestamp) {
            timestamp.textContent = new Date().toLocaleTimeString();
        }
    },

    showToast(message, type = 'info') {
        const container = document.getElementById('toast-container');
        if (!container) return;
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        toast.textContent = message;
        container.appendChild(toast);
        setTimeout(() => toast.remove(), 4000);
    },

    showModal(id) {
        document.getElementById(id)?.classList.add('active');
    },

    hideModal(id) {
        document.getElementById(id)?.classList.remove('active');
    },
};

// Start app when DOM is ready
document.addEventListener('DOMContentLoaded', () => App.init());
