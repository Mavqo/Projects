/**
 * Ralph Dashboard - API Client
 * Handles all REST API communication with the backend.
 */

const API_BASE = '/api';

class ApiClient {
    async _fetch(path, options = {}) {
        const url = `${API_BASE}${path}`;
        const defaults = {
            headers: { 'Content-Type': 'application/json' },
        };
        const config = { ...defaults, ...options };

        try {
            const response = await fetch(url, config);
            if (!response.ok) {
                const error = await response.json().catch(() => ({ detail: response.statusText }));
                throw new Error(error.detail || error.message || `HTTP ${response.status}`);
            }
            return await response.json();
        } catch (err) {
            if (err instanceof TypeError && err.message.includes('fetch')) {
                throw new Error('Network error: unable to reach dashboard server');
            }
            throw err;
        }
    }

    // System
    async getSystemStatus() {
        return this._fetch('/system/status');
    }

    async getSystemMetrics() {
        return this._fetch('/system/metrics');
    }

    async getMetricsHistory(seconds = 300) {
        return this._fetch(`/system/metrics/history?seconds=${seconds}`);
    }

    async getRalphProcesses() {
        return this._fetch('/system/processes');
    }

    // Config
    async getConfig() {
        return this._fetch('/config');
    }

    async updateConfig(config) {
        return this._fetch('/config', {
            method: 'PUT',
            body: JSON.stringify(config),
        });
    }

    // Ollama
    async getOllamaStatus() {
        return this._fetch('/ollama/status');
    }

    async getOllamaModels() {
        return this._fetch('/ollama/models');
    }

    async ollamaChat(model, messages) {
        return this._fetch('/ollama/chat', {
            method: 'POST',
            body: JSON.stringify({ model, messages }),
        });
    }

    // Projects
    async listProjects() {
        return this._fetch('/projects');
    }

    async getProject(name) {
        return this._fetch(`/projects/${encodeURIComponent(name)}`);
    }

    async createFromPrompt(data) {
        return this._fetch('/projects/create-from-prompt', {
            method: 'POST',
            body: JSON.stringify(data),
        });
    }

    async launchProject(name, options = {}) {
        return this._fetch(`/projects/${encodeURIComponent(name)}/launch`, {
            method: 'POST',
            body: JSON.stringify(options),
        });
    }

    async stopProject(name) {
        return this._fetch(`/projects/${encodeURIComponent(name)}/stop`, {
            method: 'POST',
        });
    }

    async pauseProject(name) {
        return this._fetch(`/projects/${encodeURIComponent(name)}/pause`, {
            method: 'POST',
        });
    }

    async resumeProject(name) {
        return this._fetch(`/projects/${encodeURIComponent(name)}/resume`, {
            method: 'POST',
        });
    }

    async deleteProject(name) {
        return this._fetch(`/projects/${encodeURIComponent(name)}?confirm=true`, {
            method: 'DELETE',
        });
    }

    async getProjectConfig(name) {
        return this._fetch(`/projects/${encodeURIComponent(name)}/config`);
    }

    // Tasks
    async listTasks(project) {
        return this._fetch(`/projects/${encodeURIComponent(project)}/tasks`);
    }

    async getTask(project, taskId) {
        return this._fetch(`/projects/${encodeURIComponent(project)}/tasks/${taskId}`);
    }

    async updateTask(project, taskId, update) {
        return this._fetch(`/projects/${encodeURIComponent(project)}/tasks/${taskId}`, {
            method: 'PUT',
            body: JSON.stringify(update),
        });
    }

    async createTask(project, task) {
        return this._fetch(`/projects/${encodeURIComponent(project)}/tasks`, {
            method: 'POST',
            body: JSON.stringify(task),
        });
    }

    async deleteTask(project, taskId) {
        return this._fetch(`/projects/${encodeURIComponent(project)}/tasks/${taskId}`, {
            method: 'DELETE',
        });
    }

    // Logs
    async getLogs(project, count = 200, keyword = null, level = null) {
        let url = `/projects/${encodeURIComponent(project)}/logs?count=${count}`;
        if (keyword) url += `&keyword=${encodeURIComponent(keyword)}`;
        if (level) url += `&level=${encodeURIComponent(level)}`;
        return this._fetch(url);
    }

    async listLogFiles(project) {
        return this._fetch(`/projects/${encodeURIComponent(project)}/log-files`);
    }

    async readLogFile(project, path, maxLines = 1000, offset = 0) {
        const params = new URLSearchParams({ path, max_lines: maxLines, offset });
        return this._fetch(`/projects/${encodeURIComponent(project)}/log-files/read?${params}`);
    }

    async clearLogs(project) {
        return this._fetch(`/projects/${encodeURIComponent(project)}/logs/clear`, {
            method: 'POST',
        });
    }

    // Chat Persistence
    async listChats() {
        return this._fetch('/chats');
    }

    async createChat(title = 'Nuova chat', model = '') {
        return this._fetch(`/chats?title=${encodeURIComponent(title)}&model=${encodeURIComponent(model)}`, {
            method: 'POST',
        });
    }

    async getChat(convId) {
        return this._fetch(`/chats/${encodeURIComponent(convId)}`);
    }

    async updateChat(convId, updates) {
        return this._fetch(`/chats/${encodeURIComponent(convId)}`, {
            method: 'PUT',
            body: JSON.stringify(updates),
        });
    }

    async addChatMessage(convId, role, content) {
        return this._fetch(`/chats/${encodeURIComponent(convId)}/messages`, {
            method: 'POST',
            body: JSON.stringify({ role, content }),
        });
    }

    async deleteChat(convId) {
        return this._fetch(`/chats/${encodeURIComponent(convId)}`, {
            method: 'DELETE',
        });
    }

    // Web Search
    async searchWeb(query, maxResults = 5) {
        return this._fetch(`/search?q=${encodeURIComponent(query)}&max_results=${maxResults}`);
    }
}

// Singleton
window.api = new ApiClient();
