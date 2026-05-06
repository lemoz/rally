# Rally v1: System Architecture

## Design Principles

**One pipeline, not separate lanes.** Every video flows through the same structured plan. The pipeline supports multiple tools, selected per shot by an agentic planner.

**Stylized by default, anchored by provenance.** These are vertical short-form videos, not raw product demos. Visual treatment is stylized. But every factual video includes 1-2 **proof anchors** — real UI moments, real stats, real quotes, real source cards. No "cool fake tech vibes" without a source of truth underneath.

**Not "one frontier model does everything."** The planner decomposes the video into shots and picks the right tool for each shot.

**Not "pure template-only."** Creative content is agentic. Assembly is deterministic.

**Current POC stack:** NB2 for images/storyboards, Seedance 2.0 Fast via Segmind for video, ElevenLabs for voice, RunComfy for lip sync, FFmpeg for deterministic assembly, and local `eval.py` for motion/freeze QA. Remotion remains the likely production assembly layer, but FFmpeg is sufficient for current POC iteration.

---

## Video Plan Structure

The unit of work is a **video plan**. One plan per video asset.

```
project brief + style card
    → script
        → storyboard plan (when the style needs generated visual continuity)
            → storyboard batch prompts (6 panels each)
                → panel review / storyboard QA
        → shot list (with tool assignment per shot)
            → asset generation (parallel, per shot)
                → deterministic assembly
                    → QA scoring
                        → human review
                            → publish packet
```

---

## 0. Storyboard Planning Layer

Storyboard generation is now a first-class planning layer for styles that depend on visual continuity, character consistency, or strong genre imitation. The current contract lives in [`STORYBOARD_PIPELINE_V2.md`](./STORYBOARD_PIPELINE_V2.md).

**Default unit:** 6 panels per storyboard generation.

**Default layout:** 3 columns x 2 rows on a 16:9 storyboard sheet. Each panel must still compose as a vertical 9:16 crop.

**When to use storyboard batches:**
- Anime, cinematic, character-driven, meme-story, or trend formats where visual continuity matters.
- Any style where a single generated shot depends on previous shot identity, location, or composition.
- Any video that needs a repeatable visual grammar copied from a reference format.

**When not to use storyboard batches:**
- Simple text-first explainers.
- Deterministic proof cards.
- Raw product demos or screen recordings.
- One-off b-roll where continuity does not matter.

**Extension rule:** Generate another storyboard batch instead of cramming too much into one sheet when the video needs more than 6 panels, changes location, introduces a new character, changes visual mode, or mixes proof-bearing panels with cinematic panels.

**Implementation hook:** `rally-poc/pipeline/storyboard.py` turns a structured storyboard plan into reviewable six-panel batch prompts before any vendor call is made.

---

## 1. Shot Taxonomy

| Shot Type | Purpose | Stylized? | Must Be Factual? |
|-----------|---------|-----------|-------------------|
| **hook** | First 1-2 seconds. Grabs attention. | Yes — maximum style | No |
| **context** | Sets up the problem or background | Yes | No, but claims should be grounded |
| **concept_hero** | Stylized showcase of the idea/product/vision | Yes — cinematic, energetic | No |
| **demo_hero** | The real thing. Product proof. | Lightly styled | Yes — real capture preferred |
| **evidence** | Hard proof. Stats, benchmarks, output. | No — factual presentation | Yes — must be real data |
| **proof_card** | Factual grounding when screenshots unavailable | Branded template | Yes — real data, rendered as card |
| **talking_head** | Character delivers a line on camera | Yes — generated character | No |
| **b_roll** | Atmosphere, energy, visual texture | Yes — maximum style | No |
| **payoff** | The "so what." Result, CTA, implication. | Yes | No |

**Not a shot type:** `transition`. Transitions are assembly instructions (cuts, zooms, glitch effects) applied between shots. They don't generate assets.

**Proof anchor rule:** Every factual video must include at least 1 shot of type `evidence`, `demo_hero`, or `proof_card`. The planner enforces this — a shot list without a proof anchor is invalid.

### Typical Shot Sequences by Style

