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

Las Fases 1–10 de SIVARH v2 incorporan IDs persistentes, trayectoria acotada, `SceneState`, zonas, pose selectiva, asociación persona–objeto, razonamiento temporal y telemetría. `EventManager` ya no dispara por presencia. Un lanzamiento rápido o un abandono confirmado se resuelve en el edge; una bolsa perdida brevemente tras ser transportada crea un caso `UNCERTAIN` con contexto posterior para OpenAI. Los eventos confirmados rotan un catálogo WAV pre-generado con OpenAI TTS; los mensajes específicos usan TTS por API, se cachean y recurren al catálogo si falla la red.

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

##  Estructura del Repositorio

```text
huallaga-ai-monitor/
│
├── app/                              # Backend modular en Python (FastAPI & Visión)
│   ├── main.py                       # Servidor ASGI FastAPI y montaje de frontend
│   ├── config.py                     # Configuración centralizada (.env)
│   ├── state.py                      # Estado reactivo del sistema (SystemState)
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
│   │   └── video_file.py             # Reproducción de grabaciones de prueba (.mp4)
│   │
│   ├── vision/                       # Pipeline de Visión por Computadora
│   │   ├── detector.py               # YOLO multiclase configurable por nombre
│   │   ├── tracker.py                # Adaptador ByteTrack y contrato intercambiable
│   │   ├── track_history.py          # Trayectoria, velocidad, dirección y TTL
│   │   ├── zones.py                  # Zonas poligonales normalizadas por cámara
│   │   ├── debug_overlay.py          # Overlay opcional de tracking y zonas
│   │   ├── associations.py           # Scorer y persistencia persona-objeto
│   │   ├── pose.py                   # MediaPipe opcional con activación selectiva
│   │   ├── frame_buffer.py           # Buffer circular muestreado en RAM (5s a 5 FPS por defecto)
│   │   ├── frame_selector.py         # Muestreo temporal uniforme de frames
│   │   └── image_processor.py        # Compresión JPEG, resize y Base64
│   │
│   ├── events/                       # Gestión de Eventos y Reglas de Negocio
│   │   ├── engine.py                 # Motor continuo de candidatos locales
│   │   ├── object_state.py           # Máquina de estados temporal de objetos
│   │   ├── manager.py                # Orquestador del ciclo de vida del evento
│   │   ├── cooldown.py               # Filtro temporal para evitar duplicidad
│   │   └── rules.py                  # DecisionEngine (IGNORE / LOG_ONLY / WARN)
│   │
│   ├── ai/                           # Integración con IA Multimodal
│   │   ├── vision_client.py          # Cliente OpenAI Vision (con modo simulación)
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
│       │   ├── status.py             # GET /api/status y GET /api/health
│       │   ├── events.py             # GET /api/events y GET /api/events/{id}
│       │   ├── cameras.py            # GET /api/cameras/status
│       │   ├── config.py             # GET & PATCH /api/config
│       │   └── debug.py              # POST /api/debug/test-speech
│       └── websocket.py              # WS /ws para sincronización reactiva
│
├── frontend/                         # Dashboard Web en Tiempo Real
│   ├── index.html                    # Estructura semántica de la interfaz
│   ├── css/
│   │   └── app.css                   # Estilos modernos dark-mode glassmorphic
│   └── js/
│       ├── api.js                    # Cliente HTTP REST
│       ├── websocket.js              # Cliente WebSocket con reconexión automática
│       ├── dashboard.js              # Actualización dinámica del DOM
│       └── app.js                    # Inicializador de la aplicación
│
├── prompts/                          # Prompts de Sistema Especializados
│   └── environmental_event.txt       # Directivas de inferencia cronológica
│
├── docs/                             # Documentación Académica y Técnica
│   └── ARQUITECTURA_DETALLADA.md     # Documento técnico exhaustivo
│
├── data/                             # Datos locales y auditoría (ignorado en git)
│   ├── events/                       # Registros de eventos
│   ├── frames/                       # Capturas temporales
│   ├── audio/                        # Caché y catálogo OpenAI TTS pre-generado
│   └── test_videos/                  # Grabaciones de campo para testing
│
├── tests/                            # Pruebas Unitarias Automatizadas
│   ├── test_frame_selector.py
│   ├── test_image_processor.py
│   ├── test_ai_schema.py
│   └── test_event_manager.py
│
├── scripts/                          # Diagnósticos y Benchmarking
│   ├── test_camera.py                # Verificación de cámara
│   ├── test_yolo.py                  # Verificación de detector YOLO
│   ├── test_openai.py                # Verificación de cliente Vision AI
│   ├── generate_openai_warning_catalog.py # Generación de advertencias WAV con OpenAI TTS
│   └── benchmark_images.py           # Benchmark de compresión de imágenes
│
├── .env.example                      # Plantilla de variables de entorno
├── .gitignore                        # Reglas de exclusión de git
├── requirements.txt                  # Dependencias de Python
├── pyproject.toml                    # Metadatos del proyecto Python
└── README.md                         # Este documento
```

