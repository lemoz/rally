"""Timing contract: audio drives every visual duration in the pipeline.

The pipeline orchestrator calls these functions to translate a plan + a set
of generated VO files into the canonical durations every downstream phase
must respect. Visual generation, music sizing, assembly cuts, and caption
windows all read these measurements; nothing reads `shot["duration_s"]`
after Phase 1 completes.

Contract:
    1. Each shot with `vo_text` produces a measurable mp3 file in audio/.
    2. `measure_vo_durations` returns a dict of {shot_name: float seconds}.
    3. `snap_shot_durations` snaps each measurement (+0.3s tail) to the
       Seedance-supported set in config.SEEDANCE_DURATIONS.
    4. `compute_total_target` returns the sum + transitions for music sizing.
    5. `plan_segments` splits a plan into Seedance-friendly segments
       (each <=12s of measured VO) for the multi-batch storyboard chain.

The 0.3s tail buffer is chosen to give the assembly stage room to finish a
syllable before the next shot cuts in, without padding so much that pacing
feels slack.

Used by: run_pipeline.py orchestrator, agentic studio gate enforcement,
multi-batch chain segment planner.
"""
from __future__ import annotations

import math
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

from .config import get_duration, snap_duration

VO_TAIL_BUFFER_S = 0.3
DEFAULT_MAX_SEGMENT_DURATION_S = 12.0  # 3s headroom under Seedance's 15s ceiling


@dataclass(frozen=True)
class Segment:
    """One contiguous group of shots that fits inside a single Seedance call."""

    segment_id: str
    shot_names: tuple[str, ...]
    target_duration: float
    is_first: bool
    is_last: bool


def measure_vo_durations(
    shots: Iterable[dict],
    output_dir: str | Path,
) -> dict[str, float]:
    """Return measured VO durations per shot.

    Looks for `audio/<shot_name>.mp3` under output_dir. Skips shots without
    a `vo_text` field or without a corresponding audio file. Raises nothing —
    missing files just don't appear in the result dict.
    """
    output_dir = Path(output_dir)
    audio_dir = output_dir / "audio"
    measured: dict[str, float] = {}
    for shot in shots:
        if not shot.get("vo_text"):
            continue
        name = shot["name"]
        audio_path = audio_dir / f"{name}.mp3"
        if not audio_path.exists():
            continue
        try:
            measured[name] = get_duration(str(audio_path))
        except Exception:
            # ffprobe couldn't read it; treat as unmeasurable rather than crash.
            continue
    return measured


def snap_shot_durations(
    shots: Iterable[dict],
    measured: dict[str, float],
    *,
    tail_buffer_s: float = VO_TAIL_BUFFER_S,
) -> dict[str, int]:
    """Return the Seedance-snapped visual duration per shot.

    For shots with measured VO: target = measured + tail_buffer, snapped.
    For shots without measured VO: falls back to plan's `duration_s` snapped.
    """
    snapped: dict[str, int] = {}
    for shot in shots:
        name = shot["name"]
        if name in measured:
            target = measured[name] + tail_buffer_s
        else:
            target = float(shot.get("duration_s", 5))
        snapped[name] = snap_duration(target)
    return snapped


def compute_total_target(
    shots: Iterable[dict],
    snapped: dict[str, int],
    *,
    transition_duration: float = 0.0,
) -> float:
    """Total target final-video duration based on snapped shot durations.

    With hard cuts (transition_duration=0) this is just the sum.
    With xfade transitions, each transition overlaps one duration's worth.
    """
    durations = [float(snapped.get(s["name"], s.get("duration_s", 5))) for s in shots]
    if not durations:
        return 0.0
    total = sum(durations)
    if transition_duration > 0 and len(durations) > 1:
        total -= transition_duration * (len(durations) - 1)
    return total


def plan_segments(
    shots: list[dict],
    snapped: dict[str, int],
    *,
    max_segment_duration_s: float = DEFAULT_MAX_SEGMENT_DURATION_S,
) -> list[Segment]:
    """Greedy-pack shots into segments, each <= max_segment_duration_s.

    Cuts always happen at shot boundaries. A single oversized shot gets its
    own segment even if it exceeds the cap (Seedance will be asked for the
    snapped duration regardless).
    """
    segments: list[Segment] = []
    current_shots: list[str] = []
    current_total = 0.0

    for shot in shots:
        name = shot["name"]
        dur = float(snapped.get(name, shot.get("duration_s", 5)))
        if current_shots and (current_total + dur) > max_segment_duration_s:
            segments.append(_finalize_segment(segments, current_shots, current_total))
            current_shots = []
            current_total = 0.0
        current_shots.append(name)
        current_total += dur

    if current_shots:
        segments.append(_finalize_segment(segments, current_shots, current_total))

    if segments:
        # Mark first/last by rebuilding with the flags set.
        flagged: list[Segment] = []
        for idx, seg in enumerate(segments):
            flagged.append(
                Segment(
                    segment_id=seg.segment_id,
                    shot_names=seg.shot_names,
                    target_duration=seg.target_duration,
                    is_first=idx == 0,
                    is_last=idx == len(segments) - 1,
                )
            )
        segments = flagged

    return segments


def _finalize_segment(
    existing: list[Segment],
    shot_names: list[str],
    total: float,
) -> Segment:
    return Segment(
        segment_id=f"seg{len(existing) + 1:02d}",
        shot_names=tuple(shot_names),
        target_duration=total,
        is_first=False,  # patched after finalization
        is_last=False,
    )


def drift_warning(
    measured_total: float,
    target_duration_s: float | None,
    *,
    tolerance_s: float = 1.5,
) -> str | None:
    """Return a warning string if the run.json target_duration_s drifts past tolerance.

    Used by the producer-gate preflight to fail loudly when planner intent
    and measured reality disagree. Returns None if no drift.
    """
    if target_duration_s is None:
        return None
    drift = abs(measured_total - target_duration_s)
    if drift <= tolerance_s:
        return None
    return (
        f"timing drift: target_duration_s={target_duration_s:.1f}s but measured+snapped "
        f"total={measured_total:.1f}s (drift={drift:.1f}s > {tolerance_s}s tolerance)"
    )
