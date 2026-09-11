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
   Frame → FrameBuffer → LocalDetector (YOLO) → ByteTrack → SceneState → EventManager → FrameSelector
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
from app.vision.frame_selector import EventKeyframeSelector, FrameSelector
from app.vision.image_processor import ImageProcessor
from app.vision.scheduler import MonotonicRateLimiter
from app.vision.tracker import create_tracker
from app.vision.zones import ZoneManager
from app.vision.debug_overlay import VisionDebugOverlay
from app.vision.pose import create_pose_analyzer
from app.vision.associations import (
    AssociationScorer,
    AssociationWeights,
    PersonObjectAssociationEngine,
)
from app.events.manager import EventManager
from app.events.engine import EventEngine, EventScoreWeights
from app.events.object_state import ObjectStateMachine
from app.events.rules import DecisionEngine
from app.ai.vision_client import VisionAI
from app.speech.openai_tts import OpenAISpeechService
from app.speech.audio_output import LocalSpeakerOutput
from app.speech.cached_warning import CachedWarningSpeechService
from app.storage.local_repository import SQLiteEventsRepository
from app.models.event import EventModel, LocalDetectionSummary
from app.models.scene import SceneState
from app.models.metrics import SystemMetrics
from app.metrics.collector import MetricsCollector

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
            confidence_threshold=settings.DETECTION_CONFIDENCE,
            monitored_classes=settings.DETECTION_CLASSES,
            image_size=settings.YOLO_IMGSZ,
        )
        self._detection_limiter = MonotonicRateLimiter(settings.DETECTION_FPS)
        self._metrics = MetricsCollector(
            rate_window_seconds=settings.METRICS_WINDOW_SECONDS
        )
        self._last_performance_log = 0.0
        self._frame_buffer = FrameBuffer(
            buffer_seconds=settings.BUFFER_SECONDS,
            fps=settings.BUFFER_FPS
        )
        self._frame_selector = FrameSelector(
            target_frames=settings.FRAMES_PER_ANALYSIS,
            strategy="uniform"
        )
        self._event_keyframe_selector = EventKeyframeSelector(
            max_frames=settings.OPENAI_MAX_FRAMES,
            before_seconds=settings.EVENT_KEYFRAME_BEFORE_SECONDS,
            after_seconds=settings.EVENT_KEYFRAME_AFTER_SECONDS,
        )
        self._image_processor = ImageProcessor(
            max_width=settings.IMAGE_MAX_WIDTH,
            jpeg_quality=settings.JPEG_QUALITY
        )
        self._tracker = create_tracker(
            tracker_type=settings.TRACKER_TYPE,
            enabled=settings.TRACKING_ENABLED,
            history_seconds=settings.TRACK_HISTORY_SECONDS,
            track_ttl_seconds=settings.TRACK_TTL_SECONDS,
            frame_rate=float(settings.CAMERA_FPS),
            track_activation_threshold=settings.TRACK_ACTIVATION_THRESHOLD,
            lost_track_buffer=settings.TRACK_LOST_BUFFER,
            minimum_consecutive_frames=settings.TRACK_MIN_CONSECUTIVE_FRAMES,
            minimum_iou_threshold=settings.TRACK_MIN_IOU_THRESHOLD,
        )
        zone_config_path = settings.ZONE_CONFIG_PATH
        if not zone_config_path.is_absolute():
            zone_config_path = settings.BASE_DIR / zone_config_path
        self._zone_manager = ZoneManager.from_json(zone_config_path, settings.CAMERA_ID)
        self._debug_overlay = VisionDebugOverlay(enabled=settings.VISION_DEBUG_OVERLAY)
        self._scene_state = SceneState(camera_id=settings.CAMERA_ID)
        pose_model_path = settings.POSE_MODEL_PATH
        if not pose_model_path.is_absolute():
            pose_model_path = settings.BASE_DIR / pose_model_path
        self._pose_analyzer = create_pose_analyzer(
            enabled=settings.POSE_ENABLED,
            model_path=pose_model_path,
            trigger_zones=settings.POSE_TRIGGER_ZONES,
            fps=settings.POSE_FPS,
            min_person_confidence=settings.POSE_MIN_PERSON_CONFIDENCE,
            min_detection_confidence=settings.POSE_MIN_DETECTION_CONFIDENCE,
            min_landmark_visibility=settings.POSE_MIN_LANDMARK_VISIBILITY,
            max_persons_per_frame=settings.POSE_MAX_PERSONS_PER_FRAME,
            result_ttl_seconds=settings.POSE_RESULT_TTL_SECONDS,
            crop_padding_ratio=settings.POSE_CROP_PADDING_RATIO,
            object_proximity_ratio=settings.POSE_OBJECT_PROXIMITY_RATIO,
        )
        self._association_engine = PersonObjectAssociationEngine(
            enabled=settings.ASSOCIATION_ENABLED,
            minimum_score=settings.ASSOCIATION_MIN_SCORE,
            minimum_duration=settings.ASSOCIATION_MIN_DURATION,
            scorer=AssociationScorer(
                weights=AssociationWeights(
                    bbox_proximity=settings.ASSOCIATION_BBOX_WEIGHT,
                    centroid_proximity=settings.ASSOCIATION_CENTROID_WEIGHT,
                    trajectory_similarity=settings.ASSOCIATION_TRAJECTORY_WEIGHT,
                    temporal_consistency=settings.ASSOCIATION_TEMPORAL_WEIGHT,
                    hand_proximity=settings.ASSOCIATION_HAND_WEIGHT,
                ),
                max_distance_ratio=settings.ASSOCIATION_MAX_DISTANCE_RATIO,
                hand_distance_ratio=settings.ASSOCIATION_HAND_DISTANCE_RATIO,
                trajectory_points=settings.ASSOCIATION_TRAJECTORY_POINTS,
            ),
        )
        object_state_machine = ObjectStateMachine(
            carried_score=settings.OBJECT_CARRIED_SCORE,
            carried_seconds=settings.OBJECT_CARRIED_SECONDS,
            release_score=settings.OBJECT_RELEASE_SCORE,
            release_grace_seconds=settings.OBJECT_RELEASE_GRACE_SECONDS,
            stationary_seconds=settings.OBJECT_STATIONARY_SECONDS,
            stationary_max_distance_px=settings.OBJECT_STATIONARY_MAX_DISTANCE_PX,
            moving_away_seconds=settings.PERSON_MOVING_AWAY_SECONDS,
            moving_away_min_distance_px=settings.PERSON_MOVING_AWAY_MIN_DISTANCE_PX,
            state_ttl_seconds=settings.OBJECT_STATE_TTL_SECONDS,
            relevant_zones=settings.EVENT_RELEVANT_ZONES,
        )
        self._event_engine = EventEngine(
            object_state_machine=object_state_machine,
            ignore_threshold=settings.LOCAL_IGNORE_THRESHOLD,
            confirm_threshold=settings.LOCAL_CONFIRM_THRESHOLD,
            relevant_zones=settings.EVENT_RELEVANT_ZONES,
            weights=EventScoreWeights(
                carried=settings.EVENT_CARRIED_WEIGHT,
                release=settings.EVENT_RELEASE_WEIGHT,
                target_zone=settings.EVENT_TARGET_ZONE_WEIGHT,
                stationary=settings.EVENT_STATIONARY_WEIGHT,
                moving_away=settings.EVENT_MOVING_AWAY_WEIGHT,
            ),
        )
        self._event_manager = EventManager(
            cooldown_seconds=settings.EVENT_COOLDOWN_SECONDS,
            camera_id=settings.CAMERA_ID,
            minimum_context_seconds=settings.EVENT_MIN_CONTEXT_SECONDS,
        )
        self._decision_engine = DecisionEngine(
            warning_threshold=settings.AI_WARNING_THRESHOLD,
            local_ignore_threshold=settings.LOCAL_IGNORE_THRESHOLD,
            local_confirm_threshold=settings.LOCAL_CONFIRM_THRESHOLD,
        )
        self._vision_ai = VisionAI()
        self._tts_service = OpenAISpeechService()
        self._audio_output = LocalSpeakerOutput()
        local_audio_path = settings.LOCAL_WARNING_AUDIO_PATH
        if not local_audio_path.is_absolute():
            local_audio_path = settings.BASE_DIR / local_audio_path
        tts_cache_dir = settings.TTS_CACHE_DIR
        if not tts_cache_dir.is_absolute():
            tts_cache_dir = settings.BASE_DIR / tts_cache_dir
        self._warning_speech = CachedWarningSpeechService(
            template_path=local_audio_path,
            cache_dir=tts_cache_dir,
            generic_message=settings.LOCAL_WARNING_MESSAGE,
            audio_output=self._audio_output,
            tts_fallback=self._tts_service,
            use_local_audio=settings.USE_LOCAL_WARNING_AUDIO,
            tts_fallback_enabled=settings.OPENAI_TTS_FALLBACK_ENABLED,
        )
        self._repository = SQLiteEventsRepository()

        # Frame compartido para streaming MJPEG (leído por el endpoint /api/cameras/stream)
        self._current_frame = None
        self._current_raw_frame = None
        self._frame_lock = threading.Lock()
        self._scene_lock = threading.Lock()
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

    @property
    def current_scene(self) -> SceneState:
        """Devuelve una copia coherente del estado espacial más reciente."""
        with self._scene_lock:
            return self._scene_state.model_copy(deep=True)

    def start(self) -> bool:
        """Arranca el hilo de captura continua."""
        if self._thread is not None and self._thread.is_alive():
            logger.warning("El worker de video ya está en ejecución.")
            return False

        self._stop_event.clear()
        self._tracker.reset()
        self._pose_analyzer.reset()
        self._association_engine.reset()
        self._event_engine.reset()
        self._event_manager.reset()
        self._detection_limiter.reset()
        self._metrics.reset_runtime()
        self._last_performance_log = 0.0
        now = datetime.now()
        system_state.set_detection_status(persons=0, objects=0, counts_by_label={})
        system_state.set_scene_status(
            active_persons=0,
            active_objects=0,
            track_ids=[],
            zone_occupancy={},
            timestamp=now,
        )
        with self._scene_lock:
            self._scene_state = SceneState(camera_id=settings.CAMERA_ID, timestamp=now)
        with self._frame_lock:
            self._current_frame = None
            self._current_raw_frame = None
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
        self._tracker.reset()
        self._pose_analyzer.reset()
        self._association_engine.reset()
        self._event_engine.reset()
        self._event_manager.reset()
        stopped_at = datetime.now()
        system_state.set_detection_status(persons=0, objects=0, counts_by_label={})
        system_state.set_scene_status(
            active_persons=0,
            active_objects=0,
            track_ids=[],
            zone_occupancy={},
            timestamp=stopped_at,
        )
        with self._scene_lock:
            self._scene_state = SceneState(camera_id=settings.CAMERA_ID, timestamp=stopped_at)
        with self._frame_lock:
            self._current_frame = None
            self._current_raw_frame = None
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
            camera_id=settings.CAMERA_ID,
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
                frame = None if self._current_raw_frame is None else self._current_raw_frame.copy()
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

    def _update_tracking(self, detection, frame, timestamp: datetime):
        """Actualiza tracking, zonas y SceneState para el frame actual."""
        try:
            tracker_started = time.perf_counter()
            tracked_objects = self._tracker.update(
                detection.detections,
                timestamp=timestamp,
                frame=frame,
            )
            assignments, zone_states = self._zone_manager.locate(
                tracked_objects,
                frame.shape,
            )
            self._tracker.assign_zones(assignments)
            active_states = self._tracker.active_states
            self._metrics.record_stage(
                "tracker",
                elapsed_ms=(time.perf_counter() - tracker_started) * 1000.0,
            )
            with self._scene_lock:
                self._scene_state.update(active_states, zone_states, timestamp)
                working_scene = self._scene_state.model_copy(deep=True)
            # MediaPipe puede ser costoso; no mantener el lock de lectura del dashboard.
            pose_started = time.perf_counter()
            poses = self._pose_analyzer.update(frame, working_scene)
            pose_elapsed_ms = (time.perf_counter() - pose_started) * 1000.0
            pose_inferences = getattr(self._pose_analyzer, "last_inference_count", 0)
            if pose_inferences:
                self._metrics.record_stage(
                    "pose",
                    elapsed_ms=pose_elapsed_ms / pose_inferences,
                    count=pose_inferences,
                )
            working_scene.set_poses(poses)
            associations = self._association_engine.update(working_scene)
            working_scene.set_associations(associations)
            event_engine_started = time.perf_counter()
            candidates = self._event_engine.update(working_scene)
            self._metrics.record_stage(
                "event_engine",
                elapsed_ms=(time.perf_counter() - event_engine_started) * 1000.0,
            )
            working_scene.set_reasoning(
                self._event_engine.object_states,
                candidates,
            )
            with self._scene_lock:
                self._scene_state = working_scene
                scene = self._scene_state.model_copy(deep=True)
            track_ids = [track.track_id for track in active_states]
            system_state.set_scene_status(
                active_persons=len(scene.persons),
                active_objects=len(scene.objects),
                track_ids=track_ids,
                zone_occupancy={
                    name: zone.occupancy
                    for name, zone in scene.zones.items()
                },
                timestamp=timestamp,
                association_candidates=len(scene.associations),
                confirmed_associations=sum(
                    association.confirmed
                    for association in scene.associations
                ),
                active_pose_tracks=sum(
                    person.pose is not None
                    for person in scene.persons.values()
                ),
                pose_available=self._pose_analyzer.available,
                local_event_candidates=len(scene.event_candidates),
                confirmed_local_events=sum(
                    candidate.state == "CONFIRMED"
                    for candidate in scene.event_candidates
                ),
            )
            for track_id in self._tracker.last_created_track_ids:
                system_state.add_log("TRACK", f"[TRACK] Track #{track_id} creado.")
            for track_id in self._tracker.last_expired_track_ids:
                system_state.add_log("TRACK", f"[TRACK] Track #{track_id} expirado.")
            for object_id, previous, current in self._event_engine.object_state_machine.last_transitions:
                system_state.add_log(
                    "STATE",
                    f"[STATE] Objeto #{object_id} {previous.value} -> {current.value}.",
                )
            for candidate_id in self._event_engine.last_created_candidate_ids:
                system_state.add_log(
                    "EVENT",
                    f"[EVENT] Candidato local {candidate_id[:8]} creado.",
                )
            for candidate_id in self._event_engine.last_confirmed_candidate_ids:
                system_state.add_log(
                    "EVENT",
                    f"[EVENT] Candidato local {candidate_id[:8]} confirmado.",
                )
            return scene
        except Exception as exc:
            logger.error("Error actualizando el estado espacial: %s", exc)
            system_state.set_scene_status(
                active_persons=0,
                active_objects=0,
                track_ids=[],
                zone_occupancy={},
                timestamp=timestamp,
            )
            with self._scene_lock:
                self._scene_state.update([], {}, timestamp)
                return self._scene_state.model_copy(deep=True)

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

            frame_timestamp = datetime.now()
            self._metrics.record_stage("capture")

            # Mantener la evidencia cruda separada del frame de depuración.
            with self._frame_lock:
                self._current_raw_frame = frame

            # Almacenar en buffer circular
            self._frame_buffer.add_frame(frame, timestamp=frame_timestamp)

            # Medir FPS reales
            frame_count += 1
            elapsed = time.perf_counter() - fps_start_time
            publish_performance = elapsed >= 1.0
            if elapsed >= 1.0:
                measured_fps = frame_count / elapsed
                frame_count = 0
                fps_start_time = time.perf_counter()
                system_state.set_camera_status(
                    connected=True, source=settings.CAMERA_SOURCE, fps=round(measured_fps, 1)
                )

            # YOLO y el razonamiento siguen un reloj monotónico independiente de la cámara.
            candidate = None
            if self._detection_limiter.is_due():
                detector_started = time.perf_counter()
                detection_frame = self._detector.detect(frame, timestamp=frame_timestamp)
                self._metrics.record_stage(
                    "detector",
                    elapsed_ms=(time.perf_counter() - detector_started) * 1000.0,
                )
                detection = detection_frame.to_local_summary()
                system_state.set_detection_status(
                    persons=len(detection_frame.persons),
                    objects=len(detection_frame.objects),
                    counts_by_label=detection_frame.counts_by_label,
                )
                scene = self._update_tracking(detection_frame, frame, frame_timestamp)
                if not settings.MANUAL_RECOGNITION_MODE:
                    candidate = self._event_manager.select_candidate(scene.event_candidates)
            else:
                scene = self.current_scene

            display_frame = self._debug_overlay.annotate(
                frame,
                scene,
                self._zone_manager,
            )
            with self._frame_lock:
                self._current_frame = display_frame

            # Durante pruebas manuales no se usa cooldown ni se dispara análisis por detección.
            if settings.MANUAL_RECOGNITION_MODE:
                system_state.set_cooldown_remaining(0.0)
            else:
                cooldown_rem = self._event_manager.cooldown_manager.remaining_seconds()
                system_state.set_cooldown_remaining(cooldown_rem)

            if candidate is not None:
                event = self._event_manager.create_event(candidate, detection)
                system_state.set_active_event(True)
                system_state.add_log(
                    "EVENT",
                    f"[EVENT] {candidate.event_type} {candidate.state.value} "
                    f"(score local {candidate.score:.2f}). Iniciando análisis.",
                )
                self._analysis_thread = threading.Thread(
                    target=self._process_event,
                    args=(event,),
                    name=f"EventAnalysis-{event.id[:8]}",
                    daemon=True
                )
                self._analysis_thread.start()

            if publish_performance:
                performance = self._metrics.snapshot(
                    active_tracks=scene.active_tracks,
                    active_persons=len(scene.persons),
                    active_objects=len(scene.objects),
                    pose_active=sum(
                        person.pose is not None for person in scene.persons.values()
                    ),
                    suspicious_candidates=len(scene.event_candidates),
                )
                system_state.set_performance(performance.model_dump(mode="json"))
                now_monotonic = time.perf_counter()
                if (
                    now_monotonic - self._last_performance_log
                    >= settings.PERFORMANCE_LOG_INTERVAL_SECONDS
                ):
                    self._last_performance_log = now_monotonic
                    logger.info(
                        "capture_fps=%.1f detect_fps=%.1f tracker_fps=%.1f "
                        "pose_fps=%.1f tracks=%d persons=%d pose_active=%d "
                        "latency_detector=%.1fms cpu=%.1f%% ram=%.1fMB openai=%.1f%%",
                        performance.capture_fps,
                        performance.detector_fps,
                        performance.tracker_fps,
                        performance.pose_fps,
                        performance.active_tracks,
                        performance.active_persons,
                        performance.pose_active,
                        performance.detector_latency_ms,
                        performance.cpu_percent,
                        performance.ram_mb,
                        performance.openai_percentage,
                    )

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
            event_processing_started = time.perf_counter()

            ai_result = None
            ai_latency = None
            jpeg_frames = []
            jpeg_quality = self._image_processor.jpeg_quality
            requests_fallback = (
                is_manual
                or (
                    settings.OPENAI_FALLBACK_ENABLED
                    and event.local_event_state == "UNCERTAIN"
                )
            )

            if is_manual:
                jpeg_frames = list(manual_jpeg_frames or [])
                system_state.add_log("SEQUENCE", f"[MANUAL] {len(jpeg_frames)} fotogramas preparados para consultar a la IA.")
            elif requests_fallback:
                timestamps = event.event_trace.get("timestamps", {})
                stationary_value = timestamps.get("stationary_since")
                stationary_timestamp = (
                    datetime.fromisoformat(stationary_value)
                    if isinstance(stationary_value, str)
                    else stationary_value
                )
                selected = self._event_keyframe_selector.select_event_frames(
                    self._frame_buffer.get_all_frames(),
                    release_timestamp=event.release_timestamp,
                    stationary_timestamp=stationary_timestamp,
                )
                with self._runtime_config_lock:
                    jpeg_frames = [
                        self._image_processor.compress_jpeg(frame)
                        for _, frame in selected
                    ]
                    jpeg_quality = self._image_processor.jpeg_quality
                system_state.add_log(
                    "SEQUENCE",
                    f"[SECUENCIA] {len(jpeg_frames)} keyframes seleccionados alrededor de la liberación.",
                )

            # 4. Actualizar metadata de captura
            event.capture.total_frames = len(jpeg_frames)
            event.capture.selected_frames = len(jpeg_frames)
            event.capture.jpeg_quality = jpeg_quality

            can_call_openai = (
                requests_fallback
                and bool(jpeg_frames)
                and getattr(self._vision_ai, "available", True)
            )
            if can_call_openai:
                system_state.set_ai_status("sending")
                system_state.add_log(
                    "AI",
                    f"[IA FALLBACK] Enviando metadata y {len(jpeg_frames)} keyframes "
                    f"a {settings.OPENAI_VISION_MODEL}.",
                )
                t_ai_start = time.perf_counter()
                ai_result = self._vision_ai.analyze_sequence(
                    jpeg_frames,
                    event_metadata=event.openai_metadata(),
                )
                ai_latency = time.perf_counter() - t_ai_start
                self._metrics.record_openai_latency(ai_latency * 1000.0)
                event.openai_used = getattr(self._vision_ai, "last_call_used_api", True)
                event.analysis = ai_result.model_dump()
                event.openai_confidence = ai_result.confidence
                system_state.set_ai_status("completed", latency=ai_latency)
                system_state.add_log(
                    "SUCCESS",
                    f"[RESPUESTA IA] Recibida en {ai_latency:.2f}s: "
                    f"[{ai_result.event_type}] ({int(ai_result.confidence * 100)}% conf) "
                    f"- {ai_result.description}",
                )
            else:
                system_state.set_ai_status("local_decision")
                if requests_fallback:
                    reason = "sin keyframes" if not jpeg_frames else "API no disponible"
                    system_state.add_log(
                        "AI",
                        f"[IA FALLBACK] Verificación omitida ({reason}); se mantiene decisión local segura.",
                    )

            # 7. Evaluar decisión
            decision = (
                self._decision_engine.evaluate_decision(ai_result)
                if is_manual and ai_result is not None
                else self._decision_engine.evaluate(event, ai_result)
            )
            event.decision = decision
            event.final_decision = decision

            result_confidence = (
                ai_result.confidence
                if ai_result is not None
                else (event.local_event_score or 0.0)
            )
            result_description = (
                ai_result.description
                if ai_result is not None
                else (
                    f"Decisión local {event.local_event_state or 'sin candidato'} "
                    f"con score {event.local_event_score or 0.0:.2f}."
                )
            )
            warning_message = ai_result.warning_message if ai_result is not None else None
            if decision == "WARN" and not warning_message:
                warning_message = settings.LOCAL_WARNING_MESSAGE

            if decision == "WARN":
                pending_text = " Alerta pendiente de emisión manual." if is_manual else ""
                system_state.add_log("WARN", f"[ALERTA] ¡Arrojo de residuos confirmado! Decisión: WARN.{pending_text}")
            elif decision == "LOG_ONLY":
                system_state.add_log("DECISION", f"[DECISIÓN] LOG_ONLY (Registrado para auditoría e investigación).")
            else:
                system_state.add_log("INFO", f"[INFO] Decisión: IGNORE (Sin acción de arrojo detectada).")

            # 8. Actualizar estado del sistema
            local_confirmed = (
                event.local_event_state == "CONFIRMED"
                and not event.openai_used
            )
            system_state.record_analysis_result(
                confidence=result_confidence,
                decision=decision,
                diagnosis=result_description,
                warning_message=warning_message,
                latency=ai_latency,
                openai_used=event.openai_used,
                local_confirmed=local_confirmed,
            )

            # 9. Si la decisión es WARN, generar voz y reproducir
            tts_latency_ms = 0.0
            if decision == "WARN" and warning_message and not is_manual:
                audio_started = time.perf_counter()
                playback = self._warning_speech.emit(
                    ai_result.warning_message if ai_result is not None else None
                )
                tts_latency_ms = (time.perf_counter() - audio_started) * 1000.0
                event.metrics["audio_source"] = playback.source
                system_state.set_audio_source(playback.source)
                if playback.emitted:
                    system_state.add_log(
                        "AUDIO",
                        f"[AUDIO] Advertencia emitida mediante {playback.source}.",
                    )
                else:
                    system_state.add_log(
                        "ERROR",
                        "[AUDIO] No se pudo emitir la advertencia; el evento se guardará igualmente.",
                    )

            self._metrics.record_event_outcome(
                decision=decision,
                openai_used=event.openai_used,
                local_confirmed=local_confirmed,
                autonomous=not is_manual,
            )
            scene = self.current_scene
            performance = self._metrics.snapshot(
                active_tracks=scene.active_tracks,
                active_persons=len(scene.persons),
                active_objects=len(scene.objects),
                pose_active=sum(person.pose is not None for person in scene.persons.values()),
                suspicious_candidates=len(scene.event_candidates),
            )
            total_latency_ms = (time.perf_counter() - event_processing_started) * 1000.0
            frames_sent = len(jpeg_frames) if event.openai_used else 0
            payload_bytes = sum(len(frame) for frame in jpeg_frames) if event.openai_used else 0
            event.metrics.update(
                {
                    "frames_sent": frames_sent,
                    "payload_bytes": payload_bytes,
                    "openai_latency_ms": (ai_latency or 0.0) * 1000.0,
                    "tts_latency_ms": tts_latency_ms,
                    "total_latency_ms": total_latency_ms,
                    "local_decision_ratio": performance.local_decision_ratio,
                    "openai_fallback_ratio": performance.openai_fallback_ratio,
                }
            )
            self._metrics.record_event_metrics(
                SystemMetrics(
                    event_id=event.id,
                    camera_id=event.camera_id,
                    frames_captured=len(jpeg_frames),
                    frames_sent=frames_sent,
                    image_resolution=f"{settings.CAMERA_WIDTH}x{settings.CAMERA_HEIGHT}",
                    jpeg_quality=event.capture.jpeg_quality,
                    payload_bytes=payload_bytes,
                    local_detection_confidence=event.local_detection.max_confidence,
                    ai_confidence=event.openai_confidence,
                    ai_model=settings.OPENAI_VISION_MODEL,
                    ai_latency_ms=(ai_latency or 0.0) * 1000.0,
                    tts_latency_ms=tts_latency_ms,
                    total_latency_ms=total_latency_ms,
                    decision=decision,
                )
            )
            system_state.set_performance(performance.model_dump(mode="json"))

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
