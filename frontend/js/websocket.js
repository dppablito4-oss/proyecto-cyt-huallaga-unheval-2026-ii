class WSClient {
  constructor(onMessageCallback) {
    this.onMessageCallback = onMessageCallback;
    this.socket = null;
    this.reconnectTimer = null;
  }

  connect() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws`;

    this.socket = new WebSocket(wsUrl);

    this.socket.onopen = () => {
      console.log('WebSocket conectado con el servidor.');
      if (this.reconnectTimer) {
        clearTimeout(this.reconnectTimer);
        this.reconnectTimer = null;
      }
    };

    this.socket.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data);
        if (this.onMessageCallback) {
          this.onMessageCallback(payload);
        }
      } catch (e) {
        console.error('Error parseando WebSocket payload:', e);
      }
    };

    this.socket.onclose = () => {
      console.warn('Conexión WebSocket cerrada. Reintentando en 3s...');
      this.reconnectTimer = setTimeout(() => this.connect(), 3000);
    };

    this.socket.onerror = (err) => {
      console.error('WebSocket error:', err);
    };
  }
}
