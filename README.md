# Huallaga AI Monitor 🌊🤖

**Sistema inteligente de vigilancia ambiental para la detección preventiva del arrojo de residuos sólidos en la ribera del río Huallaga**

*Proyecto de Investigación Aplicada en Ciencia y Tecnología (CyT) — Universidad Nacional Hermilio Valdizán (UNHEVAL), Huánuco, Perú (2026-II).*

---

## 📌 Resumen del Proyecto

El río Huallaga en la provincia de Leoncio Prado (Tingo María, Huánuco) constituye un ecosistema fluvial estratégico de gran biodiversidad y fuente vital de agua para consumo, agricultura y desarrollo comunitario. Sin embargo, enfrenta una creciente amenaza por vertimientos clandestinos y el arrojo indebido de residuos sólidos (botellas plásticas, bolsas y empaques) en sus riberas.

**Huallaga AI Monitor** es un sistema modular de computación en el borde (Edge Computing) e Inteligencia Artificial Multimodal diseñado para:

1. **Adquirir video continuo** desde cámaras USB, cámaras IP/RTSP o grabaciones pregrabadas.
2. **Detectar personas localmente** mediante modelos ligeros de Ultralytics YOLO (`yolov8n`), actuando como un filtro económico de bajo costo computacional.
3. **Mantener un buffer temporal en memoria RAM** con los últimos segundos de video para conservar el contexto cronológico del evento.
4. **Seleccionar y comprimir fotogramas representativos** optimizando el consumo de ancho de banda y latencia.
5. **Analizar la secuencia mediante IA Multimodal** (OpenAI Vision) para clasificar con precisión conductas de abandono o arrojo de basura frente a actividades habituales.
6. **Emitir advertencias sonoras preventivas en tiempo real** mediante Text-to-Speech (OpenAI TTS) y altavoces locales/IP.
7. **Visualizar y registrar métricas académicas** en tiempo real a través de un Dashboard Web interactivo y una base de datos local SQLite.

---

## 🏗️ Arquitectura del Sistema

```
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

En paralelo, el estado global (`SystemState`) se sincroniza en tiempo real con el **Frontend Dashboard** a través de **FastAPI** y **WebSockets**.

---

## 📂 Estructura del Repositorio

```text
huallaga-ai-monitor/
│
├── app/                              # Paquete principal del Backend (FastAPI & Visión)
│   ├── main.py                       # Punto de entrada FastAPI y servidor estático
│   ├── config.py                     # Configuración centralizada (.env)
│   ├── state.py                      # Estado global del sistema (SystemState)
│   ├── dependencies.py               # Inyección de dependencias FastAPI
│   │
│   ├── models/                       # Modelos de datos Pydantic
│   │   ├── event.py                  # Entidad EventModel y detecciones
│   │   ├── analysis.py               # Esquema de respuesta de IA (AIAnalysisResult)
│   │   ├── camera.py                 # Estado de cámara
│   │   └── metrics.py                # Métricas de latencia y payload
│   │
│   ├── camera/                       # Módulo de Adquisición de Video
│   │   ├── base.py                   # Interfaz abstracta CameraSource
│   │   ├── usb_camera.py             # Implementación para webcam USB
│   │   ├── rtsp_camera.py            # Placeholder para cámaras IP / RTSP
│   │   └── video_file.py             # Reproducción de videos de prueba (.mp4)
│   │
│   ├── vision/                       # Procesamiento de Visión por Computadora
│   │   ├── detector.py               # Detector YOLO local (filtro económico)
│   │   ├── tracker.py                # Interfaz de seguimiento de objetos
│   │   ├── frame_buffer.py           # Buffer circular temporal en RAM (deque)
│   │   ├── frame_selector.py         # Muestreo temporal uniforme de frames
│   │   └── image_processor.py        # Redimensionamiento, JPEG y Base64
│   │
│   ├── events/                       # Gestión de Eventos y Reglas de Negocio
│   │   ├── manager.py                # Gestor del ciclo de vida del evento
│   │   ├── cooldown.py               # Filtro temporal para evitar duplicados
│   │   └── rules.py                  # DecisionEngine (IGNORE / LOG_ONLY / WARN)
│   │
│   ├── ai/                           # Integración con IA Multimodal
│   │   ├── vision_client.py          # Cliente OpenAI Vision (con modo mock)
│   │   ├── schemas.py                # Re-export de esquemas de inferencia
│   │   ├── prompts.py                # Cargador dinámico de prompts
│   │   └── model_config.py           # Hiperparámetros de muestreo
│   │
│   ├── speech/                       # Síntesis y Reproducción de Audio
│   │   ├── service.py                # Interfaz abstracta SpeechService
│   │   ├── openai_tts.py             # Síntesis con OpenAI TTS (/v1/audio/speech)
│   │   └── audio_output.py           # Reproducción en altavoces locales
│   │
│   ├── storage/                      # Capa de Persistencia
│   │   ├── events_repository.py      # Interfaz abstracta de repositorio
│   │   └── local_repository.py       # Persistencia en SQLite local (data/events.db)
│   │
│   ├── metrics/                      # Recolección de Métricas Experimentales
│   │   ├── collector.py              # Agregador de métricas
│   │   ├── latency.py                # Cronómetro de alta resolución (LatencyTimer)
│   │   └── network.py                # Cálculo de tamaño de payloads
│   │
│   ├── utils/                        # Utilidades auxiliares (IDs, tiempo, archivos)
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
├── frontend/                         # Dashboard Web (Vanilla HTML/CSS/JS)
│   ├── index.html                    # Estructura de la interfaz
│   ├── css/
│   │   └── app.css                   # Estilos modernos dark-mode glassmorphic
│   └── js/
│       ├── api.js                    # Cliente HTTP REST
│       ├── websocket.js              # Cliente WebSocket con autoreconexión
│       ├── dashboard.js              # Actualización dinámica del DOM
│       └── app.js                    # Inicializador de la aplicación web
│
├── prompts/                          # Prompts especializados externos
│   └── environmental_event.txt       # Prompt de análisis cronológico de visión
│
├── docs/                             # Documentación técnica extendida
│   └── ARQUITECTURA_DETALLADA.md     # Especificación técnica exhaustiva
│
├── data/                             # Almacenamiento local (ignorado en git)
│   ├── events/                       # Metadatos de eventos
│   ├── frames/                       # Capturas de imágenes guardadas
│   ├── audio/                        # Archivos de audio generados
│   └── test_videos/                  # Videos para pruebas controladas
│
├── tests/                            # Pruebas Unitarias
│   ├── test_frame_selector.py
│   ├── test_image_processor.py
│   ├── test_ai_schema.py
│   └── test_event_manager.py
│
├── scripts/                          # Scripts de Prueba y Benchmarking
│   ├── test_camera.py                # Verificación de cámara USB
│   ├── test_yolo.py                  # Verificación de detección YOLO
│   ├── test_openai.py                # Verificación de cliente Vision AI
│   └── benchmark_images.py           # Benchmark de compresión de imágenes
│
├── .env.example                      # Plantilla de variables de entorno
├── .gitignore                        # Reglas de exclusión de git
├── requirements.txt                  # Dependencias de Python
├── pyproject.toml                    # Metadatos del proyecto Python
└── README.md                         # Documentación general del repositorio
```

---

## ⚙️ Instalación y Configuración

### 1. Clonar el repositorio
```bash
git clone https://github.com/dppablito4-oss/proyecto-cyt-huallaga-unheval-2026-ii.git
cd proyecto-cyt-huallaga-unheval-2026-ii
```

### 2. Crear entorno virtual e instalar dependencias
```bash
python -m venv .venv
# En Windows:
.venv\Scripts\activate
# En Linux/macOS:
source .venv/bin/activate

