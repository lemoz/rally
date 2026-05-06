# Storyboard Pipeline v2

## Checkpoint Brief

**Goal:** Make storyboard generation reliable enough to support many short-form video styles, not only the Glasswing anime test.

**Why it matters:** Storyboards are the creative control layer between a style reference and model generation. If this layer is loose, every video becomes a one-off prompt experiment. If this layer is structured, Rally can copy the visual grammar of popular formats while still enforcing provenance and repeatability.

**In scope:**
- Six-panel storyboard batches as the default unit.
- Follow-up batches when a video needs more scenes.
- Style cards that define visual grammar, shot rhythm, caption treatment, audio assumptions, and storyboard needs.
- Storyboard QA before video generation.
- Clear rules for when to use storyboard panels, real captures, proof cards, talking heads, b-roll, or text-first motion.

**Out of scope for this checkpoint:**
- Fully automated trend scraping.
- Posting automation.
- Remotion migration.
- Model-by-model quality benchmarking beyond the current POC findings.

**Acceptance criteria:**
- A style card can specify how storyboards should look and how many panels are needed.
- A video plan can be split into storyboard batches of up to 6 panels.
- Each panel has a role, source/provenance requirement, motion intent, and generation route.
- The system has a clear rule for creating additional batches instead of forcing too much into one image.

---

## Core Principle

The storyboard is not just concept art. It is the contract between creative direction and generation.

Every storyboard panel should answer:
- What beat does this panel serve?
- Is it decorative, claim-bearing, or proof-bearing?
- Does it need a real source underneath it?
- What should the video model preserve?
- What motion should be added after the still is generated?
- Where must captions and UI-safe areas remain clear?

---

## Storyboard Unit

**Default:** 6 panels per storyboard generation.

Six panels is the default because it gives enough coverage for a 15-35 second video without creating an overloaded image prompt. It also maps cleanly to common short-form structures:

| Video length | Typical panel count | Batches |
|---|---:|---:|
| 15-20s | 4-6 panels | 1 |
| 20-35s | 6-10 panels | 1-2 |
| 35-60s | 10-16 panels | 2-3 |

**Panel layout:** 3 columns x 2 rows in one 16:9 storyboard sheet.

Each panel is designed as a vertical 9:16 crop. The full storyboard image stays 16:9 for model reliability, but every panel must preserve a vertical composition.

---

## When To Generate Another Batch

Create a new storyboard batch when any of these are true:
- More than 6 panels are needed.
- The video moves to a new location, cast, or visual mode.
- A new character must be introduced.
- A proof-bearing panel needs a separate deterministic treatment.
- The panel prompt is becoming a paragraph of competing requirements.
- The style reference changes mid-video.

Do not cram a whole video into one storyboard image. A crowded storyboard image reduces consistency and makes panel extraction less reliable.

---

## Style Card Contract

Every popular-video style gets a style card. A style card is the reusable instruction set that keeps videos in that style recognizable.

In the POC, style cards live in `rally-poc/style_cards/` and storyboard plans should reference them with `style_id`. The first locked card is `psyop_anime_90s`, which captures the April 26 Glasswing lessons around likeness review, direct still-to-lip-sync routing, dialogue hard cuts, and proof-card determinism.

```json
{
  "style_id": "psyop_anime_90s",
  "display_name": "PsyopAnime-inspired 90s anime drama",
  "reference_notes": [
    "Character-driven scenes instead of explainer narration",
    "Extreme eye close-ups for dramatic beats",
    "Japanese dialogue with English subtitles",
    "Dark 90s cel-shaded anime, cinematic shadows"
  ],
  "visual_grammar": {
    "aspect_ratio": "9:16",
    "storyboard_layout": "3x2_on_16x9_sheet",
    "palette": ["deep blue", "red warning glow", "cold monitor light"],
    "camera": ["locked close-up", "slow push-in", "wide establishing shot"],
    "texture": ["cel shading", "film grain", "hard shadow shapes"]
  },
  "story_structure": [
    "hook",
    "discovery",
    "conflict",
    "proof",
    "decision",
    "payoff"
  ],
  "caption_treatment": {
    "position": "bottom_safe_area",
    "style": "yellow text with black backing",
    "max_lines": 2
  },
  "audio": {
    "voice_mode": "character_dialogue",
    "language": "ja",
    "music": "dark dramatic bed"
  },
  "generation_rules": {
    "default_storyboard_batch_size": 6,
    "prefer_eye_closeups_over_lipsync": true,
    "avoid_mouth_shots_unless_lipsync_required": true,
    "proof_panels_must_be_source_backed": true
  }
}
```

