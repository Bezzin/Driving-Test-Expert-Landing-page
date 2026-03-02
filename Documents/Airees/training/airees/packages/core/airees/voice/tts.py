"""Text-to-speech using piper-tts."""
from __future__ import annotations

import logging
import tempfile
from dataclasses import dataclass
from pathlib import Path

log = logging.getLogger(__name__)


@dataclass
class TextToSpeech:
    """Synthesize text to audio using piper-tts.

    Attributes:
        voice: Piper voice model name.
    """

    voice: str = "en_US-lessac-medium"
    _engine: object | None = None

    def synthesize(self, text: str) -> bytes:
        """Convert text to audio bytes (WAV format).

        Args:
            text: Text to synthesize.

        Returns:
            WAV audio bytes.
        """
        try:
            from piper import PiperVoice
        except ImportError:
            raise ImportError(
                "piper-tts is required for voice synthesis. "
                "Install it with: pip install 'airees[voice]'"
            )

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            temp_path = f.name

        try:
            voice = PiperVoice.load(self.voice)
            with open(temp_path, "wb") as wav_file:
                voice.synthesize(text, wav_file)

            audio_data = Path(temp_path).read_bytes()
            log.info("Synthesized %d chars -> %d bytes", len(text), len(audio_data))
            return audio_data
        finally:
            Path(temp_path).unlink(missing_ok=True)