**Explainer (30s):**
```
hook (1.5s) → context (4s) → concept_hero (8s) → evidence (5s) → concept_hero (6s) → payoff (3s)
```

**News flash (20s):**
```
hook (2s) → proof_card (3s) → concept_hero (8s) → evidence (4s) → payoff (3s)
```

**Hot take (25s):**
```
hook (2s) → context (5s) → concept_hero (6s) → b_roll (3s) → proof_card (4s) → payoff (3s)
```

**Before/after (30s):**
```
hook (1.5s) → demo_hero[before] (6s) → context (4s) → demo_hero[after] (8s) → evidence (5s) → payoff (3s)
```

---

## 2. Routing Rules

The planner assigns a tool to each shot based on type and project context.

### Default Routes

| Shot Type | Primary Tool | Why |
|-----------|-------------|-----|
| **hook** | FLUX image → Kling image-to-video | Needs visual punch + motion. Style-first. |
| **context** | FLUX image → Kling image-to-video | Stylized explanation. Motion adds energy. |
| **concept_hero** | FLUX image → Kling image-to-video | Cinematic showcase. Full creative freedom. |
| **demo_hero** | Playwright screen recording | Real product. Factual. Lightly styled in assembly. |
| **evidence** | Playwright screenshot | Must be real. No generation. |
| **proof_card** | Rendered from structured data (Remotion template) | Real data, deterministic visual. Not generated. |
| **talking_head** | NB2 character still → RunComfy lip sync | Optional. Only when style card calls for it. Preserve likeness before adding motion. |
| **b_roll** | Kling text-to-video (no reference image needed) | Pure atmosphere. Cheapest to generate. |
| **payoff** | FLUX image → Kling image-to-video | Style-first. Can also be text card from assembly. |

### Fallback Routes

When the primary tool fails or is unavailable:

| Shot Type | Fallback 1 | Fallback 2 | Last Resort |
|-----------|-----------|-----------|-------------|
| **hook** | Seedance 2.0 image-to-video | Static FLUX image + motion in assembly | Bold text card (assembly) |
| **context** | Static FLUX image + Ken Burns | Proof card with context data | Skip shot, extend adjacent |
| **concept_hero** | Pika Pikaframes (if keyframes exist) | Seedance 2.0 | Static image + motion overlay |
| **demo_hero** | Manual screenshot (operator provides) | Proof card with real data | Skip shot — do not fake |
| **evidence** | Proof card from same data | Manual screenshot | Skip shot — do not fake evidence |
| **proof_card** | N/A — deterministic, should not fail | — | — |
| **talking_head** | Voiceover only (drop visual character) | — | — |
| **b_roll** | Seedance 2.0 text-to-video | Stock footage / assembly-generated | Skip shot, tighten pacing |
| **payoff** | Text card (assembly) | Static FLUX image | — |

### Hard Rules

1. **Evidence and proof_card shots are never AI-generated.** Evidence comes from screenshots. Proof cards come from structured data rendered deterministically.
2. **If real capture fails for demo_hero, fall back to proof_card, not to image gen.** Don't generate fake product screenshots.
3. **Talking_head is opt-in per style card.** If lip sync quality is poor on a given attempt, drop to voiceover-only. Don't ship bad lip sync.
4. **Likeness-critical talking heads do not route through video I2V before lip sync by default.** The April 26 Dario retry showed that video I2V can drift a source-backed face. Use the approved still as the lip-sync source unless motion matters more than identity.
5. **Transitions are always assembly instructions.** Never spend a model call on a transition.
6. **The planner can upgrade a route** (e.g., use Pika Pikaframes instead of Kling for a specific shot) but cannot downgrade evidence/proof shots to generated.

---

## 3. Retry & Fallback Rules

### Per-Shot Retry Budgets

