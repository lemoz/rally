"""Seedance 2.0 video generation via Segmind synchronous API.

POST https://api.segmind.com/v1/seedance-2.0-fast -> MP4 bytes (content-type: video/mp4)
Auth: x-api-key header.
"""
from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Optional

from .config import snap_duration

API_URL = "https://api.segmind.com/v1/seedance-2.0-fast"
REQUEST_TIMEOUT = 300  # synchronous; ~75s typical for 4s clip


class SegmindError(RuntimeError):
    pass


class SegmindRetryableError(SegmindError):
    pass


# Compat aliases for callers that imported the fal-era names.
SeedanceError = SegmindError
SeedanceRetryableError = SegmindRetryableError


def generate_video(
    *,
    prompt: str,
    api_key: str,
    duration: int = 5,
    aspect_ratio: str = "9:16",
    first_frame_url: Optional[str] = None,
    seed: Optional[int] = None,
    resolution: str = "720p",
) -> bytes:
    """Generate a video clip via Segmind Seedance 2.0. Returns raw MP4 bytes."""
    duration = snap_duration(duration)

    payload: dict = {
        "prompt": prompt,
        "duration": duration,
        "aspect_ratio": aspect_ratio,
        "resolution": resolution,
    }
    if seed is not None and seed >= 0:
        payload["seed"] = seed
    if first_frame_url:
        payload["image"] = first_frame_url

    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        API_URL,
        data=body,
        headers={
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "User-Agent": "rally-pipeline/1.0",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT) as resp:
            content_type = resp.headers.get("Content-Type", "")
            data = resp.read()
    except urllib.error.HTTPError as e:
        text = e.read().decode("utf-8", errors="replace") if e.fp else ""
        msg = f"Segmind API error {e.code}: {text[:500]}"
        if text and ("content_policy" in text.lower() or "sensitive" in text.lower()):
            raise SegmindError(
                f"Content policy violation. Try softening the prompt. Detail: {text[:300]}"
            ) from e
        if e.code in {408, 429} or 500 <= e.code <= 599:
            raise SegmindRetryableError(msg) from e
        raise SegmindError(msg) from e
    except urllib.error.URLError as e:
        raise SegmindRetryableError(f"Network error: {e}") from e
    except (ConnectionError, TimeoutError, OSError) as e:
        raise SegmindRetryableError(f"Connection error: {e}") from e

    if "video" not in content_type.lower():
        # Some error responses come back as 200 with JSON.
        try:
            parsed = json.loads(data.decode("utf-8", errors="replace"))
        except Exception:
            parsed = None
        if parsed:
            raise SegmindError(f"Expected MP4, got JSON: {parsed}")
        raise SegmindError(
            f"Unexpected content-type {content_type!r}, {len(data)} bytes"
        )

    if len(data) < 10_000:
        raise SegmindError(f"Response too small to be a video ({len(data)} bytes)")

    return data
