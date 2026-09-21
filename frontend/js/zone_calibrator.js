const ZoneCalibrator = {
  zones: {},
  priorities: { observation: 0, riverbank: 10, water: 20 },
  colors: { observation: '#38bdf8', riverbank: '#f59e0b', water: '#22c55e' },
  activeZone: 'observation',
  open: false,

  async init() {
    this.canvas = document.getElementById('zone-calibration-canvas');
    this.stream = document.getElementById('live-stream');
    this.controls = document.getElementById('zone-calibration-controls');
    this.toggleButton = document.getElementById('btn-zone-calibration');
    this.select = document.getElementById('zone-calibration-select');
    this.status = document.getElementById('zone-calibration-status');
    this.count = document.getElementById('zone-calibration-count');
    if (!this.canvas || !this.stream || !this.controls || !this.toggleButton) return;

    this.toggleButton.addEventListener('click', () => this.toggle());
    document.getElementById('btn-zone-cancel')?.addEventListener('click', () => this.close());
    document.getElementById('btn-zone-undo')?.addEventListener('click', () => this.undo());
    document.getElementById('btn-zone-clear')?.addEventListener('click', () => this.clear());
    document.getElementById('btn-zone-save')?.addEventListener('click', () => this.save());
    this.select?.addEventListener('change', () => {
      this.activeZone = this.select.value;
      this.render();
    });
    this.canvas.addEventListener('pointerdown', event => this.addFromPointer(event));
    this.canvas.addEventListener('keydown', event => this.handleKeyboard(event));
    new ResizeObserver(() => this.render()).observe(this.canvas.parentElement);
    await this.load();
  },

  async load() {
    const definitions = await API.getZones();
    this.zones = {};
    definitions.forEach(zone => {
      this.zones[zone.name] = zone.polygon.map(point => ({ x: point.x, y: point.y }));
      this.priorities[zone.name] = Number(zone.priority || 0);
    });
    this.render();
  },

  toggle() {
    if (this.open) this.close();
    else this.show();
  },

  show() {
    this.open = true;
    this.canvas.hidden = false;
    this.controls.hidden = false;
    this.toggleButton.setAttribute('aria-expanded', 'true');
    this.toggleButton.textContent = 'Calibrando';
    this.render();
    this.canvas.focus();
  },

  close() {
    this.open = false;
    this.canvas.hidden = true;
    this.controls.hidden = true;
    this.toggleButton.setAttribute('aria-expanded', 'false');
    this.toggleButton.textContent = 'Calibrar zonas';
    this.toggleButton.focus();
  },

  imageRect(width, height) {
    const sourceWidth = this.stream.naturalWidth || 16;
    const sourceHeight = this.stream.naturalHeight || 9;
    const scale = Math.min(width / sourceWidth, height / sourceHeight);
    const renderWidth = sourceWidth * scale;
    const renderHeight = sourceHeight * scale;
    return {
      x: (width - renderWidth) / 2,
      y: (height - renderHeight) / 2,
      width: renderWidth,
      height: renderHeight
    };
  },

  addFromPointer(event) {
    if (!this.open) return;
    const bounds = this.canvas.getBoundingClientRect();
    const image = this.imageRect(bounds.width, bounds.height);
    const x = event.clientX - bounds.left;
    const y = event.clientY - bounds.top;
    if (x < image.x || y < image.y || x > image.x + image.width || y > image.y + image.height) {
      this.setStatus('Marca los puntos dentro de la imagen visible.');
      return;
    }
    const points = this.zones[this.activeZone] || [];
    points.push({
      x: Math.max(0, Math.min(1, (x - image.x) / image.width)),
      y: Math.max(0, Math.min(1, (y - image.y) / image.height))
    });
    this.zones[this.activeZone] = points;
    this.setStatus(`${this.label(this.activeZone)}: punto ${points.length} añadido.`);
    this.render();
  },

  handleKeyboard(event) {
    const points = this.zones[this.activeZone] || [];
    if (event.key === 'Enter' && !points.length) {
      this.zones[this.activeZone] = [{ x: 0.5, y: 0.5 }];
      this.setStatus('Punto central añadido. Usa las flechas para ajustarlo.');
      this.render();
      event.preventDefault();
      return;
    }
    if (!points.length || !['ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown'].includes(event.key)) return;
    const point = points[points.length - 1];
    const delta = event.shiftKey ? 0.05 : 0.01;
    if (event.key === 'ArrowLeft') point.x -= delta;
    if (event.key === 'ArrowRight') point.x += delta;
    if (event.key === 'ArrowUp') point.y -= delta;
    if (event.key === 'ArrowDown') point.y += delta;
    point.x = Math.max(0, Math.min(1, point.x));
    point.y = Math.max(0, Math.min(1, point.y));
    this.render();
    event.preventDefault();
  },

  undo() {
    const points = this.zones[this.activeZone] || [];
    points.pop();
    this.zones[this.activeZone] = points;
    this.setStatus(`${this.label(this.activeZone)}: último punto eliminado.`);
    this.render();
  },

  clear() {
    this.zones[this.activeZone] = [];
    this.setStatus(`${this.label(this.activeZone)} lista para dibujarse de nuevo.`);
    this.render();
  },

  async save() {
    const definitions = Object.entries(this.zones)
      .filter(([, polygon]) => polygon.length >= 3)
      .map(([name, polygon]) => ({ name, polygon, priority: this.priorities[name] || 0 }));
    if (!definitions.length) {
      this.setStatus('Dibuja al menos una zona con tres puntos antes de guardar.');
      return;
    }
    const button = document.getElementById('btn-zone-save');
    button.disabled = true;
    button.textContent = 'Guardando…';
    this.setStatus('Guardando polígonos y actualizando el pipeline…');
    const result = await API.saveZones(definitions);
    if (result?.error) {
      this.setStatus(`No se pudo guardar: ${result.error}`);
    } else {
      this.setStatus(`${result.length} zonas guardadas y activas sin reiniciar.`);
      await this.load();
    }
    button.disabled = false;
    button.textContent = 'Guardar zonas';
  },

  render() {
    if (!this.canvas || this.canvas.hidden) return;
    const bounds = this.canvas.getBoundingClientRect();
    if (!bounds.width || !bounds.height) return;
    const ratio = window.devicePixelRatio || 1;
    this.canvas.width = Math.round(bounds.width * ratio);
    this.canvas.height = Math.round(bounds.height * ratio);
    const context = this.canvas.getContext('2d');
    context.setTransform(ratio, 0, 0, ratio, 0, 0);
    context.clearRect(0, 0, bounds.width, bounds.height);
    const image = this.imageRect(bounds.width, bounds.height);
    Object.entries(this.zones).forEach(([name, points]) => {
      if (!points.length) return;
      const color = this.colors[name] || '#c084fc';
      context.beginPath();
      points.forEach((point, index) => {
        const x = image.x + point.x * image.width;
        const y = image.y + point.y * image.height;
        if (index === 0) context.moveTo(x, y);
        else context.lineTo(x, y);
      });
      if (points.length >= 3) context.closePath();
      context.fillStyle = `${color}22`;
      context.strokeStyle = color;
      context.lineWidth = name === this.activeZone ? 3 : 2;
      if (points.length >= 3) context.fill();
      context.stroke();
      points.forEach((point, index) => {
        const x = image.x + point.x * image.width;
        const y = image.y + point.y * image.height;
        context.beginPath();
        context.arc(x, y, name === this.activeZone ? 6 : 4, 0, Math.PI * 2);
        context.fillStyle = color;
        context.fill();
        context.fillStyle = '#071018';
        context.font = '600 10px Manrope';
        context.textAlign = 'center';
        context.fillText(String(index + 1), x, y + 3.5);
      });
    });
    const total = (this.zones[this.activeZone] || []).length;
    if (this.count) this.count.textContent = `${total} punto${total === 1 ? '' : 's'}`;
  },

  label(name) {
    return { observation: 'Observación', riverbank: 'Orilla', water: 'Río Huallaga' }[name] || name;
  },

  setStatus(message) {
    if (this.status) this.status.textContent = message;
  }
};
