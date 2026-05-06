"""Storyboard batching and prompt building.

This module is intentionally API-free. It turns a structured storyboard plan
into six-panel batch prompts that can be reviewed before spending model credits.
"""
from __future__ import annotations

import argparse
import json
import textwrap
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    from .style_cards import resolve_style_card
except ImportError:  # pragma: no cover - supports direct script execution.
    from style_cards import resolve_style_card


DEFAULT_BATCH_SIZE = 6
VALID_CLAIM_TYPES = {
    "decorative",
    "interpretive",
    "claim_bearing",
    "proof_bearing",
}
VALID_SOURCE_REQUIREMENTS = {
    "none",
    "reference_only",
    "source_backed",
    "deterministic_render",
}


@dataclass(frozen=True)
class StoryboardBatch:
    """One storyboard generation unit."""

    batch_id: str
    panels: list[dict[str, Any]]
    prompt: str
    reject_reasons: list[str]


def build_batches(
    plan: dict[str, Any],
    batch_size: int | None = None,
    *,
    style_card_dir: str | Path | None = None,
    plan_path: str | Path | None = None,
) -> list[StoryboardBatch]:
    """Split a storyboard plan into prompt-ready batches."""
    storyboard = plan.get("storyboard", {})
    style_card = resolve_style_card(
        plan,
        style_card_dir=style_card_dir,
        plan_path=plan_path,
    )
    generation = style_card.get("generation_rules", {})
    size = batch_size or int(
        storyboard.get("batch_size")
        or generation.get("default_storyboard_batch_size")
        or DEFAULT_BATCH_SIZE
    )
    if size <= 0:
        raise ValueError("batch_size must be positive")
    if size > DEFAULT_BATCH_SIZE:
        raise ValueError("batch_size must be 6 or less")

    panels = list(plan.get("panels") or [])
    if not panels:
        raise ValueError("plan must contain a non-empty panels array")

    batches: list[StoryboardBatch] = []
    for index in range(0, len(panels), size):
        batch_panels = panels[index:index + size]
        batch_id = f"b{len(batches) + 1:02d}"
        batches.append(
            StoryboardBatch(
                batch_id=batch_id,
                panels=batch_panels,
                prompt=build_prompt(
                    style_card=style_card,
                    panels=batch_panels,
                    batch_id=batch_id,
                    video_id=plan.get("video_id", "untitled_video"),
                    project=plan.get("project", {}),
                ),
                reject_reasons=validate_panels(batch_panels),
            )
        )
    return batches


