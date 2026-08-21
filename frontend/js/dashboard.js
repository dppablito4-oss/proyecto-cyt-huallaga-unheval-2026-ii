/**
 * Controlador de la Interfaz de Usuario (Dashboard UI Controller)
 * ===============================================================
 * 
 * Gestiona la actualización reactiva del DOM, HUD de video, métricas en vivo,
 * estado de decisión, badges booleanos y tabla histórica de eventos.
 */

const Dashboard = {
  /**
   * Actualiza los paneles con los datos reactivos del estado del sistema (`SystemState`).
   * @param {Object} data - Objeto de estado enviado por el backend
   */
  updateStatus(data) {
    if (!data) return;

    // 1. Actualizar indicador del estado del sistema
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

    // 2. Actualizar estado de la cámara, feed en vivo y HUD
    const camDot = document.querySelector('#camera-status-pill .status-dot');
    const camText = document.getElementById('camera-status-text');
    const liveStream = document.getElementById('live-stream');
    const placeholder = document.getElementById('video-placeholder');
    const hudLiveTag = document.getElementById('hud-live-tag');

    if (camDot && camText) {
      if (data.camera_connected) {
        camDot.className = 'status-dot green';
        camText.textContent = `Cámara: Conectada (${data.camera_source})`;
        
        if (liveStream) {
          liveStream.style.display = 'block';
          if (!liveStream.src || !liveStream.src.includes('/api/cameras/stream')) {
            liveStream.src = '/api/cameras/stream';
          }
        }
        if (placeholder) placeholder.style.display = 'none';
        if (hudLiveTag) hudLiveTag.style.display = 'flex';
      } else {
        camDot.className = 'status-dot yellow';
        camText.textContent = 'Cámara: Standby';
        
        if (liveStream) {
          liveStream.style.display = 'none';
          liveStream.src = '';
        }
        if (placeholder) placeholder.style.display = 'flex';
        if (hudLiveTag) hudLiveTag.style.display = 'none';
      }
    }

    // 3. Actualizar telemetría (Personas detectadas, FPS, Evento Activo, Modelo)
    const personsEl = document.getElementById('persons-count');
    const fpsEl = document.getElementById('fps-badge');
    const activeEvtEl = document.getElementById('active-event-state');
    const aiModelEl = document.getElementById('ai-model-name');

    if (personsEl) personsEl.textContent = data.persons_detected ?? 0;
    if (fpsEl) fpsEl.textContent = `${(data.fps ?? 0).toFixed(1)} FPS`;
    
    if (activeEvtEl) {
      if (data.active_event) {
        activeEvtEl.textContent = 'CAPTURANDO...';
        activeEvtEl.className = 'stat-value warn-color';
      } else {
        activeEvtEl.textContent = 'En Espera';
        activeEvtEl.className = 'stat-value highlight';
      }
    }
    
    if (aiModelEl) aiModelEl.textContent = data.ai_model || 'gpt-5.6-luna';

    // 4. Actualizar métricas del último diagnóstico de IA
    const lastTimeEl = document.getElementById('last-event-time');
    const confBarEl = document.getElementById('confidence-bar');
    const confPercentEl = document.getElementById('confidence-percent');
    const warningTextEl = document.getElementById('warning-text');
    const decisionBadge = document.getElementById('decision-status-badge');

    if (lastTimeEl && data.last_event_time) {
      lastTimeEl.textContent = new Date(data.last_event_time).toLocaleTimeString();
    }
    
    if (confBarEl && confPercentEl) {
      const confVal = data.last_analysis_confidence ?? 0;
      const confPercent = Math.round(confVal * 100);
      confBarEl.style.width = `${confPercent}%`;
      confPercentEl.textContent = `${confPercent}%`;
    }

    if (warningTextEl && data.last_warning_message) {
      warningTextEl.textContent = `"${data.last_warning_message}"`;
    }
  },

  /**
   * Actualiza el reloj HUD en tiempo real.
   */
  updateClock() {
    const clockEl = document.getElementById('hud-timestamp');
    if (clockEl) {
      clockEl.textContent = new Date().toLocaleTimeString();
    }
  },

  /**
   * Consulta el endpoint REST /api/events y renderiza la tabla de historial de eventos.
   */
  async renderEventsTable() {
    const events = await API.getEvents(15);
    const tbody = document.getElementById('events-table-body');
    if (!tbody) return;

    if (!events || events.length === 0) {
      tbody.innerHTML = '<tr><td colspan="7" class="text-center text-muted" style="padding: 1.5rem;">No se han registrado eventos todavía en la sesión actual.</td></tr>';
      return;
    }

    tbody.innerHTML = events.map(evt => {
      const decision = evt.decision || 'N/A';
      let decisionClass = 'cyan';
      if (decision === 'WARN') decisionClass = 'rose';
      else if (decision === 'LOG_ONLY') decisionClass = 'amber';
      else if (decision === 'IGNORE') decisionClass = 'emerald';

      const analysis = evt.analysis || {};
      const eventType = analysis.event_type || 'N/A';
      const actionCompleted = analysis.action_completed ? '✅ Sí' : '❌ No';
      const conf = analysis.confidence !== undefined ? `${Math.round(analysis.confidence * 100)}%` : 'N/A';
      const shortId = evt.id ? evt.id.substring(0, 8) : 'N/A';
      const timeStr = evt.started_at ? new Date(evt.started_at).toLocaleTimeString() : 'N/A';

      return `
        <tr>
          <td><code style="color: var(--primary-light); font-weight: 600;">#${shortId}</code></td>
          <td>${timeStr}</td>
          <td><strong style="color: #fff;">${evt.local_detection?.persons ?? 0}</strong></td>
          <td><span class="badge ${eventType === 'WASTE_DISPOSAL' ? 'rose' : 'cyan'}">${eventType}</span></td>
          <td><strong>${conf}</strong></td>
          <td><span class="badge ${decisionClass}">${decision}</span></td>
          <td><small>${actionCompleted}</small></td>
        </tr>
      `;
    }).join('');
  },

  /**
   * Actualiza los badges de banderas booleanas tras un diagnóstico de prueba.
   */
  updateDiagnosticFlags(analysis, decision) {
    if (!analysis) return;

    const flagPerson = document.getElementById('flag-person');
    const valFlagPerson = document.getElementById('val-flag-person');
    const flagSuspect = document.getElementById('flag-suspect');
    const valFlagSuspect = document.getElementById('val-flag-suspect');
    const flagCompleted = document.getElementById('flag-completed');
    const valFlagCompleted = document.getElementById('val-flag-completed');
    const decisionBadge = document.getElementById('decision-status-badge');

    if (flagPerson && valFlagPerson) {
      valFlagPerson.textContent = analysis.person_detected ? 'Sí' : 'No';
      flagPerson.className = `flag-badge ${analysis.person_detected ? 'active' : ''}`;
    }

    if (flagSuspect && valFlagSuspect) {
      valFlagSuspect.textContent = analysis.suspected_disposal ? 'Sí' : 'No';
      flagSuspect.className = `flag-badge ${analysis.suspected_disposal ? 'active' : ''}`;
    }

    if (flagCompleted && valFlagCompleted) {
      valFlagCompleted.textContent = analysis.action_completed ? 'Sí (Consumado)' : 'No';
      flagCompleted.className = `flag-badge ${analysis.action_completed ? 'warn-active' : ''}`;
    }

    if (decisionBadge && decision) {
      decisionBadge.textContent = decision;
      if (decision === 'WARN') decisionBadge.className = 'badge rose';
      else if (decision === 'LOG_ONLY') decisionBadge.className = 'badge amber';
      else decisionBadge.className = 'badge emerald';
    }
  }
};
