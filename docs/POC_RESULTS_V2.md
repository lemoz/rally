# Rally POC Results — Phase 2: Anime Style & Pipeline Refinement

**Date:** April 10-11, 2026
**Building on:** POC Phase 1 (April 8-9)

---

## April 26 Checkpoint: 30s Anime Candidate Pass

**Output:** `rally-poc/output/glasswing_anime_v3/final.mp4`

**Result:** The 33.9s Glasswing anime cut now passes local eval.

| Metric | Before targeted retry | After targeted retry |
|---|---:|---:|
| Overall verdict | FAIL | PASS |
| Passing shots | 4/8 | 8/8 |
| Warning shots | 2/8 | 0/8 |
| Failed shots | 2/8 | 0/8 |
| Avg freeze ratio | 38.5% | 2.8% |

**What changed:**
- Fixed subtitle rendering by moving FFmpeg `drawtext` captions to sidecar `textfile` inputs. Inline text escaping broke on apostrophes and leaked filter syntax into the frame.
- Added bottom safe-area subtitle wrapping: max 2-3 lines, black backing box, large yellow text.
- Added targeted regeneration controls to `rally-poc/pipeline/run_pipeline.py`: `--regenerate-shot` and `--regenerate-step`.
- Added `--stop-after phase1` so likeness-critical stills can be reviewed before video/lipsync spend.
- Retried only the weak shots: `s1b_researcher_eyes`, `s3a_boardroom`, `s3b_dario_speaks`, `s3d_dario_eyes`.
- Updated weak prompts to ask for continuous motion instead of static/locked-camera shots.
- Switched `s3d_dario_eyes` from I2V to T2V because the generated first-frame close-up was visually strong but motion-poor.
- Fixed local reference image handling by uploading local references to GCS before sending them to NB2. Passing local paths was not a valid likeness anchor.

**Key lesson:** Pretty still frames are not enough. Prompts for short-form video need explicit motion instructions: slow push-in, blinking, darting eyes, scrolling reflections, pulsing screens, flickering light, moving shadows, or table reflections. Otherwise the model often returns a beautiful near-still that fails the scroll test.

**Remaining caveat:** Eval still reports 7 hard cuts because dialogue-heavy assembly currently disables crossfades to avoid spoken-word overlap. This is acceptable for the current anime cut, but future non-dialogue styles should re-enable transitions with explicit audio scheduling.

**Likeness caveat:** Motion QA, likeness QA, and style QA are separate. The first passing 30s candidate passed motion/subtitle QA but did not reliably preserve Dario's real appearance. A follow-up pass added a cleaner source-backed Dario reference (`rally-poc/reference/dario_amodei_commons_2023.jpg`) and stopped after phase 1 for still-image review before spending on video. This improved likeness, but the video model pushed Dario shots toward a smoother cartoon/3D look, so the next iteration should treat "preserve 90s anime style while preserving likeness" as its own acceptance gate.

**Scene continuity caveat:** The first boardroom cut made Dario and the General feel like they were in different rooms. The general response prompt was updated to be a reverse shot in the same boardroom with the same long table, red screen, blue overhead light, and table reflections. Future planner output should treat shared-room geography as an explicit continuity constraint.

**April 26 follow-up fix:** The Dario speaking shot now uses `NB2_STILL -> RunComfy lip sync -> deterministic assembly` instead of `NB2 image -> Seedance I2V -> lip sync`. Seedance I2V preserved motion but drifted the reference-backed Dario face into a generic heavyset executive. For likeness-critical talking heads, source-backed still-to-lip-sync is the safer default; use Seedance I2V only when motion matters more than exact identity.

**Dialogue timing fix:** Dialogue-heavy cuts now use `transition_duration: 0.0` unless audio timing is explicitly counterbalanced. Visual crossfades caused spoken lines to overlap because each VO track started at its shot boundary while the previous visual/audio beat was still fading. Lip-sync outputs are also padded slightly beyond VO duration so a spoken line cannot spill into the next shot.

