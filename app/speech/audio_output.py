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
from abc import ABC, abstractmethod
from pathlib import Path

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
