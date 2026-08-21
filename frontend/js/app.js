document.addEventListener('DOMContentLoaded', () => {
  console.log('Huallaga AI Monitor Frontend Inicializado.');

  // Inicializar cliente WebSocket
  const ws = new WSClient((payload) => {
    if (payload.type === 'system_state') {
      Dashboard.updateStatus(payload.data);
    }
  });
  ws.connect();

  // Botón de refresco manual de la tabla de registros
  const refreshBtn = document.getElementById('btn-refresh-events');
  if (refreshBtn) {
    refreshBtn.addEventListener('click', () => {
      Dashboard.renderEventsTable();
    });
  }

  // Cargar eventos iniciales
  Dashboard.renderEventsTable();
});