**Style-card lock:** These lessons are now captured in `rally-poc/style_cards/psyop_anime_90s.json` and loaded by the storyboard prompt builder. Future anime plans should reference `style_id: "psyop_anime_90s"` instead of copying style instructions inline.

---

## What We Did

### 1. Built Video Eval System (`rally-poc/eval.py`)
Programmatic QA that extracts start/mid/end frames per shot and detects:
- Frozen frames (pixel diff between consecutive samples)
- Motion duration vs total shot duration
- Hard cuts vs crossfade transitions
- Outputs structured JSON + human-readable report

**Key finding:** The eval caught that our v1 videos were 50-75% frozen frames — most shots were 5s video clips padded with freeze-frame for 8-15s of voiceover. We never would have caught this with manual mid-frame inspection alone.

**Eval upgrade from mentor feedback:** Start/mid/end frames per shot, not just midpoint. Temporal QA for freezes, not just visual QA.

### 2. Fixed Duration Matching
Regenerated all 14 video clips with durations matched to VO length (4s, 6s, 8s, 10s, 12s, 15s) instead of defaulting everything to 5s. Seedance 2.0 Fast supports: 4, 5, 6, 8, 10, 12, 15 second durations.

**Cost:** ~$7.46 on Segmind for the regeneration.

**Result:** Video 3 (Glasswing) went from 75.6% frozen to 29.4% frozen (remaining freeze is intentional NB2 stills). Videos 1 & 2 improved but flagged by eval due to subtle motion in I2V shots.

### 3. Added Crossfade Transitions
FFmpeg `xfade` filter between shots (0.3-0.4s fade). Required:
- Normalizing all clips to 30fps/1080x1920 first (format mismatch breaks xfade)
- Pre-merging audio via concat, then mapping merged audio to xfaded video
- Python wrapper for building the xfade filter chain (shell variable expansion fails in complex filter strings)

### 4. Explored Anime Style (PsyopAnime-inspired)

#### PsyopAnime Analysis
Downloaded and frame-analyzed 3 PsyopAnime YouTube videos (WW3 Ceasefire, 2026 Trailer, Trump Declares War). Key findings:
- **Character-driven, not explainer-driven** — real people as anime characters with dialogue, not narration
- **90s anime aesthetic** — Akira/Death Note/Ghost in the Shell, not generic "anime style"
- **Extreme eye close-ups** for every dramatic beat — signature technique
- **Japanese voices + English subtitles** (yellow text on black bar)
- **Scene-based structure** — characters speaking in dramatic dialogue, intercut with action
- **They avoid showing mouths moving** in many shots (eye close-ups solve lip sync problem)
- **16:9 with letterboxing** — cinematic, not vertical TikTok format

#### First Anime Attempt (v1)
Generated anime version of Glasswing video using existing explainer script with anime-style prompts. Result: looked like an explainer with anime visuals, not an anime story. Missing the character-driven narrative.

#### Story-Driven Anime Script
Rewrote Glasswing as a character-driven anime with:
- **Characters:** Dario (CEO), The General (antagonist), The Researcher (discoverer)
- **Dialogue-based narrative** — no narrator explaining, characters speaking
- **Scene structure:** Discovery → Chain visualization → Boardroom confrontation → Proof → Decision → Paradox
- **Japanese voice acting** via ElevenLabs with emotional audio tags

#### Japanese Voice Acting
ElevenLabs supports Japanese with the multilingual v2 and v3 models. Tested multiple voices:
- Dario: Daniel voice (steady, authoritative)
- Researcher: Alice voice (clear, urgent)
- General: Adam voice (dominant, aggressive)
- Narrator: Liam voice (ominous)

**ElevenLabs v3 audio tags work:** `[gasps]`, `[whispers]`, `[shouting]`, `[pauses]`, `[sigh]` — dramatically improve vocal performance. The difference between flat TTS and actual voice acting.

