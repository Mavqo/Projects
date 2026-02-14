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
                <div class="empty-state" style="padding: 20px;">
                    <div class="empty-state-text" style="font-size: 12px;">Nessun progetto trovato</div>
                    <div class="empty-state-sub" style="font-size: 11px;">
                        Crea un nuovo progetto per iniziare.
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

    async createFromPrompt() {
        const nameInput = document.getElementById('new-project-name');
        const promptInput = document.getElementById('new-project-prompt');
        const modelSelect = document.getElementById('new-project-model');
        const iterInput = document.getElementById('new-project-iterations');
        const btn = document.getElementById('create-project-btn');

        const name = nameInput?.value?.trim();
        const prompt = promptInput?.value?.trim();

        if (!name) {
            App.showToast('Inserisci un nome per il progetto', 'warning');
            return;
        }
        if (!prompt) {
            App.showToast('Descrivi cosa vuoi costruire', 'warning');
            return;
        }

        // Sanitize project name
        const safeName = name.replace(/[^a-zA-Z0-9_-]/g, '-').toLowerCase();

        if (btn) {
            btn.disabled = true;
            btn.textContent = 'Creazione in corso...';
        }

        try {
            const result = await api.createFromPrompt({
                name: safeName,
                prompt: prompt,
                model: modelSelect?.value || 'qwen2.5-coder:7b',
                max_iterations: parseInt(iterInput?.value) || 50,
            });

            App.hideModal('new-project-modal');
            App.showToast(result.message || `Progetto "${safeName}" creato!`, 'success');

            // Clear form
            if (nameInput) nameInput.value = '';
            if (promptInput) promptInput.value = '';

            // Refresh projects and select the new one
            await App.loadProjects();
            App.switchMode('ralph');
            App.selectProject(safeName);
            App.switchProjectTab('tasks');
        } catch (e) {
            App.showToast(`Errore: ${e.message}`, 'error');
        } finally {
            if (btn) {
                btn.disabled = false;
                btn.textContent = 'Crea e Avvia';
            }
        }
    },

    async launch(name) {
        name = name || App.state.selectedProject;
        if (!name) {
            App.showToast('Nessun progetto selezionato', 'warning');
            return;
        }

        document.getElementById('launch-project-name').textContent = name;
        App.showModal('launch-modal');
    },

    async confirmLaunch() {
        const name = App.state.selectedProject;
        if (!name) return;

        const options = {
            max_iterations: parseInt(document.getElementById('launch-iterations').value) || 50,
            headless: true,
        };
        const model = document.getElementById('launch-model').value;
        if (model) options.model = model;

        try {
            const result = await api.launchProject(name, options);
            App.hideModal('launch-modal');
            App.showToast(result.message || `${name} avviato`, 'success');
            App.loadProjects();
            App.switchProjectTab('logs');
        } catch (e) {
            App.showToast(`Errore avvio: ${e.message}`, 'error');
        }
    },

    async stop(name) {
        name = name || App.state.selectedProject;
        if (!name) return;

        try {
            const result = await api.stopProject(name);
            App.showToast(result.message || `${name} fermato`, 'info');
            App.loadProjects();
        } catch (e) {
            App.showToast(`Errore stop: ${e.message}`, 'error');
        }
    },

    async pause(name) {
        name = name || App.state.selectedProject;
        if (!name) return;

        try {
            const result = await api.pauseProject(name);
            App.showToast(result.message || `${name} in pausa`, 'info');
            App.loadProjects();
        } catch (e) {
            App.showToast(`Errore pausa: ${e.message}`, 'error');
        }
    },

    async resume(name) {
        name = name || App.state.selectedProject;
        if (!name) return;

        try {
            const result = await api.resumeProject(name);
            App.showToast(result.message || `${name} ripreso`, 'success');
            App.loadProjects();
        } catch (e) {
            App.showToast(`Errore ripresa: ${e.message}`, 'error');
        }
    },

    _escape(str) {
        const el = document.createElement('span');
        el.textContent = str;
        return el.innerHTML;
    },
};
