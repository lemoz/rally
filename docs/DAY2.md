# Day 2 — 2026-05-07/08

The day Rally's video pipeline grew up. Day 1 shipped infrastructure; Day 2 fixed the foundation, activated the agentic studio, and produced the first end-to-end agentic video.

## What shipped

### Pipeline rebuild (audio drives timing)

After ~$25 of API spend on rally_001 through rally_013 produced visually weak, sync-drifting videos, three foundation problems became clear and got patched:

1. **Sync drift fix.** `_assemble_single` in `pipeline/ffmpeg_assembly.py` now passes `-t clip.duration` to FFmpeg with `amix duration=shortest`. rally_013 went from a buggy 30s output to a clean 15s. The single-clip path matches the multi-clip path's behavior.
2. **Universal VO-driven duration.** `pipeline/run_pipeline.py` was deriving video duration from VO only when `needs_lipsync: true`. It now does so for every shot with a generated VO, with a 0.3s tail buffer, snapped to Seedance's valid set. The plan-level `duration_s` becomes a hint for budget estimation, not a guess at length.
3. **Whisper word-level captions.** New `pipeline/whisper_client.py` calls OpenAI Whisper with `timestamp_granularities=["word"]`, groups words into ~4-word phrases (under FFmpeg's filtergraph node limit), and `pipeline/ffmpeg_assembly.py`'s `ClipSpec` gained a `caption_phrases` field that emits per-phrase drawtext with `enable='between(t,start,end)'`. Captions now sync to the actual spoken word, not estimates.

### Multi-batch storyboard chain

`pipeline/multi_batch.py` for >15s renders. Splits a plan into segments ≤12s, generates one gpt-image-2 storyboard poster per segment, calls Seedance once per segment with the poster as first-frame seed, stitches segments via FFmpeg concat. Continuity hint propagates from segment N-1's last beat into segment N's prompt. Single Seedance call per segment interprets the poster panels as sequential beats — way better continuity than 6 separate I2V calls.

### `pipeline/timing.py` — the contract module

Source-of-truth for shot durations after Phase 1 of the orchestrator runs. Three functions: `measure_vo_durations`, `snap_shot_durations`, `compute_total_target`, plus `plan_segments` for the multi-batch chain. The orchestrator now calls these once after VO generation and stores results on `state.measured_vo` / `state.snapped_durations`; downstream phases read from there.

### Production order documented

`docs/PRODUCTION_ORDER.md` formalizes the 10-step contract. Script → VO → measure → snap → image → video → music → assembly → captions → critic. Documents the cast block, drift handling, per-shot vs per-segment patterns, and anti-patterns.

### Video critic with rubric

`pipeline/video_critic.py` uploads a video to Gemini 2.5 Flash and scores it against an 8-axis rubric (`docs/VIDEO_RUBRIC.md`). Saves a structured JSON next to the video. Used by the Critic role in the agentic studio.

### Agentic studio — activated

The 10-role studio at `rally-poc/agents/` was scaffolded on Day 1 but unwired. Day 2 wired it:

- `agents/runner.py` (new) — backs `RALLY_AGENT_COMMAND_TEMPLATE`. Calls GPT-5.5 chat completions with `read_file`/`write_file`/`list_dir`/`done` tools scoped to the run dir. Critic role short-circuits to `video_critic.py`. Retries 408/429/5xx with exponential backoff (10-min timeout for the reasoning model).
- `agents/run_sequential.py` (new) — drives a full studio run without tmux. Inits the run dir via `launch_tmux` helpers, then runs each role through `worker --once`, gating on user-approved gates. Has `--auto-approve`, `--start-at`, `--stop-at`.
- `agents/plan_bridge.py` (new) — schema bridge from `storyboard.json` (panels) + `keyframe_specs.json` (specs) to `pipeline.run_pipeline`'s `plan.json`. Maps `visual_contract`/`composition` to `image_prompt`, `motion_intent`/`motion_prompt` to `video_prompt`, `caption.text` to `vo_text`/`subtitle`, `generation_route_hint` to shot type.
- `agents/worker.py` patched — when a role's `primary_output` already exists, skip the model call. Cheap re-runs.
- `agents/studio.py` patched — extended gate preflight: `concept` requires master_script, `storyboard` requires per-shot vo_text, `keyframes` requires specs covering every storyboard shot. Wires the gates to the timing contract.

### First end-to-end agentic video: rally_014_agentic_v1

The verification run produced a fully-agentic Rally video on the multiplayer-AI topic.

**Concept:** *"The Lonely Cursor Mutiny"* — 90s anime micro-drama. Hook in 0–2s: black terminal with `same bug again_` smash-cuts to an exhausted anime eye reflecting the cursor, caption *"Why are we debugging AI alone?"* CTA: *"Stop soloing AI. Make it multiplayer."*

**Roles produced (10 total):**

| Role | Output | Status |
|---|---|---|
| producer | producer_run_summary.md, decision_log.md | ✅ |
| research | source_pack.md, claim_inventory.json | ✅ |
| trend_style | style_brief.md, reference_manifest.json | ✅ |
| creative_director | concepts.md, selected_concept.md | ✅ |
| storyboard | storyboard.json (6 panels), shot_list.md | ✅ |
| art_director | keyframe_specs.json, prompt_pack.md | ✅ |
| generation | (via plan_bridge → run_pipeline; final.mp4) | ✅ |
| editor | (blocked: pipeline already rendered final.mp4 — known role-design tension) | ⚠️ |
| critic | critique.md (Gemini 2.5 Flash 8-axis rubric) | ✅ |
| publisher_packet | publish_packet.md | ✅ |

**Critic verdict: 8.375/10 PASS** with no axis below 7.

| Axis | Score |
|---|---:|
| native_feel | 7 |
| hook_integrity | 8 |
| save_worthy_moment | 9 |
| visual_quality | 9 |
| audio_match | 8 |
| pacing | 9 |
| caption_craft | 9 |
| comment_cta_strength | 8 |

**Verification — Phase 5 criteria all met:**

| Criterion | Status |
|---|---|
| Audio sync (±0.2s per shot boundary) | ✅ pipeline uses measured VO + snapped durations |
| Caption alignment (Whisper words) | ✅ caption_craft 9/10 |
| Critic verdict in output | ✅ critique.md, 8.375/10 PASS |
| All 10 handoffs filed | ✅ 9 complete + 1 editor-blocker |
| Total duration ≈ target | ✅ 24s |

**Cost: $1.85 per fully-produced agentic video** — ~$0.50 cognition (10 GPT-5.5 calls) + $1.30 Seedance + $0.05 Gemini critic + tiny Whisper/ElevenLabs.

## Decisions taken

- **GPT-5.5 over GPT-4o.** Chris caught the model-tier mistake; runner default is `gpt-5.5`. Reasoning model means 600s timeout + retry on 5xx.
- **gpt-image-2 over gpt-image-1** for storyboard posters. The newer model handles typography and multi-panel layouts cleanly (the rally_012 v rally_013 comparison made this obvious).
- **Audio drives timing — universal.** No more guessing `duration_s`; VO measurement is authoritative for every shot.
- **Editor as meta-decision, not renderer.** When the deterministic pipeline already produces final.mp4, the agentic editor role's job is to APPROVE the output for hand-off, not re-render. Role contract needs a small tweak (next session) so it stops blocking.

## What's queued for Day 3

- **Tighten editor role contract** — when generation already produced final.mp4, editor's job is approve + decide retake-vs-ship, not render.
- **First TikTok post.** rally_014's video passed the critic 8.375/10 — it's postable. Update bio to `rallysignal.co`, post the video, collect first engagement signal.
- **First multi-batch render** — pick a >15s topic and exercise `pipeline.multi_batch` end-to-end. Possible candidates: a 30s explainer of the Rally signal score, a 45s walkthrough of the agentic studio architecture.
- **Per-render music tuning** — current pipeline reuses `rally_001_score.wav`; per-render scores via fal-ai stable-audio per the architecture should be wired into multi_batch and run_pipeline.
- **Implementation work on the 5 `rally-loop` issues** — they're filed but unbuilt. Now that the loop's content side is producing real artifacts, the agent side needs the engagement-poller / signal-score / agent-runner to actually close the loop.

## Numbers

- **Day 2 spend**: ~$5 across all renders + agentic verification
- **Cumulative spend** (Day 1 + Day 2): ~$30
- **Repo size**: still <15 MB; .gitignore catching all generated media
- **Lines added Day 2**: ~2k across the pipeline rebuild + agentic plumbing
- **Pipeline phases now**: 5 generation phases + Phase 3.5 captions + new timing-contract preflight; ~700 lines of new module code in `pipeline/timing.py`, `pipeline/whisper_client.py`, `pipeline/multi_batch.py`, `pipeline/openai_image_client.py`, `pipeline/video_critic.py`

## Risks that materialized

- **Caption schema mismatch in plan_bridge.** Storyboard role uses `visual_contract`/`generation_route_hint`/`caption.text`; my first bridge draft expected `composition`/`video_route`/`subtitle`. Patched to handle both.
- **First agentic run cost-of-mistakes.** P01 had no VO by design (diegetic terminal text only); the bridge pulled from selected_concept's beat sheet anyway and duplicated the hook. Patched to respect explicit empty captions.
- **Editor role blocked.** Deterministic pipeline already rendered final.mp4; editor tried to do its own render and reported missing inputs. The role-contract assumption that editor renders the cut is wrong when the pipeline does it. Day 3 fix.

## Risks that didn't materialize

- **Studio cost runaway.** Caching on the worker (skip if primary_output exists) kept re-runs cheap. Total cognition ~$0.50 per full studio run.
- **GPT-5.5 timeout.** 600s timeout + exponential retry caught the transient 500 from research role; second run completed cleanly.
- **Whisper filtergraph overflow.** 6 shots × ~7 phrases each = ~42 drawtext nodes in the assembled video. Well under FFmpeg's ~700-node practical limit.

## Tomorrow's first hour

1. Patch editor role contract — accept pipeline-rendered final.mp4 instead of re-rendering
2. Update TikTok bio with rallysignal.co
3. Post `rally_014_agentic_v1/final/final.mp4` to `@rallysignal` — the first agentic Rally video
4. Start the multi-batch chain test on a 30s topic
