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

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

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

            # Evaluar si se debe disparar un evento
            if self._event_manager.should_trigger_event(detection):
                event = self._event_manager.create_event(detection)
                system_state.set_active_event(True)
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

    def _process_event(self, event) -> None:
        """
        Procesa un evento completo: captura → selección → compresión → IA → decisión → voz.
        Se ejecuta en un hilo separado para que la captura de cámara nunca se congele
        mientras se acumula contexto, se consulta la IA o se genera el audio.
        """
        try:
            logger.info(f"Procesando evento {event.id[:8]}...")

            # 2. Esperar un poco para acumular contexto temporal
            time.sleep(settings.EVENT_CAPTURE_SECONDS)

            # 3. Obtener frames del buffer y seleccionar los mejores
            all_frames = self._frame_buffer.get_all_frames()
            selected = self._frame_selector.select_frames(all_frames)

            # 4. Actualizar metadata de captura
            event.capture.total_frames = len(all_frames)
            event.capture.selected_frames = len(selected)
            event.capture.jpeg_quality = settings.JPEG_QUALITY

            # 5. Comprimir frames a JPEG binario (ImageProcessor solo procesa imagen)
            jpeg_frames = []
            for ts, frame in selected:
                jpeg_bytes = self._image_processor.compress_jpeg(frame)
                jpeg_frames.append(jpeg_bytes)

            # 6. Enviar a VisionAIClient (maneja serialización Base64 y request de red)
            ai_result = self._vision_ai.analyze_sequence(jpeg_frames)
            event.analysis = ai_result.model_dump()

            # 7. Evaluar decisión
            decision = self._decision_engine.evaluate_decision(ai_result)
            event.decision = decision

            # 8. Actualizar estado del sistema
            system_state.record_analysis_result(
                confidence=ai_result.confidence,
                warning_message=ai_result.warning_message
            )

            # 9. Si la decisión es WARN, generar voz y reproducir
            if decision == "WARN" and ai_result.warning_message:
                audio_path = f"data/audio/warning_{event.id[:8]}.mp3"
                generated = self._tts_service.generate_speech(ai_result.warning_message, audio_path)
                if generated:
                    self._audio_output.play(generated)

            # 10. Completar y guardar evento
            completed_event = self._event_manager.complete_event(event)
            self._repository.save(completed_event)
            logger.info(f"Evento {event.id[:8]} completado → decisión: {decision}")

        except Exception as e:
            logger.error(f"Error procesando evento: {e}")
            self._event_manager.release_event(event)
        finally:
            if self._event_manager.active_event is None:
                system_state.set_active_event(False)
            if self._analysis_thread is threading.current_thread():
                self._analysis_thread = None
