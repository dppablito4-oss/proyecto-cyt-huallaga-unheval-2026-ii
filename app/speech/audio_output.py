"""
Módulo de Reproducción de Audio (AudioOutput)
=============================================

Responsabilidad:
----------------
Manejar la emisión acústica física de los archivos de audio sintetizados.
Permite separar la lógica del software de reproducción del hardware de altavoces.

Flujo de invocación:
--------------------
- Recibe la ruta del archivo de audio producido por `app.speech.openai_tts.OpenAISpeechService`.
- En la versión inicial de laboratorio reproduce por altavoces locales del equipo.
- En fases de campo posteriores puede reemplazarse por `IPSpeakerOutput` (megáfonos IP / SIP)
  sin cambiar la lógica de decisiones ni de visión.
"""

import os
import logging
import subprocess
import threading
import time
import ctypes
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Iterable
from app.config import settings

logger = logging.getLogger(__name__)


class AudioOutput(ABC):
    """
    Interfaz abstracta para emisores de audio.
    """

    @abstractmethod
    def play(self, audio_path: str) -> bool:
        """
        Reproduce el archivo de sonido especificado.

        Args:
            audio_path (str): Ruta al archivo .mp3 o .wav.

        Returns:
            bool: True si la reproducción se inició con éxito, False en caso de error.
        """
        pass


