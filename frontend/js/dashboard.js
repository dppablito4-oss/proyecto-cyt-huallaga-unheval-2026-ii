const Dashboard = {
  lastLogsCount: 0,
  lastLogsSignature: '',
  previewKey: '',
  pendingAlertKey: '',
  dismissedAlertKey: '',

  updateStatus(data) {
    if (!data) return;

    this.updateSystemState(data);
    this.updateCameraState(data);

    this.setText('persons-count', data.persons_detected ?? 0);
    this.setText('fps-badge', `${Number(data.fps ?? 0).toFixed(1)} FPS`);
    this.updateCooldown(data.cooldown_remaining ?? 0);
    this.updateManualRecognition(data);
    this.updateAiState(data);
    this.updateDecision(data.last_decision);
    this.setText('last-diagnosis-text', data.last_diagnosis || 'Captura una secuencia manual para iniciar el análisis.');
    this.setText('warning-text', data.last_warning_message || 'Sin advertencias emitidas.');
    this.renderPreview(data.analysis_preview_urls || [], data.ai_status);
    this.updatePendingAlert(data);

    if (Array.isArray(data.logs)) this.renderLogs(data.logs);
  },

  setText(id, value) {
    const element = document.getElementById(id);
    if (element) element.textContent = value;
  },

  updateSystemState(data) {
    const dot = document.querySelector('.system-state .dot');
    if (dot) dot.className = `dot ${data.running ? 'dot-green' : 'dot-red'}`;
    this.setText('system-status-text', data.running ? 'Sistema activo' : 'Sistema detenido');
  },

  updateCameraState(data) {
    const stream = document.getElementById('live-stream');
    const placeholder = document.getElementById('video-placeholder');
    if (data.camera_connected) {
      this.setText('camera-status-text', `Conectada (${data.camera_source})`);
      if (stream) {
        stream.style.display = 'block';
        if (!stream.src || !stream.src.includes('/api/cameras/stream')) stream.src = '/api/cameras/stream';
      }
      if (placeholder) placeholder.style.display = 'none';
    } else {
      this.setText('camera-status-text', 'En espera');
      if (stream) { stream.style.display = 'none'; stream.src = ''; }
      if (placeholder) placeholder.style.display = 'block';
    }

    const select = document.getElementById('camera-source-select');
    if (select && document.activeElement !== select && data.camera_source !== undefined) select.value = String(data.camera_source);
  },

  updateCooldown(remaining) {
    if (document.getElementById('btn-start-manual-recognition')) {
      this.setText('cooldown-status', 'Manual');
      this.setText('cooldown-footer', 'Modo manual: sin espera automática');
      return;
    }
    const ready = remaining <= 0;
    const text = ready ? 'Listo' : `${Math.ceil(remaining)} s`;
    this.setText('cooldown-status', text);
    this.setText('cooldown-footer', ready ? 'Tiempo de espera: listo' : `Tiempo de espera: ${text}`);
  },

  updateManualRecognition(data) {
    const captureBtn = document.getElementById('btn-start-manual-recognition');
    const sendBtn = document.getElementById('btn-send-manual-images');
    if (!captureBtn || !sendBtn) return;

    const captured = Number(data.manual_frames_captured ?? 0);
    const ready = Boolean(data.manual_sequence_ready);
    if (ready) {
      captureBtn.disabled = false;
      captureBtn.textContent = 'Nueva secuencia';
      sendBtn.disabled = false;
      sendBtn.textContent = 'Enviar imágenes a IA';
    } else if (captured > 0) {
      captureBtn.disabled = true;
      captureBtn.textContent = `Capturando ${captured}/4...`;
      sendBtn.disabled = true;
      sendBtn.textContent = 'Enviar imágenes a IA';
    } else if (!data.active_event) {
      captureBtn.disabled = false;
      captureBtn.textContent = 'Iniciar reconocimiento';
      if (sendBtn.textContent !== 'Enviando a IA...') sendBtn.disabled = true;
    }
  },

  updateAiState(data) {
    let label = 'En reposo';
    let process = data.active_event ? 'Capturando secuencia' : 'Esperando deteccion';
    if (data.ai_status === 'sending' || data.ai_status === 'analyzing') {
      label = 'Consultando IA';
      process = 'Detectado: consultando IA';
    } else if (data.ai_status === 'completed') {
      label = 'Analisis completado';
      process = 'Analisis completado';
    }
    this.setText('ai-status-text', label);
    this.setText('process-status-text', process);
    this.setText('ai-latency-text', data.ai_latency == null ? '-- s' : `${Number(data.ai_latency).toFixed(2)} s`);
  },

  updateDecision(decision) {
    const badge = document.getElementById('last-decision-badge');
    if (!badge) return;
    const labels = { WARN: 'Alerta detectada', LOG_ONLY: 'Registrado', IGNORE: 'Sin alerta' };
    badge.textContent = labels[decision] || 'En espera';
    badge.className = `decision-badge ${decision === 'WARN' ? 'warn' : decision === 'LOG_ONLY' ? 'log-only' : 'ignore'}`;
  },

  updatePendingAlert(data) {
    const modal = document.getElementById('alert-confirmation-modal');
    const message = document.getElementById('alert-modal-message');
    if (!modal || !message) return;

    const key = `${data.last_event_time || ''}|${data.last_warning_message || ''}`;
    this.pendingAlertKey = data.alert_pending ? key : '';
    message.textContent = data.last_warning_message || 'Luna no generó un mensaje de advertencia.';
    if (data.alert_pending && key !== this.dismissedAlertKey) {
      modal.hidden = false;
      document.getElementById('btn-emit-alert')?.focus();
    } else if (!data.alert_pending) {
      modal.hidden = true;
    }
  },

  dismissPendingAlert() {
    this.dismissedAlertKey = this.pendingAlertKey;
    const modal = document.getElementById('alert-confirmation-modal');
    if (modal) modal.hidden = true;
  },

  renderPreview(urls, aiStatus) {
    const container = document.getElementById('analysis-preview');
    const status = document.getElementById('sequence-status-text');
    if (!container || !status) return;

    const key = urls.join('|');
    status.textContent = urls.length ? (aiStatus === 'sending' || aiStatus === 'analyzing' ? 'Consultando IA' : `${urls.length} fotogramas preparados`) : 'Aun no hay una secuencia';
    if (key === this.previewKey) return;
    this.previewKey = key;
    container.replaceChildren();

    if (!urls.length) {
      const message = document.createElement('p');
      message.textContent = 'Presiona “Iniciar reconocimiento” para capturar cuatro imágenes.';
      container.appendChild(message);
      return;
    }

    urls.forEach((url, index) => {
      const figure = document.createElement('figure');
      figure.className = 'preview-frame';
      const image = document.createElement('img');
      image.src = `${url}?v=${encodeURIComponent(this.previewKey)}`;
      image.alt = `Fotograma ${index + 1} de la secuencia enviada a la IA`;
      const caption = document.createElement('span');
      caption.textContent = `Fotograma ${index + 1}`;
      figure.append(image, caption);
      container.appendChild(figure);
    });
  },

  renderLogs(logs) {
    const container = document.getElementById('live-logs-container');
    if (!container) return;
    this.setText('log-count-text', `${logs.length} registros`);

    const signature = logs.map(log => `${log.time}|${log.level}|${log.message}`).join('\n');
    if (signature === this.lastLogsSignature) return;

    const previousScrollTop = container.scrollTop;
    const previousScrollHeight = container.scrollHeight;
    const isShowingLatest = previousScrollTop <= 1;
    container.replaceChildren();

    if (!logs.length) {
      this.appendLog(container, { time: '--:--:--', level: 'INFO', message: 'Sin registros. Esperando actividad.' });
    } else {
      logs.slice().reverse().forEach(log => this.appendLog(container, log));
    }
    // New entries are placed at the top. Preserve the user's current reading position.
    container.scrollTop = isShowingLatest
      ? 0
      : previousScrollTop + (container.scrollHeight - previousScrollHeight);
    this.lastLogsCount = logs.length;
    this.lastLogsSignature = signature;
  },

  appendLog(container, log) {
    const line = document.createElement('div');
    line.className = `log-line log-${log.level || 'INFO'}`;
    const time = document.createElement('span');
    time.className = 'log-time';
    time.textContent = `[${log.time || '--:--:--'}]`;
    const message = document.createElement('span');
    message.className = 'log-text';
    message.textContent = log.message || '';
    line.append(time, message);
    container.appendChild(line);
  }
};
