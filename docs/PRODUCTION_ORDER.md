# Production Order

The single contract every Rally video respects. Audio drives timing. Every visual duration, every music length, every caption window is derived from the measured voiceover. Nothing is generated against guesses after the script lands.

## The 10 steps

```
1. Script             — Creative Director writes; Producer gates.
2. VO generation      — ElevenLabs per beat. mp3 per shot in audio/.
3. Measure            — ffprobe each VO file; record per-shot seconds.
4. Snap               — visual_duration = measured + 0.3s, snapped to {4,5,6,8,10,12,15}.
5. Image gen          — gpt-image-2 storyboard poster OR NB2 stills, per shot or per segment.
6. Video gen          — Seedance 2.0 with the snapped duration.
7. Music              — sized to (sum of snapped + transitions tail).
8. Assembly           — FFmpeg with explicit -t total_duration.
9. Captions           — Whisper word-level alignment of VO; per-word drawtext windows.
10. Critic            — Gemini 2.5 Flash 8-axis rubric; gate before publish.
```

## Why this order

The previous failure mode was: writers guessed `duration_s` per shot, Seedance generated to that guess, ElevenLabs generated VO at its natural pace, and music came in at whatever length. Three independent clocks, no synchronization. Output drifted by 5-15 seconds.

The fix: **the script is the master clock.** Voice-over IS the video's heartbeat. Every other duration follows from measured VO time. `duration_s` in plan JSONs becomes a hint for budget estimation only.

## Ownership map (which file/role produces each artifact)

| Step | Artifact | Owner (pipeline) | Owner (agentic studio) |
|---|---|---|---|
| 1 | `master_script` in run.json | (writer) | `creative_director` |
| 2 | `audio/<shot>.mp3` per shot | `pipeline.elevenlabs_client` | `generation` |
| 3 | `state.measured_vo` dict | `pipeline.timing.measure_vo_durations` | `generation` (preflight) |
| 4 | `state.snapped_durations` dict | `pipeline.timing.snap_shot_durations` | `generation` (preflight) |
| 5 | `images/<shot>.png` or `assets/storyboard_poster.png` | `pipeline.fal_client` / `pipeline.openai_image_client` | `art_director` (specs) → `generation` (gen) |
| 6 | `clips/<shot>.mp4` | `pipeline.segmind_client` | `generation` |
| 7 | `music/<run_name>_score.wav` | fal-ai stable-audio | `editor` |
| 8 | `final.mp4` (pre-captions) | `pipeline.ffmpeg_assembly.assemble_video` | `editor` |
| 9 | per-word caption arrays | `pipeline.whisper_client` | `editor` |
| 10 | `critique.md` + verdict | `pipeline.video_critic` (Gemini) | `critic` |

## Drift handling

The orchestrator emits a TIMING line after Phase 1 (VO generation) that reports:
- Number of shots measured
- Snapped total duration
- Drift warning if `abs(measured_total - target_duration_s) > 1.5s`

Drift > 1.5s means the script's intended length and the measured speech length disagree by more than a hair. This is a producer-gate failure in the agentic studio. In the deterministic pipeline it's logged and the run continues.

The 1.5s threshold is empirical: 1s is normal voice-actor variance; 2s+ usually means the script estimate was wrong by a sentence.

## Per-shot vs per-segment

Two image-gen patterns are valid:

**Per-shot stills (rally_001 style):**
- One NB2 image per shot
- One Seedance I2V call per shot
- Best when shots have very different subjects
- Best when length total < 15s and continuity drift is acceptable

**Per-segment storyboard posters (rally_006/012/013 style):**
- One gpt-image-2 storyboard poster per segment (1-3 shots)
- One Seedance call per segment that interprets the poster as a sequence
- Best when continuity and brand-coherence matter more than per-shot precision
- Required for >15s videos via segment chain (Phase 3 of the rebuild)

The agentic studio's `art_director` role decides which pattern; the `generation` role implements either.

## What changes for plans written before this contract

Existing plans (rally_007 through rally_013, glasswing_anime_v3) keep working. The orchestrator now reads measured VO durations into `state.measured_vo` after Phase 1 and uses those for video gen and assembly. The `duration_s` in old plans is treated as a hint; if the measured VO drifts by >1.5s from it, a warning is logged.

This is backward-compatible by design — no plan needs to be rewritten to benefit from the timing contract.

## Multi-character voices

Add a `cast` block to the run.json:

```json
"cast": {
  "voices": {
    "Liam": "TX3LPaxmHKxFdv7VOQHJ",
    "Daniel": "onwK4e9ZLuTAKqWW03F9",
    "Adam": "pNInz6obpgDQGcFmaJgB",
    "Alice": "Xb7hH8MSUJpSbSDYk0k2"
  },
  "characters": [
    {"id": "narrator", "voice": "Liam"},
    {"id": "dario", "voice": "Daniel"},
    {"id": "general", "voice": "Adam"}
  ]
}
```

Each shot's `vo_voice` is a key into `cast.voices` (Glasswing already did this). Lip-sync rules from the existing style cards apply per character.

## Anti-patterns

Don't:
- Generate Seedance video before the VO is measured. Use `--stop-after phase1` if you need to preview VO timing.
- Set `duration_s` to round numbers and assume they'll match the spoken script. They won't.
- Reuse a music track from one render in another without adjusting volume/length. Music sized for a 27.2s anime video doesn't fit a 12s carousel.
- Pass `image_to_clip` a flat solid-color screenshot and expect eval to register motion. The freeze detector reads pixel diff; black screens with subtle zoom register as static.
- Skip the critic. The critic catches sync drift and ad-feel before the post goes out; it's the last gate before a public mistake.

## See also

- `pipeline/timing.py` — implements steps 3-4 + multi-batch segment planner
- `docs/VIDEO_RUBRIC.md` — what step 10's critic scores against
- `docs/STORYBOARD_PIPELINE_V2.md` — six-panel batch contract referenced in step 5
- `docs/STYLE_CARD_SYSTEM.md` — how style cards constrain step 5/6 output
- `docs/AGENTIC_PRODUCTION_PIPELINE.md` — how the 10-role studio enforces this contract per role
