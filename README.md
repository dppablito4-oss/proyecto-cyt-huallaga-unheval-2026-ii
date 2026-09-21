# SIVARH

**SIVARH: Sistema Inteligente de Vigilancia Ambiental para las Riberas del Río Huallaga orientado a la detección preventiva del arrojo directo de residuos sólidos, sector Puente Huallaga – UNHEVAL**

> Para una guía actualizada y fácil de navegar del código, los modos de prueba y los endpoints, consulta [docs/GUIA_DEL_REPOSITORIO.md](docs/GUIA_DEL_REPOSITORIO.md).

*Universidad Nacional Hermilio Valdizán (UNHEVAL) — Huánuco, Perú*  
*Facultad de Ciencias de la Educación — Escuela Profesional de Matemática y Física*  
*Asignatura: Ciencias Naturales y del Ambiente (Semestre 2026-II) &bull; Proyecto de Investigación CyT*

---

## Estado actual del prototipo

La versión actual implementa un flujo autónomo de extremo a extremo: captura de video, detección abierta de residuos con YOLOE-26n, tracking anónimo con ByteTrack, reconocimiento local de transporte/liberación/lanzamiento/abandono, zonas poligonales, pose selectiva, fallback multimodal para casos ambiguos, advertencias OpenAI TTS, persistencia y dashboard.

La captura permanece activa mientras el evento acumula contexto y mientras la IA o el TTS procesan el resultado. El análisis se ejecuta en un hilo independiente y se admite un solo evento activo a la vez. Para reducir el consumo de RAM, la cámara puede operar a su FPS normal, pero el buffer conserva por defecto solo **5 muestras por segundo durante 5 segundos** (máximo 25 frames antes de la selección final).

Las Fases 1–10 de SIVARH v2 incorporan IDs persistentes, trayectoria acotada, `SceneState`, zonas, pose selectiva, asociación persona–objeto, razonamiento temporal y telemetría. `EventManager` ya no dispara por presencia. Un lanzamiento rápido o un abandono confirmado se resuelve en el edge; una bolsa perdida brevemente tras ser transportada crea un caso `UNCERTAIN` con contexto posterior para OpenAI. Toda decisión `WARN` intenta primero OpenAI TTS por streaming y guarda el resultado en caché; si la API, la red o el altavoz streaming fallan, recurre al catálogo WAV pre-generado.

---

## Contexto y Justificación Científica

El río Huallaga a su paso por el área metropolitana de **Huánuco, Amarilis y Pillco Marca** enfrenta una severa crisis por contaminación y acumulación recurrente de residuos sólidos. Informes oficiales de entidades como el OEFA, FEMA y la UNHEVAL han documentado hasta **216 puntos críticos** a lo largo de su cuenca regional, con una generación diaria de entre **100 y 120 toneladas de residuos**.

En sectores de alto tránsito como el **Puente Huallaga**, el **Malecón Walker Soberón**, el **Malecón Huallaga** y los accesos peatonales a la **Universidad Nacional Hermilio Valdizán (UNHEVAL)** en Cayhuayna, la dilución de la responsabilidad y el anonimato propician el arrojo directo (*littering*) de botellas plásticas PET, bolsas de polietileno y empaques hacia las pendientes y el caudal del río.

Las estrategias tradicionales basadas en campañas de limpieza periódicas son valiosas pero de efecto efímero debido a la reincidencia conductual. **SIVARH** aborda la raíz del problema mediante una **intervención preventiva en el instante pre-impacto**, utilizando visión por computadora, modelos multimodales de Inteligencia Artificial y estímulos disuasorios acústicos (*nudges* cognitivos) en tiempo real para provocar el desistimiento del infractor antes de que el residuo toque el agua.

---

##  Delimitación del Alcance

| Fuente de Contaminación | Descripción | Alcance en SIVARH |
| :--- | :--- | :--- |
| **1. Disposición directa por personas (*Littering*)** | Arrojo intencional o negligente de botellas, bolsas y envoltorios por peatones y conductores. | ** ENFOQUE EXCLUSIVO DEL SISTEMA.** |
| **2. Residuos transportados por la corriente** | Basura arrastrada desde cuencas altas por lluvia y caudal. | Fuera de alcance (requiere dragado/infraestructura). |
| **3. Vertimientos de aguas residuales** | Efluentes domésticos o industriales (ej. Camal Municipal). | Fuera de alcance (requiere plantas PTAR). |
| **4. Escombros masivos de construcción** | Descargas clandestinas nocturnas con volquetes pesados. | Fuera de alcance inicial. |
| **5. Lixiviados y agroquímicos** | Percolación de botaderos (Chilepampa) y fertilizantes agrícolas. | Fuera de alcance algorítmico. |

