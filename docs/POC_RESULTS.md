# Rally POC Results

**Date:** April 8-9, 2026
**Duration:** ~1 day
**Videos Produced:** 3 (across 3 iterations of the pipeline)
**Total Cost:** ~$7-8 (fal.ai images + Segmind video gen + ElevenLabs free tier)

---

## Videos Produced

| # | Project | Style | Duration | Final Version |
|---|---------|-------|----------|---------------|
| 1 | OpenScreen (free Screen Studio alternative) | Explainer | 61s | `project-a/final/video1_explainer_sd2.mp4` |
| 2 | OpenScreen | News Flash | 44s | `project-a/final/video2_newsflash_sd2.mp4` |
| 3 | Project Glasswing / Claude Mythos | Hot Take | 85s | `project-b/final/video3_hottake_sd2.mp4` |

Each video went through 3 iterations:
- **v1**: NB2 still images + Ken Burns zoom (functional but static)
- **v2**: Seedance 1.5 Pro video clips (text destroyed, unusable for text-heavy shots)
- **sd2**: Seedance 2.0 Fast video clips (text preserved, significant quality upgrade)

---

## Toolchain Findings

### Image Generation

| Model | Result | Notes |
|-------|--------|-------|
| **FLUX Schnell (fal.ai)** | REJECTED | Cannot render text. Every image had garbled/nonsense text. Unusable for infographics, stats cards, UI mockups. |
| **Nano Banana 2 (fal.ai)** | ADOPTED | Excellent text rendering (character-by-character validation). Nails infographics, dashboards, comparison cards, UI mockups, news graphics. $0.08/image at 1K. |

**Key finding:** NB2 is built on Gemini 3.1 Flash (autoregressive, not diffusion). This is why it handles text — it reasons about composition before rendering.

**NB2 settings that work:**
- `aspect_ratio: "9:16"` for vertical video
- `resolution: "1K"` (sufficient quality, fast)
- `output_format: "png"` (higher quality than jpeg for downstream I2V)

### Video Generation

| Model | Text Preservation | Motion Quality | Cost | Via | Verdict |
|-------|------------------|---------------|------|-----|---------|
| **Seedance 1.5 Pro** | BAD — destroys text | Good for abstract | $0.13/clip | fal.ai | DROPPED |
| **Seedance 2.0 Fast** | EXCELLENT | Excellent | $0.27/clip | Segmind | ADOPTED (primary) |
| **Kling 3.0 Pro** | EXCELLENT (with cfg_scale 0.3) | Good | $0.56/clip | fal.ai | ADOPTED (secondary) |
| **Kling 2.5 Turbo Pro** | Decent | Good | $0.35/clip | fal.ai | Available but not needed |

**Critical finding:** Video generation models (as of April 2026) still cannot reliably generate text from scratch (T2V). They CAN preserve text from source images (I2V) if the model is good enough. Seedance 2.0 and Kling 3.0 both handle this well. Seedance 1.5 does not.

**Seedance 2.0 access:** ByteDance suspended overseas API on March 15, 2026 (Hollywood copyright disputes). Accessible via Segmind (`api.segmind.com/v1/seedance-2.0-fast`). Blocked on fal.ai for US users.

**Shot routing rules (validated):**

| Shot Content | Best Approach | Why |
|-------------|---------------|-----|
| Text-heavy infographic (stats, comparisons, proof cards) | NB2 still (Ken Burns zoom) OR I2V with Seedance 2.0 | Text must be readable. I2V with SD2.0 preserves text well. Still is safest fallback. |
| Atmospheric/abstract (server rooms, particles, energy effects) | T2V with Seedance 2.0 | No text to preserve. Motion is the point. |
| UI/app screenshot | I2V with Seedance 2.0 | Preserves UI layout and text. Adds subtle animation. |
| Logo/brand reveal | I2V with Seedance 2.0 | Simple graphics animate beautifully. Text preserved. |
| Code editor / programming | T2V with Seedance 2.0 | Looks realistic but code is pseudo-gibberish. Acceptable because viewers don't read code in short-form. |

