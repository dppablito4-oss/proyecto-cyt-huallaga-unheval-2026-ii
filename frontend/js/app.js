/**
 * Punto de Entrada del Frontend (App Initialization)
 * ==================================================
 * Inicializa el cliente WebSocket, vincula los escuchadores de eventos a los botones
 * y maneja las interacciones del usuario.
 */

document.addEventListener('DOMContentLoaded', () => {
  console.log('Inicializando interfaz simplificada de Huallaga AI Monitor...');

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

  // 5. Botón: Probar voz TTS rápida (Onyx)
  const testSpeechBtn = document.getElementById('btn-test-speech');
  if (testSpeechBtn) {
    testSpeechBtn.addEventListener('click', async () => {
      testSpeechBtn.disabled = true;
      testSpeechBtn.textContent = 'Sintetizando...';
      const result = await API.testSpeech('Prueba del sistema de vigilancia ambiental del río Huallaga.');
      if (result) {
        console.log('TTS resultado:', result);
      }
      testSpeechBtn.disabled = false;
      testSpeechBtn.textContent = 'Probar Voz';
    });
  }

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

  // 7. Carga inicial del estado por REST
  API.getStatus().then(data => {
    if (data) {
      Dashboard.updateStatus(data);
    }
  });
});
