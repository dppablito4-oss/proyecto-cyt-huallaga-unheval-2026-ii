"""
Módulo de Worker de Captura Continua y Pipeline de Vigilancia (VideoPipelineWorker)
==================================================================================

Responsabilidad:
----------------
Ejecutar el bucle principal de captura de video, detección local con YOLO, gestión de
eventos y análisis multimodal en un hilo de fondo dedicado. Esto permite que el servidor
FastAPI (y el dashboard web) continúen funcionando sin bloqueos mientras la cámara captura
fotogramas continuamente.

Flujo de invocación:
--------------------
1. `app.main` inicializa y arranca el worker al evento `startup` de FastAPI.
2. El worker abre la cámara configurada y ejecuta un ciclo continuo:
   Frame → FrameBuffer → LocalDetector (YOLO) → EventManager → FrameSelector
   → ImageProcessor → VisionAI → DecisionEngine → SpeechService → AudioOutput.
3. En `shutdown`, el worker se detiene limpiamente cerrando la cámara y liberando recursos.
"""

import time
import logging
import threading
import uuid
from datetime import datetime
from typing import Optional

from app.config import settings
from app.state import system_state
from app.camera.base import CameraSource
from app.camera.usb_camera import UsbCamera
from app.camera.video_file import VideoFileCamera
from app.vision.detector import LocalDetector
from app.vision.frame_buffer import FrameBuffer
from app.vision.frame_selector import FrameSelector
from app.vision.image_processor import ImageProcessor
from app.events.manager import EventManager
from app.events.rules import DecisionEngine
from app.ai.vision_client import VisionAI
from app.speech.openai_tts import OpenAISpeechService
from app.speech.audio_output import LocalSpeakerOutput
from app.storage.local_repository import SQLiteEventsRepository
from app.models.event import EventModel, LocalDetectionSummary

logger = logging.getLogger(__name__)


def _create_camera_source() -> CameraSource:
    """
    Instancia la fuente de cámara correcta según `settings.CAMERA_SOURCE`.
    - Cadenas numéricas ("0", "1") → UsbCamera
    - Rutas a archivos de video → VideoFileCamera
    - URLs RTSP → RtspCamera (importada dinámicamente)
    """
    source = settings.CAMERA_SOURCE
    if source.isdigit():
        return UsbCamera(
            camera_index=int(source),
            width=settings.CAMERA_WIDTH,
            height=settings.CAMERA_HEIGHT,
            fps=settings.CAMERA_FPS
        )
    elif source.startswith("rtsp://"):
        from app.camera.rtsp_camera import RtspCamera
        return RtspCamera(rtsp_url=source)
    else:
        return VideoFileCamera(file_path=source, loop=True)