---

##  Arquitectura del Sistema (Edge Computing & Multimodal AI)

```text
                    CÁMARA (USB / RTSP / Video)
                               │
                               ▼
                         CameraSource
                               │
                   OpenCV (Flujo de Frames)
                               │
         ┌─────────────────────┴─────────────────────┐
         ▼                                           ▼
 LocalDetector (YOLOE-26n)                   FrameBuffer (5s RAM)
(persona + bolsas + residuos)          (5 muestras/s; antes y después)
         │                                           │
         └─────────────────────┬─────────────────────┘
                               │
                               ▼
          ByteTrack → AssociationEngine → EventEngine
       (CARRIED → RELEASED → THROWN / ABANDONED)
                               │
                               ▼
                   DecisionEngine local
              ┌────────────┴────────────┐
              ▼                         ▼
      CONFIRMED → WARN          UNCERTAIN → keyframes
                               │
                               ▼
                        ImageProcessor
                 (Resize 1280w + JPEG 70 + B64)
                               │
                               ▼
                           VisionAI
                    (sólo fallback ambiguo)
                               │
                               ▼
                       AIAnalysisResult
                    (JSON con tipado estricto)
                               │
                               ▼
                        DecisionEngine
                   ┌───────────┴───────────┐
                               │
                               ▼
                       AIAnalysisResult
                    (JSON con tipado estricto)
                               │
                               ▼
                        DecisionEngine
                   ┌───────────┴───────────┐
                   ▼                       ▼
            IGNORE / LOG_ONLY             WARN
             (Auditar en DB)               │
                                           ▼
                              OpenAI TTS dinámico/caché
                            o catálogo WAV pre-generado
                                           │
                                           ▼
                                      AudioOutput
                                  (🔊 Altavoz Local)
```

La captura de cámara continúa en su propio hilo mientras el análisis del evento espera contexto, consulta la IA y genera audio. En paralelo, el estado global (`SystemState`) se difunde al **Dashboard Web** mediante **FastAPI** y **WebSocket**.

---

## 📁 Estructura del Repositorio