**Kling 3.0 Pro settings for text preservation:**
- `cfg_scale: 0.3` (low motion)
- `negative_prompt: "distorted text, warped text, illegible text, blurry, morphing, jitter"`

**Seedance 2.0 Fast settings:**
- `duration: 5`
- `resolution: "720p"`
- `aspect_ratio: "9:16"`
- `generate_audio: false`
- `seed: -1`

**Known quirk:** Seedance 2.0 (ByteDance model) occasionally generates Chinese text in T2V shots (especially payment/subscription UIs). Not an issue for I2V where text comes from source image.

### Voiceover

| Provider | Voice | Result | Notes |
|----------|-------|--------|-------|
| **ElevenLabs** | Liam (`TX3LPaxmHKxFdv7VOQHJ`) | ADOPTED | Clear, energetic, good for tech explainers. Free tier sufficient for POC. |

**Settings:**
- `model_id: "eleven_multilingual_v2"`
- `stability: 0.8` (higher stability for proper nouns like "Mythos")
- `similarity_boost: 0.8`
- `style: 0.2-0.4` (lower for deliberate pacing, higher for energetic)

**Pronunciation finding:** Unusual words (e.g., "Mythos") require higher stability (0.8 vs default 0.5). Multiple phonetic spellings were tested; the original word with high stability worked best.

### Assembly

**Tool:** FFmpeg (command-line, no CapCut needed for POC)

**Key techniques:**
- `tpad=stop=-1:stop_mode=clone` — freeze last frame when VO is longer than video clip (most clips are 5s, most VO segments are 8-15s)
- `scale=1080:1920` — upscale 720p Seedance output to 1080p for final
- `zoompan` — Ken Burns effect for NB2 still shots
- `concat` demuxer — join all shots into final video
- `-shortest` — trim to shorter of video/audio

**What's missing (for production pipeline):**
- Transitions between shots (currently hard cuts)
- Background music bed
- Animated text overlays / captions
- Proper timing alignment (VO pacing vs visual beats)

### Eval Process

**Mandatory step discovered during POC.** Without frame-by-frame eval, broken shots ship undetected.

**Process:**
1. Extract one frame from the midpoint of each shot using `ffmpeg -ss {time} -frames:v 1`
2. Visually inspect each frame for: text legibility, visual coherence, match to script intent
3. Rate each shot PASS / MIXED / FAIL
4. Rebuild failed shots before final assembly

**Failure modes caught by eval:**
- Seedance 1.5 destroying text in I2V shots
- FFmpeg crop math putting real screenshot off-screen (Shot 2, v1)
- Frozen frame showing wrong shot at wrong timestamp

---

## Cost Breakdown

### Per-Video Cost (Seedance 2.0 pipeline)

| Component | Count per Video | Unit Cost | Total |
|-----------|----------------|-----------|-------|
| NB2 images | 3-5 | $0.08 | $0.24-0.40 |
| Seedance 2.0 Fast clips | 3-5 | $0.27 | $0.81-1.35 |
| ElevenLabs VO | 5-7 segments | Free tier | $0.00 |
| **Total per video** | | | **$1.05-1.75** |

### POC Total Spend

| Provider | Spend | What |
|----------|-------|------|
| fal.ai | ~$2-3 | FLUX images (discarded), NB2 images, Seedance 1.5 clips (discarded), Kling tests |
| Segmind | ~$4-5 | Seedance 2.0 Fast clips (15 final + 1 test) |
| ElevenLabs | $0 | Free tier |
| **Total** | **~$7-8** | 3 finished videos + extensive model testing |

**Projected cost at 30-50 videos/week:** $31-88/week ($1.05-1.75 per video). Well under the $5/video cost guard.

---

## Architecture Implications

### Changes to ARCHITECTURE.md routing

1. **Default image model:** Nano Banana 2 (not FLUX)
2. **Default video model:** Seedance 2.0 Fast via Segmind (not Seedance 1.5 via fal.ai)
3. **Fallback video model:** Kling 3.0 Pro via fal.ai
4. **Shot routing must consider text content** — the planner needs to classify each shot as text-heavy vs abstract and route accordingly
5. **Eval step is mandatory** — add to pipeline between assembly and review

