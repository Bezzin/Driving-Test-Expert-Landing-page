"""Tests for voice STT pipeline."""
from __future__ import annotations

import pytest

from airees.voice.stt import SpeechToText


def test_stt_creation():
    stt = SpeechToText()
    assert stt.model_size == "base"


def test_stt_creation_custom_model():
    stt = SpeechToText(model_size="small")
    assert stt.model_size == "small"


def test_stt_transcribe_no_faster_whisper(monkeypatch):
    """Without faster-whisper installed, transcribe raises ImportError."""
    import builtins
    real_import = builtins.__import__

    def mock_import(name, *args, **kwargs):
        if name == "faster_whisper":
            raise ImportError("No module named 'faster_whisper'")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", mock_import)

    stt = SpeechToText()
    with pytest.raises(ImportError, match="faster-whisper"):
        stt.transcribe(b"fake audio bytes")
