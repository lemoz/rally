"""Convert a storyboard.json (agentic-studio format) into a plan.json
(pipeline.run_pipeline format) so the Generation role can hand off to the
deterministic pipeline.

The studio's `storyboard` role outputs `artifacts/storyboard.json` with a
`panels` array. `pipeline.run_pipeline` consumes a flat plan with `shots`.
This bridge does the schema map plus a few smart defaults.

Used by:
    python3 -m agents.plan_bridge <run_dir>

Or programmatically:
    from agents.plan_bridge import bridge_storyboard
    plan_path = bridge_storyboard(run_dir)
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


# Map agentic-studio video_route hints → pipeline shot types.
ROUTE_TO_TYPE = {
    "NB2_STORYBOARD_PANEL_TO_SEEDANCE_I2V": "I2V",
    "NB2_STILL_TO_RUNCOMFY_LIPSYNC": "NB2_STILL",
    "NB2_STILL_TO_LIPSYNC": "NB2_STILL",
    "NB2_STILL_WITH_ASSEMBLY_MOTION": "NB2_STILL",
    "DETERMINISTIC_PROOF_CARD": "NB2_STILL",
    "REAL_CAPTURE": "NB2_STILL",  # treated as still + assembly motion
    "T2V": "T2V",
    "I2V": "I2V",
    "NB2_STILL": "NB2_STILL",
}


def bridge_storyboard(run_dir: str | Path) -> Path:
    """Read run_dir/artifacts/storyboard.json, write run_dir/artifacts/plan.json.

    Returns path to the generated plan.json.
    """
    run_dir = Path(run_dir).resolve()
    storyboard_path = run_dir / "artifacts" / "storyboard.json"
    if not storyboard_path.exists():
        raise FileNotFoundError(f"missing {storyboard_path}")

    storyboard = json.loads(storyboard_path.read_text(encoding="utf-8"))
    run_meta = json.loads((run_dir / "run.json").read_text(encoding="utf-8"))

    project = run_meta.get("project", run_dir.name)
    style_id = storyboard.get("style_id") or run_meta.get("style_id", "psyop_anime_90s")
    cast = storyboard.get("cast") or run_meta.get("cast") or {}

    panels = storyboard.get("shots") or storyboard.get("panels") or []
    shots: list[dict[str, Any]] = []
    for panel in panels:
        shots.append(_panel_to_shot(panel, cast))

    plan = {
        "project": project,
        "style": style_id,
        "style_id": style_id,
        "output_dir": str(run_dir / f"output/{project}"),
        "target_duration_s": storyboard.get("target_duration_s") or run_meta.get("target_duration_s"),
        "master_script": storyboard.get("master_script") or run_meta.get("master_script"),
        "cast": cast,
        "audio_strategy": "vo_drives_video",
        "shots": shots,
        "music": storyboard.get("music"),
        "transition_duration": storyboard.get("transition_duration", 0.0),
    }
    plan = {k: v for k, v in plan.items() if v is not None}

    out_path = run_dir / "artifacts" / "plan.json"
    out_path.write_text(json.dumps(plan, indent=2), encoding="utf-8")
    return out_path


def _panel_to_shot(panel: dict[str, Any], cast: dict[str, Any]) -> dict[str, Any]:
    """Convert one storyboard panel into a pipeline shot dict."""
    # Name: prefer panel name; fall back to panel_id.
    name = panel.get("name") or panel.get("panel_id") or "shot"

    # Type: derive from video_route or fall back to type field.
    route = (panel.get("video_route") or "").upper()
    shot_type = panel.get("type") or ROUTE_TO_TYPE.get(route, "I2V")

    # Image / video prompts: composition for image, motion_intent for video.
    composition = panel.get("composition") or panel.get("image_prompt") or panel.get("beat") or ""
    motion = panel.get("motion_intent") or panel.get("video_prompt") or composition

    image_prompt = panel.get("image_prompt") or composition
    video_prompt = panel.get("video_prompt") or _build_video_prompt(composition, motion)

    # Voice: panel.vo_voice → fall back to cast default.
    vo_voice = panel.get("vo_voice")
    if not vo_voice:
        characters = cast.get("characters", [])
        if characters:
            vo_voice = characters[0].get("voice", "Liam")
    vo_voice = vo_voice or "Liam"

    needs_lipsync = bool(panel.get("needs_lipsync") or panel.get("lipsync_required"))

    shot: dict[str, Any] = {
        "name": name,
        "type": shot_type,
        "duration_s": panel.get("duration_s", 5),
        "vo_text": panel.get("vo_text") or panel.get("script") or panel.get("dialogue"),
        "vo_voice": vo_voice,
        "needs_lipsync": needs_lipsync,
        "subtitle": panel.get("subtitle") or panel.get("caption") or panel.get("beat"),
    }
    if shot_type in ("I2V", "NB2_STILL"):
        shot["image_prompt"] = image_prompt
    if shot_type in ("I2V", "T2V"):
        shot["video_prompt"] = video_prompt
    if panel.get("reference_image"):
        shot["reference_image"] = panel["reference_image"]

    # Strip empty values so the pipeline's defaults take over.
    return {k: v for k, v in shot.items() if v not in (None, "")}


def _build_video_prompt(composition: str, motion: str) -> str:
    """Default video prompt: composition first, then explicit motion intent."""
    parts = []
    if composition:
        parts.append(composition.strip())
    if motion and motion not in composition:
        parts.append(f"Motion: {motion.strip()}")
    parts.append("9:16 vertical")
    return " ".join(parts)


def _main() -> None:
    parser = argparse.ArgumentParser(description="Bridge storyboard.json to plan.json")
    parser.add_argument("run_dir")
    args = parser.parse_args()
    out = bridge_storyboard(args.run_dir)
    print(out)


if __name__ == "__main__":
    _main()