### New provider: Segmind

Seedance 2.0 is only accessible via Segmind for US users. This adds a second API provider alongside fal.ai:
- **fal.ai**: NB2 images, Kling video (fallback), file uploads
- **Segmind**: Seedance 2.0 video (primary)

### Assembly upgrade path

Current FFmpeg assembly is functional but basic. For production:
- **Remotion** for programmatic assembly with transitions, animated text, timing control
- Or continue FFmpeg with more sophisticated filter chains
- Background music from licensed library (not implemented in POC)

### Pipeline timing

| Step | Time (per video) |
|------|-----------------|
| NB2 image generation | ~10s per image (3-5 images = 30-50s) |
| Seedance 2.0 clip generation | ~90-110s per clip, parallelizable (3-5 clips = ~2 min with batching) |
| ElevenLabs VO generation | ~2-3s per segment |
| FFmpeg assembly | ~10s |
| Eval (frame extraction + review) | ~30s automated, 1-2 min human review |
| **Total** | **~5-7 min per video** (excluding human review) |

At 30-50 videos/week, that's 2.5-6 hours of generation time (parallelizable).

---

## What Worked

1. **Nano Banana 2 for images** — text rendering is a game-changer for infographic-style content
2. **Seedance 2.0 for video** — massive upgrade from 1.5, preserves text in I2V, cinematic T2V
3. **ElevenLabs Liam** — natural, energetic, good for tech content
4. **Shot-level asset routing** — different models for different shot types based on content
5. **Eval before ship** — caught every major failure before it went into final video
6. **FFmpeg assembly** — no need for CapCut or Remotion for POC-quality output
7. **Parallel generation** — batching 5 clips at a time, all 15 in ~6 minutes

## What Didn't Work

1. **FLUX for images** — cannot render text, wasted time before switching to NB2
2. **Seedance 1.5 for text-heavy I2V** — destroyed all text, wasted a full rebuild cycle
3. **T2V for specific UI/screen content** — video models generate plausible-looking but incorrect interfaces. Only use for atmospheric/abstract.
4. **Seedance 2.0 on fal.ai** — blocked for US users. Required finding Segmind as alternative provider.
5. **Chinese text in Seedance 2.0 T2V** — ByteDance model bias, occasionally generates Chinese UI text in T2V (not I2V)

## Open Questions for Next Phase

1. **Background music** — licensed library needed. Not tested in POC.
2. **Transitions** — hard cuts work but feel amateur. Need cross-dissolves or motion transitions.
3. **Captions/subtitles** — research showed 85% watch muted. Need burned-in animated captions.
4. **Posting to TikTok** — haven't posted any videos yet. Need account + engagement data.
5. **Remotion templates** — should we build reusable templates for each style?
6. **Seedance 2.0 Standard vs Fast** — Standard ($0.40) may produce better motion. Worth testing.
7. **Retry strategy** — when I2V drifts values (e.g., star count 26,100 → 23,877), should we retry or accept?

---

## File Locations

```
rally-poc/
  project-a/                          # OpenScreen
    assets/                           # NB2 images, FLUX images (legacy), test clips
    audio/                            # ElevenLabs VO segments
    final/
      video1_explainer_sd2.mp4        # FINAL - Explainer style
      video2_newsflash_sd2.mp4        # FINAL - News Flash style
    script-v1-explainer-v2.md         # Latest script (mixed media)
    script-v2-newsflash-v2.md
    notes.md
  project-b/                          # Glasswing
    assets/
    audio/
    final/
      video3_hottake_sd2.mp4          # FINAL - Hot Take style
    script-v3-hottake-v2.md
    notes.md
```

## API Keys (stored in .env)

| Provider | Key Variable | Purpose |
|----------|-------------|---------|
| fal.ai | `FAL_KEY` | NB2 images, Kling video, file uploads |
| ElevenLabs | `ELEVENLABS_API_KEY` | Voiceover generation |
| Segmind | `SEGMIND_API_KEY` | Seedance 2.0 video generation |