| Tool | Max Retries | Retry Trigger | After Budget Exhausted |
|------|------------|---------------|----------------------|
| FLUX image gen | 3 | Artifacts, wrong composition, off-brief | Use fallback route |
| Kling video gen | 2 | Artifacts, motion issues, subject inconsistency | Try Seedance. If both fail, use static image + assembly motion |
| Seedance video gen | 2 | Same as Kling | Use static image + assembly motion |
| Pika Pikaframes | 2 | Interpolation artifacts, pacing issues | Fall back to Kling single-shot per keyframe |
| Playwright capture | 1 | Page load failure, auth wall, layout broken | Manual capture or proof_card. Do not retry — flaky captures don't get better. |
| ElevenLabs TTS | 2 | Audio artifacts, wrong pacing | Retry with adjusted parameters |
| Sync Labs lip sync | 1 | Poor sync quality, visual artifacts | Drop talking_head, use voiceover-only |

### Per-Video Retry Budget

After assembly + QA, if the video scores below threshold:

| QA Round | Action |
|----------|--------|
| Round 1 fail | QA model identifies weakest shots. Planner regenerates those specific shots (up to 3 shots). Reassemble. |
| Round 2 fail | Flag for human review with QA notes. Human decides: regen specific shots, change style, or kill the video. |
| Round 3 | No round 3. If two full QA cycles can't fix it, the project × style pairing doesn't work. Log it and move on. |

### Cost Guards

| Guard | Threshold | Action |
|-------|-----------|--------|
| Per-video generation cost | >$5 | Alert. Likely too many retries. Review tooling. |
| Per-video total attempts | >15 shots attempted | Kill. The plan is bad, not the tools. |
| Daily API spend | >$50 | Pause generation. Review what's burning money. |

---

## 4. System Architecture

### Components

```
┌──────────────────────────────────────────────────────────────┐
│                     PLANNER (Claude API)                     │
│                                                              │
│  Inputs:  project brief, style card                          │
│  Outputs: script, shot list, tool assignments, retry budget  │
│                                                              │
│  Enforces: proof anchor rule, shot sequence validity,        │
│            retry budgets, cost estimates                     │
│  After QA fail: receives QA notes, regenerates weak shots    │
└──────────────────────────┬───────────────────────────────────┘
                           │
              shot list + tool assignments
                           │
                           v
┌──────────────────────────────────────────────────────────────┐
│                    ROUTER / EXECUTOR                         │
│                                                              │
│  For each shot in the plan:                                  │
│    1. Dispatch to assigned tool                              │
│    2. Track attempt in SQLite                                │
│    3. On failure: retry or escalate to fallback              │
│    4. On success: store asset reference                      │
│                                                              │
│  Parallel execution for independent shots.                   │
│  Sequential only where shots depend on each other.           │
└───────┬──────────┬──────────┬──────────┬─────────────────────┘
        │          │          │          │
        v          v          v          v
┌────────────┐┌─────────┐┌──────────┐┌─────────────┐
│   REAL     ││ IMAGE   ││ VIDEO    ││ LIP SYNC    │
│   CAPTURE  ││ GEN     ││ GEN      ││ (optional)  │
│            ││         ││          ││             │
│ Playwright ││ FLUX    ││ Kling 3.0││ Sync Labs   │
│            ││ (fal.ai)││ (fal.ai) ││ API         │
│            ││         ││          ││             │
│            ││         ││ Seedance ││             │
│            ││         ││ (fal.ai) ││             │
│            ││         ││          ││             │
│            ││         ││ Pika     ││             │
│            ││         ││ (fal.ai) ││             │
└─────┬──────┘└────┬────┘└─────┬────┘└──────┬──────┘
      │            │           │             │
      └────────────┴───────────┴─────────────┘
                        │
                  asset references
                        │
                        v
┌──────────────────────────────────────────────────────────────┐
│                   TTS (ElevenLabs)                            │
│                                                              │
│  Script → voiceover audio track                              │
│  One voice per style card (consistent)                       │
│  Separate from video gen — always controllable               │
└──────────────────────────┬───────────────────────────────────┘
                           │
                           v
┌──────────────────────────────────────────────────────────────┐
│               ASSEMBLY (Remotion — deterministic)            │
│                                                              │
│  Inputs: shot assets, voiceover, shot list with timings      │
│                                                              │
│  Does:                                                       │
│    - Sequence shots per shot list                            │
│    - Apply transitions (cuts, zooms, effects)                │
│    - Layer voiceover track                                   │
│    - Layer music bed                                         │
│    - Add captions / text overlays                            │
│    - Add branding (if applicable)                            │
│    - Render proof_card shots from structured data            │
│    - Export 9:16 at platform quality targets                 │
│                                                              │
│  Does NOT:                                                   │
│    - Make creative decisions                                 │
│    - Choose or modify assets                                 │
│    - Retry anything (if an asset is missing, it fails loud)  │
└──────────────────────────┬───────────────────────────────────┘
                           │
                           v
┌──────────────────────────────────────────────────────────────┐
│                    QA (Claude or Gemini Vision)               │
│                                                              │
│  Reviews assembled video against rubric:                     │
│    - Hook strength (would you stop scrolling?)               │
│    - Pacing (does it drag or rush?)                          │
│    - Visual clarity (artifacts, readability)                 │
│    - Audio sync (voiceover matches visuals)                  │
│    - Proof anchor present and legible                        │
│    - Brand/style consistency                                 │
│    - Overall score (1-10)                                    │
│                                                              │
│  Output: pass/fail + per-shot notes                          │
│  On fail: notes go back to planner for targeted regen        │
└──────────────────────────┬───────────────────────────────────┘
                           │
                      pass → review queue
                           │
                           v
┌──────────────────────────────────────────────────────────────┐
│                 HUMAN REVIEW (Chris)                          │
│                                                              │
│  Approve / reject (with codified reason) / request regen     │
│  Approved → publish packet assembled                         │
└──────────────────────────┬───────────────────────────────────┘
                           │
                           v
┌──────────────────────────────────────────────────────────────┐
│                   PUBLISH QUEUE                              │
│                                                              │
│  Packet: video file, caption, hashtags, platform notes,      │
│          tracking ID, scheduled window                       │
│  Stored in shared location (Google Drive / Dropbox)          │
│  Friend pulls and posts on their schedule                    │
│  Friend reports back engagement numbers                      │
└──────────────────────────────────────────────────────────────┘
```

