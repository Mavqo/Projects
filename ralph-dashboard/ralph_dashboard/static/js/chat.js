/**
 * Ralph Dashboard - Chat Module
 * Direct chat with local Ollama models via WebSocket streaming.
 */

const Chat = {
    _messages: [],
    _ws: null,
    _streaming: false,
    _currentAssistantDiv: null,
    _currentContent: '',

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

    newConversation() {
        this._messages = [];
        this._streaming = false;
        this._currentAssistantDiv = null;
        this._currentContent = '';
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
    },

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

    async send() {
        const input = document.getElementById('chat-input');
        const text = input?.value?.trim();
        if (!text || this._streaming) return;

        // Clear welcome message if first message
        const container = document.getElementById('chat-messages');
        const welcome = container?.querySelector('.chat-welcome');
        if (welcome) welcome.remove();

        // Add user message
        this._messages.push({ role: 'user', content: text });
        this._appendMessageBubble('user', text);
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
};