### 5. Lip Sync Investigation

| Approach | Result |
|----------|--------|
| Seedance 1.5 Pro | Can't do lip sync |
| Seedance 2.0 `first_frame_url` + `reference_audios` | ERROR: "first frame cannot be mixed with reference media" |
| Seedance 2.0 `reference_images` + `reference_audios` + `@Image1 speaks @Audio1` prompt | **WORKS** — lip sync from audio reference |
| Kling 3.0 Pro `audio_url` | Works but generates English audio, need to swap in JP audio post |
| Kling 3.0 Pro image quality | Lower than Seedance 2.0 for anime style |

**Key finding:** Seedance 2.0 CAN do lip sync — the API pattern is `reference_images` + `reference_audios` (not `first_frame_url`). Prompt must include `@Image1 speaks the words in @Audio1 with natural lip sync`.

**Best practices for Seedance lip sync (from research):**
- Medium close-up with locked camera
- Front-facing or slight three-quarter angle
- Short sentences (5-10 words per line)
- Audio at 44.1kHz or 48kHz, clean pronunciation
- Emotion anchors in prompt ("calm, low-energy" or "excited, fast-paced")

### 6. Storyboard Workflow

**Breakthrough approach:** Generate a multi-panel storyboard in a single NB2 call so character designs stay consistent across all panels.

**Format that works:** 16:9 overall image, 3 vertical panels side by side. Each panel extracts to roughly 9:16. Three NB2 calls = 9 panels = full scene coverage.

**Format that doesn't work:**
- 9:16 overall with 3 stacked panels → panels end up horizontal/landscape
- 8:1 overall → panels end up too wide/square
- 1:1 grid → panels are square, not vertical

**Character consistency from reference photos:** Feed NB2 a real photo via `reference_images` parameter + prompt to transform into anime style with exaggerated features. Tested with Dario Amodei photo (grabbed from Lex Fridman podcast frame) — produced recognizable anime version with exaggerated curly hair, angular glasses, intense eyes.

---

## Updated Toolchain

| Tool | Use | Provider | Cost |
|------|-----|----------|------|
| **Nano Banana 2** | Images + storyboards | fal.ai | $0.08-0.15/image |
| **Seedance 2.0 Fast** | Video (primary), lip sync | Segmind | $0.27/clip (5s), scales with duration |
| **Kling 3.0 Pro** | Video (fallback), lip sync alternative | fal.ai | $0.56/clip |
| **ElevenLabs v3** | Voice acting with emotion tags | ElevenLabs | Free tier |
| **FFmpeg** | Assembly, transitions, subtitles | Local | Free |
| **eval.py** | Automated video QA | Local | Free |

### New Capabilities Discovered
- **Seedance 2.0 lip sync** via `reference_images` + `reference_audios`
- **ElevenLabs audio tags** for emotional performance ([gasps], [whispers], [shouting])
- **NB2 storyboard generation** for character consistency across scenes
- **NB2 reference image transformation** — real photo → anime character
- **Japanese voice acting** via ElevenLabs multilingual models

### Dropped
- **Seedance 1.5 Pro** — replaced entirely by 2.0
- **FLUX** — replaced entirely by NB2

---

## Production Workflow (Refined)

### For Explainer/News Flash style:
1. Script with shot-level asset routing (claim-bearing vs decorative)
2. NB2 images → Seedance 2.0 I2V (duration-matched to VO)
3. ElevenLabs VO (Liam, English)
4. FFmpeg assembly with xfade transitions
5. Eval before shipping

### For Anime/PsyopAnime style:
1. Script as **story with characters and dialogue** (not explainer narration)
2. Find/download reference photos of real people
3. NB2 storyboard with reference photos → 3-panel strips for consistency
4. Slice panels → Seedance 2.0 with lip sync (`reference_images` + `reference_audios`)
5. ElevenLabs Japanese VO with emotion tags (v3 model)
6. FFmpeg assembly with xfade + burned-in English subtitles (yellow on black)
7. Eval before shipping

