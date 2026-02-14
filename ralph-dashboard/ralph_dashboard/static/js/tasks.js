/**
 * Ralph Dashboard - Tasks Module
 * Manages task display, filtering, and CRUD operations.
 */

const Tasks = {
    _tasks: [],
    _filter: { status: '', priority: '', search: '' },

    async loadTasks(project) {
        const panel = document.getElementById('panel-tasks');
        if (!panel || !project) return;

        try {
            const tasks = await api.listTasks(project);
            this._tasks = tasks;
            this.render(tasks);
        } catch (e) {
            panel.innerHTML = `
                <div class="empty-state">
                    <div class="empty-state-icon">&#9888;</div>
                    <div class="empty-state-text">Failed to load tasks</div>
                    <div class="empty-state-sub">${e.message}</div>
                </div>
            `;
        }
    },

    render(tasks) {
        const panel = document.getElementById('tasks-body');
        if (!panel) return;

        let filtered = tasks;

        // Apply filters
        if (this._filter.status) {
            filtered = filtered.filter(t => t.status === this._filter.status);
        }
        if (this._filter.priority) {
            filtered = filtered.filter(t => t.priority === this._filter.priority);
        }
        if (this._filter.search) {
            const q = this._filter.search.toLowerCase();
            filtered = filtered.filter(t =>
                t.title.toLowerCase().includes(q) ||
                t.description.toLowerCase().includes(q) ||
                String(t.id).includes(q)
            );
        }

        // Update count
        const countEl = document.getElementById('tasks-count');
        if (countEl) countEl.textContent = `${filtered.length} of ${tasks.length} tasks`;

        if (filtered.length === 0) {
            panel.innerHTML = `
                <tr><td colspan="6" style="text-align: center; padding: 40px; color: var(--text-muted);">
                    ${tasks.length === 0 ? 'No tasks found for this project' : 'No tasks match the current filters'}
                </td></tr>
            `;
            return;
        }

        panel.innerHTML = filtered.map(t => `
            <tr data-task-id="${t.id}">
                <td style="font-family: var(--font-mono); color: var(--text-muted);">${t.id}</td>
                <td>
                    <strong>${this._escape(t.title)}</strong>
                    ${t.description ? `<div style="font-size: 11px; color: var(--text-muted); margin-top: 2px;">${this._escape(t.description).substring(0, 100)}${t.description.length > 100 ? '...' : ''}</div>` : ''}
                </td>
                <td><span class="badge badge-${t.status}">${t.status}</span></td>
                <td><span class="badge badge-${t.priority}">${t.priority}</span></td>
                <td>${(t.dependencies || []).map(d => `<span class="dep-tag">${d}</span>`).join(' ') || '<span style="color: var(--text-muted);">none</span>'}</td>
                <td>
                    <div style="display: flex; gap: 4px;">
                        <button class="btn btn-sm" onclick="Tasks.editTask('${t.id}')" title="Edit">&#9998;</button>
                        <button class="btn btn-sm btn-success" onclick="Tasks.toggleComplete('${t.id}')" title="Toggle complete">&#10003;</button>
                        <button class="btn btn-sm btn-danger" onclick="Tasks.removeTask('${t.id}')" title="Delete">&#10005;</button>
                    </div>
                </td>
            </tr>
        `).join('');
    },

    filterByStatus(status) {
        this._filter.status = status;
        this.render(this._tasks);
    },

    filterByPriority(priority) {
        this._filter.priority = priority;
        this.render(this._tasks);
    },

    filterBySearch(query) {
        this._filter.search = query;
        this.render(this._tasks);
    },

    showAddModal() {
        if (!App.state.selectedProject) {
            App.showToast('Select a project first', 'warning');
            return;
        }
        document.getElementById('new-task-title').value = '';
        document.getElementById('new-task-description').value = '';
        document.getElementById('new-task-priority').value = 'medium';
        document.getElementById('new-task-deps').value = '';
        App.showModal('add-task-modal');
    },

    async confirmAdd() {
        const project = App.state.selectedProject;
        if (!project) return;

        const title = document.getElementById('new-task-title').value.trim();
        if (!title) {
            App.showToast('Title is required', 'warning');
            return;
        }

        const depsRaw = document.getElementById('new-task-deps').value.trim();
        const deps = depsRaw ? depsRaw.split(',').map(d => d.trim()).filter(Boolean) : [];

        try {
            await api.createTask(project, {
                title,
                description: document.getElementById('new-task-description').value.trim(),
                priority: document.getElementById('new-task-priority').value,
                dependencies: deps,
            });
            App.hideModal('add-task-modal');
            App.showToast('Task created', 'success');
            this.loadTasks(project);
        } catch (e) {
            App.showToast(`Failed to create task: ${e.message}`, 'error');
        }
    },

    async toggleComplete(taskId) {
        const project = App.state.selectedProject;
        if (!project) return;

        const task = this._tasks.find(t => String(t.id) === String(taskId));
        if (!task) return;

        const newStatus = task.status === 'completed' ? 'pending' : 'completed';
        try {
            await api.updateTask(project, taskId, { status: newStatus });
            App.showToast(`Task ${taskId} ${newStatus}`, 'success');
            this.loadTasks(project);
        } catch (e) {
            App.showToast(`Failed to update task: ${e.message}`, 'error');
        }
    },

    editTask(taskId) {
        const task = this._tasks.find(t => String(t.id) === String(taskId));
        if (!task) return;

        document.getElementById('edit-task-id').value = task.id;
        document.getElementById('edit-task-title').value = task.title;
        document.getElementById('edit-task-description').value = task.description || '';
        document.getElementById('edit-task-status').value = task.status;
        document.getElementById('edit-task-priority').value = task.priority;
        document.getElementById('edit-task-deps').value = (task.dependencies || []).join(', ');
        App.showModal('edit-task-modal');
    },

    async confirmEdit() {
        const project = App.state.selectedProject;
        if (!project) return;

        const taskId = document.getElementById('edit-task-id').value;
        const depsRaw = document.getElementById('edit-task-deps').value.trim();
        const deps = depsRaw ? depsRaw.split(',').map(d => d.trim()).filter(Boolean) : [];

        try {
            await api.updateTask(project, taskId, {
                title: document.getElementById('edit-task-title').value.trim(),
                description: document.getElementById('edit-task-description').value.trim(),
                status: document.getElementById('edit-task-status').value,
                priority: document.getElementById('edit-task-priority').value,
                dependencies: deps,
            });
            App.hideModal('edit-task-modal');
            App.showToast('Task updated', 'success');
            this.loadTasks(project);
        } catch (e) {
            App.showToast(`Failed to update task: ${e.message}`, 'error');
        }
    },

    async removeTask(taskId) {
        const project = App.state.selectedProject;
        if (!project) return;

        if (!confirm(`Delete task ${taskId}?`)) return;

        try {
            await api.deleteTask(project, taskId);
            App.showToast(`Task ${taskId} deleted`, 'info');
            this.loadTasks(project);
        } catch (e) {
            App.showToast(`Failed to delete task: ${e.message}`, 'error');
        }
    },

    showDependencyTree() {
        if (!this._tasks.length) {
            App.showToast('No tasks to display', 'warning');
            return;
        }

        const treeHtml = this._buildDepTree(this._tasks);
        document.getElementById('dep-tree-content').innerHTML = treeHtml;
        App.showModal('dep-tree-modal');
    },

    _buildDepTree(tasks) {
        const taskMap = {};
        tasks.forEach(t => { taskMap[String(t.id)] = t; });

        const statusIcon = (status) => {
            const icons = {
                'completed': '<span style="color: var(--success);">&#10003;</span>',
                'in-progress': '<span style="color: var(--accent);">&#9654;</span>',
                'blocked': '<span style="color: var(--danger);">&#9632;</span>',
                'pending': '<span style="color: var(--text-muted);">&#9675;</span>',
                'cancelled': '<span style="color: var(--text-muted);">&#10007;</span>',
                'deferred': '<span style="color: var(--warning);">&#8987;</span>',
            };
            return icons[status] || icons['pending'];
        };

        // Find root tasks (no dependencies or deps not in task list)
        const roots = tasks.filter(t =>
            !t.dependencies?.length ||
            t.dependencies.every(d => !taskMap[String(d)])
        );

        const renderNode = (task, indent = 0) => {
            const prefix = indent > 0 ? '&nbsp;'.repeat(indent * 4) + '&#9492;&#9472; ' : '';
            let html = `<div class="dep-tree-node">
                ${prefix}${statusIcon(task.status)} <strong>${task.id}</strong>: ${this._escape(task.title)}
                <span class="badge badge-${task.status}" style="margin-left: 8px;">${task.status}</span>
            </div>`;

            // Find tasks that depend on this one
            const children = tasks.filter(t =>
                t.dependencies?.includes(task.id) || t.dependencies?.includes(String(task.id))
            );
            children.forEach(child => {
                html += renderNode(child, indent + 1);
            });

            return html;
        };

        return roots.map(r => renderNode(r)).join('');
    },

    _escape(str) {
        const el = document.createElement('span');
        el.textContent = str || '';
        return el.innerHTML;
    },
};
