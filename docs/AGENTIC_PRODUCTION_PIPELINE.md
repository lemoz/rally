# Agentic Production Pipeline v1

## Goal

Rally video quality should come from a visible production process, not from one large prompt. Each stage is an agent process with a narrow contract, a typed artifact, and a review gate before the next expensive step.

This is not "more agents for its own sake." It is a production line:

1. Make the source truth explicit.
2. Make the style target explicit.
3. Make the creative concept compete before generation.
4. Make storyboard and keyframes pass taste review before video spend.
5. Make generation retry requests specific and local.
6. Keep deterministic assembly responsible for editing, captions, proof cards, and exports.

## Why Tmux

Tmux is the view layer. It lets an operator see every role's current task, logs, and handoff file in one session.

Tmux is not the coordination layer. Coordination lives in the run directory:

```text
rally-poc/runs/<run_id>/
  run.json
  artifacts/
  gates/
  handoffs/
  logs/
  prompts/
  status/
```

Every agent process reads the same `run.json`, writes its own handoff, and updates `status/<role>.json`.

## Roles

| Order | Role | Owns | Primary output |
|---:|---|---|---|
| 00 | producer | Run state, budget, gates, final decision log | `artifacts/producer_run_summary.md` |
| 01 | research | Facts, sources, provenance, claim boundaries | `artifacts/source_pack.md` |
| 02 | trend_style | Reference format, trend pattern, style constraints | `artifacts/style_brief.md` |
| 03 | creative_director | Concepts, hook, emotional arc, selected direction | `artifacts/selected_concept.md` |
| 04 | storyboard | Six-panel story sequence and shot logic | `artifacts/storyboard.json` |
| 05 | art_director | Keyframe specs, prompt pack, visual continuity | `artifacts/keyframe_specs.json` |
| 06 | generation | Image/video generation attempts and asset manifest | `artifacts/generation_manifest.json` |
| 07 | editor | Rough cut, captions, pacing, audio, proof-card integration | `artifacts/edit_decisions.md` |
| 08 | critic | Quality review and retry requests | `artifacts/critique.md` |
| 09 | publisher_packet | Final caption, source notes, posting handoff | `artifacts/publish_packet.md` |

## Gates

Gates are the quality control points. Producer owns them, but the critic can force a rollback.

| Gate | Required before | Pass condition |
|---|---|---|
| `source_pack` | Style/concept work | Facts are source-backed and claim boundaries are clear. |
| `style_brief` | Concept selection | The style is a real visual language, not only a format variant. |
| `concept` | Storyboard | Hook, audience promise, and emotional arc are strong enough to test. |
| `storyboard` | Keyframes | Each panel has one beat, provenance label, motion intent, and safe caption area. |
| `keyframes` | Video generation | Keyframes are visually strong enough to animate. |
| `clips` | Final edit | Weak or off-style clips have retry requests or are cut. |
| `final_edit` | Publish packet | Final video clears taste, factuality, pacing, and export checks. |

## Hard Rules

- Agents own artifacts, not vague steps.
- Proof-bearing claims stay deterministic or source-backed.
- Generated product UI is allowed only when clearly non-literal.
- Trend imitation must capture structure and rhythm, not copy protected assets.
- The producer cannot skip handoff documentation.
- The generation agent cannot spend on video until storyboard/keyframes pass.
- The critic must name retry requests by exact shot, reason, and suggested fix.

## Minimal Usage

Create and launch a visible tmux production line:

```bash
cd /Users/cdossman/rally/rally-poc
python3 -m agents.launch_tmux --project openscreen --style psyop_anime_90s --run-id openscreen_anime_agentic_v1
```

Attach to the session:

```bash
tmux attach -t rally-openscreen_anime_agentic_v1
```

By default, panes run a local scaffold worker that writes prompts and handoff templates. To plug in a real model runner, set:

```bash
export RALLY_AGENT_COMMAND_TEMPLATE='your-agent-command --prompt-file {prompt_file}'
```

The launcher will replace these placeholders:

- `{prompt_file}`
- `{run_dir}`
- `{role}`
- `{project}`
- `{style_id}`

## Next Implementation Target

The next quality jump is to make `creative_director`, `storyboard`, `art_director`, and `critic` call stronger models against their artifact contracts. The tmux launcher already gives those model processes a stable file system and visible logs.
