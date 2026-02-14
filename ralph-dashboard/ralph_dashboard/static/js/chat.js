/**
 * Ralph Dashboard - Chat Module
 * Direct chat with local Ollama models via WebSocket streaming.
 * Features: persistence, text-to-speech, web search.
 */

const Chat = {
    _messages: [],
    _ws: null,
    _streaming: false,
    _currentAssistantDiv: null,
    _currentContent: '',
    _conversationId: null,
    _ttsUtterance: null,

    getModel() {
        const sel = document.getElementById('chat-model-select');
        return sel ? sel.value : 'qwen2.5-coder:7b';
    },

    handleKey(event) {
        if (event.key === 'Enter' && !event.shiftKey) {
            event.preventDefault();
            this.send();
        }
    },

    autoResize(el) {
        el.style.height = 'auto';
        el.style.height = Math.min(el.scrollHeight, 200) + 'px';
    },

    // --- Conversation Management ---

    async loadChatList() {
        try {
            const chats = await api.listChats();
            const list = document.getElementById('chat-history-list');
            if (!list) return;

            let html = `<div class="chat-history-item" onclick="Chat.newConversation()">+ Nuova chat</div>`;
            for (const c of chats) {
                const active = c.id === this._conversationId ? ' active' : '';
                const title = this._escapeHtml(c.title || 'Chat senza titolo');
                html += `
                    <div class="chat-history-item${active}" data-id="${c.id}" onclick="Chat.loadConversation('${c.id}')">
                        <span style="flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">${title}</span>
                        <span class="chat-delete-btn" onclick="event.stopPropagation();Chat.deleteConversation('${c.id}')" title="Elimina">&times;</span>
                    </div>
                `;
            }
            list.innerHTML = html;
        } catch (e) {
            console.warn('Failed to load chat list:', e);
        }
    },

    async newConversation() {
        this._messages = [];
        this._streaming = false;
        this._currentAssistantDiv = null;
        this._currentContent = '';
        this._conversationId = null;

        const container = document.getElementById('chat-messages');
        if (container) {
            container.innerHTML = `
                <div class="chat-welcome">
                    <div class="chat-welcome-icon">R</div>
                    <div class="chat-welcome-title">Chat con il tuo modello locale</div>
                    <div class="chat-welcome-sub">
                        Scrivi un messaggio per chattare direttamente con Qwen o un altro modello Ollama installato sulla tua macchina.
                    </div>
                </div>
            `;
        }
        this.loadChatList();
    },

    async loadConversation(convId) {
        try {
            const conv = await api.getChat(convId);
            this._conversationId = convId;
            this._messages = (conv.messages || []).map(m => ({
                role: m.role,
                content: m.content,
            }));

            // Render messages
            const container = document.getElementById('chat-messages');
            if (!container) return;
            container.innerHTML = '';

            for (const msg of this._messages) {
                this._appendMessageBubble(msg.role, msg.content);
            }

            if (this._messages.length === 0) {
                container.innerHTML = `
                    <div class="chat-welcome">
                        <div class="chat-welcome-icon">R</div>
                        <div class="chat-welcome-title">Chat con il tuo modello locale</div>
                        <div class="chat-welcome-sub">
                            Scrivi un messaggio per chattare direttamente con Qwen o un altro modello Ollama installato sulla tua macchina.
                        </div>
                    </div>
                `;
            }

            this.loadChatList();
        } catch (e) {
            App.showToast(`Errore caricamento chat: ${e.message}`, 'error');
        }
    },

    async deleteConversation(convId) {
        try {
            await api.deleteChat(convId);
            if (this._conversationId === convId) {
                this.newConversation();
            } else {
                this.loadChatList();
            }
            App.showToast('Chat eliminata', 'info');
        } catch (e) {
            App.showToast(`Errore: ${e.message}`, 'error');
        }
    },

    async _ensureConversation() {
        if (!this._conversationId) {
            const conv = await api.createChat('Nuova chat', this.getModel());
            this._conversationId = conv.id;
            this.loadChatList();
        }
    },

    async _saveMessage(role, content) {
        if (this._conversationId) {
            try {
                await api.addChatMessage(this._conversationId, role, content);
                // Refresh list to update title (auto-titled from first message)
                if (this._messages.length <= 2) {
                    this.loadChatList();
                }
            } catch (e) {
                console.warn('Failed to persist message:', e);
            }
        }
    },

    // --- WebSocket ---

    _ensureWs() {
        if (this._ws && this._ws.readyState === WebSocket.OPEN) return;

        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const url = `${protocol}//${window.location.host}/ws/chat`;
        this._ws = new WebSocket(url);

        this._ws.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                if (data.type === 'chat_token') {
                    this._appendToken(data.content);
                } else if (data.type === 'chat_done') {
                    this._finishStream();
                } else if (data.type === 'chat_error') {
                    this._appendToken(`\n[ERRORE] ${data.error}`);
                    this._finishStream();
                }
            } catch (e) {
                console.warn('[Chat WS] parse error:', e);
            }
        };

        this._ws.onclose = () => {
            if (this._streaming) {
                this._finishStream();
            }
        };
    },

    // --- Send Message ---

    async send() {
        const input = document.getElementById('chat-input');
        const text = input?.value?.trim();
        if (!text || this._streaming) return;

        // Clear welcome message if first message
        const container = document.getElementById('chat-messages');
        const welcome = container?.querySelector('.chat-welcome');
        if (welcome) welcome.remove();

        // Ensure conversation exists for persistence
        await this._ensureConversation();

        // Add user message
        this._messages.push({ role: 'user', content: text });
        this._appendMessageBubble('user', text);
        this._saveMessage('user', text);
        input.value = '';
        input.style.height = 'auto';

        // Create assistant bubble
        this._currentContent = '';
        this._currentAssistantDiv = this._appendMessageBubble('assistant', '');
        this._streaming = true;
        this._updateSendButton();

        // Send via WebSocket for streaming
        this._ensureWs();

        const sendPayload = () => {
            if (this._ws.readyState === WebSocket.OPEN) {
                this._ws.send(JSON.stringify({
                    model: this.getModel(),
                    messages: this._messages.map(m => ({ role: m.role, content: m.content })),
                }));
            }
        };

        if (this._ws.readyState === WebSocket.OPEN) {
            sendPayload();
        } else {
            this._ws.onopen = sendPayload;
        }
    },

    // --- Web Search ---

    async searchWeb() {
        const input = document.getElementById('chat-input');
        const query = input?.value?.trim();
        if (!query) {
            App.showToast('Scrivi una query di ricerca', 'warning');
            return;
        }

        // Clear welcome if present
        const container = document.getElementById('chat-messages');
        const welcome = container?.querySelector('.chat-welcome');
        if (welcome) welcome.remove();

        await this._ensureConversation();

        // Show search indicator
        this._appendMessageBubble('user', `Ricerca web: ${query}`);
        this._messages.push({ role: 'user', content: `Ricerca web: ${query}` });
        this._saveMessage('user', `Ricerca web: ${query}`);
        input.value = '';
        input.style.height = 'auto';

        const searchDiv = this._appendMessageBubble('assistant', '');
        if (searchDiv) searchDiv.innerHTML = '<span class="spinner" style="display:inline-block;margin-right:8px;"></span> Ricerca in corso...';

        try {
            const result = await api.searchWeb(query);
            const results = result.results || [];

            if (results.length === 0) {
                searchDiv.innerHTML = '<div style="color:var(--text-muted);">Nessun risultato trovato.</div>';
                return;
            }

            // Render search results as cards
            let html = '<div style="font-size:13px;color:var(--text-faint);margin-bottom:8px;">Risultati web:</div>';
            for (const r of results) {
                html += `
                    <div style="margin-bottom:10px;padding:10px;background:var(--bg-elevated);border:1px solid var(--border-subtle);border-radius:var(--radius-md);">
                        <a href="${this._escapeHtml(r.url)}" target="_blank" rel="noopener" style="color:var(--accent);font-weight:500;text-decoration:none;font-size:13px;">${this._escapeHtml(r.title)}</a>
                        <div style="font-size:12px;color:var(--text-faint);margin-top:2px;word-break:break-all;">${this._escapeHtml(r.url)}</div>
                        ${r.snippet ? `<div style="font-size:12px;color:var(--text-secondary);margin-top:4px;">${this._escapeHtml(r.snippet)}</div>` : ''}
                    </div>
                `;
            }
            html += `<button class="btn btn-sm" onclick="Chat.addSearchToContext()" style="margin-top:4px;">Usa nel contesto AI</button>`;
            searchDiv.innerHTML = html;

            // Store results for context inclusion
            this._lastSearchResults = results;

            // Save as assistant message
            const summary = results.map(r => `- ${r.title}: ${r.url}`).join('\n');
            this._messages.push({ role: 'assistant', content: `Risultati web per "${query}":\n${summary}` });
            this._saveMessage('assistant', `Risultati web per "${query}":\n${summary}`);

        } catch (e) {
            searchDiv.innerHTML = `<div style="color:var(--error);">Errore ricerca: ${this._escapeHtml(e.message)}</div>`;
        }
    },

    _lastSearchResults: null,

    addSearchToContext() {
        if (!this._lastSearchResults?.length) return;
        const context = this._lastSearchResults.map(r =>
            `[${r.title}](${r.url}): ${r.snippet}`
        ).join('\n\n');
        const input = document.getElementById('chat-input');
        if (input) {
            input.value = `Basandoti su questi risultati web:\n${context}\n\nRispondi: `;
            input.focus();
            this.autoResize(input);
        }
        App.showToast('Risultati aggiunti al contesto', 'success');
    },

    // --- Text-to-Speech ---

    speak(text) {
        if (!('speechSynthesis' in window)) {
            App.showToast('Text-to-Speech non supportato', 'warning');
            return;
        }

        // Stop if already speaking
        if (speechSynthesis.speaking) {
            speechSynthesis.cancel();
            return;
        }

        const utterance = new SpeechSynthesisUtterance(text);
        utterance.lang = 'it-IT';
        utterance.rate = 1.0;
        utterance.pitch = 1.0;

        // Try to find an Italian voice
        const voices = speechSynthesis.getVoices();
        const itVoice = voices.find(v => v.lang.startsWith('it'));
        if (itVoice) utterance.voice = itVoice;

        this._ttsUtterance = utterance;
        speechSynthesis.speak(utterance);
    },

    stopSpeak() {
        if ('speechSynthesis' in window && speechSynthesis.speaking) {
            speechSynthesis.cancel();
        }
    },

    // --- UI Rendering ---

    _appendMessageBubble(role, content) {
        const container = document.getElementById('chat-messages');
        if (!container) return null;

        const wrapper = document.createElement('div');
        wrapper.className = `chat-msg chat-msg-${role}`;

        const label = document.createElement('div');
        label.className = 'chat-msg-label';
        label.textContent = role === 'user' ? 'Tu' : this.getModel();

        const body = document.createElement('div');
        body.className = 'chat-msg-body';
        body.textContent = content;

        wrapper.appendChild(label);
        wrapper.appendChild(body);

        // Add TTS button for assistant messages
        if (role === 'assistant' && content) {
            const actions = document.createElement('div');
            actions.className = 'chat-msg-actions';
            actions.innerHTML = `
                <button class="btn btn-sm btn-ghost chat-tts-btn" onclick="Chat.speak(this.closest('.chat-msg').querySelector('.chat-msg-body').textContent)" title="Leggi ad alta voce">
                    &#128264; Ascolta
                </button>
            `;
            wrapper.appendChild(actions);
        }

        container.appendChild(wrapper);
        container.scrollTop = container.scrollHeight;

        return body;
    },

    _appendToken(token) {
        if (!this._currentAssistantDiv) return;
        this._currentContent += token;
        this._currentAssistantDiv.textContent = this._currentContent;
        const container = document.getElementById('chat-messages');
        if (container) container.scrollTop = container.scrollHeight;
    },

    _finishStream() {
        if (this._currentContent) {
            this._messages.push({ role: 'assistant', content: this._currentContent });
            this._saveMessage('assistant', this._currentContent);

            // Add TTS button after stream finishes
            if (this._currentAssistantDiv) {
                const wrapper = this._currentAssistantDiv.closest('.chat-msg');
                if (wrapper && !wrapper.querySelector('.chat-msg-actions')) {
                    const actions = document.createElement('div');
                    actions.className = 'chat-msg-actions';
                    actions.innerHTML = `
                        <button class="btn btn-sm btn-ghost chat-tts-btn" onclick="Chat.speak(this.closest('.chat-msg').querySelector('.chat-msg-body').textContent)" title="Leggi ad alta voce">
                            &#128264; Ascolta
                        </button>
                    `;
                    wrapper.appendChild(actions);
                }
            }
        }
        this._streaming = false;
        this._currentAssistantDiv = null;
        this._currentContent = '';
        this._updateSendButton();
    },

    _updateSendButton() {
        const btn = document.getElementById('chat-send-btn');
        if (btn) {
            btn.disabled = this._streaming;
            btn.style.opacity = this._streaming ? '0.5' : '1';
        }
    },

    async loadModels() {
        try {
            const models = await api.getOllamaModels();
            const chatSelect = document.getElementById('chat-model-select');
            const projectSelect = document.getElementById('new-project-model');

            [chatSelect, projectSelect].forEach(sel => {
                if (!sel || !models.length) return;
                sel.innerHTML = models.map(m =>
                    `<option value="${m.name}">${m.name}</option>`
                ).join('');
            });
        } catch (e) {
            console.warn('Failed to load Ollama models:', e);
        }
    },

    _escapeHtml(str) {
        const el = document.createElement('span');
        el.textContent = str || '';
        return el.innerHTML;
    },
};