---

## Panel Contract

Each storyboard panel should be explicit enough that a planner can route it.

```json
{
  "panel_id": "p03",
  "beat": "The board realizes the model can chain exploits",
  "role": "conflict",
  "shot_type": "concept_hero",
  "claim_type": "decorative",
  "source_requirement": "none",
  "characters": ["dario", "general"],
  "composition": "medium close-up, Dario half in shadow, red monitor glow behind him",
  "motion_intent": "slow push-in, subtle eye movement, locked camera",
  "caption_safe_area": "bottom 18 percent clear",
  "video_route": "NB2_STORYBOARD_PANEL_TO_SEEDANCE_I2V",
  "fallback_route": "NB2_STILL_WITH_ASSEMBLY_MOTION"
}
```

### Claim Types

| Claim type | Meaning | Allowed generation |
|---|---|---|
| `decorative` | Mood, metaphor, atmosphere, cinematic glue | Fully generative |
| `interpretive` | Opinion or dramatized framing | Generative, with no fake evidence |
| `claim_bearing` | Makes a factual claim viewers may believe | Must be source-backed or deterministic |
| `proof_bearing` | Evidence, stat, quote, output, repo metadata | Never fake; use real source data |

### Source Requirements

| Source requirement | Use when | Examples |
|---|---|---|
| `none` | Pure style, emotion, b-roll | energy burst, dark lab, eye close-up |
| `reference_only` | Needs character or object consistency | real photo to anime character |
| `source_backed` | Makes a factual claim | repo stars, release quote, benchmark number |
| `deterministic_render` | Text must be exact | proof card, comparison card, stat card |

---

## Routing Rules

| Panel situation | Route |
|---|---|
| Decorative + motion-critical | NB2 storyboard panel -> Seedance I2V, or Seedance T2V if no continuity needed |
| Decorative + consistency-critical | NB2 storyboard panel using reference images -> Seedance I2V |
| Claim-bearing + readability-critical | deterministic proof card or source-backed NB2 still; I2V only if text is preserved |
| Claim-bearing + motion-critical | animate source-backed image with I2V; fall back to still + assembly motion |
| Talking character | use storyboard panel + short VO line; prefer eye close-up unless lip sync is required |
| Likeness-critical talking character | source-backed NB2 still -> lip sync directly; avoid video-model I2V before lip sync unless identity drift is acceptable |
| Trend format depends on text overlay | render text in assembly or deterministic card, not T2V text |
| Real product/demo moment | real capture first; generated concept shot only if clearly non-literal |

---

## Storyboard QA

Storyboard QA happens before video generation. It is cheaper to reject a storyboard panel than to discover after video generation that the panel cannot work.

Pass criteria:
- Every panel has one clear beat.
- Characters remain recognizable across panels.
- Real-person characters use source-backed reference images before video generation.
- Likeness-critical panels pass a still-image review before any video/lipsync spend.
- Likeness-critical talking-head panels preserve the approved still as the lip-sync source. Do not route through Seedance I2V first unless motion is more important than identity.
- Conversational scenes preserve shared room geography across reverse shots.
- Each vertical crop has a strong composition.
- Bottom caption safe area is clear unless the style card says otherwise.
- Proof-bearing panels are source-backed or deterministic.
- No generated panel presents fake UI, fake stats, or fake quotes as evidence.
- Motion intent is compatible with the panel image.
- The panel sequence has enough visual variation.

Reject reasons:
- `unclear_beat`
- `crowded_panel`
- `weak_hook`
- `character_drift`
- `likeness_mismatch`
- `scene_continuity_break`
- `unsafe_caption_area`
- `fake_evidence_risk`
- `bad_vertical_crop`
- `motion_mismatch`
- `style_mismatch`

---

## Video Generation Polish Rules

The April 26 anime retry showed that motion intent must be concrete. Generic phrases like "cinematic" or "dramatic" do not reliably produce motion, and "locked camera" can accidentally produce a beautiful frozen shot.

