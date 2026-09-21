const DetectorConfig = {
  async init() {
    this.input = document.getElementById('detection-classes-input');
    this.button = document.getElementById('btn-update-detection-classes');
    this.status = document.getElementById('detection-classes-status');
    if (!this.input || !this.button) return;
    this.button.addEventListener('click', () => this.update());
    await this.refresh();
  },

  async refresh() {
    const data = await API.getDetectionClasses();
    if (!data) {
      this.setStatus('No se pudo consultar el vocabulario actual.');
      return null;
    }
    if (document.activeElement !== this.input) this.input.value = (data.classes || []).join(', ');
    this.setStatus(data.message || 'Vocabulario listo.');
    return data;
  },

  async update() {
    const classes = this.input.value.split(',').map(value => value.trim()).filter(Boolean);
    if (!classes.length) {
      this.input.focus();
      this.setStatus('Escribe al menos una clase de residuo.');
      return;
    }
    this.button.disabled = true;
    this.button.textContent = 'Preparando…';
    this.setStatus('Solicitando la actualización en segundo plano…');
    const result = await API.updateDetectionClasses(classes);
    if (result?.error) {
      this.setStatus(`No se pudo actualizar: ${result.error}`);
      this.finish();
      return;
    }
    await this.pollUntilReady();
  },

  async pollUntilReady() {
    const started = Date.now();
    while (Date.now() - started < 120000) {
      const data = await this.refresh();
      if (!data || data.status === 'error' || data.status === 'ready') {
        this.finish();
        return;
      }
      await new Promise(resolve => setTimeout(resolve, 1200));
    }
    this.setStatus('La preparación continúa en segundo plano; vuelve a consultar en unos segundos.');
    this.finish();
  },

  finish() {
    this.button.disabled = false;
    this.button.textContent = 'Actualizar detector';
  },

  setStatus(message) {
    if (this.status) this.status.textContent = message;
  }
};
