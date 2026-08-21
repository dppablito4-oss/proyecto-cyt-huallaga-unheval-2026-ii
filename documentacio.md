# 1. Nombre provisional

**Sistema inteligente de vigilancia ambiental para detección preventiva del arrojo de residuos sólidos en la ribera del río Huallaga**

Versión inicial:

**0.1 — Prototipo experimental local**

---

# 2. Objetivo técnico del sistema

Construir un sistema modular capaz de:

1. recibir video desde una cámara;
2. detectar localmente la presencia de personas;
3. mantener un pequeño buffer temporal de fotogramas;
4. identificar cuándo existe un evento potencialmente relevante;
5. seleccionar una secuencia corta de imágenes;
6. comprimirlas;
7. enviarlas a una IA multimodal;
8. recibir un resultado estructurado;
9. decidir si corresponde emitir una advertencia;
10. generar dinámicamente el texto de la advertencia;
11. convertir el texto a voz;
12. reproducir el audio;
13. mostrar todo el estado del sistema mediante una interfaz web;
14. registrar métricas para posteriores experimentos.

El prototipo debe diseñarse de manera que posteriormente la webcam pueda reemplazarse por cámaras IP/RTSP sin modificar la lógica principal.

---

# 3. Principio de arquitectura

Separar completamente:

- adquisición de video;
- detección local;
- almacenamiento temporal;
- selección de imágenes;
- análisis mediante IA;
- generación de voz;
- reproducción;
- API web;
- interfaz gráfica;
- métricas.

Ningún módulo debería depender directamente de detalles internos de otro módulo.

Ejemplo:

```text
CameraSource
      ↓
FrameBuffer
      ↓
LocalDetector
      ↓
EventManager
      ↓
FrameSelector
      ↓
ImageProcessor
      ↓
VisionAI
      ↓
DecisionEngine
      ↓
SpeechService
      ↓
AudioOutput
```

En paralelo:

```text
SystemState
      ↓
FastAPI
      ↓
WebSocket
      ↓
Dashboard HTML/JS
```

---

# 4. Arquitectura general del prototipo

```text
                    CÁMARA
                      │
                      ▼
                CameraSource
                      │
                      ▼
                 OpenCV
                      │
              flujo de frames
                      │
         ┌────────────┴────────────┐
         │                         │
         ▼                         ▼
   LocalDetector              FrameBuffer
      YOLO                  últimos segundos
         │                         │
         └────────────┬────────────┘
                      │
                      ▼
                 EventManager
                      │
             evento sospechoso
                      │
                      ▼
                 FrameSelector
                      │
              3 / 5 / 8 frames
                      │
                      ▼
                ImageProcessor
             resize / crop / JPEG
                      │
                      ▼
                   VisionAI
                OpenAI API
                      │
                      ▼
              respuesta JSON
                      │
                      ▼
               DecisionEngine
                │           │
              NO            SÍ
                │           │
               fin          ▼
                       SpeechService
                            │
                            ▼
                         AUDIO
                            │
                            ▼
                       🔊 parlante
```

La interfaz funciona en paralelo:

```text
Todos los módulos
       ↓
   SystemState
       ↓
    FastAPI
       ↓
 WebSocket / REST
       ↓
HTML + CSS + JavaScript
```

---

# 5. Tecnologías principales

## Backend

**Python 3.12+**

Evitar inicialmente versiones demasiado nuevas si existen incompatibilidades con PyTorch, CUDA o paquetes de visión.

---

# 6. Librerías Python

## 6.1 FastAPI

Paquete:

```text
fastapi
```

Responsabilidad:

- servidor HTTP;
- endpoints REST;
- servir estado del sistema;
- configuración;
- pruebas manuales;
- comunicación con frontend;
- WebSockets.

NO debe realizar directamente detección de objetos.

---

## 6.2 Uvicorn

```text
uvicorn[standard]
```

Servidor ASGI utilizado para ejecutar FastAPI.

Ejemplo conceptual:

```text
uvicorn app.main:app --reload
```