```text
huallaga-ai-monitor/
│
├── run.py                            # Lanzador principal del servidor y dashboard
├── app/                              # Backend modular en Python (FastAPI & Visión)
│   ├── main.py                       # Servidor ASGI FastAPI, ciclo de vida y montaje de frontend
│   ├── config.py                     # Configuración centralizada tipada (.env con Pydantic)
│   ├── state.py                      # Estado reactivo del sistema (SystemState singleton)
│   ├── dependencies.py               # Inyección de dependencias FastAPI
│   │
│   ├── models/                       # Modelos de datos y esquemas Pydantic
│   │   ├── event.py                  # Entidad EventModel y detecciones
│   │   ├── detection.py              # Detection y DetectionFrame multiclase
│   │   ├── tracking.py               # TrackedObject, TrackState y trayectoria
│   │   ├── scene.py                  # SceneState y contratos de zonas
│   │   ├── association.py            # Señales y asociación persona-objeto
│   │   ├── pose.py                   # Landmarks corporales útiles y efímeros
│   │   ├── reasoning.py              # Estado de objeto, evidencia y EventCandidate
│   │   ├── analysis.py               # Esquema estructurado AIAnalysisResult
│   │   ├── camera.py                 # Estado técnico de cámara
│   │   └── metrics.py                # Métricas experimentales (latencia, payload)
│   │
│   ├── camera/                       # Capa de Abstracción de Hardware de Video
│   │   ├── base.py                   # Interfaz abstracta CameraSource
│   │   ├── usb_camera.py             # Implementación para webcam USB (OpenCV)
│   │   ├── rtsp_camera.py            # Controlador para cámaras IP / RTSP
│   │   ├── video_file.py             # Reproducción de grabaciones de prueba (.mp4)
│   │   └── worker.py                 # Orquestador del bucle continuo de captura y eventos
│   │
│   ├── vision/                       # Pipeline de Visión por Computadora
│   │   ├── detector.py               # YOLOE multiclase configurable por prompts abiertos
│   │   ├── tracker.py                # Adaptador ByteTrack y contrato intercambiable
│   │   ├── track_history.py          # Trayectoria, velocidad, dirección y TTL
│   │   ├── zones.py                  # Zonas poligonales normalizadas por cámara
│   │   ├── debug_overlay.py          # Overlay opcional de tracking y zonas
│   │   ├── associations.py           # Scorer y persistencia persona-objeto
│   │   ├── pose.py                   # MediaPipe opcional con activación selectiva
│   │   ├── frame_buffer.py           # Buffer circular muestreado en RAM (5s a 5 FPS por defecto)
│   │   ├── frame_selector.py         # Muestreo temporal uniforme de frames
│   │   ├── image_processor.py        # Compresión JPEG, resize y Base64
│   │   └── scheduler.py              # Limitador monotónico de tasa (FPS)
│   │
│   ├── events/                       # Gestión de Eventos y Reglas de Negocio
│   │   ├── engine.py                 # Motor continuo de candidatos locales
│   │   ├── object_state.py           # Máquina de estados temporal de objetos
│   │   ├── manager.py                # Orquestador del ciclo de vida del evento
│   │   ├── cooldown.py               # Filtro temporal para evitar duplicidad
│   │   └── rules.py                  # DecisionEngine (IGNORE / LOG_ONLY / WARN)
│   │
│   ├── ai/                           # Integración con IA Multimodal
│   │   ├── vision_client.py          # Cliente OpenAI Vision (con modo simulación y estructurado)
│   │   ├── schemas.py                # Re-export de esquemas de respuesta
│   │   ├── prompts.py                # Cargador dinámico de prompts
│   │   └── model_config.py           # Hiperparámetros de muestreo
│   │
│   ├── speech/                       # Síntesis y Salida de Audio
│   │   ├── service.py                # Interfaz abstracta SpeechService
│   │   ├── openai_tts.py             # Generación de voz con OpenAI TTS (/v1/audio/speech)
│   │   ├── cached_warning.py         # TTS dinámico, caché y catálogo WAV rotativo
│   │   └── audio_output.py           # Reproductor en altavoces de la estación
│   │
│   ├── reports/                      # Generación de Reportes Forenses
│   │   ├── __init__.py
│   │   └── pdf.py                    # Generador de reportes en PDF con ReportLab
│   │
│   ├── storage/                      # Persistencia de Datos
│   │   ├── events_repository.py      # Interfaz abstracta de repositorio
│   │   └── local_repository.py       # Base de datos SQLite local (data/events.db)
│   │
│   ├── metrics/                      # Métricas para Investigación Científica
│   │   ├── collector.py              # Agregador de registros
│   │   ├── latency.py                # Cronómetro de alta resolución (LatencyTimer)
│   │   └── network.py                # Medición de tamaño de payloads
│   │
│   ├── utils/                        # Utilidades (UUIDs, timestamps, archivos)
│   │   ├── ids.py
│   │   ├── time.py
│   │   └── files.py
│   │
│   └── api/                          # Endpoints REST y WebSockets
│       ├── routes/
│       │   ├── status.py             # GET /api/status, /api/metrics y /api/health
│       │   ├── system.py             # Controles de inicio/parada, logs y secuencia manual
│       │   ├── events.py             # GET /api/events y GET /api/events/{id}
│       │   ├── cameras.py            # Stream MJPEG, status, conmutación y previews
│       │   ├── scene.py              # GET /api/scene (estado espacial estructurado)
│       │   ├── reports.py            # GET /api/reports/evidence.pdf (exportación PDF)
│       │   ├── config.py             # GET & PATCH /api/config
│       │   └── debug.py              # Pruebas manuales de TTS, Luna y análisis multimodal
│       └── websocket.py              # WS /ws para sincronización reactiva
│
├── frontend/                         # Dashboard Web en Tiempo Real
│   ├── index.html                    # Estructura semántica, controles de cámara y modal de alerta
│   ├── css/
│   │   └── app.css                   # Estilos modernos dark-mode glassmorphic
│   ├── js/
│   │   ├── api.js                    # Cliente HTTP REST
│   │   ├── websocket.js              # Cliente WebSocket con reconexión automática
│   │   ├── dashboard.js              # Actualización dinámica del DOM y métricas
│   │   └── app.js                    # Inicializador de la aplicación y eventos de usuario
│   └── assets/                       # Logotipos e identidades gráficas UNHEVAL/SIVARH
│
├── prompts/                          # Prompts de Sistema Especializados
│   ├── environmental_event.txt       # Directivas de inferencia cronológica
│   └── warning_script_from_event.txt # Pauta de redacción disuasoria de Luna
│
├── docs/                             # Documentación Académica y Técnica
│   ├── ARQUITECTURA_DETALLADA.md     # Documento técnico exhaustivo
│   ├── GUIA_DEL_REPOSITORIO.md       # Guía rápida de navegación y modos de prueba
│   └── documentacion_imprimible.html # Versión HTML estilizada para impresión
│
├── data/                             # Datos locales y auditoría (ignorado en git)
│   ├── audio/                        # Caché y catálogo WAV OpenAI TTS pre-generado
│   ├── frames/                       # Capturas temporales de vista previa
│   ├── models/                       # Embeddings YOLOE y modelos de pose
│   └── events.db                     # Base de datos SQLite
│
├── tests/                            # Pruebas Automatizadas (29 suites, 88 tests pasando)
│   ├── test_tracker.py               # Asociación frame-a-frame de ByteTrack
│   ├── test_track_history.py         # Cinemática, velocidad y purga por TTL
│   ├── test_zones.py                 # Geometría y punto-en-polígono
│   ├── test_scene_state.py           # Ocupación y estado espacial
│   ├── test_associations.py          # Correlación espacio-temporal persona-objeto
│   ├── test_pose.py                  # Landmarks corporales selectivos
│   ├── test_event_engine.py          # Razonamiento temporal de candidatos locales
│   ├── test_event_manager.py         # Ciclo de vida y orquestación de eventos
│   ├── test_throw_alert_flow.py      # Flujo completo de lanzamiento y alerta
│   ├── test_cached_warning.py        # Caché por contenido y catálogo rotativo
│   ├── test_audio_output.py          # Emisión física de sonido
│   ├── test_camera_preview.py        # Extracción y entrega de previews
│   ├── test_camera_switch.py         # Conmutación de cámara en caliente
│   ├── test_runtime_config.py        # Modificación dinámica de parámetros
│   └── ...                           # (29 suites con 88 pruebas unitarias)
│
├── scripts/                          # Diagnósticos, Herramientas y Benchmarks
│   ├── test_camera.py                # Verificación de fuentes de video
│   ├── test_yolo.py                  # Verificación del detector YOLO/YOLOE
│   ├── test_openai.py                # Verificación de cliente Vision AI
│   ├── generate_openai_warning_catalog.py # Generación de catálogo WAV con OpenAI TTS
│   ├── generate_local_warning.py     # Generación de advertencia local de respaldo
│   ├── prepare_yoloe_detector.py     # Generación de embeddings de clases abiertas
│   ├── download_pose_model.py        # Descarga del modelo de pose MediaPipe
│   ├── benchmark_images.py           # Benchmark de compresión JPEG y reescalado
│   └── export_docs_to_pdf.py         # Script de exportación de documentación técnica
│
├── .env.example                      # Plantilla de variables de entorno
├── .gitignore                        # Reglas de exclusión de git
├── requirements.txt                  # Dependencias principales de Python
├── requirements-pose.txt             # Dependencias opcionales de MediaPipe Pose
├── pyproject.toml                    # Metadatos del proyecto Python
├── documentacion.md                  # Memoria técnica oficial del proyecto
└── README.md                         # Este documento
```