pip install -r requirements.txt
```

### 3. Configurar variables de entorno
Copia la plantilla `.env.example` a `.env`:
```bash
cp .env.example .env
```
Edita `.env` y configura tu clave de OpenAI si deseas inferencia real:
```env
OPENAI_API_KEY=sk-tu-api-key-aqui
OPENAI_VISION_MODEL=gpt-4o
OPENAI_TTS_MODEL=tts-1
OPENAI_TTS_VOICE=alloy
CAMERA_SOURCE=0
YOLO_MODEL=yolov8n.pt
```
> [!NOTE]
> El sistema arranca y funciona perfectamente en **Modo Simulación (Fase 0)** incluso sin configurar una API Key ni tener una cámara conectada.

---

## 🚀 Ejecución del Servidor

Inicia el servidor backend y el dashboard web con Uvicorn:
```bash
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Abre tu navegador en:
👉 **`http://127.0.0.1:8000`**

---

## 🧪 Ejecución de Pruebas Unitarias y Benchmarks

### Pruebas Unitarias:
```bash
python tests/test_frame_selector.py
python tests/test_image_processor.py
python tests/test_ai_schema.py
python tests/test_event_manager.py
```

### Scripts de Diagnóstico y Benchmark:
```bash
python scripts/test_yolo.py
python scripts/test_openai.py
python scripts/benchmark_images.py
```

---

## 📡 Endpoints de la API REST

| Método | Endpoint | Descripción |
| :--- | :--- | :--- |
| `GET` | `/api/status` | Retorna el estado operativo completo del sistema en JSON. |
| `GET` | `/api/health` | Sonda de salud y disponibilidad (Health Check). |
| `GET` | `/api/events` | Lista los eventos históricos registrados en SQLite. |
| `GET` | `/api/events/{id}` | Retorna el detalle completo de un evento por su UUID. |
| `GET` | `/api/cameras/status` | Consulta la resolución y estado de enlace de la cámara. |
| `GET` | `/api/config` | Consulta los parámetros operacionales activos no sensibles. |
| `PATCH` | `/api/config` | Modifica en caliente parámetros (frames, calidad JPEG, umbrales). |
| `POST` | `/api/debug/test-speech` | Prueba manual de síntesis y reproducción de voz TTS. |
| `WS` | `/ws` | Canal WebSocket para actualizaciones reactivas en tiempo real. |

---

## 🛡️ Principios Éticos y Privacidad

- **Vigilancia Ambiental, NO Reconocimiento Facial:** El sistema está diseñado exclusivamente para evaluar conductas de contaminación y objetos.
- **Sin datos biométricos:** No se almacenan nombres, documentos de identidad (DNI) ni perfiles de personas.
- **Transparencia Académica:** Todo el código y métricas experimentales son reproducibles con fines de investigación científica.

---

## 👥 Equipo de Investigación y Créditos

- **Institución:** Universidad Nacional Hermilio Valdizán (UNHEVAL) — Huánuco, Perú.
- **Proyecto:** CyT Huallaga 2026-II.
- **Repositorio:** [github.com/dppablito4-oss/proyecto-cyt-huallaga-unheval-2026-ii](https://github.com/dppablito4-oss/proyecto-cyt-huallaga-unheval-2026-ii)