---

# 6.3 OpenCV

```text
opencv-python
```

Responsabilidades:

- abrir webcam;
- recibir streams;
- manipular frames;
- resize;
- crop;
- JPEG;
- mostrar/debuggear imágenes;
- lectura de video grabado.

Fuente inicial:

```text
cv2.VideoCapture(0)
```

La arquitectura debe permitir posteriormente:

```text
cv2.VideoCapture("rtsp://...")
```

Por eso NO escribir lógica de negocio directamente alrededor de `VideoCapture`.

Crear una abstracción `CameraSource`.

---

# 6.4 Ultralytics YOLO

```text
ultralytics
```

Responsabilidad inicial:

**detección de personas.**

NO intentar todavía entrenar un modelo para detectar acciones de arrojo de basura.

YOLO inicialmente solo funciona como filtro barato:

```text
¿hay una persona?
```

Si no:

```text
NO ejecutar IA multimodal
```

Si sí:

```text
posible evento → capturar contexto
```

Debe ser posible modificar posteriormente:

- modelo;
- threshold;
- clases;
- tracker.

El paquete de Ultralytics acepta imágenes, ndarray de OpenCV, webcam, video y streams como entrada.

---

# 6.5 OpenAI SDK

```text
openai
```

Responsabilidad:

realizar llamadas desde Python hacia la API multimodal.

La API key debe cargarse desde:

```text
.env
```

Nunca desde:

```text
frontend/app.js
```

Nunca hardcodearla en Git.

Variable:

```text
OPENAI_API_KEY=
```

Modelo configurable:

```text
OPENAI_VISION_MODEL=
```

No hardcodear el modelo en varios archivos.

Debe existir UNA sola configuración central.

---

# 6.6 Pillow

```text
Pillow
```

Puede utilizarse para:

- manipular imágenes;
- convertir formatos;
- crear contact sheets;
- realizar pruebas de compresión.

OpenCV seguirá siendo la herramienta principal para procesamiento de video.

---

# 6.7 Pydantic

FastAPI ya depende de Pydantic.

Utilizarlo explícitamente para definir:

- eventos;
- resultados IA;
- configuración;
- métricas;
- estado del sistema.

Ejemplo conceptual:

```text
AIAnalysisResult
Event
CameraStatus
SystemMetrics
```

---

# 6.8 python-dotenv

```text
python-dotenv
```

Responsabilidad:

cargar configuración local desde `.env`.

---

# 6.9 httpx

```text
httpx
```

Puede utilizarse para futuras llamadas HTTP externas distintas al SDK principal.

No utilizar `requests` y `httpx` mezclados sin necesidad.

Preferir `httpx` por compatibilidad async.

---

# 6.10 NumPy

```text
numpy
```

Necesario para manipulación eficiente de frames.

OpenCV ya trabaja principalmente con arrays NumPy.

---

# 6.11 logging

Utilizar el módulo estándar:

```text
logging
```

NO llenar el proyecto de:

```text
print(...)
```

Crear logs separados por nivel:

```text
INFO
WARNING
ERROR
DEBUG
```

---

# 7. Text-to-Speech

Crear una interfaz:

```text
SpeechService
```

Primera implementación:

```text
OpenAISpeechService
```

Debe recibir solamente:

```text
texto
```

y devolver:

```text
archivo/ruta/audio bytes
```

El endpoint oficial `/v1/audio/speech` permite generar audio a partir de texto.

NO mezclar la generación TTS dentro del módulo VisionAI.

La IA de visión genera:

```text
mensaje_advertencia
```

El módulo TTS convierte:

```text
mensaje_advertencia → audio
```

---

# 8. Reproducción de audio

Crear:

```text
AudioOutput
```

Responsabilidad:

reproducir audio generado.

Primera versión:

altavoces conectados a la PC.

No implementar todavía megáfono IP.

Debe poder reemplazarse posteriormente por:

```text
LocalSpeakerOutput
IPSpeakerOutput
HTTPAudioOutput
```

---