### State Model (SQLite)

Every entity has explicit state transitions. No implicit states.

**video_plans**
```sql
CREATE TABLE video_plans (
  id            TEXT PRIMARY KEY,  -- deterministic: hash(project_slug + style_slug + date)
  project_slug  TEXT NOT NULL,
  style_slug    TEXT NOT NULL,
  test_group    TEXT,              -- 'controlled_1', 'controlled_2', 'exploration'
  state         TEXT NOT NULL,     -- see state machine below
  script        TEXT,
  shot_list     TEXT,              -- JSON: ordered array of shot specs
  voiceover_url TEXT,
  audio_strategy TEXT,             -- 'licensed_bed', 'voiceover_only'
  music_url     TEXT,              -- path to licensed track from music_library
  final_video   TEXT,              -- path to assembled video
  qa_score      REAL,
  qa_notes      TEXT,
  review_result TEXT,              -- 'approved', 'rejected'
  reject_reason TEXT,              -- codified reject reason
  retry_round   INTEGER DEFAULT 0,
  total_cost    REAL DEFAULT 0,
  created_at    TEXT NOT NULL,
  updated_at    TEXT NOT NULL
);
```

**shots**
```sql
CREATE TABLE shots (
  id            TEXT PRIMARY KEY,  -- deterministic: hash(plan_id + shot_index)
  plan_id       TEXT NOT NULL REFERENCES video_plans(id),
  shot_index    INTEGER NOT NULL,
  shot_type     TEXT NOT NULL,     -- hook, context, concept_hero, demo_hero, evidence, proof_card, talking_head, b_roll, payoff
  assigned_tool TEXT NOT NULL,     -- flux, kling, seedance, pika, playwright, proof_card_renderer, sync_labs
  prompt        TEXT,
  duration_sec  REAL NOT NULL,
  state         TEXT NOT NULL,     -- planned, generating, generated, failed, fallback, skipped
  asset_url     TEXT,
  attempts      INTEGER DEFAULT 0,
  max_attempts  INTEGER NOT NULL,  -- from retry budget
  cost          REAL DEFAULT 0,
  created_at    TEXT NOT NULL,
  updated_at    TEXT NOT NULL
);
```

