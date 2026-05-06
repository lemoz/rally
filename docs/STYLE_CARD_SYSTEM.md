# Style Card System

Style cards are Rally's reusable creative control layer. A style card should be specific enough that a planner can generate storyboards, route shots, and QA outputs without rediscovering the same lessons on every video.

## Current Locked Card

`rally-poc/style_cards/psyop_anime_90s.json`

This card captures the April 26 Glasswing anime lessons:
- Six-panel storyboard batches are the default and max unit.
- Dialogue scenes must preserve shared-room geography across reverse shots.
- Real-person/likeness-critical talking heads require source-backed still review before video or lip sync spend.
- Likeness-critical talking heads route `NB2 still -> RunComfy lip sync`; do not run Seedance I2V before lip sync by default because it can drift the face.
- Dialogue-heavy cuts use hard cuts unless audio timing is explicitly counterbalanced.
- Lip-sync outputs get slight end padding so spoken words do not spill into the next shot.
- Proof cards are deterministic/source-backed and never generated as fake evidence.

## Current Candidate Cards

- `rally-poc/style_cards/raw_demo_build_log.json` — native-feeling screen recording and voiceover. Best next video-generation candidate.
- `rally-poc/style_cards/proof_carousel.json` — deterministic save-worthy slides. Best volume candidate.
- `rally-poc/style_cards/before_after_transformation.json` — result-first transformation. Best when a project has a visible before/after delta.

The first OpenScreen style test prompts live under `rally-poc/output/style_test_*`. See `docs/STYLE_TESTS.md` for the readout.

## File Shape

Each style card has:
- `visual_grammar`: palette, camera language, texture, composition rules.
- `story_structure`: expected narrative beats.
- `caption_treatment`: subtitle placement and constraints.
- `audio`: voice mode, language, voice map, music assumption.
- `storyboard`: batch size and when to create additional batches.
- `generation_rules`: hard routing and QA lessons.
- `routing`: default and fallback routes by shot type.
- `qa`: pass checks, reject reasons, and eval thresholds.

## Usage

Storyboard plans should reference a style card by id:

```json
{
  "video_id": "glasswing_anime_short_001",
  "style_id": "psyop_anime_90s",
  "storyboard": {
    "batch_size": 6
  },
  "panels": []
}
```

Generate batch prompts:

```bash
python3 -m pipeline.storyboard storyboard_plan_example.json output/storyboard_example_locked
```

The storyboard builder loads `rally-poc/style_cards/<style_id>.json`, injects the card's routing guidance into prompts, and validates panel-level risks like missing likeness references or unsafe lip-sync routes.

## Rule Of Thumb

If a lesson affects repeatability, it belongs in the style card. If it affects one specific video only, it belongs in that video plan.