class LocalSpeakerOutput(AudioOutput):
    """
    Implementación para reproducción a través de los altavoces de la computadora anfitriona.
    Utiliza el reproductor multimedia nativo del sistema operativo en un hilo separado
    para no bloquear el pipeline principal de vigilancia.
    """

    def play(self, audio_path: str) -> bool:
        path = Path(audio_path).resolve()
        if not path.exists():
            logger.error(f"Archivo de audio no encontrado para reproducción: {audio_path}")
            return False

    def play_pcm_stream(self, chunks: Iterable[bytes], sample_rate: int = 24000) -> bool:
        """Reproduce PCM continuo con búfer; usa PortAudio y conserva fallback nativo de Windows."""
        try:
            import sounddevice as sd

            # 16-bit mono a 24 kHz: 2 bytes por muestra. 200 ms absorben pequeñas variaciones de red.
            min_buffer_bytes = max(2, int(sample_rate * 2 * settings.OPENAI_TTS_STREAM_BUFFER_MS / 1000))
            iterator = iter(chunks)
            initial_buffer = bytearray()
            for chunk in iterator:
                if chunk:
                    initial_buffer.extend(chunk)
                if len(initial_buffer) >= min_buffer_bytes:
                    break

            if not initial_buffer:
                return False
            if len(initial_buffer) % 2:
                initial_buffer.pop()

            with sd.RawOutputStream(
                samplerate=sample_rate,
                channels=1,
                dtype="int16",
                latency="low",
            ) as stream:
                logger.info(
                    "[PARLANTE ACTIVO] Reproduciendo advertencia PCM en streaming "
                    f"con búfer de {settings.OPENAI_TTS_STREAM_BUFFER_MS} ms."
                )
                stream.write(initial_buffer)
                for chunk in iterator:
                    if not chunk:
                        continue
                    if len(chunk) % 2:
                        chunk = chunk[:-1]
                    if chunk:
                        stream.write(chunk)
            return True
        except ImportError:
            logger.warning("sounddevice no disponible; usando reproducción PCM nativa de Windows.")
        except Exception as e:
            logger.error(f"Error en reproducción PCM con sounddevice: {e}")
            return False

        return self._play_pcm_stream_winmm(chunks, sample_rate)

    def _play_pcm_stream_winmm(self, chunks: Iterable[bytes], sample_rate: int = 24000) -> bool:
        """Fallback PCM nativo de Windows, usado solo si sounddevice no está disponible."""
        if os.name != "nt":
            logger.warning("La reproducción PCM en streaming está implementada para Windows.")
            return False

        class WAVEFORMATEX(ctypes.Structure):
            _fields_ = [
                ("wFormatTag", ctypes.c_ushort),
                ("nChannels", ctypes.c_ushort),
                ("nSamplesPerSec", ctypes.c_uint),
                ("nAvgBytesPerSec", ctypes.c_uint),
                ("nBlockAlign", ctypes.c_ushort),
                ("wBitsPerSample", ctypes.c_ushort),
                ("cbSize", ctypes.c_ushort),
            ]

        class WAVEHDR(ctypes.Structure):
            _fields_ = [
                ("lpData", ctypes.c_void_p),
                ("dwBufferLength", ctypes.c_uint),
                ("dwBytesRecorded", ctypes.c_uint),
                ("dwUser", ctypes.c_size_t),
                ("dwFlags", ctypes.c_uint),
                ("dwLoops", ctypes.c_uint),
                ("lpNext", ctypes.c_void_p),
                ("reserved", ctypes.c_size_t),
            ]

        WAVE_FORMAT_PCM = 1
        WAVE_MAPPER = ctypes.c_uint(-1).value
        WHDR_DONE = 0x00000001
        wave_out = ctypes.c_void_p()
        fmt = WAVEFORMATEX(WAVE_FORMAT_PCM, 1, sample_rate, sample_rate * 2, 2, 16, 0)
        winmm = ctypes.windll.winmm

        if winmm.waveOutOpen(ctypes.byref(wave_out), WAVE_MAPPER, ctypes.byref(fmt), 0, 0, 0) != 0:
            logger.error("No se pudo abrir la salida de audio PCM de Windows.")
            return False

        try:
            started = False
            for chunk in chunks:
                if not chunk:
                    continue
                buffer = ctypes.create_string_buffer(chunk)
                header = WAVEHDR(
                    ctypes.cast(buffer, ctypes.c_void_p), len(chunk), 0, 0, 0, 0, None, 0
                )
                if winmm.waveOutPrepareHeader(wave_out, ctypes.byref(header), ctypes.sizeof(header)) != 0:
                    logger.error("No se pudo preparar un fragmento PCM para reproducción.")
                    return False
                if winmm.waveOutWrite(wave_out, ctypes.byref(header), ctypes.sizeof(header)) != 0:
                    winmm.waveOutUnprepareHeader(wave_out, ctypes.byref(header), ctypes.sizeof(header))
                    logger.error("No se pudo enviar un fragmento PCM al altavoz.")
                    return False
                if not started:
                    logger.info("[PARLANTE ACTIVO] Reproduciendo advertencia PCM en streaming.")
                    started = True
                while not (header.dwFlags & WHDR_DONE):
                    time.sleep(0.005)
                winmm.waveOutUnprepareHeader(wave_out, ctypes.byref(header), ctypes.sizeof(header))
            return started
        except Exception as e:
            logger.error(f"Error durante la reproducción PCM en streaming: {e}")
            return False
        finally:
            winmm.waveOutClose(wave_out)

        try:
            logger.info(f"[PARLANTE ACTIVO] Reproduciendo advertencia sonora: {path}")
            # Lanzar reproducción en hilo separado para no bloquear el pipeline
            thread = threading.Thread(target=self._play_system, args=(str(path),), daemon=True)
            thread.start()
            return True
        except Exception as e:
            logger.error(f"Error al iniciar reproducción de audio: {e}")
            return False

    @staticmethod
    def _play_system(file_path: str) -> None:
        """
        Reproduce el archivo de audio utilizando el reproductor nativo del sistema operativo.
        En Windows usa PowerShell con Windows Media Player COM object.
        En Linux/macOS intenta reproductores comunes (aplay, ffplay, afplay).
        """
        try:
            if os.name == 'nt':
                # Windows: usar PowerShell con Windows Media Player
                ps_script = (
                    f'$player = New-Object System.Media.SoundPlayer "{file_path}"; '
                    f'$player.PlaySync()'
                )
                # SoundPlayer solo soporta .wav; para .mp3 usar Media.MediaPlayer
                if file_path.lower().endswith('.mp3'):
                    ps_script = (
                        f'Add-Type -AssemblyName PresentationCore; '
                        f'$player = New-Object System.Windows.Media.MediaPlayer; '
                        f'$player.Open([uri]"{file_path}"); '
                        f'$player.Play(); '
                        f'Start-Sleep -Seconds 15'  # Esperar duración razonable
                    )
                subprocess.run(
                    ['powershell', '-NoProfile', '-Command', ps_script],
                    capture_output=True, timeout=30
                )
            else:
                # Linux / macOS: intentar reproductores comunes
                for player_cmd in ['ffplay', 'aplay', 'afplay', 'paplay']:
                    try:
                        args = [player_cmd]
                        if player_cmd == 'ffplay':
                            args += ['-nodisp', '-autoexit', '-loglevel', 'quiet']
                        args.append(file_path)
                        subprocess.run(args, capture_output=True, timeout=30)
                        return
                    except FileNotFoundError:
                        continue
                logger.warning("No se encontró un reproductor de audio compatible en el sistema.")
        except subprocess.TimeoutExpired:
            logger.warning(f"Reproducción de audio excedió el tiempo límite: {file_path}")
        except Exception as e:
            logger.error(f"Error durante la reproducción de audio del sistema: {e}")
