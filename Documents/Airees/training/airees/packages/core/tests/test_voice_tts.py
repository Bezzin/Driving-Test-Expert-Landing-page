"""Tests for voice TTS pipeline."""
from __future__ import annotations

import pytest

from airees.voice.tts import TextToSpeech


def test_tts_creation():
    tts = TextToSpeech()
    assert tts.voice is not None


def test_tts_synthesize_no_piper(monkeypatch):
    """Without piper-tts installed, synthesize raises ImportError."""
    import builtins
    real_import = builtins.__import__

    def mock_import(name, *args, **kwargs):
        if "piper" in name:
            raise ImportError("No module named 'piper'")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", mock_import)

    tts = TextToSpeech()
    with pytest.raises(ImportError, match="piper"):
        tts.synthesize("Hello world")
