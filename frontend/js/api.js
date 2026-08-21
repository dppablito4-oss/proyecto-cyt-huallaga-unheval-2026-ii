/**
 * Cliente HTTP REST para comunicación con el Backend de FastAPI
 * =============================================================
 * 
 * Provee métodos asíncronos para interactuar con los endpoints /api/status,
 * /api/events, /api/config, /api/system y /api/debug.
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
  },

  /**
   * Inicia el pipeline de captura y procesamiento de video.
   * Endpoint: POST /api/system/start
   */
  async startPipeline() {
    try {
      const res = await fetch('/api/system/start', { method: 'POST' });
      if (!res.ok) throw new Error(`HTTP error! status: ${res.status}`);
      return await res.json();
    } catch (e) {
      console.error('Error al iniciar pipeline:', e);
      return null;
    }
  },

  /**
   * Detiene el pipeline de captura y procesamiento de video.
   * Endpoint: POST /api/system/stop
   */
  async stopPipeline() {
    try {
      const res = await fetch('/api/system/stop', { method: 'POST' });
      if (!res.ok) throw new Error(`HTTP error! status: ${res.status}`);
      return await res.json();
    } catch (e) {
      console.error('Error al detener pipeline:', e);
      return null;
    }
  },

  /**
   * Prueba la síntesis y reproducción de voz por altavoz.
   * Endpoint: POST /api/debug/test-speech
   * @param {string} text - Texto a sintetizar
   */
  async testSpeech(text = 'Prueba del sistema de vigilancia ambiental del río Huallaga.') {
    try {
      const res = await fetch('/api/debug/test-speech', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text })
      });
      if (!res.ok) throw new Error(`HTTP error! status: ${res.status}`);
      return await res.json();
    } catch (e) {
      console.error('Error al probar TTS:', e);
      return null;
    }
  },

  /**
   * Prueba el análisis de visión multimodal con fotogramas del buffer o sintéticos.
   * Endpoint: POST /api/debug/test-analysis
   */
  async testAnalysis(useBuffer = true, numFrames = 3) {
    try {
      const res = await fetch('/api/debug/test-analysis', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ use_buffer: useBuffer, num_frames: numFrames })
      });
      if (!res.ok) throw new Error(`HTTP error! status: ${res.status}`);
      return await res.json();
    } catch (e) {
      console.error('Error al probar análisis IA:', e);
      return null;
    }
  }
};
