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

  // 3. Cargar la tabla de eventos inicial mediante petición REST
  Dashboard.renderEventsTable();
});