**shot_attempts**
```sql
CREATE TABLE shot_attempts (
  id            TEXT PRIMARY KEY,
  shot_id       TEXT NOT NULL REFERENCES shots(id),
  attempt_num   INTEGER NOT NULL,
  tool_used     TEXT NOT NULL,
  prompt_used   TEXT,
  state         TEXT NOT NULL,     -- pending, running, succeeded, failed
  asset_url     TEXT,
  error         TEXT,
  cost          REAL DEFAULT 0,
  duration_ms   INTEGER,
  created_at    TEXT NOT NULL
);
```

**publish_packets**
```sql
CREATE TABLE publish_packets (
  id              TEXT PRIMARY KEY,
  plan_id         TEXT NOT NULL REFERENCES video_plans(id),
  video_url       TEXT NOT NULL,
  caption         TEXT,
  hashtags        TEXT,              -- JSON per platform
  platform_notes  TEXT,
  scheduled_window TEXT,
  state           TEXT NOT NULL,     -- queued, sent_to_friend, posted, measured
  created_at      TEXT NOT NULL
);
```

**engagement**
```sql
CREATE TABLE engagement (
  id            TEXT PRIMARY KEY,
  packet_id     TEXT NOT NULL REFERENCES publish_packets(id),
  platform      TEXT NOT NULL,     -- tiktok, reels, youtube_shorts
  views         INTEGER,
  watch_through REAL,              -- percentage
  likes         INTEGER,
  comments      INTEGER,
  shares        INTEGER,
  saves         INTEGER,
  follower_delta INTEGER,
  reported_at   TEXT NOT NULL
);
```

**assets** *(add by week 2)*
```sql
CREATE TABLE assets (
  id            TEXT PRIMARY KEY,  -- deterministic: hash(project_slug + asset_type + source_url)
  project_slug  TEXT NOT NULL,
  asset_type    TEXT NOT NULL,     -- screenshot, screen_recording, proof_card, flux_image, video_clip, music_track
  source_url    TEXT,              -- original source (project URL, repo URL, etc.)
  file_path     TEXT NOT NULL,     -- local path to asset
  metadata      TEXT,              -- JSON: dimensions, duration, tags, mood/energy (for music)
  created_at    TEXT NOT NULL,
  last_used_at  TEXT
);
```

**music_library**
```sql
CREATE TABLE music_library (
  id            TEXT PRIMARY KEY,
  title         TEXT NOT NULL,
  file_path     TEXT NOT NULL,
  source        TEXT NOT NULL,     -- 'artlist', 'epidemic_sound', etc.
  license       TEXT NOT NULL,     -- license type
  mood          TEXT NOT NULL,     -- hype, chill, dramatic, curious, urgent
  energy        TEXT NOT NULL,     -- low, mid, high
  style_tags    TEXT,              -- JSON: which video styles this pairs with
  duration_sec  REAL NOT NULL,
  use_count     INTEGER DEFAULT 0,
  created_at    TEXT NOT NULL
);
```

### State Machine: video_plans.state

```
brief_created
    → scripted           (script generated)
    → script_failed      (retry or kill)

scripted
    → shot_list_ready    (shot list + tool assignments created)

shot_list_ready
    → generating         (shots dispatched to tools)

generating
    → shots_complete     (all shots resolved: generated, fallback, or skipped)
    → generation_failed  (too many shots failed, over cost guard)

shots_complete
    → assembling         (Remotion rendering)

assembling
    → assembled          (video rendered)
    → assembly_failed    (missing asset, render error)

assembled
    → qa_reviewing       (vision model scoring)

qa_reviewing
    → qa_passed          (score above threshold)
    → qa_failed          (score below threshold → back to planner for shot-level regen)

qa_failed
    → generating         (planner regenerates specific shots, retry_round incremented)
    → killed             (retry_round >= 2, not fixable)

qa_passed
    → review_queued      (waiting for Chris)

review_queued
    → approved           (Chris approves)
    → rejected           (Chris rejects with reason)
    → regen_requested    (Chris wants specific changes → back to planner)

approved
    → packaged           (publish packet assembled)

packaged
    → published          (friend confirmed posted)

published
    → measured           (engagement data received)
```

