/**
 * Punto de Entrada del Frontend (App Initialization)
 * ==================================================
 * 
 * Se ejecuta al cargarse el DOM en el navegador. Inicializa el cliente WebSocket,
 * vincula los escuchadores de eventos a los botones e invoca la primera carga de datos.
 */

document.addEventListener('DOMContentLoaded', () => {
  console.log('🚀 Inicializando interfaz de Huallaga AI Monitor...');

  // 1. Instanciar y conectar el cliente WebSocket para actualizaciones reactivas
  const ws = new WSClient((payload) => {
    if (payload.type === 'system_state') {
      Dashboard.updateStatus(payload.data);
    }
  });
  ws.connect();

  // 2. Asociar el botón de refresco manual de la tabla de eventos
  const refreshBtn = document.getElementById('btn-refresh-events');
  if (refreshBtn) {
    refreshBtn.addEventListener('click', () => {
      Dashboard.renderEventsTable();
    });
  }

  // 3. Botón: Iniciar pipeline de monitoreo
  const startBtn = document.getElementById('btn-start-pipeline');
  if (startBtn) {
    startBtn.addEventListener('click', async () => {
      startBtn.disabled = true;
      startBtn.textContent = '⏳ Iniciando...';
      const result = await API.startPipeline();
      if (result) {
        console.log('Pipeline:', result.message);
      }
      startBtn.disabled = false;
      startBtn.textContent = '▶ Iniciar Monitoreo';
    });
  }

  // 4. Botón: Detener pipeline de monitoreo
  const stopBtn = document.getElementById('btn-stop-pipeline');
  if (stopBtn) {
    stopBtn.addEventListener('click', async () => {
      stopBtn.disabled = true;
      stopBtn.textContent = '⏳ Deteniendo...';
      const result = await API.stopPipeline();
      if (result) {
        console.log('Pipeline:', result.message);
      }
      stopBtn.disabled = false;
      stopBtn.textContent = '⏹ Detener Monitoreo';
    });
  }

  // 5. Botón: Probar alerta de voz
  const testSpeechBtn = document.getElementById('btn-test-speech');
  if (testSpeechBtn) {
    testSpeechBtn.addEventListener('click', async () => {
      testSpeechBtn.disabled = true;
      testSpeechBtn.textContent = '🔊 Generando...';
      const result = await API.testSpeech();
      if (result) {
        console.log('TTS resultado:', result);
      }
      testSpeechBtn.disabled = false;
      testSpeechBtn.textContent = '🔊 Probar Alerta';
    });
  }

  // 6. Cargar la tabla de eventos inicial mediante petición REST
  Dashboard.renderEventsTable();
});
