/**
 * Ralph Dashboard - Projects Module
 * Manages the project sidebar and project actions.
 */

const Projects = {
    renderList(projects) {
        const container = document.getElementById('project-list');
        if (!container) return;

        if (projects.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <div class="empty-state-icon">&#128193;</div>
                    <div class="empty-state-text">No projects found</div>
                    <div class="empty-state-sub">
                        Create a Ralph-TUI project in your projects directory,
                        or check your configuration.
                    </div>
                </div>
            `;
            return;
        }

        container.innerHTML = projects.map(p => `
            <div class="project-item ${App.state.selectedProject === p.name ? 'active' : ''}"
                 data-project="${this._escape(p.name)}"
                 onclick="Projects.select('${this._escape(p.name)}')">
                <div class="project-item-info">
                    <div class="project-item-name">${this._escape(p.name)}</div>
                    <div class="project-item-meta">
                        ${p.completed_tasks}/${p.task_count} tasks
                        ${p.pid ? `&#183; PID ${p.pid}` : ''}
                    </div>
                </div>
                <div class="project-item-status ${p.status}"></div>
            </div>
        `).join('');
    },

    select(name) {
        App.selectProject(name);
    },

    async launch(name) {
        name = name || App.state.selectedProject;
        if (!name) {
            App.showToast('No project selected', 'warning');
            return;
        }

        // Show launch modal
        document.getElementById('launch-project-name').textContent = name;
        App.showModal('launch-modal');
    },

    async confirmLaunch() {
        const name = App.state.selectedProject;
        if (!name) return;

        const options = {
            max_iterations: parseInt(document.getElementById('launch-iterations').value) || 50,
            headless: document.getElementById('launch-headless').checked,
        };
        const model = document.getElementById('launch-model').value;
        if (model) options.model = model;

        try {
            const result = await api.launchProject(name, options);
            App.hideModal('launch-modal');
            App.showToast(result.message || `${name} launched`, 'success');
            App.loadProjects();
            // Auto-switch to logs
            App.switchTab('logs');
        } catch (e) {
            App.showToast(`Launch failed: ${e.message}`, 'error');
        }
    },

    async stop(name) {
        name = name || App.state.selectedProject;
        if (!name) return;

        try {
            const result = await api.stopProject(name);
            App.showToast(result.message || `${name} stopped`, 'info');
            App.loadProjects();
        } catch (e) {
            App.showToast(`Stop failed: ${e.message}`, 'error');
        }
    },

    async pause(name) {
        name = name || App.state.selectedProject;
        if (!name) return;

        try {
            const result = await api.pauseProject(name);
            App.showToast(result.message || `${name} paused`, 'info');
            App.loadProjects();
        } catch (e) {
            App.showToast(`Pause failed: ${e.message}`, 'error');
        }
    },

    async resume(name) {
        name = name || App.state.selectedProject;
        if (!name) return;

        try {
            const result = await api.resumeProject(name);
            App.showToast(result.message || `${name} resumed`, 'success');
            App.loadProjects();
        } catch (e) {
            App.showToast(`Resume failed: ${e.message}`, 'error');
        }
    },

    async remove(name) {
        name = name || App.state.selectedProject;
        if (!name) return;

        document.getElementById('delete-project-name').textContent = name;
        App.showModal('delete-modal');
    },

    async confirmDelete() {
        const name = App.state.selectedProject;
        if (!name) return;

        try {
            const result = await api.deleteProject(name);
            App.hideModal('delete-modal');
            App.showToast(result.message || `${name} deleted`, 'info');
            App.state.selectedProject = null;
            App.loadProjects();
        } catch (e) {
            App.showToast(`Delete failed: ${e.message}`, 'error');
        }
    },

    _escape(str) {
        const el = document.createElement('span');
        el.textContent = str;
        return el.innerHTML;
    },
};