---

## Full Anime Video Produced

**`project-b/final/glasswing_anime_final.mp4`** — 69 seconds, 6 scenes

Built scene-by-scene with storyboard → slice → generate → assemble → subtitle workflow.

### What's Working
- **Storyboard consistency** — NB2 3-panel strips maintain character design across scenes
- **Real photo → anime transformation** — Dario from Lex Fridman frame → recognizable anime character
- **Japanese VO with emotion** — ElevenLabs v3 audio tags produce real voice acting
- **Scene-by-scene workflow** — iterate on one scene, review, move to next
- **Subtitle integration** — yellow on black, FFmpeg drawtext via Python
- **Crossfade transitions** — smooth scene-to-scene flow

### What's Still Rough
- **Lip sync quality** — Seedance 2.0 `reference_images` + `reference_audios` works but sync is approximate, not frame-perfect
- **Character consistency across VIDEO clips** — storyboard panels are consistent but Seedance sometimes drifts character design between clips
- **Content filter** — Seedance flags some prompts as sensitive (company logos, intense expressions), requires softer reprompts or T2V fallback
- **Subtitle timing** — manually calculating timestamps is fragile, need automation (Whisper word-level alignment)
- **No background music** — dramatic anime needs a score
- **Duration** — 69s is too long for TikTok. Mentor feedback says 15-35s target.

### Cost for Anime Video
- 6 storyboard images (NB2): ~$0.48
- 15 video clips (Seedance 2.0 Fast): ~$6-8 (lip sync clips cost more due to reference_images)
- 10 VO lines (ElevenLabs): free tier
- Total: ~$7-9 for one anime video (higher than explainer style due to lip sync and more clips)

## Open Questions for Next Session

1. **Lip sync improvement** — try Kling 3.0 lip sync vs Seedance 2.0 side by side on same scene. Or avoid mouth shots (PsyopAnime eye close-up technique).
2. **Shorter cuts** — mentor wants 15-35s. Can we cut the Glasswing anime to 30s and still tell the story?
3. **Background music** — need a dark dramatic instrumental. Licensed or AI-generated?
4. **Automated subtitle timing** — Whisper word-level timestamps instead of manual calculation
5. **Character consistency in video** — try passing the full storyboard strip as an additional reference to Seedance (not just individual panel)
6. **Content filter workarounds** — build a library of prompts that pass vs fail
7. **Posting** — still need to post to TikTok and get engagement data
8. **Other characters from real photos** — Jensen Huang, Tim Cook, etc. for multi-character scenes

---

## Files Created/Modified

- `rally-poc/eval.py` — video eval system
- `rally-poc/project-b/script-glasswing-anime-v2.md` — story-driven anime script
- `rally-poc/project-b/audio/anime/` — Japanese voice acting samples (10 dialogue lines)
- `rally-poc/project-b/final/video3_hottake_v4.mp4` — fixed duration + transitions
- `rally-poc/project-b/final/glasswing_anime_story.mp4` — first anime attempt (bulk)
- `rally-poc/project-b/final/glasswing_anime_story_subs.mp4` — with English subtitles
- `rally-poc/project-a/final/video1_explainer_v4.mp4` — fixed duration + transitions
- `rally-poc/project-a/final/video2_newsflash_v4.mp4` — fixed duration + transitions
- `rally-poc/reference/psyopanime/` — downloaded reference videos + extracted frames
- `rally-poc/reference/dario_amodei.jpg` — reference photo for anime transformation
- `/tmp/dario_anime_from_photo.png` — anime Dario from real photo (storyboard test)
- `/tmp/storyboard_panels/` — sliced panels from storyboard grid
- `/tmp/rally_lipsync_test/` — lip sync comparison clips (Seedance vs Kling)
