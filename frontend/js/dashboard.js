const Dashboard = {
  updateStatus(data) {
    if (!data) return;

    // Actualizar indicador del sistema
    const sysDot = document.querySelector('#system-status-pill .status-dot');
    const sysText = document.getElementById('system-status-text');
    if (data.running) {
      sysDot.className = 'status-dot green';
      sysText.textContent = 'Sistema: Activo';
    } else {
      sysDot.className = 'status-dot red';
      sysText.textContent = 'Sistema: Inactivo';
    }

    // Actualizar indicador de cámara
    const camDot = document.querySelector('#camera-status-pill .status-dot');
    const camText = document.getElementById('camera-status-text');
    if (data.camera_connected) {
      camDot.className = 'status-dot green';
      camText.textContent = `Cámara: ${data.camera_source}`;
    } else {
      camDot.className = 'status-dot yellow';
      camText.textContent = 'Cámara: Standby / Simulación';
    }

    // Actualizar estadísticas de detección
    document.getElementById('persons-count').textContent = data.persons_detected ?? 0;
    document.getElementById('fps-badge').textContent = `${(data.fps ?? 0).toFixed(1)} FPS`;
    document.getElementById('active-event-state').textContent = data.active_event ? 'Sí (En proceso)' : 'No';
    document.getElementById('ai-model-name').textContent = data.ai_model || 'gpt-4o';

    // Actualizar diagnóstico del último evento
    if (data.last_event_time) {
      document.getElementById('last-event-time').textContent = new Date(data.last_event_time).toLocaleTimeString();
    }
    if (data.last_analysis_confidence !== null && data.last_analysis_confidence !== undefined) {
      const confPercent = Math.round(data.last_analysis_confidence * 100);
      document.getElementById('confidence-bar').style.width = `${confPercent}%`;
      document.getElementById('confidence-percent').textContent = `${confPercent}%`;
    }
    if (data.last_warning_message) {
      document.getElementById('warning-text').textContent = `"${data.last_warning_message}"`;
    }
  },

  async renderEventsTable() {
    const events = await API.getEvents(10);
    const tbody = document.getElementById('events-table-body');
    if (!events || events.length === 0) {
      tbody.innerHTML = '<tr><td colspan="6" class="text-center text-muted">No se han registrado eventos todavía.</td></tr>';
      return;
    }

    tbody.innerHTML = events.map(evt => `
      <tr>
        <td><code>${evt.id.substring(0, 8)}...</code></td>
        <td>${new Date(evt.started_at).toLocaleTimeString()}</td>
        <td>${evt.local_detection?.persons ?? 0}</td>
        <td>${evt.analysis?.confidence ? Math.round(evt.analysis.confidence * 100) + '%' : 'N/A'}</td>
        <td><span class="badge ${evt.decision === 'WARN' ? 'warning' : ''}">${evt.decision || 'N/A'}</span></td>
        <td><span class="badge blue">${evt.status}</span></td>
      </tr>
    `).join('');
  }
};
