"""Style card loading and validation for storyboard planning."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


DEFAULT_STYLE_CARD_DIR = Path(__file__).parent.parent / "style_cards"

REQUIRED_TOP_LEVEL_FIELDS = {
    "style_id",
    "display_name",
    "visual_grammar",
    "caption_treatment",
    "generation_rules",
}

REQUIRED_VISUAL_FIELDS = {
    "aspect_ratio",
    "storyboard_layout",
    "palette",
    "camera",
    "texture",
}


def resolve_style_card(
    plan: dict[str, Any],
    *,
    style_card_dir: str | Path | None = None,
    plan_path: str | Path | None = None,
) -> dict[str, Any]:
    """Return the style card for a plan.

    Plans can either embed a full ``style_card`` dict or reference one by
    ``style_id``. External cards are resolved from rally-poc/style_cards by
    default, with plan-relative file paths also supported for experiments.
    """
    embedded = plan.get("style_card")
    if isinstance(embedded, dict):
        return embedded
    if isinstance(embedded, str) and embedded:
        return load_style_card(embedded, style_card_dir=style_card_dir, plan_path=plan_path)

    style_id = plan.get("style_id") or plan.get("style")
    if not style_id:
        return {}
    return load_style_card(str(style_id), style_card_dir=style_card_dir, plan_path=plan_path)


def load_style_card(
    identifier: str,
    *,
    style_card_dir: str | Path | None = None,
    plan_path: str | Path | None = None,
) -> dict[str, Any]:
    """Load a style card by id or path."""
    path = _resolve_style_card_path(
        identifier,
        style_card_dir=Path(style_card_dir) if style_card_dir else DEFAULT_STYLE_CARD_DIR,
        plan_path=Path(plan_path) if plan_path else None,
    )
    with path.open(encoding="utf-8") as handle:
        card = json.load(handle)

    errors = validate_style_card(card)
    if errors:
        joined = ", ".join(errors)
        raise ValueError(f"Invalid style card {path}: {joined}")
    return card


def validate_style_card(card: dict[str, Any]) -> list[str]:
    """Return validation errors for a style card."""
    errors: list[str] = []
    for field in sorted(REQUIRED_TOP_LEVEL_FIELDS):
        if field not in card:
            errors.append(f"missing_{field}")

    visual = card.get("visual_grammar", {})
    if isinstance(visual, dict):
        for field in sorted(REQUIRED_VISUAL_FIELDS):
            if field not in visual:
                errors.append(f"missing_visual_grammar.{field}")
    else:
        errors.append("visual_grammar_not_object")

    generation = card.get("generation_rules", {})
    if not isinstance(generation, dict):
        errors.append("generation_rules_not_object")
    elif generation.get("default_storyboard_batch_size", 0) > 6:
        errors.append("default_storyboard_batch_size_exceeds_6")

    caption = card.get("caption_treatment", {})
    if not isinstance(caption, dict):
        errors.append("caption_treatment_not_object")

    return errors


def _resolve_style_card_path(
    identifier: str,
    *,
    style_card_dir: Path,
    plan_path: Path | None,
) -> Path:
    raw = Path(identifier)
    candidates: list[Path] = []

    if raw.is_absolute():
        candidates.append(raw)
    else:
        if raw.suffix == ".json":
            if plan_path:
                candidates.append(plan_path.parent / raw)
            candidates.append(style_card_dir / raw)
        else:
            candidates.append(style_card_dir / f"{identifier}.json")

    for candidate in candidates:
        if candidate.exists():
            return candidate

    tried = ", ".join(str(c) for c in candidates)
    raise FileNotFoundError(f"Style card not found for {identifier}. Tried: {tried}")
