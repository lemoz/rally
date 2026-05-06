"""ElevenLabs TTS API client."""
from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass

from .config import VOICES

BASE_URL = "https://api.elevenlabs.io/v1"
REQUEST_TIMEOUT = 60


class ElevenLabsError(RuntimeError):
    pass


class ElevenLabsRetryableError(ElevenLabsError):
    pass


@dataclass(frozen=True)
class SpeechResult:
    audio_bytes: bytes
    voice_id: str
    char_count: int


def generate_speech(
    *,
    text: str,
    voice: str,
    api_key: str,
    model_id: str = "eleven_multilingual_v2",
    stability: float = 0.8,
    similarity_boost: float = 0.8,
) -> SpeechResult:
    """Generate speech audio from text. Returns raw MP3 bytes."""
    voice_id = VOICES.get(voice, voice)  # accept name or raw ID

    url = f"{BASE_URL}/text-to-speech/{voice_id}"
    payload = {
        "text": text,
        "model_id": model_id,
        "voice_settings": {
            "stability": stability,
            "similarity_boost": similarity_boost,
        },
    }

    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        headers={
            "xi-api-key": api_key,
            "Content-Type": "application/json",
            "Accept": "audio/mpeg",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT) as resp:
            audio = resp.read()
    except urllib.error.HTTPError as e:
        text_err = e.read().decode("utf-8") if e.fp else ""
        msg = f"ElevenLabs API error {e.code}: {text_err[:300]}"
        if e.code in {408, 429} or 500 <= e.code <= 599:
            raise ElevenLabsRetryableError(msg) from e
        raise ElevenLabsError(msg) from e
    except urllib.error.URLError as e:
        raise ElevenLabsRetryableError(f"Network error: {e}") from e
    except (ConnectionError, TimeoutError, OSError) as e:
        raise ElevenLabsRetryableError(f"Connection error: {e}") from e

    return SpeechResult(
        audio_bytes=audio,
        voice_id=voice_id,
        char_count=len(text),
    )
