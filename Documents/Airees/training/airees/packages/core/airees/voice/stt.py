"""Speech-to-text using faster-whisper."""
from __future__ import annotations

import logging
import tempfile
from dataclasses import dataclass
from pathlib import Path

log = logging.getLogger(__name__)


@dataclass
class SpeechToText:
    """Transcribe audio to text using faster-whisper.

    Attributes:
        model_size: Whisper model size (tiny, base, small, medium, large).
    """

    model_size: str = "base"
    _model: object | None = None

    def _get_model(self):
        if self._model is None:
            try:
                from faster_whisper import WhisperModel
            except ImportError:
                raise ImportError(
                    "faster-whisper is required for voice support. "
                    "Install it with: pip install 'airees[voice]'"
                )
            self._model = WhisperModel(self.model_size, compute_type="int8")
            log.info("Loaded Whisper model: %s", self.model_size)
        return self._model

    def transcribe(self, audio_data: bytes, language: str = "en") -> str:
        """Transcribe audio bytes to text.

        Args:
            audio_data: Raw audio bytes (WAV or OGG format).
            language: Language code for transcription.

        Returns:
            Transcribed text.
        """
        model = self._get_model()

        # Write to temp file (faster-whisper requires a file path)
        temp_path = None
        try:
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                temp_path = f.name
                f.write(audio_data)
            segments, _info = model.transcribe(temp_path, language=language)
            text = " ".join(segment.text.strip() for segment in segments)
            log.info("Transcribed %d bytes -> %d chars", len(audio_data), len(text))
            return text
        finally:
            if temp_path is not None:
                Path(temp_path).unlink(missing_ok=True)