---

## 🛠️ Instalación y Configuración

### 1. Clonar el repositorio
```bash
git clone https://github.com/dppablito4-oss/proyecto-cyt-huallaga-unheval-2026-ii.git
cd proyecto-cyt-huallaga-unheval-2026-ii
```

### 2. Crear entorno virtual e instalar librerías
```bash
python -m venv .venv
# En Windows:
.venv\Scripts\activate
# En Linux/macOS:
source .venv/bin/activate

pip install -r requirements.txt
```

MediaPipe Pose es un extra opcional. Para habilitarlo:

```bash
pip install -r requirements-pose.txt
python scripts/download_pose_model.py
```

Después establece `POSE_ENABLED=True`. Sin ese extra o sin el modelo, SIVARH continúa con asociación geométrica y temporal.

El repositorio incluye cuatro advertencias WAV generadas con OpenAI TTS en `data/audio/templates/`. Para regenerar el catálogo con la API configurada:

```bash
python scripts/generate_openai_warning_catalog.py --overwrite
```

`warning_default.wav` se conserva como respaldo de emergencia generado por el sistema operativo:

```bash
python scripts/generate_local_warning.py --overwrite
```

El archivo pequeño `data/models/sivarh-yoloe-26n-prompts.npz` ya contiene las categorías abiertas de SIVARH. El peso `yoloe-26n-seg.pt` se descarga automáticamente la primera vez (aprox. 11 MB). Si cambias la lista de clases, vuelve a preparar los prompts con `python scripts/prepare_yoloe_detector.py`.