def build_prompt(
    *,
    style_card: dict[str, Any],
    panels: list[dict[str, Any]],
    batch_id: str,
    video_id: str,
    project: dict[str, Any] | None = None,
) -> str:
    """Build a model prompt for one 3x2 storyboard sheet."""
    visual = style_card.get("visual_grammar", {})
    caption = style_card.get("caption_treatment", {})
    generation = style_card.get("generation_rules", {})
    routing = style_card.get("routing", {})
    reference_notes = style_card.get("reference_notes", [])

    lines = [
        f"Create storyboard sheet {batch_id} for video {video_id}.",
        "",
    ]

    if project:
        lines.extend(_project_context_lines(project))
        lines.append("")

    lines.extend([
        "Canvas and layout:",
        "- 16:9 overall storyboard sheet.",
        "- 3 columns x 2 rows, six panels total.",
        "- Each panel must compose as a vertical 9:16 crop.",
        "- Keep panel boundaries clean and evenly spaced.",
        "- Leave the bottom caption safe area clear in every panel.",
        "",
        "Style:",
        f"- Style id: {style_card.get('style_id', 'unspecified')}",
        f"- Display name: {style_card.get('display_name', 'unspecified')}",
        f"- Palette: {_join(visual.get('palette'))}",
        f"- Camera grammar: {_join(visual.get('camera'))}",
        f"- Texture: {_join(visual.get('texture'))}",
        f"- Caption position: {caption.get('position', 'bottom_safe_area')}",
        f"- Caption style: {caption.get('style', 'style-card default')}",
    ])

    composition_rules = visual.get("composition_rules") or []
    if composition_rules:
        lines.extend(["", "Composition rules:"])
        lines.extend(f"- {rule}" for rule in composition_rules)

    lines.extend([
        "",
        "Reference notes:",
    ])

    if reference_notes:
        lines.extend(f"- {note}" for note in reference_notes)
    else:
        lines.append("- None.")

    if generation.get("prefer_eye_closeups_over_lipsync"):
        lines.append("- Prefer dramatic eye close-ups over visible mouth shots unless the panel asks for lip sync.")
    if generation.get("proof_panels_must_be_source_backed", True):
        lines.append("- Proof-bearing panels must look like designed evidence cards, not invented screenshots.")

    route_guidance = _route_guidance_lines(generation, routing)
    if route_guidance:
        lines.extend(["", "Routing guidance:"])
        lines.extend(route_guidance)

    lines.extend(["", "Panels:"])
    for idx, panel in enumerate(panels, start=1):
        lines.extend(_panel_prompt_lines(idx, panel))

    lines.extend([
        "",
        "Quality bar:",
        "- One clear beat per panel.",
        "- Strong vertical composition in every panel.",
        "- Character identities stay consistent across panels.",
        "- Do not invent exact UI, exact stats, or exact quotes unless the panel is marked deterministic_render.",
        "- No tiny unreadable text except decorative texture.",
    ])
    return "\n".join(lines)


def validate_panels(panels: list[dict[str, Any]]) -> list[str]:
    """Return reject reasons for storyboard panels before generation."""
    reasons: list[str] = []
    for panel in panels:
        panel_id = panel.get("panel_id", "unknown")
        claim_type = panel.get("claim_type", "")
        source_req = panel.get("source_requirement", "")

        if claim_type not in VALID_CLAIM_TYPES:
            reasons.append(f"{panel_id}: invalid_claim_type")
        if source_req not in VALID_SOURCE_REQUIREMENTS:
            reasons.append(f"{panel_id}: invalid_source_requirement")
        if claim_type == "proof_bearing" and source_req not in {
            "source_backed",
            "deterministic_render",
        }:
            reasons.append(f"{panel_id}: fake_evidence_risk")
        if not panel.get("beat"):
            reasons.append(f"{panel_id}: unclear_beat")
        if not panel.get("motion_intent"):
            reasons.append(f"{panel_id}: missing_motion_intent")
        if panel.get("likeness_critical") and not panel.get("reference_character"):
            reasons.append(f"{panel_id}: missing_reference_character")
        if panel.get("likeness_critical") and panel.get("needs_lipsync"):
            route = panel.get("video_route", "")
            if route not in {
                "NB2_STILL_TO_RUNCOMFY_LIPSYNC",
                "NB2_STILL_TO_LIPSYNC",
            }:
                reasons.append(f"{panel_id}: identity_drift_risk")
    return reasons


def write_batch_files(
    plan_path: str,
    output_dir: str,
    batch_size: int | None = None,
    *,
    style_card_dir: str | Path | None = None,
) -> list[Path]:
    """Write storyboard batch JSON files and prompt text files."""
    with open(plan_path) as f:
        plan = json.load(f)

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    written: list[Path] = []
    for batch in build_batches(
        plan,
        batch_size=batch_size,
        style_card_dir=style_card_dir,
        plan_path=plan_path,
    ):
        payload = {
            "batch_id": batch.batch_id,
            "panels": batch.panels,
            "prompt": batch.prompt,
            "reject_reasons": batch.reject_reasons,
        }
        json_path = out / f"{batch.batch_id}.json"
        prompt_path = out / f"{batch.batch_id}_prompt.txt"
        json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        prompt_path.write_text(batch.prompt, encoding="utf-8")
        written.extend([json_path, prompt_path])
    return written


