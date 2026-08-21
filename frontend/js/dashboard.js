/**
 * Controlador de la Interfaz de Usuario (Dashboard UI Controller)
 * ===============================================================
 * 
 * Se encarga de actualizar dinámicamente los elementos del DOM en respuesta
 * a los eventos recibidos vía WebSocket o consultas REST.
 */

const Dashboard = {
  /**
   * Actualiza los paneles principales con los datos del estado del sistema (`SystemState`).
   * @param {Object} data - Objeto de estado enviado por el backend
   */
  updateStatus(data) {
    if (!data) return;

    // 1. Actualizar indicador visual del estado del sistema
    const sysDot = document.querySelector('#system-status-pill .status-dot');
    const sysText = document.getElementById('system-status-text');
    if (sysDot && sysText) {
      if (data.running) {
        sysDot.className = 'status-dot green';
        sysText.textContent = 'Sistema: Activo';
      } else {
        sysDot.className = 'status-dot red';
        sysText.textContent = 'Sistema: Inactivo';
      }
    }

    // 2. Actualizar indicador visual del estado de la cámara
    const camDot = document.querySelector('#camera-status-pill .status-dot');
    const camText = document.getElementById('camera-status-text');
    if (camDot && camText) {
      if (data.camera_connected) {
        camDot.className = 'status-dot green';
        camText.textContent = `Cámara: Conectada (${data.camera_source})`;
      } else {
        camDot.className = 'status-dot yellow';
        camText.textContent = 'Cámara: Standby';
      }
    }

    // 3. Actualizar conteo de personas detectadas y FPS
    const personsEl = document.getElementById('persons-count');
    const fpsEl = document.getElementById('fps-badge');
    const activeEvtEl = document.getElementById('active-event-state');
    const aiModelEl = document.getElementById('ai-model-name');

    if (personsEl) personsEl.textContent = data.persons_detected ?? 0;
    if (fpsEl) fpsEl.textContent = `${(data.fps ?? 0).toFixed(1)} FPS`;
    if (activeEvtEl) activeEvtEl.textContent = data.active_event ? 'Sí (Capturando)' : 'No';
    if (aiModelEl) aiModelEl.textContent = data.ai_model || 'gpt-4o';

    // 4. Actualizar métricas del último diagnóstico de IA
    const lastTimeEl = document.getElementById('last-event-time');
    const confBarEl = document.getElementById('confidence-bar');
    const confPercentEl = document.getElementById('confidence-percent');
    const warningTextEl = document.getElementById('warning-text');

    if (lastTimeEl && data.last_event_time) {
      lastTimeEl.textContent = new Date(data.last_event_time).toLocaleTimeString();
    }
    
    if (confBarEl && confPercentEl && data.last_analysis_confidence !== null && data.last_analysis_confidence !== undefined) {
      const confPercent = Math.round(data.last_analysis_confidence * 100);
      confBarEl.style.width = `${confPercent}%`;
      confPercentEl.textContent = `${confPercent}%`;
    }

    if (warningTextEl && data.last_warning_message) {
      warningTextEl.textContent = `"${data.last_warning_message}"`;
    }
  },

  /**
   * Consulta el endpoint REST /api/events y renderiza la tabla de historial de eventos.
   */
  async renderEventsTable() {
    const events = await API.getEvents(10);
    const tbody = document.getElementById('events-table-body');
    if (!tbody) return;

    if (!events || events.length === 0) {
      tbody.innerHTML = '<tr><td colspan="6" class="text-center text-muted">No se han registrado eventos todavía.</td></tr>';
      return;
    }

    tbody.innerHTML = events.map(evt => `
      <tr>
        <td><code>${evt.id ? evt.id.substring(0, 8) + '...' : 'N/A'}</code></td>
        <td>${evt.started_at ? new Date(evt.started_at).toLocaleTimeString() : 'N/A'}</td>
        <td>${evt.local_detection?.persons ?? 0}</td>
        <td>${evt.analysis?.confidence ? Math.round(evt.analysis.confidence * 100) + '%' : 'N/A'}</td>
        <td><span class="badge ${evt.decision === 'WARN' ? 'warning' : ''}">${evt.decision || 'N/A'}</span></td>
        <td><span class="badge blue">${evt.status || 'created'}</span></td>
      </tr>
    `).join('');
  }
};
