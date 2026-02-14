/**
 * Ralph Dashboard - Main Application
 * Orchestrates all dashboard components and manages state.
 */

const App = {
    state: {
        projects: [],
        selectedProject: null,
        activeTab: 'tasks',
        theme: localStorage.getItem('ralph-theme') || 'dark',
        connected: false,
        ralphAvailable: false,
    },

    init() {
        document.documentElement.setAttribute('data-theme', this.state.theme);

        // Initialize tabs
        this.initTabs();

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

        // Periodic project list refresh
        setInterval(() => this.loadProjects(), 10000);

        // Theme toggle
        document.getElementById('theme-toggle')?.addEventListener('click', () => this.toggleTheme());

        // Load metrics history for charts
        this.loadMetricsHistory();
        setInterval(() => this.loadMetricsHistory(), 30000);
    },

    initTabs() {
        document.querySelectorAll('.tab').forEach(tab => {
            tab.addEventListener('click', () => {
                const tabName = tab.dataset.tab;
                this.switchTab(tabName);
            });
        });
    },

    switchTab(tabName) {
        this.state.activeTab = tabName;
        document.querySelectorAll('.tab').forEach(t => t.classList.toggle('active', t.dataset.tab === tabName));
        document.querySelectorAll('.tab-panel').forEach(p => p.classList.toggle('active', p.id === `panel-${tabName}`));

        // Load tab-specific data
        if (tabName === 'tasks' && this.state.selectedProject) {
            Tasks.loadTasks(this.state.selectedProject);
        } else if (tabName === 'logs' && this.state.selectedProject) {
            Logs.connect(this.state.selectedProject);
        } else if (tabName === 'config' && this.state.selectedProject) {
            Config.loadConfig(this.state.selectedProject);
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
        document.querySelectorAll('.project-item').forEach(item => {
            item.classList.toggle('active', item.dataset.project === name);
        });

        // Disconnect previous log stream
        Logs.disconnect();

        // Load data for selected project
        if (this.state.activeTab === 'tasks') {
            Tasks.loadTasks(name);
        } else if (this.state.activeTab === 'logs') {
            Logs.connect(name);
        } else if (this.state.activeTab === 'config') {
            Config.loadConfig(name);
        }

        // Update main panel header
        const header = document.getElementById('main-project-name');
        if (header) header.textContent = name;
    },

    toggleTheme() {
        this.state.theme = this.state.theme === 'dark' ? 'light' : 'dark';
        document.documentElement.setAttribute('data-theme', this.state.theme);
        localStorage.setItem('ralph-theme', this.state.theme);
        const btn = document.getElementById('theme-toggle');
        if (btn) btn.textContent = this.state.theme === 'dark' ? '☀' : '☾';
    },

    updateConnectionStatus(connected) {
        const dot = document.getElementById('connection-dot');
        const text = document.getElementById('connection-text');
        if (dot) dot.className = `status-dot ${connected ? '' : 'offline'}`;
        if (text) text.textContent = connected ? 'Connected' : 'Disconnected';
    },

    updateStatusBar(statusData) {
        const activeCount = document.getElementById('status-active-count');
        const ralphStatus = document.getElementById('status-ralph');
        const timestamp = document.getElementById('status-timestamp');

        if (activeCount) {
            const running = this.state.projects.filter(p => p.status === 'running').length;
            activeCount.textContent = `${running} active agent${running !== 1 ? 's' : ''}`;
        }
        if (ralphStatus) {
            ralphStatus.textContent = this.state.ralphAvailable ? 'ralph-tui: ready' : 'ralph-tui: not found';
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
