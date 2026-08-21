/**
 * Cliente WebSocket para Sincronización en Tiempo Real
 * ====================================================
 * 
 * Gestiona la conexión persistente con el endpoint ws://localhost:8000/ws.
 * Incluye lógica de reconexión automática con backoff en caso de corte de red.
 */

class WSClient {
  /**
   * @param {Function} onMessageCallback - Función callback ejecutada al recibir un payload JSON
   */
  constructor(onMessageCallback) {
    this.onMessageCallback = onMessageCallback;
    this.socket = null;
    this.reconnectTimer = null;
  }

  /**
   * Inicializa la conexión con el servidor WebSocket.
   */
  connect() {
    // Determinar protocolo ws:// o wss:// dinámicamente según HTTP/HTTPS
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws`;

    this.socket = new WebSocket(wsUrl);

    // Evento de conexión exitosa
    this.socket.onopen = () => {
      console.log('✅ WebSocket conectado exitosamente con Huallaga AI Monitor.');
      if (this.reconnectTimer) {
        clearTimeout(this.reconnectTimer);
        this.reconnectTimer = null;
      }
    };

    // Evento de recepción de mensaje del backend
    this.socket.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data);
        if (this.onMessageCallback) {
          this.onMessageCallback(payload);
        }
      } catch (e) {
        console.error('Error al deserializar mensaje WebSocket:', e);
      }
    };

    // Evento de cierre de conexión: Dispara intento de reconexión
    this.socket.onclose = () => {
      console.warn('⚠️ Conexión WebSocket cerrada. Reintentando en 3 segundos...');
      this.reconnectTimer = setTimeout(() => this.connect(), 3000);
    };

    // Evento de error en el socket
    this.socket.onerror = (err) => {
      console.error('Error en WebSocket:', err);
    };
  }
}
