"""Advertencias OpenAI TTS dinámicas con catálogo local de baja latencia."""

from __future__ import annotations

import hashlib
import logging
import re
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from app.speech.audio_output import AudioOutput
from app.speech.openai_tts import OpenAISpeechService

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class WarningPlaybackResult:
    emitted: bool
    source: str
    audio_path: str | None = None


class CachedWarningSpeechService:
    """Usa TTS dinámico cuando hay texto y un catálogo WAV como respaldo inmediato."""

    def __init__(
        self,
        template_path: Path,
        cache_dir: Path,
        generic_message: str,
        audio_output: AudioOutput,
        tts_fallback: OpenAISpeechService,
        use_local_audio: bool = True,
        tts_fallback_enabled: bool = True,
        catalog_paths: Sequence[Path] | None = None,
    ):
        self.template_path = Path(template_path)
        self.cache_dir = Path(cache_dir)
        self.generic_message = generic_message.strip()
        self.audio_output = audio_output
        self.tts_fallback = tts_fallback
        self.use_local_audio = use_local_audio
        self.tts_fallback_enabled = tts_fallback_enabled
        self.catalog_paths = tuple(
            dict.fromkeys(Path(path) for path in (catalog_paths or ()))
        )
        self._catalog_index = 0
        self._catalog_lock = threading.Lock()

    def emit(self, dynamic_message: str | None = None) -> WarningPlaybackResult:
        dynamic_text = (dynamic_message or "").strip()
        should_synthesize = (
            self.tts_fallback_enabled
            and bool(dynamic_text)
            and self._normalize(dynamic_text) != self._normalize(self.generic_message)
        )

        if should_synthesize:
            cached_path = self._cache_path(dynamic_text)
            if cached_path.is_file() and self.audio_output.play(str(cached_path)):
                return WarningPlaybackResult(True, "tts_cache", str(cached_path))
            if cached_path.is_file():
                logger.warning(
                    "El audio TTS cacheado no pudo reproducirse; se regenerará: %s",
                    cached_path,
                )

            self.cache_dir.mkdir(parents=True, exist_ok=True)
            generated = self.tts_fallback.generate_and_play_streaming(
                dynamic_text,
                str(cached_path),
                self.audio_output,
            )
            if generated:
                return WarningPlaybackResult(True, "openai_tts", str(generated))
            logger.warning(
                "OpenAI TTS no pudo emitir el mensaje dinámico; usando el catálogo local."
            )

        return self._play_local_warning()

    def _play_local_warning(self) -> WarningPlaybackResult:
        if not self.use_local_audio:
            return WarningPlaybackResult(False, "none")

        catalog = tuple(path for path in self.catalog_paths if path.is_file())
        if catalog:
            with self._catalog_lock:
                start = self._catalog_index % len(catalog)
                self._catalog_index = (self._catalog_index + 1) % len(catalog)
            for offset in range(len(catalog)):
                path = catalog[(start + offset) % len(catalog)]
                if self.audio_output.play(str(path)):
                    return WarningPlaybackResult(True, "openai_template", str(path))
                logger.warning("No se pudo reproducir la plantilla OpenAI TTS: %s", path)

        if self.template_path.is_file() and self.audio_output.play(str(self.template_path)):
            return WarningPlaybackResult(True, "local_template", str(self.template_path))
        if self.template_path.is_file():
            logger.warning("La plantilla local de emergencia no pudo reproducirse.")
        return WarningPlaybackResult(False, "none")

    def _cache_path(self, text: str) -> Path:
        digest = hashlib.sha256(self._normalize(text).encode("utf-8")).hexdigest()[:20]
        return self.cache_dir / f"warning_{digest}.wav"

    @staticmethod
    def _normalize(text: str) -> str:
        return re.sub(r"\s+", " ", text.strip().casefold())
