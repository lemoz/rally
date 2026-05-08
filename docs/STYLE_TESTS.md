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

---

## Style Decision Criteria

Until @rallysignal has real engagement data (≥7 days post-launch with 5+ posts), style decisions cannot be made on view counts. We use three explicit proxies:

### 1. Native-feel test
When the unmuted MP4 plays on a phone alongside 3 unrelated dev TikToks pulled from the For You feed, can a third-party viewer (Chris + 1-2 dev friends if available, otherwise Chris alone) tell which one is the AI-generated outlier within 3 seconds?
- **Pass** = no, it blends in
- **Fail** = yes, it stands out as overproduced or "ad-like"

This codifies the trend doc's finding: *"Authenticity beats production value — raw, phone-shot content sees 31% higher engagement; the algorithm deprioritizes overproduced content as 'ad-like.'"*

### 2. Hook integrity at 2s
Does a viewer, on mute, with no prior context, understand the project or get a reason to keep watching after 2 seconds? Test against:
- The first-frame screenshot alone (does the still composition convey?)
- The 0–2s loop (does the motion + caption combination convey?)

- **Pass** = yes on both
- **Fail** = either fails

This codifies the trend doc's finding: *"~70% watch-through required for viral distribution. Videos that don't hook in 2-3 seconds rarely exceed 10K views."*

### 3. Save-worthy moment
Is there a single frame or beat a viewer would screenshot, share, or send to a friend?
- **Pass** = yes, with a specific timestamp
- **Fail** = no obvious moment

This codifies the trend doc's finding: *"Save value is the strongest 2026 algorithm signal. Photo carousels and listicles overperform because individual slides are screenshot-worthy."*

### Use of these criteria

These are **proxies, not metrics**. They replace data we don't have yet. Once 5+ posts have ≥7 days of engagement data, real watch-through and save rates take over and these criteria become secondary triangulation only.

### Decision rule

When comparing N renders, score each on the three criteria + Chris's gut score (1-10). Top-1 by gut score (with criteria as triangulation, weighted 70/30 gut/criteria) becomes Rally's primary style for the next 1-2 weeks. Top-2 is secondary.

---

## Style Comparison Files

When multiple renders of the same content exist across styles, comparison lives in `docs/STYLE_COMPARISON_*.md` (one file per comparison batch). See `STYLE_COMPARISON_RALLY_001_005.md` for the first comparison.