# 9. Estructura de carpetas propuesta

```text
huallaga-ai-monitor/
│
├── app/
│   │
│   ├── main.py
│   │
│   ├── config.py
│   │
│   ├── state.py
│   │
│   ├── dependencies.py
│   │
│   ├── models/
│   │   ├── event.py
│   │   ├── analysis.py
│   │   ├── camera.py
│   │   └── metrics.py
│   │
│   ├── camera/
│   │   ├── base.py
│   │   ├── usb_camera.py
│   │   ├── rtsp_camera.py
│   │   └── video_file.py
│   │
│   ├── vision/
│   │   ├── detector.py
│   │   ├── tracker.py
│   │   ├── frame_buffer.py
│   │   ├── frame_selector.py
│   │   └── image_processor.py
│   │
│   ├── events/
│   │   ├── manager.py
│   │   ├── rules.py
│   │   └── cooldown.py
│   │
│   ├── ai/
│   │   ├── vision_client.py
│   │   ├── schemas.py
│   │   ├── prompts.py
│   │   └── model_config.py
│   │
│   ├── speech/
│   │   ├── service.py
│   │   ├── openai_tts.py
│   │   └── audio_output.py
│   │
│   ├── api/
│   │   ├── routes/
│   │   │   ├── status.py
│   │   │   ├── events.py
│   │   │   ├── cameras.py
│   │   │   ├── config.py
│   │   │   └── debug.py
│   │   │
│   │   └── websocket.py
│   │
│   ├── metrics/
│   │   ├── collector.py
│   │   ├── network.py
│   │   └── latency.py
│   │
│   ├── storage/
│   │   ├── events_repository.py
│   │   └── local_repository.py
│   │
│   └── utils/
│       ├── ids.py
│       ├── time.py
│       └── files.py
│
├── frontend/
│   ├── index.html
│   ├── css/
│   │   └── app.css
│   └── js/
│       ├── app.js
│       ├── api.js
│       ├── websocket.js
│       └── dashboard.js
│
├── prompts/
│   └── environmental_event.txt
│
├── data/
│   ├── events/
│   ├── frames/
│   ├── audio/
│   └── test_videos/
│
├── tests/
│   ├── test_frame_selector.py
│   ├── test_image_processor.py
│   ├── test_ai_schema.py
│   └── test_event_manager.py
│
├── scripts/
│   ├── test_camera.py
│   ├── test_yolo.py
│   ├── test_openai.py
│   └── benchmark_images.py
│
├── .env.example
├── .gitignore
├── requirements.txt
├── README.md
└── pyproject.toml
```

---

# 10. Responsabilidad de cada módulo

## CameraSource

Interfaz abstracta.

Debe proporcionar algo conceptualmente equivalente a:

```text
open()
read()
close()
get_metadata()
```

No debe conocer YOLO.

---

# 11. UsbCamera

Implementación inicial.

Entrada:

```text
camera_index = 0
```

Devuelve frames OpenCV.

---

# 12. RtspCamera

Crear solamente la estructura inicialmente.

No hace falta implementarla completamente durante el primer sprint.

Permitirá después:

```text
rtsp://usuario:password@ip/stream
```

---

# 13. VideoFile

Muy importante para investigación.

Permite ejecutar repetidamente exactamente el mismo evento.

Ejemplo:

```text
persona_tira_botella_001.mp4
```

Esto facilita comparar:

- modelos;
- número de frames;
- compresión;
- prompts.

La webcam NO sirve como único origen de pruebas porque nunca reproduce exactamente la misma situación.

---

# 14. FrameBuffer

Mantendrá los últimos N segundos del video en RAM.

Ejemplo:

```text
BUFFER_SECONDS=5
```

No almacenar video continuamente en disco.

Conceptualmente:

```text
deque(maxlen=N)
```

Debe guardar:

```text
timestamp
frame
```

---

# 15. LocalDetector

Primera versión:

YOLO.

Responsabilidad:

```text
detectar personas
```

Salida conceptual:

```json
{
  "persons": 1,
  "detections": [
    {
      "class": "person",
      "confidence": 0.92,
      "bbox": []
    }
  ]
}
```

No decidir:

```text
esta persona arrojó basura
```

Eso corresponde al análisis multimodal.

---

# 16. Tracker

Inicialmente opcional.

Crear interfaz pero permitir dejarlo desactivado.

Posteriormente permitirá mantener:

```text
person_id=3
```

a través de varios frames.

Podrían utilizarse trackers compatibles con Ultralytics como ByteTrack.

---

# 17. EventManager

Es el coordinador local.

Ejemplo de lógica:

```text
frame
↓
persona detectada
↓
¿existe evento activo?
↓
NO
↓
crear evento
↓
obtener frames previos del buffer
↓
continuar capturando algunos segundos
↓
cerrar evento
↓
enviar a FrameSelector
```

Debe impedir ejecutar 20 llamadas a la IA porque una persona permanece 20 segundos en cámara.

---

# 18. Cooldown

Configurable.

Ejemplo:

```text
EVENT_COOLDOWN_SECONDS=10
```

Evita eventos duplicados.

No debe ser un número mágico escondido en código.

---

# 19. FrameSelector

Uno de los módulos más importantes para investigación.

Entrada:

```text
30-150 frames
```

Salida:

```text
3 / 5 / 8 / N imágenes
```

Primera estrategia:

muestreo temporal uniforme.

Ejemplo:

```text
T-2
T-1
T
T+1
T+2
```

Posteriormente podrán añadirse estrategias:

```text
uniform
motion_based
confidence_based
adaptive
```

---

# 20. ImageProcessor

Responsabilidades:

- resize;
- JPEG;
- calidad;
- crop;
- conversión Base64 cuando sea necesario;
- creación opcional de contact sheet.

Configuración:

```text
IMAGE_MAX_WIDTH=1280
JPEG_QUALITY=70
```

Estos parámetros deben registrarse en cada experimento.

---

# 21. VisionAI

Responsabilidad exclusiva:

```text
imágenes + prompt → resultado estructurado
```

No debe:

- reproducir audio;
- decidir eventos;
- leer webcam;
- modificar frontend.

Entrada:

```text
frames procesados
```

Salida:

objeto `AIAnalysisResult`.

---

# 22. Respuesta estructurada esperada

Modelo lógico:

```json
{
  "event_detected": true,
  "confidence": 0.91,
  "event_type": "possible_littering",
  "object": "plastic bottle",
  "description": "La persona parece dejar una botella en la ribera.",
  "recommended_action": "warn",
  "warning_message": "Por favor, recoja la botella y ayúdenos a mantener limpio el río."
}
```

No confiar en texto libre como:

```text
Creo que posiblemente...
```

Validar siempre mediante esquema.

---

# 23. Regla crítica del sistema

La IA NO identifica personas.

No utilizar:

```text
face recognition
```

No almacenar:

```text
nombre
DNI
identidad biométrica
```

El objetivo es detectar una conducta potencialmente contaminante.

---

# 24. Niveles de decisión

Definir en configuración.

Ejemplo inicial:

```text
confidence < 0.50
    → ignorar

0.50 <= confidence < 0.80
    → registrar evento ambiguo

confidence >= 0.80
    → permitir advertencia
```

Los valores NO deben considerarse definitivos.

Se determinarán mediante experimentación.

---

# 25. Prompt del sistema multimodal

Guardar fuera del código.

Archivo:

```text
prompts/environmental_event.txt
```

Objetivo:

analizar secuencia cronológica.

Debe pedir al modelo:

1. observar cambios entre imágenes;
2. determinar si una persona parece abandonar o arrojar un objeto;
3. diferenciar:
   - portar objeto;
   - recoger objeto;
   - colocar temporalmente;
   - arrojar;
   - abandonar;
4. evitar acusaciones cuando exista ambigüedad;
5. proporcionar nivel de confianza;
6. generar advertencia breve y respetuosa.