def _panel_prompt_lines(index: int, panel: dict[str, Any]) -> list[str]:
    chars = _join(panel.get("characters"))
    lines = [
        f"{index}. Panel {panel.get('panel_id', f'p{index:02d}')}",
        f"   Beat: {panel.get('beat', '')}",
        f"   Role: {panel.get('role', '')}",
        f"   Shot type: {panel.get('shot_type', '')}",
        f"   Claim type: {panel.get('claim_type', '')}",
        f"   Source requirement: {panel.get('source_requirement', '')}",
        f"   Characters: {chars}",
        f"   Composition: {panel.get('composition', '')}",
        f"   Motion intent: {panel.get('motion_intent', '')}",
        f"   Caption safe area: {panel.get('caption_safe_area', 'bottom 18 percent clear')}",
    ]
    if panel.get("scene_id"):
        lines.append(f"   Scene id: {panel.get('scene_id')}")
    if panel.get("reference_character"):
        lines.append(f"   Reference character: {panel.get('reference_character')}")
    if panel.get("likeness_critical"):
        lines.append("   Likeness critical: yes, review still before video or lip sync.")
    if panel.get("needs_lipsync"):
        lines.append("   Needs lip sync: yes.")
    if panel.get("video_route"):
        lines.append(f"   Video route: {panel.get('video_route')}")
    if panel.get("fallback_route"):
        lines.append(f"   Fallback route: {panel.get('fallback_route')}")
    return lines


def _route_guidance_lines(
    generation: dict[str, Any],
    routing: dict[str, Any],
) -> list[str]:
    lines: list[str] = []
    default_routes = routing.get("default_routes", {})
    if default_routes:
        for shot_type, route in default_routes.items():
            lines.append(f"- {shot_type}: {route}")

    if generation.get("avoid_i2v_before_lipsync_for_likeness"):
        lines.append(
            "- For likeness-critical talking heads, use the approved NB2 still directly as the lip-sync source; do not run video I2V first."
        )
    if generation.get("review_likeness_before_video"):
        lines.append("- Stop after still generation for likeness-critical panels and approve the face before spending on video/lip sync.")
    if generation.get("dialogue_transition_duration") == 0:
        lines.append("- Dialogue-heavy cuts use hard cuts unless audio timing is explicitly counterbalanced.")
    if generation.get("motion_required_per_video_shot"):
        lines.append("- Every generated video shot needs explicit camera, character, environment, or graphic motion.")
    return lines


def _project_context_lines(project: dict[str, Any]) -> list[str]:
    lines = ["Project context:"]
    for field in ("name", "repo", "one_liner"):
        if project.get(field):
            lines.append(f"- {field}: {project[field]}")
    known_proof = project.get("known_proof") or []
    if known_proof:
        lines.append("- known proof:")
        lines.extend(f"  - {item}" for item in known_proof)
    return lines


def _join(value: Any) -> str:
    if isinstance(value, list):
        return ", ".join(str(v) for v in value) if value else "unspecified"
    return str(value) if value else "unspecified"


def _main() -> None:
    parser = argparse.ArgumentParser(
        description="Build six-panel storyboard batch prompts from a plan JSON."
    )
    parser.add_argument("plan", help="Path to storyboard plan JSON")
    parser.add_argument("output_dir", help="Directory for batch prompt outputs")
    parser.add_argument("--batch-size", type=int, default=None)
    parser.add_argument("--style-card-dir", default=None)
    args = parser.parse_args()

    written = write_batch_files(
        args.plan,
        args.output_dir,
        batch_size=args.batch_size,
        style_card_dir=args.style_card_dir,
    )
    print(f"Wrote {len(written)} files:")
    for path in written:
        print(f"  {path}")


if __name__ == "__main__":
    _main()
