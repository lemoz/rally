# Style Tests

## April 26 Candidate Set

Shared project: OpenScreen (`github.com/siddharthvaddem/openscreen`)

Generated prompt batches:
- `rally-poc/output/style_test_raw_demo/b01_prompt.txt`
- `rally-poc/output/style_test_proof_carousel/b01_prompt.txt`
- `rally-poc/output/style_test_before_after/b01_prompt.txt`

Source plans:
- `rally-poc/style_tests/openscreen_raw_demo_build_log.json`
- `rally-poc/style_tests/openscreen_proof_carousel.json`
- `rally-poc/style_tests/openscreen_before_after_transformation.json`

Style cards:
- `rally-poc/style_cards/raw_demo_build_log.json`
- `rally-poc/style_cards/proof_carousel.json`
- `rally-poc/style_cards/before_after_transformation.json`

All three prompt batches currently validate with `reject_reasons: []`.

## Readout

### `raw_demo_build_log`

Best next video-generation candidate.

Why:
- Closest to native dev TikTok.
- Uses real capture/proof first, so factual risk is lower.
- Makes OpenScreen's actual product motion the hook.
- Can become the baseline for project demos.

Main risk:
- Needs usable screen capture. If capture is weak, the style collapses into proof cards.

### `proof_carousel`

Best volume candidate.

Why:
- Cheapest and most deterministic.
- Strong for saves and muted viewing.
- Avoids most video-model failure modes.

Main risk:
- It tests slide/story quality more than video-generation quality.

### `before_after_transformation`

Best high-retention candidate if the project has a clear visible delta.

Why:
- Result-first hook is strong.
- Side-by-side comparison is easy to understand.
- Works well for productivity tools like OpenScreen.

Main risk:
- Requires a credible before and after. If the visual delta is weak, it feels forced.

## Recommendation

Generate in this order:
1. `raw_demo_build_log`
2. `before_after_transformation`
3. `proof_carousel`

Do not generate all three until the first one produces a clean factual capture and a usable assembly path. If real capture is blocked, switch immediately to `proof_carousel`.
