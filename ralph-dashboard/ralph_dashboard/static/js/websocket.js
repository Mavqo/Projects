/**
 * Ralph Dashboard - WebSocket Manager
 * Handles real-time connections for metrics and log streaming.
 */

class WebSocketManager {
    constructor() {
        this._connections = {};
        this._listeners = {};
        this._reconnectTimers = {};
    }

    _getWsUrl(path) {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        return `${protocol}//${window.location.host}${path}`;
    }

    connect(name, path, onMessage) {
        if (this._connections[name]?.readyState === WebSocket.OPEN) {
            return;
        }

        const url = this._getWsUrl(path);
        const ws = new WebSocket(url);

        ws.onopen = () => {
            console.log(`[WS] Connected: ${name}`);
            this._emit('connected', name);
        };

        ws.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                onMessage(data);
            } catch (e) {
                console.warn(`[WS] Parse error on ${name}:`, e);
            }
        };

        ws.onclose = (event) => {
            console.log(`[WS] Disconnected: ${name} (code: ${event.code})`);
            this._emit('disconnected', name);
            // Auto-reconnect after 3 seconds
            this._reconnectTimers[name] = setTimeout(() => {
                if (this._connections[name] === ws) {
                    console.log(`[WS] Reconnecting: ${name}`);
                    this.connect(name, path, onMessage);
                }
            }, 3000);
        };

        ws.onerror = (error) => {
            console.error(`[WS] Error on ${name}:`, error);
        };

        this._connections[name] = ws;
    }

    disconnect(name) {
        const ws = this._connections[name];
        if (ws) {
            ws.close();
            delete this._connections[name];
        }
        if (this._reconnectTimers[name]) {
            clearTimeout(this._reconnectTimers[name]);
            delete this._reconnectTimers[name];
        }
    }

    disconnectAll() {
        for (const name of Object.keys(this._connections)) {
            this.disconnect(name);
        }
    }

    send(name, data) {
        const ws = this._connections[name];
        if (ws?.readyState === WebSocket.OPEN) {
            ws.send(typeof data === 'string' ? data : JSON.stringify(data));
        }
    }

    isConnected(name) {
        return this._connections[name]?.readyState === WebSocket.OPEN;
    }

    on(event, callback) {
        if (!this._listeners[event]) {
            this._listeners[event] = [];
        }
        this._listeners[event].push(callback);
    }

    _emit(event, ...args) {
        (this._listeners[event] || []).forEach(cb => {
            try { cb(...args); } catch (e) { console.error(e); }
        });
    }
}

window.wsManager = new WebSocketManager();
