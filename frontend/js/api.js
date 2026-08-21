/**
 * Cliente HTTP REST para comunicación con el Backend de FastAPI
 * =============================================================
 * 
 * Provee métodos asíncronos para interactuar con los endpoints /api/status,
 * /api/events y /api/config.
 */

const API = {
  /**
   * Obtiene el estado general del sistema (cámara, FPS, personas detectadas, etc.)
   * Endpoint: GET /api/status
   */
  async getStatus() {
    try {
      const res = await fetch('/api/status');
      if (!res.ok) throw new Error(`HTTP error! status: ${res.status}`);
      return await res.json();
    } catch (e) {
      console.error('Error al consultar /api/status:', e);
      return null;
    }
  },

  /**
   * Obtiene el historial de eventos recientes registrados en la base de datos local SQLite.
   * Endpoint: GET /api/events?limit={limit}
   * @param {number} limit - Cantidad máxima de registros a recuperar
   */
  async getEvents(limit = 20) {
    try {
      const res = await fetch(`/api/events?limit=${limit}`);
      if (!res.ok) throw new Error(`HTTP error! status: ${res.status}`);
      return await res.json();
    } catch (e) {
      console.error('Error al consultar /api/events:', e);
      return [];
    }
  },

  /**
   * Obtiene los parámetros de configuración seguros (no sensibles) del backend.
   * Endpoint: GET /api/config
   */
  async getConfig() {
    try {
      const res = await fetch('/api/config');
      if (!res.ok) throw new Error(`HTTP error! status: ${res.status}`);
      return await res.json();
    } catch (e) {
      console.error('Error al consultar /api/config:', e);
      return null;
    }
  }
};
