"""OpenAI Whisper client for word-level transcript timestamps.

Used by the captions stage of the pipeline (step 9 of PRODUCTION_ORDER.md):
each shot's VO mp3 → list of {word, start, end} that the FFmpeg assembly
turns into per-word drawtext windows synced to actual speech, not estimates.

Cost: $0.006/min (whisper-1). A 30s video runs ~$0.003 across all shots.

Usage:
    from pipeline.whisper_client import transcribe_with_word_timestamps
    words = transcribe_with_word_timestamps("audio/s01.mp3", api_key)
    # [{"word": "I'm", "start": 0.10, "end": 0.32}, ...]
"""
from __future__ import annotations

import json
import urllib.error
import urllib.request
import uuid
from dataclasses import dataclass
from pathlib import Path

API_URL = "https://api.openai.com/v1/audio/transcriptions"
DEFAULT_MODEL = "whisper-1"
REQUEST_TIMEOUT = 120


class WhisperError(RuntimeError):
    pass


class WhisperRetryableError(WhisperError):
    pass


@dataclass
class TranscriptResult:
    text: str
    words: list[dict]  # [{"word": str, "start": float, "end": float}, ...]
    duration_s: float


def transcribe_with_word_timestamps(
    audio_path: str | Path,
    api_key: str,
    *,
    model: str = DEFAULT_MODEL,
    language: str | None = "en",
) -> TranscriptResult:
    """Transcribe an audio file and return per-word timestamps.

    Returns the words array as parsed from Whisper's verbose_json response.
    Each word entry has keys: word, start, end (clip-relative seconds).
    """
    audio_path = Path(audio_path)
    if not audio_path.exists():
        raise FileNotFoundError(f"audio file not found: {audio_path}")

    body, content_type = _build_multipart(
        audio_path,
        model=model,
        response_format="verbose_json",
        timestamp_granularities=["word"],
        language=language,
    )

    request = urllib.request.Request(
        API_URL,
        data=body,
        headers={
            "Content-Type": content_type,
            "Authorization": f"Bearer {api_key}",
            "User-Agent": "rally-pipeline/1.0",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        text = e.read().decode("utf-8", errors="replace") if e.fp else ""
        msg = f"Whisper API error {e.code}: {text[:500]}"
        if e.code in {408, 429} or 500 <= e.code <= 599:
            raise WhisperRetryableError(msg) from e
        raise WhisperError(msg) from e
    except urllib.error.URLError as e:
        raise WhisperRetryableError(f"Network error: {e}") from e

    words = data.get("words") or []
    text = data.get("text", "")
    duration = float(data.get("duration", 0.0))
    return TranscriptResult(text=text, words=words, duration_s=duration)


def _build_multipart(
    audio_path: Path,
    *,
    model: str,
    response_format: str,
    timestamp_granularities: list[str],
    language: str | None,
) -> tuple[bytes, str]:
    """Build a multipart/form-data body for the Whisper transcriptions endpoint."""
    boundary = f"----rally{uuid.uuid4().hex}"
    crlf = b"\r\n"
    parts: list[bytes] = []

    def field(name: str, value: str) -> None:
        parts.append(f"--{boundary}".encode("utf-8"))
        parts.append(crlf)
        parts.append(
            f'Content-Disposition: form-data; name="{name}"'.encode("utf-8")
        )
        parts.append(crlf)
        parts.append(crlf)
        parts.append(value.encode("utf-8"))
        parts.append(crlf)

    field("model", model)
    field("response_format", response_format)
    for granularity in timestamp_granularities:
        field("timestamp_granularities[]", granularity)
    if language:
        field("language", language)

    # File field
    file_bytes = audio_path.read_bytes()
    parts.append(f"--{boundary}".encode("utf-8"))
    parts.append(crlf)
    parts.append(
        (
            f'Content-Disposition: form-data; name="file"; filename="{audio_path.name}"'
        ).encode("utf-8")
    )
    parts.append(crlf)
    parts.append(b"Content-Type: audio/mpeg")
    parts.append(crlf)
    parts.append(crlf)
    parts.append(file_bytes)
    parts.append(crlf)
    parts.append(f"--{boundary}--".encode("utf-8"))
    parts.append(crlf)

    body = b"".join(parts)
    content_type = f"multipart/form-data; boundary={boundary}"
    return body, content_type


def group_words_into_phrases(
    words: list[dict],
    *,
    max_words_per_phrase: int = 4,
    max_phrase_duration_s: float = 2.5,
) -> list[dict]:
    """Group consecutive Whisper words into short phrases for caption display.

    Each phrase: {text, start, end}. Used by the FFmpeg assembly to emit one
    drawtext block per phrase rather than one per word (which can hit the
    ~700-node filtergraph limit on long videos and reads choppy on screen).
    """
    phrases: list[dict] = []
    current: list[dict] = []

    def flush():
        if not current:
            return
        text = " ".join(w["word"].strip() for w in current).strip()
        phrases.append({
            "text": text,
            "start": float(current[0]["start"]),
            "end": float(current[-1]["end"]),
        })

    for word in words:
        if not current:
            current.append(word)
            continue
        if (
            len(current) >= max_words_per_phrase
            or (float(word["end"]) - float(current[0]["start"])) > max_phrase_duration_s
        ):
            flush()
            current = [word]
        else:
            current.append(word)

    flush()
    return phrases
