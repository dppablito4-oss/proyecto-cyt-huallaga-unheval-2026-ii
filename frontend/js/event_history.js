const EventHistory = {
  async init() {
    document.getElementById('btn-refresh-history')?.addEventListener('click', () => this.load());
    await this.load();
    window.setInterval(() => this.load(), 30000);
  },

  async load() {
    const button = document.getElementById('btn-refresh-history');
    if (button) {
      button.disabled = true;
      button.textContent = 'Actualizando…';
    }
    const [events, statistics] = await Promise.all([
      API.getEvents(30),
      API.getEventStatistics()
    ]);
    this.renderStatistics(statistics);
    this.renderEvents(events);
    if (button) {
      button.disabled = false;
      button.textContent = 'Actualizar';
    }
  },

  renderStatistics(data) {
    if (!data) return;
    Dashboard.setText('history-total-events', data.total_events ?? 0);
    Dashboard.setText('history-observed-events', data.observed_warn_events ?? 0);
    Dashboard.setText(
      'history-nudge-rate',
      data.desistimiento_rate == null ? 'Sin datos' : `${Math.round(data.desistimiento_rate * 100)}%`
    );
    const progress = document.getElementById('history-nudge-progress');
    if (progress) {
      progress.value = data.desistimiento_rate == null ? 0 : Math.round(data.desistimiento_rate * 100);
      progress.setAttribute(
        'aria-valuetext',
        data.desistimiento_rate == null ? 'Sin observaciones disponibles' : `${progress.value}% de desistimientos confirmados`
      );
    }
  },

  renderEvents(events) {
    const container = document.getElementById('event-history-grid');
    if (!container) return;
    container.replaceChildren();
    if (!Array.isArray(events) || !events.length) {
      const empty = document.createElement('p');
      empty.className = 'history-empty';
      empty.textContent = 'Todavía no hay incidencias guardadas. Los próximos eventos aparecerán aquí.';
      container.appendChild(empty);
      return;
    }
    events.forEach(event => container.appendChild(this.eventCard(event)));
  },

  eventCard(event) {
    const article = document.createElement('article');
    article.className = 'event-card';
    const header = document.createElement('header');
    header.className = 'event-card-header';
    const heading = document.createElement('div');
    const label = document.createElement('span');
    label.className = 'muted-label';
    label.textContent = event.object_class ? `Residuo: ${event.object_class}` : 'Incidencia registrada';
    const time = document.createElement('p');
    time.className = 'event-card-time';
    const parsedDate = new Date(event.started_at);
    time.textContent = Number.isNaN(parsedDate.getTime())
      ? event.started_at
      : parsedDate.toLocaleString('es-PE', { dateStyle: 'medium', timeStyle: 'medium' });
    heading.append(label, time);
    const decision = document.createElement('span');
    decision.className = `decision-badge ${event.decision === 'WARN' ? 'warn' : event.decision === 'LOG_ONLY' ? 'log-only' : 'ignore'}`;
    decision.textContent = event.decision || 'SIN DECISIÓN';
    header.append(heading, decision);

    const diagnosis = document.createElement('p');
    diagnosis.className = 'event-card-diagnosis';
    diagnosis.textContent = event.analysis?.description || this.localDiagnosis(event);
    const frames = document.createElement('div');
    frames.className = 'event-frames';
    const frameCount = Math.min(4, event.capture?.frame_paths?.length || 0);
    if (frameCount) {
      for (let index = 0; index < frameCount; index += 1) {
        const image = document.createElement('img');
        image.src = `/api/events/${encodeURIComponent(event.id)}/frames/${index}`;
        image.alt = `Fotograma ${index + 1} del evento registrado`;
        image.loading = 'lazy';
        image.addEventListener('error', () => {
          const placeholder = document.createElement('span');
          placeholder.className = 'event-frame-placeholder';
          placeholder.textContent = 'No disponible';
          image.replaceWith(placeholder);
        }, { once: true });
        frames.appendChild(image);
      }
    } else {
      const placeholder = document.createElement('span');
      placeholder.className = 'event-frame-placeholder';
      placeholder.textContent = 'Sin fotogramas';
      frames.appendChild(placeholder);
    }

    const footer = document.createElement('footer');
    footer.className = 'event-card-footer';
    const nudge = document.createElement('span');
    nudge.className = 'nudge-result';
    if (event.desistimiento_confirmado === true) {
      nudge.classList.add('success');
      nudge.textContent = 'Desistimiento confirmado';
    } else if (event.desistimiento_confirmado === false) {
      nudge.classList.add('failed');
      nudge.textContent = 'No recogió el residuo';
    } else {
      nudge.textContent = event.decision === 'WARN' ? 'Observación no disponible' : 'Sin alerta acústica';
    }
    footer.appendChild(nudge);
    if (event.metrics?.audio_path) {
      const audio = document.createElement('audio');
      audio.controls = true;
      audio.preload = 'none';
      audio.src = `/api/events/${encodeURIComponent(event.id)}/audio`;
      audio.setAttribute('aria-label', 'Reproducir la advertencia emitida');
      footer.appendChild(audio);
    }
    article.append(header, diagnosis, frames, footer);
    return article;
  },

  localDiagnosis(event) {
    if (event.local_event_state) {
      const score = Math.round(Number(event.local_event_score || 0) * 100);
      return `Detección local ${event.local_event_state.toLowerCase()} con ${score}% de confianza.`;
    }
    return 'Evento guardado sin diagnóstico textual disponible.';
  }
};
