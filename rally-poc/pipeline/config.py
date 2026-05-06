"""Pipeline configuration: env loading, constants, voice IDs."""
from __future__ import annotations

import os
import subprocess


# -- Environment -----------------------------------------------------------

def load_env(path: str) -> None:
    """Load .env file into os.environ (will not overwrite existing vars)."""
    if not os.path.exists(path):
        return
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, val = line.split("=", 1)
            val = val.strip().strip("'\"")
            os.environ.setdefault(key, val)


def load_all_env() -> None:
    """Load credentials from standard locations."""
    load_env(os.path.join(os.path.dirname(__file__), "../../.env"))
    load_env(os.path.expanduser("~/.env"))


def require_key(name: str) -> str:
    """Get an env var or raise with a clear message."""
    val = os.environ.get(name, "")
    if not val:
        raise RuntimeError(f"{name} not set — check .env file")
    return val


# -- Media helpers ---------------------------------------------------------

def get_duration(path: str) -> float:
    """Get media file duration in seconds via ffprobe."""
    r = subprocess.run(
        ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", path],
        capture_output=True, text=True,
    )
    return float(r.stdout.strip())


# -- Seedance duration snapping --------------------------------------------

SEEDANCE_DURATIONS = [4, 5, 6, 8, 10, 12, 15]


def snap_duration(target: float) -> int:
    """Snap a target duration to the nearest valid Seedance 2.0 value."""
    return min(SEEDANCE_DURATIONS, key=lambda d: abs(d - target))


# -- ElevenLabs voice IDs -------------------------------------------------

VOICES = {
    "Liam": "TX3LPaxmHKxFdv7VOQHJ",
    "Daniel": "onwK4e9ZLuTAKqWW03F9",
    "Alice": "Xb7hH8MSUJpSbSDYk0k2",
    "Adam": "pNInz6obpgDQGcFmaJgB",
}


# -- Cost constants --------------------------------------------------------

COST_NB2_IMAGE = 0.08
COST_SEGMIND_PER_SECOND = 0.054   # ~$0.27 per 5s clip
COST_LIPSYNC_BASE = 0.15
COST_ELEVENLABS = 0.00            # free tier
COST_GUARD_PER_VIDEO = 15.0