Nunca hardcodear un prompt gigantesco dentro de `vision_client.py`.

---

# 26. SpeechService

Entrada:

```text
warning_message
```

Salida:

```text
audio
```

La generación debe ejecutarse únicamente cuando `DecisionEngine` determine que corresponde advertir.

No generar audio para todos los eventos.

---

# 27. DecisionEngine

Responsabilidad:

combinar:

```text
resultado IA
+
reglas locales
+
cooldown
+
estado del sistema
```

Salida:

```text
IGNORE
LOG_ONLY
WARN
```

Posteriormente puede incluir:

```text
REQUEST_MORE_FRAMES
```

para inferencia progresiva.

Pero NO implementar todavía la lógica adaptativa avanzada.

---

# 28. SystemState

Debe existir una fuente central de estado.

Ejemplo:

```json
{
  "running": true,
  "camera_connected": true,
  "fps": 24.7,
  "persons_detected": 1,
  "active_event": true,
  "last_analysis_confidence": 0.91,
  "last_warning": "...",
  "ai_model": "...",
  "frames_per_analysis": 5
}
```

El frontend lee esto.

El frontend NO ejecuta lógica de visión.

---

# 29. FastAPI

Endpoints iniciales.

## GET /api/status

Estado general.

## GET /api/events

Últimos eventos.

## GET /api/events/{id}

Detalle.

## GET /api/config

Configuración no sensible.

## PATCH /api/config

Modificar parámetros permitidos.

Ejemplo:

```text
frames_per_analysis
jpeg_quality
confidence_threshold
```

## POST /api/system/start

Iniciar procesamiento.

## POST /api/system/stop

Detener procesamiento.

## POST /api/test/speech

Probar TTS.

## POST /api/test/analysis

Enviar manualmente imágenes para probar IA.

---

# 30. WebSocket

Ruta:

```text
/ws
```

Utilizarla para mandar al frontend:

```text
camera_status
person_detected
event_started
analysis_started
analysis_finished
warning_started
metrics_updated
```

Esto evita hacer:

```text
fetch cada 100 ms
```

---

# 31. Frontend

Tecnología inicial:

```text
HTML
CSS
JavaScript vanilla
```

NO React inicialmente.

Razón:

el dashboard es auxiliar y debe permanecer sencillo.

Podrá migrarse posteriormente si realmente lo necesita.

---

# 32. Dashboard inicial

Debe mostrar:

## Estado

```text
Sistema: ACTIVO
Cámara: CONECTADA
IA: DISPONIBLE
```

## Video

Preview local.

## Detección

```text
Personas detectadas
FPS
```

## Evento actual

```text
Analizando...
```

## Último resultado

```text
Evento: posible arrojo
Confianza: 91 %
Objeto: botella
```

## Advertencia

```text
"Por favor..."
```

## Métricas

```text
latencia IA
latencia total
tamaño imágenes
cantidad imágenes
modelo
```

---

# 33. Modos de interfaz

Preparar conceptualmente dos vistas.

## Modo exposición

Grande, visual, simple.

## Modo técnico

Muestra:

- FPS;
- resolución;
- número de frames;
- JPEG quality;
- tiempo de selección;
- tamaño del payload;
- tiempo API;
- tiempo TTS;
- tiempo total;
- modelo;
- confidence.

Inicialmente pueden estar en la misma página.

---

# 34. Métricas

Registrar por cada evento:

```text
event_id
timestamp
camera_id
frames_captured
frames_sent
image_resolution
jpeg_quality
payload_bytes
local_detection_confidence
ai_confidence
ai_model
ai_latency_ms
tts_latency_ms
total_latency_ms
decision
```

Estas métricas son fundamentales para el trabajo académico.

---

# 35. Datos experimentales

Separar eventos reales y simulados.

Ejemplo:

```text
data/test_videos/
├── positive/
└── negative/
```

Positive:

```text
persona_deja_botella
persona_tira_bolsa
```

Negative:

```text
persona_caminar_con_botella
persona_recoge_botella
persona_se_sienta
persona_deja_mochila
```

