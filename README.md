# Huallaga AI Monitor

**Sistema inteligente de vigilancia ambiental para la detección preventiva del arrojo de residuos sólidos en la ribera del río Huallaga**

*Proyecto de Investigación Aplicada en Ciencia y Tecnología (CyT) — Universidad Nacional Hermilio Valdizán (UNHEVAL), Huánuco, Perú (2026-II).*

---

## Contexto y Justificación Científica

El río Huallaga a su paso por el área metropolitana de **Huánuco, Amarilis y Pillco Marca** enfrenta una severa crisis por contaminación y acumulación recurrente de residuos sólidos. Informes oficiales de entidades como el OEFA, FEMA y la UNHEVAL han documentado hasta **216 puntos críticos** a lo largo de su cuenca regional, con una generación diaria de entre **100 y 120 toneladas de residuos**.

En sectores de alto tránsito como el **Puente Huallaga**, el **Malecón Walker Soberón**, el **Malecón Huallaga** y los accesos peatonales a la **Universidad Nacional Hermilio Valdizán (UNHEVAL)** en Cayhuayna, la dilución de la responsabilidad y el anonimato propician el arrojo directo (*littering*) de botellas plásticas PET, bolsas de polietileno y empaques hacia las pendientes y el caudal del río.

Las estrategias tradicionales basadas en campañas de limpieza periódicas son valiosas pero de efecto efímero debido a la reincidencia conductual. **Huallaga AI Monitor** aborda la raíz del problema mediante una **intervención preventiva en el instante pre-impacto**, utilizando visión por computadora, modelos multimodales de Inteligencia Artificial y estímulos disuasorios acústicos (*nudges* cognitivos) en tiempo real para provocar el desistimiento del infractor antes de que el residuo toque el agua.

---

##  Delimitación del Alcance

| Fuente de Contaminación | Descripción | Alcance en Huallaga AI Monitor |
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
   LocalDetector (YOLO)                     FrameBuffer (5s RAM)
(¿Hay personas presentes?)               (Contexto temporal previo)
         │                                           │
         └─────────────────────┬─────────────────────┘
                               │
                               ▼
                          EventManager
                     (Cooldown & Trigger)
                               │
                               ▼
                         FrameSelector
                    (3 / 5 / 8 frames clave)
                               │
                               ▼
                        ImageProcessor
                 (Resize 1280w + JPEG 70 + B64)
                               │
                               ▼
                           VisionAI
                 (OpenAI Multimodal / GPT-4o)
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
                                     SpeechService
                                    (OpenAI TTS-1)
                                           │
                                           ▼
                                      AudioOutput
                                  (🔊 Altavoz Local)
```

En paralelo, el estado global (`SystemState`) se difunde reactivamente al **Dashboard Web** a través de **FastAPI** y canales **WebSocket**.

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
│   │   ├── detector.py               # YOLOv8 local (filtro económico de personas)
│   │   ├── tracker.py                # Interfaz de seguimiento de objetos
│   │   ├── frame_buffer.py           # Buffer circular temporal en RAM (5s)
│   │   ├── frame_selector.py         # Muestreo temporal uniforme de frames
│   │   └── image_processor.py        # Compresión JPEG, resize y Base64
│   │
│   ├── events/                       # Gestión de Eventos y Reglas de Negocio
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
│   ├── audio/                        # Archivos de audio generados
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

### 3. Variables de entorno
Copia el archivo `.env.example` a `.env`:
```bash
cp .env.example .env
```
Edita `.env` con tus credenciales si deseas ejecutar inferencia real:
```env
OPENAI_API_KEY=sk-tu-api-key-aqui
OPENAI_VISION_MODEL=gpt-4o
OPENAI_TTS_MODEL=tts-1
OPENAI_TTS_VOICE=alloy
CAMERA_SOURCE=0
YOLO_MODEL=yolov8n.pt
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

### Pruebas de Módulos:
```bash
python tests/test_frame_selector.py
python tests/test_image_processor.py
python tests/test_ai_schema.py
python tests/test_event_manager.py
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
| `GET` | `/api/health` | Sonda básica de salud y disponibilidad. |
| `GET` | `/api/events` | Lista los eventos históricos registrados en SQLite. |
| `GET` | `/api/events/{id}` | Retorna el detalle completo de un evento por su UUID. |
| `GET` | `/api/cameras/status` | Consulta la resolución y estado de la cámara. |
| `GET` | `/api/config` | Consulta los parámetros de configuración no sensibles. |
| `PATCH` | `/api/config` | Modifica en caliente parámetros (frames, calidad JPEG, umbrales). |
| `POST` | `/api/debug/test-speech` | Prueba manual de síntesis y reproducción de voz TTS. |
| `WS` | `/ws` | Canal WebSocket para actualizaciones en vivo del dashboard. |

---

##  Marco Ético y Protección de Datos Personales

El diseño del sistema cumple estrictamente con el marco legal peruano (**Ley N° 29733 de Protección de Datos Personales**, **Ley N° 30120** y la **Directiva N° 01-2020-JUS/DGTAIPD**):
- **Anonimización por Diseño (*Privacy by Design*):** El sistema analiza siluetas y conductas físicas de arrojo de objetos, **SIN utilizar reconocimiento facial ni identificación biométrica**.
- **No almacenamiento de identidades civiles:** No se registran nombres, rostros ni números de DNI.
- **Minimización de Datos:** Los fotogramas donde no se detectan eventos se descartan instantáneamente de la memoria volátil; solo se conservan metadatos estadísticos anonimizados para investigación académica.

---

##  Equipo y Créditos

- **Institución:** Universidad Nacional Hermilio Valdizán (UNHEVAL) — Huánuco, Perú.
- **Proyecto:** CyT Huallaga 2026-II.
- **Repositorio:** [github.com/dppablito4-oss/proyecto-cyt-huallaga-unheval-2026-ii](https://github.com/dppablito4-oss/proyecto-cyt-huallaga-unheval-2026-ii)
