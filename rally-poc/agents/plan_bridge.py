"""Convert agentic studio artifacts (storyboard.json + keyframe_specs.json +
selected_concept.md) into a pipeline plan.json that pipeline.run_pipeline
can consume.

The studio's storyboard role outputs a panels array with rich fields
(visual_contract, motion_intent, caption, generation_route_hint). The
art_director outputs keyframe_specs.json with even richer per-panel
prompts (still_prompt, motion_prompt, deterministic_elements). The
creative_director's selected_concept.md has the beat sheet with VO/caption
wording that downstream roles reference but don't always copy verbatim.

This bridge merges all three into a flat plan.json shaped for run_pipeline.

Used by:
    python3 -m agents.plan_bridge <run_dir>

Or programmatically:
    from agents.plan_bridge import bridge_storyboard
    plan_path = bridge_storyboard(run_dir)
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


# Map agentic-studio video_route hints → pipeline shot types.
ROUTE_TYPE_HINTS = {
    "T2V": "T2V",
    "I2V": "I2V",
    "NB2": "I2V",
    "STILL": "NB2_STILL",
    "DETERMINISTIC": "NB2_STILL",
    "REAL_CAPTURE": "NB2_STILL",
    "SCREEN_CAPTURE": "NB2_STILL",
    "SCREENSHOT": "NB2_STILL",
    "PROOF_CARD": "NB2_STILL",
    "LIPSYNC": "NB2_STILL",
}


def bridge_storyboard(run_dir: str | Path) -> Path:
    """Read storyboard.json + keyframe_specs.json + selected_concept.md from run_dir,
    write plan.json. Returns its path.
    """
    run_dir = Path(run_dir).resolve()
    storyboard_path = run_dir / "artifacts" / "storyboard.json"
    keyframes_path = run_dir / "artifacts" / "keyframe_specs.json"
    concept_md_path = run_dir / "artifacts" / "selected_concept.md"

    if not storyboard_path.exists():
        raise FileNotFoundError(f"missing {storyboard_path}")

    storyboard = json.loads(storyboard_path.read_text(encoding="utf-8"))
    keyframes_data: dict[str, Any] = (
        json.loads(keyframes_path.read_text(encoding="utf-8"))
        if keyframes_path.exists() else {}
    )
    keyframe_by_panel = {
        kf.get("panel_id", kf.get("keyframe_id", "")): kf
        for kf in (keyframes_data.get("keyframes") or keyframes_data.get("specs") or [])
    }

    # VO lines keyed by start-second from the concept's beat sheet markdown table.
    vo_by_start = _parse_beat_sheet_vo(concept_md_path) if concept_md_path.exists() else {}

    run_meta = json.loads((run_dir / "run.json").read_text(encoding="utf-8"))
    project = run_meta.get("project", run_dir.name)
    style_id = storyboard.get("style_id") or run_meta.get("style_id", "psyop_anime_90s")
    cast = storyboard.get("cast") or run_meta.get("cast") or {}

    panels = storyboard.get("panels") or storyboard.get("shots") or []
    shots: list[dict[str, Any]] = []
    for panel in panels:
        keyframe = keyframe_by_panel.get(panel.get("panel_id"))
        shots.append(_panel_to_shot(panel, keyframe, vo_by_start, cast))

    target_total = storyboard.get("duration_target_s") or run_meta.get("target_duration_s")

    plan = {
        "project": project,
        "style": style_id,
        "style_id": style_id,
        "output_dir": str(run_dir / f"output/{project}"),
        "target_duration_s": target_total,
        "master_script_path": str(concept_md_path) if concept_md_path.exists() else None,
        "cast": cast or None,
        "audio_strategy": "vo_drives_video",
        "shots": shots,
        "music": storyboard.get("music"),
        "transition_duration": storyboard.get("transition_duration", 0.0),
    }
    plan = {k: v for k, v in plan.items() if v not in (None, "", {}, [])}

    out_path = run_dir / "artifacts" / "plan.json"
    out_path.write_text(json.dumps(plan, indent=2), encoding="utf-8")
    return out_path


def _panel_to_shot(
    panel: dict[str, Any],
    keyframe: dict[str, Any] | None,
    vo_by_start: dict[float, str],
    cast: dict[str, Any],
) -> dict[str, Any]:
    """Convert one storyboard panel + matching keyframe spec into a shot dict."""
    panel_id = panel.get("panel_id") or panel.get("name") or "shot"
    name = panel_id.lower().replace(" ", "_") if isinstance(panel_id, str) else "shot"

    # Duration from time_range_s
    time_range = panel.get("time_range_s") or {}
    if isinstance(time_range, dict):
        start = float(time_range.get("start", 0.0))
        end = float(time_range.get("end", start + 5.0))
    elif isinstance(time_range, (list, tuple)) and len(time_range) >= 2:
        start, end = float(time_range[0]), float(time_range[1])
    else:
        start, end = 0.0, 5.0
    duration_s = max(2.0, round(end - start))

    # Type derivation from route hint(s)
    route_hint_raw = (
        (keyframe or {}).get("route") or
        panel.get("generation_route_hint") or
        panel.get("video_route") or ""
    )
    route_hint = route_hint_raw.upper() if isinstance(route_hint_raw, str) else ""
    shot_type = "I2V"  # safest default — uses NB2 still + Seedance motion
    for token, t in ROUTE_TYPE_HINTS.items():
        if token in route_hint:
            shot_type = t
            break

    # Image prompt: prefer keyframe's still_prompt, then composition, then visual_contract
    image_prompt = (
        (keyframe or {}).get("still_prompt") or
        (keyframe or {}).get("composition") or
        panel.get("visual_contract") or
        panel.get("composition") or
        panel.get("beat") or ""
    )

    # Video prompt: prefer keyframe's motion_prompt, fallback to panel's motion_intent
    video_prompt_raw = (
        (keyframe or {}).get("motion_prompt") or
        panel.get("motion_intent") or ""
    )
    motion_source = (
        (keyframe or {}).get("motion_source") or
        panel.get("motion_source") or ""
    )
    parts = []
    if image_prompt:
        parts.append(image_prompt.strip())
    if video_prompt_raw:
        parts.append(f"Motion: {video_prompt_raw.strip()}")
    if motion_source and motion_source not in video_prompt_raw:
        parts.append(f"Motion sources: {motion_source.strip()}")
    parts.append("9:16 vertical")
    video_prompt = " ".join(parts)

    # VO text. Trust the panel's explicit caption.text first — an empty string
    # there is intentional (e.g., diegetic-only shots have caption.text=""), so
    # we do NOT fall back to the beat-sheet for those. We only pull from the
    # beat sheet when the panel doesn't define a caption at all.
    vo_text: str | None = None
    panel_cap = panel.get("caption")
    panel_cap_explicit = isinstance(panel_cap, dict) and "text" in panel_cap
    if isinstance(panel_cap, dict):
        candidate = panel_cap.get("text", "").strip()
        vo_text = candidate or None
    elif isinstance(panel_cap, str):
        vo_text = panel_cap.strip() or None

    if vo_text is None and not panel_cap_explicit:
        # Panel didn't even define a caption field — use beat-sheet match.
        vo_text = vo_by_start.get(round(start)) or vo_by_start.get(round(start, 1))

    # Subtitle: same caption text. Empty → no on-screen subtitle this panel.
    subtitle = None
    if isinstance(panel_cap, dict):
        subtitle = panel_cap.get("text", "").strip() or None
    elif isinstance(panel_cap, str):
        subtitle = panel_cap.strip() or None

    # Voice
    vo_voice = panel.get("vo_voice")
    if not vo_voice:
        characters = cast.get("characters") if isinstance(cast, dict) else []
        if characters:
            vo_voice = characters[0].get("voice", "Liam")
    vo_voice = vo_voice or "Liam"

    needs_lipsync = bool(panel.get("needs_lipsync") or panel.get("lipsync_required"))

    shot: dict[str, Any] = {
        "name": name,
        "type": shot_type,
        "duration_s": int(duration_s),
        "vo_text": vo_text,
        "vo_voice": vo_voice,
        "needs_lipsync": needs_lipsync,
        "subtitle": subtitle,
    }
    if shot_type in ("I2V", "NB2_STILL"):
        shot["image_prompt"] = image_prompt
    if shot_type in ("I2V", "T2V"):
        shot["video_prompt"] = video_prompt
    if panel.get("reference_image"):
        shot["reference_image"] = panel["reference_image"]

    return {k: v for k, v in shot.items() if v not in (None, "")}


def _parse_beat_sheet_vo(concept_md: Path) -> dict[float, str]:
    """Pull VO/caption-safe wording from the concept's beat-sheet markdown table.

    Looks for a markdown table whose first column is a time range like "0-2s"
    or "13–19s". Returns dict mapping start-second → wording cell text.
    """
    text = concept_md.read_text(encoding="utf-8")
    out: dict[float, str] = {}
    # Match table rows: | <time> | <beat> | <visual> | <wording> |
    row_re = re.compile(
        r"\|\s*(?P<time>[\d\.]+)\s*[–\-]+\s*(?P<end>[\d\.]+)?\s*s?\s*"
        r"\|\s*(?P<beat>[^|]*?)\s*"
        r"\|\s*(?P<visual>[^|]*?)\s*"
        r"\|\s*(?P<wording>[^|]*?)\s*\|",
        re.MULTILINE,
    )
    for m in row_re.finditer(text):
        try:
            start = float(m.group("time"))
        except (TypeError, ValueError):
            continue
        wording = m.group("wording").strip().strip('"').strip("'").strip("“").strip("”")
        if wording:
            out[round(start)] = wording
    return out


def _main() -> None:
    parser = argparse.ArgumentParser(description="Bridge agentic artifacts to plan.json")
    parser.add_argument("run_dir")
    args = parser.parse_args()
    out = bridge_storyboard(args.run_dir)
    print(out)


if __name__ == "__main__":
    _main()