Esto permitirá medir falsos positivos.

---

# 36. Persistencia inicial

NO usar Supabase todavía como dependencia obligatoria.

Primera versión:

```text
JSON / SQLite
```

Preferiblemente:

```text
SQLite
```

Ventajas:

- local;
- portable;
- sin Internet;
- suficiente para pruebas.

Crear interfaz:

```text
EventsRepository
```

Implementación inicial:

```text
SQLiteEventsRepository
```

Posteriormente:

```text
SupabaseEventsRepository
```

El resto del sistema no debe enterarse.

---

# 37. Configuración

Archivo:

```text
.env
```

Ejemplo:

```text
OPENAI_API_KEY=
OPENAI_VISION_MODEL=gpt-5.6-luna

CAMERA_SOURCE=0

YOLO_MODEL=
YOLO_PERSON_CONFIDENCE=0.50

BUFFER_SECONDS=5
EVENT_CAPTURE_SECONDS=3
EVENT_COOLDOWN_SECONDS=10

FRAMES_PER_ANALYSIS=5
IMAGE_MAX_WIDTH=1280
JPEG_QUALITY=70

AI_WARNING_THRESHOLD=0.80
```

Crear:

```text
.env.example
```

SIN secretos.

---

# 38. Seguridad

`.gitignore` debe contener:

```text
.env
__pycache__/
*.pyc
.venv/
data/events/*
data/audio/*
```

No subir API keys.

No mostrar secretos mediante `/api/config`.

---

# 39. Flujo completo esperado

```text
1. iniciar servidor

2. cargar configuración

3. inicializar cámara

4. inicializar detector YOLO

5. iniciar FrameBuffer

6. leer frames

7. YOLO detecta persona

8. EventManager crea Event

9. recopilar contexto temporal

10. FrameSelector selecciona N imágenes

11. ImageProcessor:
       resize
       crop opcional
       JPEG

12. VisionAI llama API

13. validar JSON

14. DecisionEngine decide

15. registrar evento

16. si WARN:
       generar voz
       reproducir audio

17. actualizar frontend

18. continuar vigilancia
```

---

# 40. Concurrencia

No ejecutar todo en el thread principal.

Como mínimo separar:

```text
camera loop
AI analysis
web server
```

La captura de cámara NO puede congelarse mientras la API tarda varios segundos.

Arquitectura sugerida:

```text
Camera Worker
      ↓
 Event Queue
      ↓
Analysis Worker
```

FastAPI continúa funcionando independientemente.

Primera versión puede utilizar:

```text
threading
queue.Queue
```

o:

```text
asyncio
```

pero no mezclar ambos indiscriminadamente.

Preferencia inicial:

- captura OpenCV en thread;
- cola thread-safe;
- API FastAPI async;
- análisis ejecutado por worker.

---

# 41. Cola de eventos

Utilizar una cola.

Ejemplo:

```text
EventQueue
```

Evita ejecutar simultáneamente cinco análisis porque aparecen cinco personas.

Primera versión:

```text
MAX_CONCURRENT_ANALYSES=1
```

Posteriormente podrá aumentarse.

---

# 42. Manejo de errores

El sistema debe continuar funcionando si:

## falla OpenAI

```text
registrar error
no reproducir advertencia incorrecta
continuar detección local
```

## se desconecta cámara

```text
intentar reconexión
actualizar dashboard
```

## falla TTS

```text
registrar
continuar monitoreo
```

## respuesta IA inválida

```text
no actuar
registrar raw response para debugging
```

Nunca realizar una advertencia cuando el análisis falla.

---

# 43. Desarrollo por etapas

## Fase 0

Crear solamente estructura.

Debe arrancar FastAPI.

Dashboard básico.

---

## Fase 1

Webcam → OpenCV → preview.

---

## Fase 2

Webcam → YOLO → detectar persona.

---

## Fase 3

Implementar buffer + eventos.

---

## Fase 4

Seleccionar frames y guardarlos localmente.

SIN API todavía.

