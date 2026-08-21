/**
 * Punto de Entrada del Frontend (App Initialization)
 * ==================================================
 * 
 * Se ejecuta al cargarse el DOM en el navegador. Inicializa el cliente WebSocket,
 * el reloj HUD en tiempo real, vincula los escuchadores de eventos a los botones
 * e invoca la primera carga de datos.
 */

document.addEventListener('DOMContentLoaded', () => {
  console.log('🚀 Inicializando interfaz moderna de Huallaga AI Monitor...');

  // 1. Iniciar reloj HUD en tiempo real (cada segundo)
  Dashboard.updateClock();
  setInterval(() => Dashboard.updateClock(), 1000);

  // 2. Instanciar y conectar el cliente WebSocket para actualizaciones reactivas
  const ws = new WSClient((payload) => {
    if (payload.type === 'system_state') {
      Dashboard.updateStatus(payload.data);
    }
  });
  ws.connect();

  // 3. Botón: Refresco manual de la tabla de eventos
  const refreshBtn = document.getElementById('btn-refresh-events');
  if (refreshBtn) {
    refreshBtn.addEventListener('click', async () => {
      refreshBtn.disabled = true;
      await Dashboard.renderEventsTable();
      refreshBtn.disabled = false;
    });
  }

  // 4. Botón: Iniciar pipeline de monitoreo
  const startBtn = document.getElementById('btn-start-pipeline');
  if (startBtn) {
    startBtn.addEventListener('click', async () => {
      startBtn.disabled = true;
      startBtn.innerHTML = `
        <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor" class="spin"><path d="M12 2v4m0 12v4M4.93 4.93l2.83 2.83m8.48 8.48l2.83 2.83M2 12h4m12 0h4M4.93 19.07l2.83-2.83m8.48-8.48l2.83-2.83"/></svg>
        Iniciando...
      `;
      const result = await API.startPipeline();
      if (result) {
        console.log('Pipeline status:', result.message);
      }
      startBtn.disabled = false;
      startBtn.innerHTML = `
        <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><path d="M8 5v14l11-7z"/></svg>
        Iniciar Monitoreo
      `;
    });
  }

  // 5. Botón: Detener pipeline de monitoreo
  const stopBtn = document.getElementById('btn-stop-pipeline');
  if (stopBtn) {
    stopBtn.addEventListener('click', async () => {
      stopBtn.disabled = true;
      stopBtn.innerHTML = `
        <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><path d="M6 6h12v12H6z"/></svg>
        Deteniendo...
      `;
      const result = await API.stopPipeline();
      if (result) {
        console.log('Pipeline status:', result.message);
      }
      stopBtn.disabled = false;
      stopBtn.innerHTML = `
        <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><path d="M6 6h12v12H6z"/></svg>
        Detener
      `;
    });
  }

  // 6. Botón: Probar voz TTS rápida (Onyx)
  const testSpeechBtn = document.getElementById('btn-test-speech');
  if (testSpeechBtn) {
    testSpeechBtn.addEventListener('click', async () => {
      testSpeechBtn.disabled = true;
      testSpeechBtn.textContent = '🔊 Sintetizando Onyx...';
      const result = await API.testSpeech();
      if (result) {
        console.log('TTS resultado:', result);
      }
      testSpeechBtn.disabled = false;
      testSpeechBtn.innerHTML = `
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M11 5L6 9H2v6h4l5 4V5z"/><path d="M19.07 4.93a10 10 0 0 1 0 14.14M15.54 8.46a5 5 0 0 1 0 7.07"/></svg>
        Probar Voz (Onyx)
      `;
    });
  }

  // 7. Botón: Reproducir texto personalizado en el altavoz
  const playCustomBtn = document.getElementById('btn-play-custom');
  const customTextInput = document.getElementById('custom-speech-text');
  if (playCustomBtn && customTextInput) {
    playCustomBtn.addEventListener('click', async () => {
      const text = customTextInput.value.trim();
      if (!text) return;
      playCustomBtn.disabled = true;
      playCustomBtn.textContent = '⏳ Sintetizando...';
      const result = await API.testSpeech(text);
      if (result) {
        console.log('TTS personalizado:', result);
      }
      playCustomBtn.disabled = false;
      playCustomBtn.textContent = '🔊 Reproducir';
    });
  }

  // 8. Botón: Probar inferencia multimodal con GPT-5.6 Luna
  const testAiBtn = document.getElementById('btn-test-ai');
  if (testAiBtn) {
    testAiBtn.addEventListener('click', async () => {
      testAiBtn.disabled = true;
      testAiBtn.innerHTML = `
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2a10 10 0 1 0 10 10A10 10 0 0 0 12 2zm0 18a8 8 0 1 1 8-8 8 8 0 0 1-8 8z"/><path d="M12 6v6l4 2"/></svg>
        Analizando Luna...
      `;
      const result = await API.testAnalysis(true, 3);
      if (result && result.analysis) {
        console.log('Resultado prueba IA:', result);
        
        // Actualizar descripción y flags
        const diagEl = document.getElementById('analysis-diagnosis');
        if (diagEl) {
          diagEl.textContent = result.analysis.description || 'Análisis completado sin observaciones.';
        }
        Dashboard.updateDiagnosticFlags(result.analysis, result.decision);
      }
      testAiBtn.disabled = false;
      testAiBtn.innerHTML = `
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2a10 10 0 1 0 10 10A10 10 0 0 0 12 2zm0 18a8 8 0 1 1 8-8 8 8 0 0 1-8 8z"/><path d="M12 6v6l4 2"/></svg>
        Inferencia GPT-5.6 Luna
      `;
    });
  }

  // 9. Cargar la tabla de eventos inicial mediante petición REST
  Dashboard.renderEventsTable();
});
