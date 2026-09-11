"""Advertencias locales cacheadas con TTS remoto únicamente como respaldo."""

from __future__ import annotations

import hashlib
import logging
import re
from dataclasses import dataclass
from pathlib import Path

from app.speech.audio_output import AudioOutput
from app.speech.openai_tts import OpenAISpeechService

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class WarningPlaybackResult:
    emitted: bool
    source: str
    audio_path: str | None = None


class CachedWarningSpeechService:
    """Prioriza una plantilla WAV y evita sintetizar dos veces el mismo texto."""

    def __init__(
        self,
        template_path: Path,
        cache_dir: Path,
        generic_message: str,
        audio_output: AudioOutput,
        tts_fallback: OpenAISpeechService,
        use_local_audio: bool = True,
        tts_fallback_enabled: bool = True,
    ):
        self.template_path = Path(template_path)
        self.cache_dir = Path(cache_dir)
        self.generic_message = generic_message.strip()
        self.audio_output = audio_output
        self.tts_fallback = tts_fallback
        self.use_local_audio = use_local_audio
        self.tts_fallback_enabled = tts_fallback_enabled

    def emit(self, dynamic_message: str | None = None) -> WarningPlaybackResult:
        if self.use_local_audio and self.template_path.is_file():
            if self.audio_output.play(str(self.template_path)):
                return WarningPlaybackResult(True, "local_template", str(self.template_path))
            logger.warning("La plantilla local no pudo reproducirse; evaluando fallback TTS.")

        dynamic_text = (dynamic_message or "").strip()
        if (
            not self.tts_fallback_enabled
            or not dynamic_text
            or self._normalize(dynamic_text) == self._normalize(self.generic_message)
        ):
            return WarningPlaybackResult(False, "none")

        cached_path = self._cache_path(dynamic_text)
        if cached_path.is_file():
            if self.audio_output.play(str(cached_path)):
                return WarningPlaybackResult(True, "tts_cache", str(cached_path))
            logger.warning("El audio TTS cacheado no pudo reproducirse: %s", cached_path)
            return WarningPlaybackResult(False, "none")

        self.cache_dir.mkdir(parents=True, exist_ok=True)
        generated = self.tts_fallback.generate_and_play_streaming(
            dynamic_text,
            str(cached_path),
            self.audio_output,
        )
        if generated:
            return WarningPlaybackResult(True, "openai_tts", str(generated))
        return WarningPlaybackResult(False, "none")

    def _cache_path(self, text: str) -> Path:
        digest = hashlib.sha256(self._normalize(text).encode("utf-8")).hexdigest()[:20]
        return self.cache_dir / f"warning_{digest}.wav"

    @staticmethod
    def _normalize(text: str) -> str:
        return re.sub(r"\s+", " ", text.strip().casefold())