---

## Fase 5

Enviar manualmente imágenes a IA.

---

## Fase 6

Integrar análisis automático.

---

## Fase 7

Integrar TTS.

---

## Fase 8

Integración completa.

---

## Fase 9

Benchmarks.

---

# 44. Lo que NO debe implementar todavía el agente

NO implementar:

- Supabase;
- autenticación;
- reconocimiento facial;
- Kotlin;
- Android;
- 4G adaptativo;
- cámaras PTZ;
- ONVIF;
- fibra;
- múltiples cámaras;
- seguimiento automático mecánico;
- modelos IA dinámicos;
- routing Luna/Terra/Sol;
- razonamiento adaptativo;
- inferencia progresiva;
- almacenamiento cloud;
- entrenamiento YOLO personalizado.

Solo dejar la arquitectura preparada para extensión.

---

# 45. Principio fundamental

El primer objetivo NO es detectar perfectamente basura.

El primer objetivo es demostrar el pipeline:

```text
CÁMARA
↓
PERSONA DETECTADA
↓
EVENTO
↓
IMÁGENES
↓
IA
↓
JSON
↓
DECISIÓN
↓
VOZ
```

Cuando eso funcione de extremo a extremo, recién se optimiza.

---

# 46. Diseño extensible

El sistema debe permitir posteriormente cambiar:

```text
UsbCamera
```

por:

```text
RtspCamera
```

sin cambiar VisionAI.

Cambiar:

```text
OpenAIVisionAI
```

por otro proveedor sin cambiar CameraSource.

Cambiar:

```text
LocalSpeakerOutput
```

por altavoz IP sin cambiar DecisionEngine.

Cambiar:

```text
SQLiteRepository
```

por Supabase sin cambiar EventManager.

---

# 47. Contrato conceptual de Event

```json
{
  "id": "uuid",
  "camera_id": "CAM_001",
  "started_at": "...",
  "ended_at": "...",
  "local_detection": {
    "persons": 1,
    "max_confidence": 0.93
  },
  "capture": {
    "total_frames": 75,
    "selected_frames": 5,
    "jpeg_quality": 70
  },
  "analysis": null,
  "decision": null,
  "metrics": {}
}
```

---

# 48. Contrato conceptual de Analysis

```json
{
  "event_detected": true,
  "confidence": 0.91,
  "event_type": "possible_littering",
  "object": "plastic_bottle",
  "description": "Possible disposal of a plastic bottle.",
  "recommended_action": "warn",
  "warning_message": "Por favor, recoja la botella y ayúdenos a mantener limpio el río."
}
```

---

# 49. Primera prueba end-to-end objetivo

Escenario:

```text
una persona entra al encuadre
↓
YOLO detecta persona
↓
se crea Event
↓
se recuperan imágenes del buffer
↓
se seleccionan 5
↓
IA analiza
↓
devuelve JSON
↓
dashboard muestra resultado
↓
si corresponde:
se genera voz
↓
parlante reproduce advertencia
```

Esta prueba define el primer milestone funcional.

---

# 50. Instrucción específica para el agente

Crear la estructura completa del proyecto descrita en este documento.

En esta primera ejecución:

1. crear carpetas;
2. crear módulos;
3. crear clases/interfaces base;
4. crear modelos Pydantic;
5. crear configuración;
6. crear `.env.example`;
7. crear `requirements.txt`;
8. crear FastAPI básico;
9. crear frontend básico;
10. implementar endpoints mínimos de health/status;
11. dejar placeholders explícitos para cámara, YOLO, IA y TTS;
12. documentar cada módulo;
13. garantizar que el proyecto arranque sin necesidad de cámara ni API key;
14. NO implementar todavía la lógica completa de detección;
15. NO inventar funcionalidades adicionales.

El código debe privilegiar:

- claridad;
- modularidad;
- tipado;
- mantenibilidad;
- facilidad para experimentar.

Evitar abstracciones excesivas y patrones empresariales innecesarios.

El sistema todavía es un prototipo de investigación.