### 3. Variables de entorno
Copia el archivo `.env.example` a `.env`:
```bash
cp .env.example .env
```
Edita `.env` con tus credenciales si deseas ejecutar inferencia real:
```env
OPENAI_API_KEY=sk-tu-api-key-aqui
OPENAI_VISION_MODEL=gpt-5.6-luna
OPENAI_TTS_MODEL=gpt-4o-mini-tts
OPENAI_TTS_VOICE=onyx
OPENAI_WARNING_CATALOG_DIR=data/audio/templates
OPENAI_WARNING_CATALOG_PATTERN=openai_warning_*.wav
CALIBRATION_MODE=False
CAMERA_SOURCE=0
DETECTOR_BACKEND=yoloe
YOLO_MODEL=yoloe-26n-seg.pt
YOLO_PROMPT_EMBEDDINGS_PATH=data/models/sivarh-yoloe-26n-prompts.npz
DETECTION_CONFIDENCE=0.20
DETECTION_CLASSES=person,plastic bag,trash bag,garbage bag,bottle,cup,food wrapper,cardboard box,backpack,handbag
TRACKING_ENABLED=True
TRACKER_TYPE=bytetrack
TRACK_HISTORY_SECONDS=15
TRACK_TTL_SECONDS=5
ZONE_CONFIG_PATH=config/zones.json
VISION_DEBUG_OVERLAY=False
ASSOCIATION_ENABLED=True
ASSOCIATION_MIN_SCORE=0.65
ASSOCIATION_MIN_DURATION=0.5
ASSOCIATION_HAND_WEIGHT=0.25
POSE_ENABLED=False
POSE_MODEL_PATH=data/models/pose_landmarker_lite.task
POSE_FPS=7
OPENAI_FALLBACK_ENABLED=True
OPENAI_MAX_FRAMES=3
OBJECT_LOST_RELEASE_SECONDS=0.35
OBJECT_THROW_MIN_SPEED_PX_S=90
OBJECT_THROW_MIN_DISTANCE_PX=24
EVENT_MIN_CONTEXT_SECONDS=2.2
BUFFER_SECONDS=5
BUFFER_FPS=5
```
> [!NOTE]
> El sistema arranca y opera en **Modo Simulación / Standby** sin necesidad de API Key ni cámara conectada.
> Para pruebas controladas dentro de una habitación puede usarse `CALIBRATION_MODE=True`: las zonas siguen siendo polígonos virtuales y una bolsa/objeto de prueba se evalúa como residuo simulado. Mantén este modo desactivado en producción.
---

## 🚀 Puesta en Marcha

### Opción 1: Lanzador Principal (Recomendado)
Ejecuta el script integrado en la raíz que inicializa el servidor backend y sirve el dashboard web en tiempo real:
```bash
python run.py
```
*(O en Windows con el selector de Python: `py -3.11 run.py`)*

### Opción 2: Ejecución directa con Uvicorn
```bash
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Accede al dashboard reactivo en tu navegador:
👉 **`http://127.0.0.1:8000`**

Documentación interactiva Swagger / OpenAPI:
👉 **`http://127.0.0.1:8000/docs`**

---

## 🧪 Pruebas Automatizadas y Diagnósticos

El repositorio cuenta con una suite completa de **29 archivos de pruebas unitarias e integración con 88 tests automatizados** que validan desde la cinemática de ByteTrack hasta el razonamiento temporal, zonas poligonales, generación de voz y conmutación de cámaras.

### Ejecutar la suite completa:
```bash
python -m pytest -q
```
*(Resultado actual verificado: `88 passed`)*