For every generated video shot, include at least one explicit motion source:
- Camera motion: slow push-in, dolly down table, handheld drift, parallax slide.
- Character motion: blink, eye dart, head turn, shoulder tension, breath movement.
- Environment motion: flickering monitor light, scrolling reflections, pulsing warning screen, moving shadows.
- Graphic motion: orbiting code, waveform sweep, glitch pulse, data ribbon movement.

Avoid static phrasing unless the shot is intentionally still and will be animated deterministically in assembly. If a generated shot fails local eval for freeze or low motion, regenerate only that shot and downstream derived assets.

Current implementation support:
- `rally-poc/pipeline/run_pipeline.py --regenerate-shot <name>` resets selected shots.
- `--regenerate-step video` resets video, normalized clips, and lipsync outputs.
- `--regenerate-step image` resets storyboard/image-derived assets plus downstream video/lipsync.
- `--stop-after phase1` lets the operator review reference-backed stills before spending on video or lip sync.

### Real-Person Likeness Rule

If a style depicts a real public figure, the planner must mark those shots as likeness-critical and attach a source-backed reference image. Descriptive prompts alone are not enough. The pipeline should review likeness in this order:

1. Source photo quality: clear face, current enough for the story, usable provenance.
2. Generated still likeness: recognizable hair, face shape, glasses, age, and silhouette.
3. Video preservation: motion does not drift the person into a generic character.
4. Style preservation: the likeness pass does not break the target genre look.

### Same-Scene Continuity Rule

When two characters are in conversation, the planner must describe the room as a shared location, not as separate atmospheric backgrounds. Reverse shots should repeat anchor details: the same table, same screen, same window/blinds, same light direction, and matching color palette. If a character cutaway needs a different location, the shot list must explicitly mark it as a new scene.

---

## Sample 30s Plan

```json
{
  "video_id": "glasswing_anime_short_001",
  "target_duration_s": 30,
  "style_id": "psyop_anime_90s",
  "storyboard": {
    "batch_size": 6,
    "batches": [
      {
        "batch_id": "b01",
        "purpose": "complete 30s story",
        "panels": ["p01", "p02", "p03", "p04", "p05", "p06"]
      }
    ]
  },
  "panels": [
    {
      "panel_id": "p01",
      "role": "hook",
      "shot_type": "concept_hero",
      "claim_type": "decorative",
      "source_requirement": "none",
      "beat": "Researcher sees red vulnerability alerts reflected in her eyes"
    },
    {
      "panel_id": "p02",
      "role": "discovery",
      "shot_type": "talking_head",
      "claim_type": "interpretive",
      "source_requirement": "reference_only",
      "beat": "Researcher whispers that the model found over a thousand zero-days"
    },
    {
      "panel_id": "p03",
      "role": "conflict",
      "shot_type": "talking_head",
      "claim_type": "interpretive",
      "source_requirement": "reference_only",
      "beat": "Dario warns the board that the model can break every system"
    },
    {
      "panel_id": "p04",
      "role": "opposition",
      "shot_type": "talking_head",
      "claim_type": "interpretive",
      "source_requirement": "none",
      "beat": "General argues they must use it before someone else does"
    },
    {
      "panel_id": "p05",
      "role": "proof",
      "shot_type": "proof_card",
      "claim_type": "proof_bearing",
      "source_requirement": "deterministic_render",
      "beat": "Proof card shows previous model: 2 exploits, Mythos: 181"
    },
    {
      "panel_id": "p06",
      "role": "payoff",
      "shot_type": "payoff",
      "claim_type": "interpretive",
      "source_requirement": "none",
      "beat": "The red AI eye watches as the researcher realizes the paradox"
    }
  ]
}
```

---

## Active Backlog

**Now:**
- Six-panel storyboard batch planner.
- Style card format.
- Storyboard QA checklist.
- Subtitle safe-area handling.

**Next:**
- Automated panel slicing from 3x2 storyboard sheets.
- Whisper word-level subtitle timing.
- Style-card library for 3-5 popular formats.
- Proof-card renderer for exact source-backed text.

**Later:**
- Trend ingestion.
- Automated reference video analysis.
- Remotion migration.
- Posting automation and measurement ingestion.