---

## 5. Audio Strategy

**Default: Licensed instrumental library.** Copyright flags on TikTok/Reels mute or suppress videos, which kills reach. The experiment can't afford that.

### Licensed music library

**Source:** Artlist or Epidemic Sound subscription (~$150-200/yr).

**Library spec:**
- 40-60 instrumental tracks minimum
- Tagged by mood (hype, chill, dramatic, curious, urgent), energy level (low/mid/high), and compatible video styles
- Downloaded manually, stored in local asset library
- Style cards specify mood + energy, assembly picks matching track from `music_library` table
- Refresh monthly — add 10-15 new tracks, retire overused ones

### Audio strategy per style card

Style cards specify one of two options:

- **`licensed_bed`** (default) — Assembly layers a licensed track from the library under the voiceover. Safe for all platforms, no reach risk.
- **`voiceover_only`** — No music bed. Voiceover carries the energy. Works for hot takes, urgent news, some talking-head formats.

### Future option: platform-native trending audio

When Rally has its own audience and posting workflow, trending audio can be added on-platform by the poster using each platform's licensed sound library. This gets the algorithmic boost without copyright risk. Not in v1 scope — requires the poster to make a creative decision per video, which adds friction to the current workflow.

---

## 6. Talking Head Strategy

**Not baseline. Not buried. Reserved exploration volume.**

Talking-head content dominates short-form engagement on every platform. The architecture supports it cleanly (shot type + routing + lip sync tooling). But it adds complexity (character consistency, lip sync quality, uncanny valley risk) that shouldn't gate the core pipeline.

**v1 approach:**
- Reserve ~20% of exploration volume for talking_head experiments
- Track engagement separately to see if it outperforms voiceover-only styles
- For real-person or likeness-critical characters, review the NB2 still before lip sync and use that still directly as the lip-sync source
- If it wins, promote to a standard style in the library
- If lip sync quality is consistently poor, drop it entirely — don't ship uncanny valley

---

## 7. Asset Caching

**Not week-1 critical. Add by week 2.**

At 30-50 videos/week, the same project will appear across multiple videos (same project × different styles in controlled tests, follow-up videos on high-signal projects). Without caching, you re-screenshot and re-generate base images every time.

**Week 2 addition:** `assets` table (see schema below) indexed by project + asset type. Before generating, check if a usable asset already exists. Proof cards and screenshots are the highest-value cache targets — they don't change between style variants of the same project.

---

## Closed Decisions

- [x] **Audio:** Licensed instrumental library as default (Artlist or Epidemic Sound). Voiceover-only as alternative. No copyrighted audio in rendered videos — copyright flags kill reach.
- [x] **Talking head:** Exploration only (~20% of exploration volume). Not baseline. Track engagement separately.
- [x] **Asset caching:** Add `assets` table by week 2. Not week-1 critical.
- [x] **Storyboard unit:** 6-panel batches by default, extended with additional batches when needed.
- [x] **Video gen primary:** Seedance 2.0 Fast via Segmind. Fallback: Kling 3.0 via fal.ai.
- [x] **Image gen:** Nano Banana 2 via fal.ai.
- [x] **TTS:** ElevenLabs (separate from video gen).
- [x] **Assembly:** FFmpeg for POC production; Remotion remains the likely later template system.
- [x] **State tracking:** JSON checkpoints in the POC; SQLite when this leaves POC shape.
- [x] **Lip sync:** Optional for talking_head shots. Current POC path uses RunComfy; provider remains swappable.
- [x] **API providers:** fal.ai for NB2/Kling/file-adjacent work; Segmind for Seedance 2.0 Fast.

## Open Decisions

- [ ] Specific ElevenLabs voice(s) — pick before generating
- [ ] fal.ai account setup + API keys
- [ ] Segmind account setup + API keys
- [ ] RunComfy account setup + API token if talking-head/lip sync remains active
- [ ] Shared folder location for publish queue
- [ ] Artlist vs Epidemic Sound — pick one, subscribe, curate initial instrumental library
- [ ] Hosting for the pipeline itself — local machine? Cloud?
- [ ] Account names for TikTok / IG / YouTube