class VideoPipelineWorker:
    """
    Worker de captura y procesamiento continuo de video en hilo de fondo.
    Orquesta todo el pipeline: cámara → YOLO → eventos → IA → voz → persistencia.
    """

    def __init__(self):
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._camera: Optional[CameraSource] = None

        # Componentes del pipeline
        self._detector = LocalDetector(
            model_name=settings.YOLO_MODEL,
            confidence_threshold=settings.YOLO_PERSON_CONFIDENCE
        )
        self._frame_buffer = FrameBuffer(
            buffer_seconds=settings.BUFFER_SECONDS,
            fps=settings.BUFFER_FPS
        )
        self._frame_selector = FrameSelector(
            target_frames=settings.FRAMES_PER_ANALYSIS,
            strategy="uniform"
        )
        self._image_processor = ImageProcessor(
            max_width=settings.IMAGE_MAX_WIDTH,
            jpeg_quality=settings.JPEG_QUALITY
        )
        self._event_manager = EventManager(
            cooldown_seconds=settings.EVENT_COOLDOWN_SECONDS
        )
        self._decision_engine = DecisionEngine(
            warning_threshold=settings.AI_WARNING_THRESHOLD
        )
        self._vision_ai = VisionAI()
        self._tts_service = OpenAISpeechService()
        self._audio_output = LocalSpeakerOutput()
        self._repository = SQLiteEventsRepository()

        # Frame compartido para streaming MJPEG (leído por el endpoint /api/cameras/stream)
        self._current_frame = None
        self._frame_lock = threading.Lock()
        self._analysis_thread: Optional[threading.Thread] = None
        self._manual_capture_thread: Optional[threading.Thread] = None
        self._manual_frames = []
        self._manual_jpeg_quality = settings.JPEG_QUALITY
        self._manual_lock = threading.Lock()
        self._runtime_config_lock = threading.Lock()

    @property
    def current_frame(self):
        """Obtiene el último frame capturado (thread-safe) para streaming MJPEG."""
        with self._frame_lock:
            return self._current_frame

    def start(self) -> bool:
        """Arranca el hilo de captura continua."""
        if self._thread is not None and self._thread.is_alive():
            logger.warning("El worker de video ya está en ejecución.")
            return False

        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_loop, name="VideoPipelineWorker", daemon=True)
        self._thread.start()
        logger.info("VideoPipelineWorker iniciado.")
        return True

    def stop(self) -> None:
        """Detiene el hilo de captura de forma limpia."""
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=5.0)
            self._thread = None
        analysis_thread = self._analysis_thread
        if analysis_thread is not None:
            analysis_thread.join(timeout=5.0)
            if not analysis_thread.is_alive() and self._analysis_thread is analysis_thread:
                self._analysis_thread = None
        if self._camera is not None:
            self._camera.close()
            self._camera = None
        system_state.set_camera_status(connected=False, source=settings.CAMERA_SOURCE, fps=0.0)
        logger.info("VideoPipelineWorker detenido.")

    def start_manual_recognition(self) -> tuple[bool, str]:
        """Inicia una captura manual de cuatro imágenes; todavía no consulta la IA."""
        if not self.is_running or self._camera is None:
            return False, "La cámara no está activa. Inicia el pipeline primero."
        if self._analysis_thread is not None and self._analysis_thread.is_alive():
            return False, "Hay un análisis en curso."
        if self._manual_capture_thread is not None and self._manual_capture_thread.is_alive():
            return False, "La secuencia manual ya se está capturando."

        with self._manual_lock:
            self._manual_frames = []
        system_state.set_analysis_preview_urls([])
        system_state.set_manual_sequence_status(captured=0, ready=False)
        self._manual_capture_thread = threading.Thread(
            target=self._capture_manual_sequence,
            name="ManualRecognitionCapture",
            daemon=True,
        )
        self._manual_capture_thread.start()
        return True, "Captura manual iniciada."

    def analyze_manual_sequence(self) -> tuple[bool, str]:
        """Envía a la IA la última secuencia manual lista."""
        if self._analysis_thread is not None and self._analysis_thread.is_alive():
            return False, "Hay un análisis en curso."
        with self._manual_lock:
            jpeg_frames = list(self._manual_frames)
        if len(jpeg_frames) != settings.MANUAL_CAPTURE_FRAMES:
            return False, f"Primero captura los {settings.MANUAL_CAPTURE_FRAMES} fotogramas."

        event = EventModel(
            id=str(uuid.uuid4()),
            camera_id="CAM_001",
            started_at=datetime.now(),
            status="created",
            local_detection=LocalDetectionSummary(),
        )
        with self._manual_lock:
            event.capture.jpeg_quality = self._manual_jpeg_quality
        system_state.set_active_event(True)
        system_state.set_manual_sequence_status(captured=len(jpeg_frames), ready=False)
        self._analysis_thread = threading.Thread(
            target=self._process_event,
            args=(event, jpeg_frames, True),
            name=f"ManualAnalysis-{event.id[:8]}",
            daemon=True,
        )
        self._analysis_thread.start()
        return True, "Imágenes enviadas a la IA."

    def _capture_manual_sequence(self) -> None:
        """Guarda la imagen actual cada 1.5 segundos y publica una vista previa."""
        captured = []
        preview_urls = []
        total = settings.MANUAL_CAPTURE_FRAMES
        interval = settings.MANUAL_CAPTURE_INTERVAL_SECONDS
        preview_dir = settings.DATA_DIR / "frames"
        preview_dir.mkdir(parents=True, exist_ok=True)
        with self._runtime_config_lock:
            sequence_processor = ImageProcessor(
                max_width=self._image_processor.max_width,
                jpeg_quality=self._image_processor.jpeg_quality,
            )
        system_state.add_log("SEQUENCE", f"[MANUAL] Capturando {total} fotogramas, uno cada {interval:g}s.")

        for index in range(total):
            if self._stop_event.is_set():
                return
            with self._frame_lock:
                frame = None if self._current_frame is None else self._current_frame.copy()
            if frame is None:
                system_state.add_log("ERROR", "[MANUAL] No se pudo obtener un fotograma de la cámara.")
                system_state.set_manual_sequence_status(captured=len(captured), ready=False)
                return

            jpeg_bytes = sequence_processor.compress_jpeg(frame)
            captured.append(jpeg_bytes)
            preview_name = f"manual-preview-{uuid.uuid4().hex}-{index + 1}.jpg"
            (preview_dir / preview_name).write_bytes(jpeg_bytes)
            preview_urls.append(f"/api/cameras/analysis-preview/{preview_name}")
            system_state.set_analysis_preview_urls(preview_urls)
            system_state.set_manual_sequence_status(captured=len(captured), ready=False)
            system_state.add_log("SEQUENCE", f"[MANUAL] Fotograma {index + 1}/{total} capturado.")
            if index < total - 1:
                time.sleep(interval)

        with self._manual_lock:
            self._manual_frames = captured
            self._manual_jpeg_quality = sequence_processor.jpeg_quality
        system_state.set_manual_sequence_status(captured=total, ready=True)
        system_state.add_log("SEQUENCE", "[MANUAL] Secuencia lista. Presiona 'Enviar imágenes a IA'.")

    def switch_source(self, new_source: str) -> bool:
        """
        Cambia la fuente de captura de video en caliente.
        Detiene la cámara actual si está activa, actualiza la configuración y la reinicia con la nueva fuente.
        """
        logger.info(f"Cambiando fuente de cámara a: {new_source}")
        was_running = self.is_running
        if was_running:
            self.stop()

        settings.CAMERA_SOURCE = str(new_source)
        system_state.set_camera_status(connected=False, source=settings.CAMERA_SOURCE, fps=0.0)

        if was_running:
            return self.start()
        return True

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def apply_runtime_config(
        self,
        frames_per_analysis: Optional[int] = None,
        jpeg_quality: Optional[int] = None,
        ai_warning_threshold: Optional[float] = None,
    ) -> dict:
        """Aplica configuración mutable al singleton y a los componentes ya construidos."""
        applied = {}
        with self._runtime_config_lock:
            if frames_per_analysis is not None:
                settings.FRAMES_PER_ANALYSIS = frames_per_analysis
                self._frame_selector.target_frames = frames_per_analysis
                system_state.set_frames_per_analysis(frames_per_analysis)
                applied["FRAMES_PER_ANALYSIS"] = frames_per_analysis

            if jpeg_quality is not None:
                settings.JPEG_QUALITY = jpeg_quality
                self._image_processor.jpeg_quality = jpeg_quality
                applied["JPEG_QUALITY"] = jpeg_quality

            if ai_warning_threshold is not None:
                settings.AI_WARNING_THRESHOLD = ai_warning_threshold
                self._decision_engine.warning_threshold = ai_warning_threshold
                applied["AI_WARNING_THRESHOLD"] = ai_warning_threshold

        if applied:
            summary = ", ".join(f"{key}={value}" for key, value in applied.items())
            system_state.add_log("INFO", f"Configuración operativa actualizada: {summary}.")
        return applied

    def _run_loop(self) -> None:
        """
        Bucle principal de captura y procesamiento. Ejecuta en hilo de fondo.
        """
        # 1. Abrir la cámara
        self._camera = _create_camera_source()
        if not self._camera.open():
            logger.error("No se pudo abrir la cámara. Worker detenido.")
            system_state.set_camera_status(connected=False, source=settings.CAMERA_SOURCE, fps=0.0)
            return

        system_state.set_camera_status(connected=True, source=settings.CAMERA_SOURCE, fps=0.0)
        logger.info(f"Cámara abierta: {self._camera.get_metadata()}")

        # 2. Inicializar el detector YOLO
        self._detector.initialize()
        self._vision_ai.initialize()

        frame_count = 0
        fps_start_time = time.perf_counter()
        measured_fps = 0.0

        # 3. Bucle de captura continua
        while not self._stop_event.is_set():
            ret, frame = self._camera.read()
            if not ret or frame is None:
                logger.warning("Fallo de lectura de cámara. Reintentando...")
                time.sleep(0.1)
                continue

            # Guardar frame actual para streaming MJPEG
            with self._frame_lock:
                self._current_frame = frame

            # Almacenar en buffer circular
            self._frame_buffer.add_frame(frame)

            # Medir FPS reales
            frame_count += 1
            elapsed = time.perf_counter() - fps_start_time
            if elapsed >= 1.0:
                measured_fps = frame_count / elapsed
                frame_count = 0
                fps_start_time = time.perf_counter()
                system_state.set_camera_status(
                    connected=True, source=settings.CAMERA_SOURCE, fps=round(measured_fps, 1)
                )

            # Detección local de personas con YOLO
            detection = self._detector.detect_persons(frame)
            system_state.set_persons_detected(detection.persons)

            # Durante pruebas manuales no se usa cooldown ni se dispara análisis por detección.
            if settings.MANUAL_RECOGNITION_MODE:
                system_state.set_cooldown_remaining(0.0)
            else:
                cooldown_rem = self._event_manager.cooldown_manager.remaining_seconds()
                system_state.set_cooldown_remaining(cooldown_rem)

            # Evaluar si se debe disparar un evento
            if not settings.MANUAL_RECOGNITION_MODE and self._event_manager.should_trigger_event(detection):
                event = self._event_manager.create_event(detection)
                system_state.set_active_event(True)
                system_state.add_log(
                    "PERSON",
                    f"[PERSONA] Detectada ({detection.persons} pers., {int(detection.max_confidence * 100)}% conf). Iniciando secuencia posterior a la deteccion..."
                )
                self._analysis_thread = threading.Thread(
                    target=self._process_event,
                    args=(event,),
                    name=f"EventAnalysis-{event.id[:8]}",
                    daemon=True
                )
                self._analysis_thread.start()

            # Limitar la velocidad del bucle si la cámara no tiene limitador propio
            time.sleep(0.001)

        # Cleanup
        if self._camera is not None:
            self._camera.close()
            self._camera = None

    def _process_event(self, event, manual_jpeg_frames=None, is_manual: bool = False) -> None:
        """
        Procesa un evento completo: captura → selección → compresión → IA → decisión → voz.
        Se ejecuta en un hilo separado para que la captura de cámara nunca se congele
        mientras se acumula contexto, se consulta la IA o se genera el audio.
        """
        try:
            logger.info(f"Procesando evento {event.id[:8]}...")

            if is_manual:
                jpeg_frames = list(manual_jpeg_frames or [])
                system_state.add_log("SEQUENCE", f"[MANUAL] {len(jpeg_frames)} fotogramas preparados para consultar a la IA.")
            else:
                with self._runtime_config_lock:
                    frames_per_analysis = settings.FRAMES_PER_ANALYSIS
                    interval = settings.SEQUENCE_FRAME_INTERVAL_SECONDS
                    capture_seconds = max(settings.EVENT_CAPTURE_SECONDS, frames_per_analysis * interval)
                system_state.add_log(
                    "SEQUENCE",
                    f"[SECUENCIA] Capturando {frames_per_analysis} fotogramas, uno cada {interval:g}s durante {capture_seconds:g}s."
                )
                time.sleep(capture_seconds)
                selected = self._frame_buffer.get_frames_at_intervals(
                    start_time=event.started_at,
                    interval_seconds=interval,
                    count=frames_per_analysis,
                )
                with self._runtime_config_lock:
                    jpeg_frames = [self._image_processor.compress_jpeg(frame) for _, frame in selected]
                    jpeg_quality = self._image_processor.jpeg_quality

            # 4. Actualizar metadata de captura
            event.capture.total_frames = len(jpeg_frames)
            event.capture.selected_frames = len(jpeg_frames)
            if not is_manual:
                event.capture.jpeg_quality = jpeg_quality

            # 6. Enviar a VisionAIClient midiendo tiempo exacto de respuesta
            system_state.set_ai_status("sending")
            system_state.add_log(
                "AI",
                f"[IA] Enviando {len(jpeg_frames)} fotogramas a OpenAI Vision ({settings.OPENAI_VISION_MODEL}, reasoning={settings.OPENAI_VISION_REASONING_EFFORT}, detalle={settings.IMAGE_DETAIL}). Esperando respuesta..."
            )

            t_ai_start = time.perf_counter()
            ai_result = self._vision_ai.analyze_sequence(jpeg_frames)
            ai_latency = time.perf_counter() - t_ai_start

            event.analysis = ai_result.model_dump()
            system_state.set_ai_status("completed", latency=ai_latency)

            system_state.add_log(
                "SUCCESS",
                f"[RESPUESTA IA] Recibida en {ai_latency:.2f}s: [{ai_result.event_type}] ({int(ai_result.confidence * 100)}% conf) - {ai_result.description}"
            )

            # 7. Evaluar decisión
            decision = self._decision_engine.evaluate_decision(ai_result)
            event.decision = decision

            if decision == "WARN":
                pending_text = " Alerta pendiente de emisión manual." if is_manual else ""
                system_state.add_log("WARN", f"[ALERTA] ¡Arrojo de residuos confirmado! Decisión: WARN.{pending_text}")
            elif decision == "LOG_ONLY":
                system_state.add_log("DECISION", f"[DECISIÓN] LOG_ONLY (Registrado para auditoría e investigación).")
            else:
                system_state.add_log("INFO", f"[INFO] Decisión: IGNORE (Sin acción de arrojo detectada).")

            # 8. Actualizar estado del sistema
            system_state.record_analysis_result(
                confidence=ai_result.confidence,
                decision=decision,
                diagnosis=ai_result.description,
                warning_message=ai_result.warning_message,
                latency=ai_latency
            )

            # 9. Si la decisión es WARN, generar voz y reproducir
            if decision == "WARN" and ai_result.warning_message and not is_manual:
                system_state.add_log("AUDIO", f"[VOZ] Sintetizando advertencia: \"{ai_result.warning_message}\"")
                system_state.add_log("AUDIO", "[AUDIO] Recibiendo PCM y reproduciendo advertencia en streaming...")
                audio_path = f"data/audio/warning_{event.id[:8]}.wav"
                generated = self._tts_service.generate_and_play_streaming(
                    ai_result.warning_message, audio_path, self._audio_output
                )
                if generated:
                    system_state.add_log("AUDIO", "[AUDIO] Advertencia finalizada y archivada en formato WAV.")

            # 10. Completar y guardar evento
            if is_manual:
                event.ended_at = datetime.now()
                event.status = "completed"
                completed_event = event
            else:
                completed_event = self._event_manager.complete_event(event)
            self._repository.save(completed_event)
            if not is_manual:
                system_state.add_log("COOLDOWN", f"[ENFRIAMIENTO] Periodo de {settings.EVENT_COOLDOWN_SECONDS}s activado para evitar spam.")
            logger.info(f"Evento {event.id[:8]} completado → decisión: {decision}")

        except Exception as e:
            logger.error(f"Error procesando evento: {e}")
            if not is_manual:
                self._event_manager.release_event(event)
        finally:
            if is_manual:
                system_state.set_manual_sequence_status(captured=0, ready=False)
            if self._event_manager.active_event is None:
                system_state.set_active_event(False)
            if self._analysis_thread is threading.current_thread():
                self._analysis_thread = None