---

##  Instalación y Configuración

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

---

## Puesta en Marcha

Inicia el servidor backend y dashboard con Uvicorn:
```bash
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Accede al dashboard en tu navegador:
👉 **`http://127.0.0.1:8000`**

---

##  Pruebas Unitarias y Diagnóstico

### Suite completa:
```bash
python -m pytest -q
```

### Scripts de Diagnóstico:
```bash
python scripts/test_yolo.py
python scripts/test_openai.py
python scripts/benchmark_images.py
```

---

##  Endpoints de la API REST

| Método | Endpoint | Descripción |
| :--- | :--- | :--- |
| `GET` | `/api/status` | Retorna el estado operativo completo del sistema en JSON. |
| `GET` | `/api/metrics` | Retorna FPS, CPU, RAM, latencias y proporción de fallback OpenAI. |
| `GET` | `/api/health` | Sonda básica de salud y disponibilidad. |
| `GET` | `/api/events` | Lista los eventos históricos registrados en SQLite. |
| `GET` | `/api/events/{id}` | Retorna el detalle completo de un evento por su UUID. |
| `GET` | `/api/cameras/status` | Consulta la resolución y estado de la cámara. |
| `GET` | `/api/config` | Consulta los parámetros de configuración no sensibles. |
| `PATCH` | `/api/config` | Actualiza valores de configuración en memoria; algunos componentes requieren reiniciar el pipeline para aplicar el cambio. |
| `POST` | `/api/debug/test-speech` | Prueba manual de síntesis y reproducción de voz TTS. |
| `POST` | `/api/debug/test-local-warning` | Reproduce una advertencia del catálogo OpenAI TTS sin llamar a la API en ese instante. |
| `WS` | `/ws` | Canal WebSocket para actualizaciones en vivo del dashboard. |

---

##  Marco Ético y Protección de Datos Personales

El diseño adopta principios de minimización de datos y evita deliberadamente la identificación biométrica. Un despliegue real en espacios públicos requerirá evaluación y autorización institucional conforme al marco legal peruano aplicable:
- **Transparencia de voz:** Las advertencias son voces sintéticas generadas por IA con OpenAI TTS, no voces humanas; el dashboard lo informa expresamente.
- **Detección conductual:** El sistema detecta presencia de personas y analiza acciones, **SIN utilizar reconocimiento facial ni intentar identificar nombres o identidades civiles**.
- **No almacenamiento de identidades civiles:** No se registran nombres, rostros ni números de DNI.
- **Minimización de datos:** El buffer es temporal, acotado y muestreado. Los frames no se guardan en disco por defecto; los eventos conservan resultados y metadatos para evaluación.

---

## Mejoras previstas para fases posteriores

Estas mejoras forman parte de la hoja de ruta y **no se consideran implementadas en la versión actual**:

- entrenamiento supervisado futuro sobre las clases abiertas ya operativas de YOLOE;
- evaluación de precisión, recall y falsos positivos con videos etiquetados de campo;
- conjunto de videos positivos y negativos etiquetados;
- reconexión automática de cámaras RTSP/USB;
- configuración completamente dinámica sin reiniciar componentes;
- autenticación y protección de endpoints para un despliegue en red;
- cola persistente o escalable para múltiples cámaras y eventos.

Las zonas iniciales viven en `config/zones.json` con coordenadas normalizadas. Son una calibración genérica de arranque y deben ajustarse con una imagen real de cada cámara antes de utilizarse para decisiones ambientales.

---

##  Equipo y Créditos

- **Institución:** Universidad Nacional Hermilio Valdizán (UNHEVAL) — Huánuco, Perú.
- **Proyecto:** CyT Huallaga 2026-II.
- **Repositorio:** [github.com/dppablito4-oss/proyecto-cyt-huallaga-unheval-2026-ii](https://github.com/dppablito4-oss/proyecto-cyt-huallaga-unheval-2026-ii)