### Ejecutar pruebas por módulo específico:
```bash
python -m pytest tests/test_event_engine.py -v     # Razonamiento temporal de eventos
python -m pytest tests/test_associations.py -v     # Asociación persona-objeto
python -m pytest tests/test_cached_warning.py -v   # Fallback de voz y catálogo WAV
```

### Scripts de Diagnóstico y Herramientas:
```bash
python scripts/test_camera.py                      # Diagnóstico de enlaces de cámara
python scripts/test_yolo.py                        # Inferencia local YOLOE de prueba
python scripts/test_openai.py                      # Verificación del cliente Vision AI
python scripts/benchmark_images.py                 # Rendimiento de compresión y reescalado
python scripts/generate_openai_warning_catalog.py  # Genera advertencias WAV con OpenAI TTS
python scripts/generate_local_warning.py           # Genera plantilla de audio de respaldo local
python scripts/prepare_yoloe_detector.py           # Re-calcula embeddings para clases abiertas
python scripts/download_pose_model.py              # Descarga MediaPipe Pose Landmarker
python scripts/export_docs_to_pdf.py               # Compila la documentación técnica a PDF
```

---

## 📡 Endpoints de la API REST y WebSockets

| Método | Endpoint | Categoría | Descripción |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/status` | Estado | Retorna el JSON completo del estado operativo (`SystemState`). |
| `GET` | `/api/metrics` | Métricas | Retorna métricas de rendimiento: FPS, CPU, RAM y latencias. |
| `GET` | `/api/health` | Monitoreo | Sonda básica de disponibilidad (`{"status": "ok"}`). |
| `GET` | `/api/scene` | Espacial | Retorna ocupación de zonas, tracks y estado de objetos (`SceneState`). |
| `GET` | `/api/scene/zones` | Espacial | Devuelve los polígonos normalizados activos. |
| `PUT` | `/api/scene/zones` | Espacial | Guarda y aplica una calibración visual sin reiniciar. |
| `GET` | `/api/events` | Eventos | Lista el histórico de eventos almacenados en SQLite. |
| `GET` | `/api/events/statistics` | Eventos | Resume alertas observadas y tasa de desistimiento. |
| `GET` | `/api/events/{id}` | Eventos | Retorna el detalle completo de un evento por su UUID. |
| `GET` | `/api/events/{id}/frames/{index}` | Evidencia | Sirve un fotograma histórico validado. |
| `GET` | `/api/events/{id}/audio` | Evidencia | Reproduce la advertencia asociada al evento. |
| `GET` | `/api/cameras/status` | Cámara | Parámetros técnicos, resolución y enlace de la fuente activa. |
| `POST` | `/api/cameras/switch` | Cámara | Cambia dinámicamente de fuente de video (índice, archivo o RTSP). |
| `GET` | `/api/cameras/stream` | Video | Flujo MJPEG multipart continuo para monitoreo en vivo en el navegador. |
| `GET` | `/api/cameras/analysis-preview/{file}` | Video | Sirve fotogramas seleccionados para inspección visual. |
| `GET` | `/api/config` | Configuración | Consulta los parámetros operativos no sensibles. |
| `PATCH` | `/api/config` | Configuración | Modifica dinámicamente parámetros de configuración en memoria. |
| `GET` | `/api/config/detection-classes` | Visión | Consulta el estado y vocabulario YOLOE activo. |
| `POST` | `/api/config/detection-classes` | Visión | Prepara y activa clases abiertas en segundo plano. |
| `POST` | `/api/system/start` | Control | Inicia el worker de captura continua y pipeline de video. |
| `POST` | `/api/system/stop` | Control | Detiene el worker de captura continua y libera recursos. |
| `POST` | `/api/system/clear-logs` | Control | Limpia la cola de logs del sistema en el dashboard. |
| `POST` | `/api/system/manual/start-recognition` | Manual | Inicia ráfaga de 4 fotogramas manuales espaciados por 1.5s. |
| `POST` | `/api/system/manual/send-images` | Manual | Envía la ráfaga manual a OpenAI Vision para evaluación. |
| `POST` | `/api/system/manual/emit-alert` | Manual | Emite por altavoz la advertencia redactada tras confirmación humana. |
| `GET` | `/api/reports/evidence.pdf` | Reportes | Exporta reporte formal en PDF con estado, secuencia y logs forenses. |
| `POST` | `/api/debug/test-speech` | Depuración | Genera y reproduce un audio de prueba con OpenAI TTS. |
| `POST` | `/api/debug/test-local-warning` | Depuración | Reproduce el catálogo WAV local sin consumir la API de OpenAI. |
| `POST` | `/api/debug/generate-event-speech` | Depuración | Genera un guion contextual con Luna (`gpt-5.6`) y lo reproduce. |
| `POST` | `/api/debug/test-analysis` | Depuración | Prueba el análisis multimodal con frames sintéticos o del buffer. |
| `WS` | `/ws` | Tiempo Real | Canal WebSocket para sincronización bidireccional reactiva del dashboard. |

---

## 🔍 Análisis Crítico de Brechas y Puntos Ciegos (Huecos del Proyecto)

Para orientar las siguientes fases de desarrollo y la sustentación académica del proyecto de investigación CyT, se identifican los siguientes **huecos y debilidades estructurales** en el estado actual:

### 1. Brechas en Visión por Computadora y Entorno Físico (Computer Vision)
* **Calibración rígida de zonas (`config/zones.json`):** Los polígonos de ribera y agua se definen con coordenadas normalizadas fijas. Si la cámara montada en el Puente Huallaga o Malecón sufre vibraciones por tráfico pesado, desalineación o cambio de ángulo, las zonas quedan descalibradas. *Falta una herramienta visual interactiva en el frontend que permita dibujar y ajustar los polígonos directamente sobre el fotograma en vivo.*
* **Condiciones meteorológicas y nocturnas:** El río Huallaga presenta lluvias torrenciales, neblina matinal y reflejos especulares intensos sobre la corriente. Asimismo, gran parte del *littering* clandestino ocurre de noche. El detector YOLOE-26n opera en RGB estándar y carece de pre-procesamiento adaptativo (CLAHE, filtrado de destellos o soporte térmico/IR nocturno).
* **Oclusiones y multitudes en barandas:** En horas punta sobre el Puente Huallaga, los peatones caminan aglomerados o se detienen pegados a barandillas metálicas. Las barandas provocan cortes de bounding box (*occlusion*), lo que puede fragmentar el tracking de ByteTrack o degradar la correlación mano-objeto de la pose.
* **Vocabulario de residuos cerrado en runtime:** Aunque YOLOE soporta clases abiertas vía CLIP, el archivo precalculado `sivarh-yoloe-26n-prompts.npz` contiene un set predeterminado (bolsas, botellas, vasos, envoltorios, cajas). Si un transeúnte arroja costales de rafia, llantas, latas de cerveza o desmonte en bolsas atípicas, el detector local no los clasifica como residuos a menos que se reentrenen o amplíen dichos embeddings.

### 2. Brechas en Arquitectura, Concurrencia y Resiliencia en el Borde (Edge Computing)
* **Procesamiento de eventos monohilo (`_active_event_thread`):** El worker de pipeline admite un solo evento activo a la vez para proteger la RAM. Si ocurren dos conductas sospechosas simultáneas en extremos opuestos del campo visual, el segundo evento no se atiende hasta que concluya el primero.
* **Tolerancia a fallos y reconexión de cámaras:** Si la cámara IP (RTSP) pierde enlace por microcortes de red o PoE, o si una cámara USB sufre desconexión momentánea, el sistema captura la excepción pero no cuenta con un bucle formal de reconexión con *exponential backoff* automático, requiriendo intervención en el dashboard (`POST /api/cameras/switch`).
* **Gestión de almacenamiento en disco (Purga/Retention):** Los fotogramas de vista previa (`data/frames/`) y los audios generados (`data/audio/`) crecen indefinidamente. En una placa embebida de borde (NVIDIA Jetson Orin o Raspberry Pi 5 con almacenamiento flash acotado), el disco se saturará en pocos días si no se implementa una política automática de rotación y limpieza LRU/TTL.

### 3. Brechas en Seguridad, Red y Despliegue Operativo
* **Ausencia de Autenticación y Autorización (Zero-Auth):** Los endpoints REST de control (`/api/system/start`, `/api/system/stop`, `/api/config`) y el WebSocket `/ws` están completamente abiertos. Cualquier dispositivo en la red de la UNHEVAL o de la municipalidad podría encender, apagar o modificar parámetros operativos.
* **Seguridad de credenciales en el hardware de campo:** La variable `OPENAI_API_KEY` se lee directamente de un archivo `.env` en texto claro. En una estación física instalada a la intemperie en un poste, el robo del dispositivo o de la tarjeta SD comprometería la clave de la API. Se requiere migrar a un almacén de secretos protegido o restringir la clave por IP/presupuesto.
* **Políticas CORS y transporte no cifrado:** Por defecto, el servidor opera sobre HTTP/WS plano. Un despliegue en producción municipal requiere HTTPS/WSS y encabezados de seguridad reforzados.

### 4. Brechas en Metodología Científica y Validación Experimental (CyT UNHEVAL)
* **Ausencia de un Dataset Benchmark Local Etiquetado:** No se dispone en el repositorio de un set formal de videos de campo del río Huallaga anotados cuadro por cuadro (formato MOT / COCO) con verdad de terreno (*ground truth*). Esto impide calcular formalmente curvas ROC, $mAP@50$, $MOTA$ e $IDF1$ con rigor estadístico publicable.
* **Medición cuantitativa del Desistimiento Conductual (*Nudge Impact*):** La hipótesis científica sostiene que el estímulo sonoro provoca el desistimiento pre-impacto. Sin embargo, el sistema actualmente emite la advertencia pero no evalúa algorítmicamente en los siguientes 5 segundos si la persona detuvo la mano o recogió el objeto. Dicha confirmación debe medirse cuantitativamente y registrarse en SQLite como métrica de eficacia disuasoria.

### Estado de cierre de brechas — septiembre de 2026

Las siguientes brechas de la lista anterior ya están resueltas en el prototipo actual:

- calibración visual de `observation`, `riverbank` y `water` directamente sobre el video, con persistencia atómica y aplicación en caliente;
- observación post-alerta de cinco segundos, transición `RELEASED → CARRIED` y columna SQLite `desistimiento_confirmado`;
- historial web de incidencias con hasta cuatro fotogramas, diagnóstico, decisión, resultado del nudge y audio reproducible;
- reconexión automática de cámara cada dos segundos y reproducción continua de archivos de prueba;
- actualización asincrónica del vocabulario YOLOE desde el dashboard, con embeddings y clases persistentes.

---

##  Marco Ético y Protección de Datos Personales

El diseño adopta principios de minimización de datos y evita deliberadamente la identificación biométrica. Un despliegue real en espacios públicos requerirá evaluación y autorización institucional conforme al marco legal peruano aplicable:
- **Transparencia de voz:** Las advertencias son voces sintéticas generadas por IA con OpenAI TTS, no voces humanas; el dashboard lo informa expresamente.
- **Detección conductual:** El sistema detecta presencia de personas y analiza acciones, **SIN utilizar reconocimiento facial ni intentar identificar nombres o identidades civiles**.
- **No almacenamiento de identidades civiles:** No se registran nombres, rostros ni números de DNI.
- **Minimización de datos:** El buffer general es temporal, acotado y muestreado. Solo los fotogramas clave de eventos se conservan para auditoría e investigación.

---

## Mejoras previstas para fases posteriores

Estas mejoras forman parte de la hoja de ruta y **no se consideran implementadas en la versión actual**:

- entrenamiento supervisado futuro sobre las clases abiertas ya operativas de YOLOE;
- evaluación de precisión, recall y falsos positivos con videos etiquetados de campo;
- conjunto de videos positivos y negativos etiquetados;
- política configurable de retención y purga de fotogramas y audio;
- calibración nocturna y preprocesamiento para lluvia, niebla y reflejos;
- autenticación y protección de endpoints para un despliegue en red;
- cola persistente o escalable para múltiples cámaras y eventos.

Las zonas iniciales viven en `config/zones.json` con coordenadas normalizadas. Son una calibración genérica de arranque y deben ajustarse con una imagen real de cada cámara antes de utilizarse para decisiones ambientales.

---

##  Equipo y Créditos

- **Institución:** Universidad Nacional Hermilio Valdizán (UNHEVAL) — Huánuco, Perú.
- **Proyecto:** CyT Huallaga 2026-II.
- **Repositorio:** [github.com/dppablito4-oss/proyecto-cyt-huallaga-unheval-2026-ii](https://github.com/dppablito4-oss/proyecto-cyt-huallaga-unheval-2026-ii)
