/**
 * Ralph Dashboard - Config Module
 * Manages project configuration editing.
 */

const Config = {
    _rawToml: '',
    _projectName: null,

    async loadConfig(project) {
        this._projectName = project;
        const panel = document.getElementById('panel-config');
        if (!panel || !project) return;

        try {
            const config = await api.getProjectConfig(project);
            this._rawToml = config.raw_toml || '';

            const editor = document.getElementById('config-editor');
            if (editor) editor.value = this._rawToml;

            // Display parsed values
            const info = document.getElementById('config-info');
            if (info) {
                info.innerHTML = `
                    <div style="display: grid; grid-template-columns: 120px 1fr; gap: 4px 12px; font-size: 13px;">
                        <span style="color: var(--text-muted);">Tracker:</span>
                        <span>${this._escape(config.issue_tracker)}</span>
                        <span style="color: var(--text-muted);">Agent:</span>
                        <span>${this._escape(config.agent)}</span>
                        <span style="color: var(--text-muted);">Model:</span>
                        <span>${this._escape(config.model)}</span>
                        <span style="color: var(--text-muted);">Max Iterations:</span>
                        <span>${config.max_iterations}</span>
                        <span style="color: var(--text-muted);">Headless:</span>
                        <span>${config.headless ? 'Yes' : 'No'}</span>
                        <span style="color: var(--text-muted);">Directory:</span>
                        <span style="font-family: var(--font-mono); font-size: 12px;">${this._escape(config.project_dir)}</span>
                    </div>
                `;
            }
        } catch (e) {
            const editor = document.getElementById('config-editor');
            if (editor) editor.value = `# Failed to load config: ${e.message}`;
        }
    },

    async save() {
        if (!this._projectName) {
            App.showToast('No project selected', 'warning');
            return;
        }

        const editor = document.getElementById('config-editor');
        if (!editor) return;

        const newToml = editor.value;
        try {
            // Send raw TOML as JSON string
            await fetch(`/api/projects/${encodeURIComponent(this._projectName)}/config`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(newToml),
            });
            this._rawToml = newToml;
            App.showToast('Configuration saved', 'success');
            this.loadConfig(this._projectName);
        } catch (e) {
            App.showToast(`Save failed: ${e.message}`, 'error');
        }
    },

    reset() {
        const editor = document.getElementById('config-editor');
        if (editor) editor.value = this._rawToml;
        App.showToast('Changes reverted', 'info');
    },

    _escape(str) {
        const el = document.createElement('span');
        el.textContent = str || '';
        return el.innerHTML;
    },
};
