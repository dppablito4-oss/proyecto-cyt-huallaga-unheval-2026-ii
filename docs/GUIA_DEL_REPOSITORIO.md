# Guía del repositorio: SIVARH

**Proyecto:** SIVARH: Sistema Inteligente de Vigilancia Ambiental para las Riberas del Río Huallaga orientado a la detección preventiva del arrojo directo de residuos sólidos, sector Puente Huallaga – UNHEVAL.

## ¿Qué es este proyecto?

SIVARH es un prototipo de vigilancia ambiental para las riberas del río Huallaga, en el sector Puente Huallaga – UNHEVAL. Usa una cámara para observar la ribera, detecta personas y objetos configurados con YOLO, mantiene tracks anónimos con ByteTrack, calcula su zona y envía una secuencia de imágenes a OpenAI Vision para decidir si ocurrió abandono o arrojo de residuos.

Cuando el resultado se clasifica como `WARN`, el sistema genera una advertencia de voz. Los eventos, las imágenes de vista previa y los audios se guardan localmente para auditoría.

## Modo actual de pruebas

El repositorio está configurado temporalmente en modo manual para hacer pruebas controladas:

1. Se inicia la cámara.
2. En el dashboard se presiona **Iniciar reconocimiento**.
3. El sistema toma 4 imágenes, una cada 1.5 segundos.
4. Se presiona **Enviar imágenes a IA**.
5. OpenAI Vision analiza la secuencia y el sistema registra la decisión.

En este modo no se activa el análisis automático por presencia de personas ni el cooldown de 20 segundos.

Configuración relacionada en `.env`:

```env
MANUAL_RECOGNITION_MODE=True
MANUAL_CAPTURE_FRAMES=4
MANUAL_CAPTURE_INTERVAL_SECONDS=1.5
```

## Flujo del sistema

```text
Cámara USB / RTSP / video
        ↓
VideoPipelineWorker
        ↓
YOLO: detecta personas y objetos configurados
        ↓
ByteTrack: mantiene IDs temporales y trayectorias
        ↓
SceneState + ZoneManager: ubicación y ocupación por zona
        ↓
AssociationEngine: relación temporal persona-objeto
        ↓
Captura manual de 4 imágenes
        ↓
OpenAI Vision: GPT-5.6 Luna
        ↓
DecisionEngine: IGNORE / LOG_ONLY / WARN
        ↓
TTS OpenAI y altavoz, si la decisión es WARN
        ↓
SQLite + dashboard + logs
```

## Estructura principal

| Ruta | Contenido |
|---|---|
| `app/main.py` | Inicia FastAPI, el dashboard y el worker de cámara. |
| `app/config.py` | Lee y centraliza toda la configuración de `.env`. |
| `app/camera/worker.py` | Orquesta captura, modo manual, IA, decisiones y audio. |
| `app/vision/` | YOLO multiclase, ByteTrack, zonas, asociaciones, overlay, historial temporal, buffer, selección y compresión. |
| `app/ai/vision_client.py` | Envía las imágenes y el prompt a OpenAI Vision. |
| `prompts/environmental_event.txt` | Instrucciones que sigue el modelo de visión. |
| `app/events/` | Reglas de decisión y cooldown del modo automático. |
| `app/speech/` | Generación TTS y reproducción por altavoz. |
| `app/storage/` | Guarda eventos en SQLite. |
| `app/api/routes/` | Endpoints REST para estado, cámara, pruebas y control. |
| `frontend/` | Dashboard web: HTML, estilos y JavaScript. |
| `data/` | Audios, fotogramas y base de datos creados durante ejecución. |
| `tests/` | Pruebas unitarias. |
| `scripts/` | Pruebas de cámara, YOLO, OpenAI y benchmarks. |

## Dashboard y botones

El dashboard está en `frontend/`:

| Archivo | Responsabilidad |
|---|---|
| `frontend/index.html` | Estructura y botones visibles. |
| `frontend/js/app.js` | Acciones de los botones. |
| `frontend/js/api.js` | Llamadas HTTP al backend. |
| `frontend/js/dashboard.js` | Actualiza métricas, secuencia y consola. |
| `frontend/js/websocket.js` | Recibe el estado en vivo por WebSocket. |
| `frontend/css/app.css` | Estilos del panel. |

## API útil para pruebas

| Método | Endpoint | Uso |
|---|---|---|
| `POST` | `/api/system/start` | Inicia cámara y pipeline. |
| `POST` | `/api/system/stop` | Detiene cámara y pipeline. |
| `POST` | `/api/system/manual/start-recognition` | Inicia la captura manual de 4 imágenes. |
| `POST` | `/api/system/manual/send-images` | Envía la secuencia manual a OpenAI Vision. |
| `GET` | `/api/status` | Estado en vivo, logs y progreso de la secuencia. |
| `GET` | `/api/events` | Eventos guardados en SQLite. |
| `POST` | `/api/debug/test-speech` | Prueba la generación de voz. |
| `GET` | `/docs` | Documentación interactiva de FastAPI. |
| `WS` | `/ws` | Canal usado por el dashboard para recibir cambios. |

## Configuración importante

| Variable | Valor actual de prueba | Función |
|---|---:|---|
| `OPENAI_VISION_MODEL` | `gpt-5.6-luna` | Modelo de análisis visual. |
| `OPENAI_VISION_REASONING_EFFORT` | `none` | Reduce latencia de la clasificación. |
| `IMAGE_DETAIL` | `low` | Reduce el costo y tiempo de las imágenes. |
| `MANUAL_CAPTURE_FRAMES` | `4` | Imágenes por prueba manual. |
| `MANUAL_CAPTURE_INTERVAL_SECONDS` | `1.5` | Tiempo entre imágenes manuales. |
| `OPENAI_TTS_MODEL` | `gpt-4o-mini-tts` | Motor actual de voz. |
| `OPENAI_TTS_SPEED` | `1.1` | Velocidad de la advertencia. |

No se debe publicar el archivo `.env`, porque contiene la clave de OpenAI. Para compartir una plantilla se usa `.env.example`.

## Cómo ejecutar

```powershell
python -m uvicorn app.main:app --host 127.0.0.1 --port 8001
```

Luego abrir:

```text
http://127.0.0.1:8001
```

La documentación interactiva de los endpoints está en:

```text
http://127.0.0.1:8001/docs
```

## Otros documentos existentes

- `README.md`: explicación general, contexto del proyecto y guía de instalación.
- `docs/ARQUITECTURA_DETALLADA.md`: arquitectura técnica más extensa.
- `documentacio.md`: documento académico sobre el problema ambiental y la propuesta.
- `Investigación sobre la Problemática...docx`: versión Word de la investigación.

## Cuando se termine la fase manual

Para volver al comportamiento habitual:

```env
MANUAL_RECOGNITION_MODE=False
```

Entonces YOLO volverá a disparar el análisis automáticamente cuando detecte personas y se aplicará el cooldown configurado.
