/**
 * Punto de Entrada del Frontend (App Initialization)
 * ==================================================
 * Inicializa el cliente WebSocket, vincula los escuchadores de eventos a los botones
 * y maneja las interacciones del usuario.
 */

document.addEventListener('DOMContentLoaded', () => {
  console.log('Inicializando interfaz simplificada de SIVARH...');

  // 1. Instanciar y conectar el cliente WebSocket para actualizaciones reactivas continuas
  const ws = new WSClient((payload) => {
    if (payload.type === 'system_state') {
      Dashboard.updateStatus(payload.data);
    }
  });
  ws.connect();

  // 2. Botón: Iniciar pipeline de monitoreo
  const startBtn = document.getElementById('btn-start-pipeline');
  if (startBtn) {
    startBtn.addEventListener('click', async () => {
      startBtn.disabled = true;
      startBtn.textContent = 'Iniciando...';
      const result = await API.startPipeline();
      if (result) {
        console.log('Pipeline status:', result.message);
      }
      startBtn.disabled = false;
      startBtn.textContent = 'Iniciar';
    });
  }

  const manualCaptureBtn = document.getElementById('btn-start-manual-recognition');
  const manualSendBtn = document.getElementById('btn-send-manual-images');
  if (manualCaptureBtn && manualSendBtn) {
    manualCaptureBtn.addEventListener('click', async () => {
      manualCaptureBtn.disabled = true;
      manualSendBtn.disabled = true;
      manualCaptureBtn.textContent = 'Capturando 0/4...';
      const result = await API.startManualRecognition();
      if (!result || !result.accepted) {
        alert(result?.message || 'No se pudo iniciar la captura manual.');
        manualCaptureBtn.disabled = false;
        manualCaptureBtn.textContent = 'Iniciar reconocimiento';
      }
    });

    manualSendBtn.addEventListener('click', async () => {
      manualSendBtn.disabled = true;
      manualSendBtn.textContent = 'Enviando a IA...';
      const result = await API.sendManualImages();
      if (!result || !result.accepted) {
        alert(result?.message || 'No se pudo enviar la secuencia a la IA.');
        manualSendBtn.disabled = false;
        manualSendBtn.textContent = 'Enviar imágenes a IA';
      }
    });
  }

  // 3. Botón: Detener pipeline de monitoreo
  const stopBtn = document.getElementById('btn-stop-pipeline');
  if (stopBtn) {
    stopBtn.addEventListener('click', async () => {
      stopBtn.disabled = true;
      stopBtn.textContent = 'Deteniendo...';
      const result = await API.stopPipeline();
      if (result) {
        console.log('Pipeline status:', result.message);
      }
      stopBtn.disabled = false;
      stopBtn.textContent = 'Detener';
    });
  }

  // 4. Selector: Cambiar fuente de cámara en tiempo real
  const cameraSelect = document.getElementById('camera-source-select');
  if (cameraSelect) {
    cameraSelect.addEventListener('change', async (e) => {
      const newSource = e.target.value;
      cameraSelect.disabled = true;
      console.log(`Cambiando dispositivo de video a: ${newSource}...`);
      
      const result = await API.switchCamera(newSource);
      if (result && result.success) {
        console.log(`Cámara cambiada exitosamente a: ${newSource}`);
        // Refrescar stream de video con timestamp para forzar reconexión limpia en el navegador
        const liveStream = document.getElementById('live-stream');
        if (liveStream && liveStream.style.display !== 'none') {
          liveStream.src = `/api/cameras/stream?t=${Date.now()}`;
        }
      } else {
        alert('No se pudo inicializar la cámara seleccionada. Verifica que el dispositivo esté conectado.');
      }
      cameraSelect.disabled = false;
    });
  }

  // 5. Panel de prueba: Luna genera un guion desde una descripción y lo envía al TTS
  const testSpeechBtn = document.getElementById('btn-test-speech');
  const speechEventDescription = document.getElementById('speech-event-description');
  const speechVoice = document.getElementById('speech-voice');
  const speechSpeed = document.getElementById('speech-speed');
  const speechSpeedValue = document.getElementById('speech-speed-value');
  const speechTestStatus = document.getElementById('speech-test-status');
  const speechGeneratedResult = document.getElementById('speech-generated-result');
  const speechGeneratedText = document.getElementById('speech-generated-text');
  if (speechSpeed && speechSpeedValue) {
    const updateSpeedLabel = () => { speechSpeedValue.value = `${Number(speechSpeed.value).toFixed(2)}x`; };
    speechSpeed.addEventListener('input', updateSpeedLabel);
    updateSpeedLabel();
  }
  if (testSpeechBtn) {
    testSpeechBtn.addEventListener('click', async () => {
      const eventDescription = speechEventDescription?.value.trim();
      if (!eventDescription) {
        speechEventDescription?.focus();
        if (speechTestStatus) speechTestStatus.textContent = 'Describe primero el evento de prueba.';
        return;
      }
      testSpeechBtn.disabled = true;
      testSpeechBtn.textContent = 'Luna está redactando...';
      if (speechTestStatus) speechTestStatus.textContent = 'Generando el guion y preparando la voz...';
      if (speechGeneratedResult) speechGeneratedResult.hidden = true;
      const result = await API.generateSpeechFromEvent(eventDescription, speechVoice?.value, Number(speechSpeed?.value));
      if (result?.audio_generated) {
        if (speechGeneratedText) speechGeneratedText.textContent = result.generated_script;
        if (speechGeneratedResult) speechGeneratedResult.hidden = false;
        if (speechTestStatus) speechTestStatus.textContent = `Reproducido: ${result.voice} · ${Number(result.speed).toFixed(2)}x`;
      } else if (speechTestStatus) {
        speechTestStatus.textContent = result?.error || 'No se pudo generar el guion o el audio.';
      }
      testSpeechBtn.disabled = false;
      testSpeechBtn.textContent = 'Generar guion y reproducir';
    });
  }

  const alertModal = document.getElementById('alert-confirmation-modal');
  const emitAlertBtn = document.getElementById('btn-emit-alert');
  const dismissAlertBtn = document.getElementById('btn-dismiss-alert');
  const alertVoiceSummary = document.getElementById('alert-modal-voice-summary');
  const alertEmissionStatus = document.getElementById('alert-emission-status');
  const updateAlertVoiceSummary = () => {
    if (alertVoiceSummary) alertVoiceSummary.textContent = `Voz sintética OpenAI TTS: ${speechVoice?.value || 'onyx'} · Velocidad: ${Number(speechSpeed?.value || 1.1).toFixed(2)}x`;
  };
  speechVoice?.addEventListener('change', updateAlertVoiceSummary);
  speechSpeed?.addEventListener('input', updateAlertVoiceSummary);
  updateAlertVoiceSummary();
  dismissAlertBtn?.addEventListener('click', () => Dashboard.dismissPendingAlert());
  alertModal?.addEventListener('click', (event) => {
    if (event.target === alertModal) Dashboard.dismissPendingAlert();
  });
  emitAlertBtn?.addEventListener('click', async () => {
    emitAlertBtn.disabled = true;
    dismissAlertBtn.disabled = true;
    emitAlertBtn.textContent = 'Emitiendo...';
    if (alertEmissionStatus) alertEmissionStatus.textContent = 'Generando la voz y reproduciendo por el altavoz...';
    const result = await API.emitManualAlert(speechVoice?.value || 'onyx', Number(speechSpeed?.value || 1.1));
    if (result?.accepted) {
      if (alertEmissionStatus) alertEmissionStatus.textContent = 'Alerta emitida correctamente.';
      Dashboard.dismissPendingAlert();
    } else if (alertEmissionStatus) {
      alertEmissionStatus.textContent = result?.message || 'No se pudo emitir la alerta.';
    }
    emitAlertBtn.disabled = false;
    dismissAlertBtn.disabled = false;
    emitAlertBtn.textContent = 'Emitir alerta';
  });

  // 6. Botón: Limpiar consola de logs
  const clearLogsBtn = document.getElementById('btn-clear-logs');
  if (clearLogsBtn) {
    clearLogsBtn.addEventListener('click', async () => {
      clearLogsBtn.disabled = true;
      await API.clearLogs();
      const container = document.getElementById('live-logs-container');
      if (container) {
        container.innerHTML = `
          <div class="log-line log-INFO">
            <span class="log-time">[${new Date().toLocaleTimeString()}]</span>
            <span class="log-text">Consola limpiada.</span>
          </div>
        `;
      }
      clearLogsBtn.disabled = false;
    });
  }

  const exportPdfBtn = document.getElementById('btn-export-pdf');
  if (exportPdfBtn) {
    exportPdfBtn.addEventListener('click', async () => {
      exportPdfBtn.disabled = true;
      exportPdfBtn.textContent = 'Generando PDF...';
      const result = await API.exportEvidencePdf();
      if (result) {
        const url = URL.createObjectURL(result.blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = result.filename;
        document.body.appendChild(link);
        link.click();
        link.remove();
        URL.revokeObjectURL(url);
      } else {
        alert('No se pudo generar el reporte PDF.');
      }
      exportPdfBtn.disabled = false;
      exportPdfBtn.textContent = 'Exportar PDF';
    });
  }

  // 8. Carga inicial del estado por REST
  API.getStatus().then(data => {
    if (data) {
      Dashboard.updateStatus(data);
    }
  });
});
