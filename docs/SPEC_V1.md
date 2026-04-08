# Rally v1: Style-Matched Video Generation Pipeline

## What We're Building

A system that discovers trending video styles, generates videos in those styles about target projects, and mass distributes them cross-platform. No platform. No feed. No agents yet. Just: trending style + interesting project = engaging video, posted everywhere.

The output is proof that technical content in trending formats generates engagement. That data becomes the foundation for everything else.

## First User

**Viewer.** Someone scrolling TikTok, YouTube Shorts, or Instagram Reels who stops on a video because the format is familiar and engaging, then stays because the content is genuinely interesting.

They don't know Rally exists. They don't need to.

---

## Three Components

### 1. Style Discovery

Monitor trending video formats across platforms. Classify them well enough to reproduce with AI.

**Per style, capture:**
- Format type (talking head, text overlay, split screen, before/after, reaction, voiceover + footage, meme template, tutorial, storytime)
- Visual signature (pacing, transitions, text placement, color treatment)
- Audio signature (voiceover style, trending sounds, music, TTS characteristics)
- Hook pattern (what happens in the first 2 seconds)
- Duration sweet spot
- Trend velocity (rising, peaking, declining)

**Output:** A ranked set of active styles with enough detail to reproduce them.

**Update cadence:** Styles move fast. Refresh every few days minimum.

### 2. Video Generation

Take a project + a trending style, produce a video that applies that style to that project.

**Pipeline stages:**
1. **Script** — Short, punchy, matches the style's tone and hook pattern
2. **Visual assets** — Screenshots, diagrams, demos, AI-generated imagery
3. **Audio** — TTS voiceover matched to style, music/sounds where applicable
4. **Composition** — Assemble with pacing, transitions, text overlays matching the style template
5. **Quality evaluation** — Automated check (vision model) + human review for early batches

**Volume:** Start with 3-5 styles x 5-10 projects = 15-50 videos per week. Scale based on what works.

**Variants:** For projects showing engagement, generate additional variants (different styles, different hooks, different angles). Let engagement pick the winner.

### 3. Distribution + Tracking

Post to all major short-form platforms. Track everything.

**Platforms:** TikTok, YouTube Shorts, Instagram Reels, Twitter/X, Reddit

**Per-platform:** Adapt aspect ratio, captions, hashtags, posting time. Stagger posts.

**Track per video:**
- Views, watch-through rate, replays
- Likes, comments (count + sentiment), shares, saves
- Follower growth attributed to video

**Track per project:**
- Total engagement across all videos about it
- Best-performing style for this project
- Engagement trend over time

**Track per style:**
- Average engagement across all projects
- Which project types pair best
- Style lifecycle (still rising or played out?)

---

## Lessons Applied

From previous video generation work, these principles are baked into the design:

**Cost tracking from day one.** Every API call (TTS, video generation, vision evaluation) gets per-unit cost tracking with hard caps. No runaway bills. Know exactly what each video costs to produce.

**Partial failure is normal.** Generating a batch of videos means some will fail. The system handles partial success gracefully, doesn't abort the whole batch for one failure, charges only for what succeeded.

**Resume capability.** Long generation runs get interrupted. Deterministic task IDs and state checkpointing so the pipeline picks up where it left off without duplicate work.

**Quality gates before publishing.** Vision models (Gemini or equivalent) evaluate video quality before anything goes live. Catches visual defects, brand inconsistencies, and generation artifacts that text-only checks miss. Ensemble approach (multiple evaluation calls) for reliability.

**Provider abstraction.** TTS providers, video generation models, face sync tools change constantly. The pipeline abstracts providers behind interfaces so swapping one out doesn't require rewriting the pipeline.

**Async and parallel by default.** Video generation is inherently parallelizable. Multiple videos generate simultaneously. Within a single video, independent stages (asset generation, audio generation) run in parallel. Sequential only where there's a real dependency.

**Deterministic IDs for everything.** Every run, every task, every variant gets a deterministic ID derived from its inputs. Enables debugging, deduplication, and reproducible results.

---

## Target Projects (Initial Set)

Manual curation to start. Pick 5-10 projects per week from:

- GitHub trending (daily/weekly)
- Hacker News front page discussions
- Product Hunt launches
- Notable open source milestones
- Tech problems getting discussed on social media
- Rally itself (dogfooding)

Per project, capture:
- What it is (one sentence)
- Why it's interesting (the hook angle)
- Key visual elements (screenshots, demos, diagrams)
- The "so what" for a non-technical viewer

Automate discovery later once we know what kinds of projects generate engagement.

---

## What This Proves

1. **AI can generate engaging technical content in trending formats.** Core bet. If the videos don't get engagement, nothing else matters.
2. **Style matching matters.** Same project in different styles should show meaningful engagement differences.
3. **Technical content can compete.** Rally videos get comparable engagement to entertainment content on the same platforms.
4. **We can identify signal.** Engagement data ranks projects by what people care about. Precursor to the agent signal system.

## What This Doesn't Prove Yet

- That engagement can direct useful agent work (next phase)
- That a dedicated platform adds value over cross-platform distribution (later)
- Revenue model (later)

---

## Success Metrics

| Milestone | Target |
|-----------|--------|
| Week 1-2 | Pipeline operational. First 20 videos generated and posted. |
| Week 3-4 | Engagement data flowing. At least 3 videos exceeding 1K views on any platform. |
| Month 2 | Top-performing style + project combinations identified. At least 1 video exceeding 10K views. |
| Month 3 | Consistent output (20+ videos/week). Growing follower base. Engagement data sufficient to rank projects by signal strength. |

**Key metric:** Engagement rate per video relative to platform average for the account size. Not absolute numbers. Relative engagement tells you if the content is genuinely compelling.

---

## Architecture (High Level)

```
┌───────────────┐    ┌───────────────┐
│    Style       │    │   Project     │
│    Discovery   │    │   Curator     │
│                │    │               │
│  Trend monitor │    │  GitHub, HN,  │
│  Style catalog │    │  manual picks │
└───────┬────────┘    └───────┬───────┘
        │                     │
        └──────────┬──────────┘
                   │
                   v
        ┌───────────────────┐
        │  Video Generator   │
        │                    │
        │  script            │
        │  assets            │
        │  audio             │
        │  composition       │
        │  quality eval      │
        │                    │
        │  [cost tracking]   │
        │  [resume capable]  │
        │  [provider-agnostic]│
        └─────────┬──────────┘
                  │
                  v
        ┌───────────────────┐
        │  Distributor       │
        │                    │
        │  TikTok            │
        │  YouTube Shorts    │
        │  Instagram Reels   │
        │  Twitter/X         │
        │  Reddit            │
        └─────────┬──────────┘
                  │
                  v
        ┌───────────────────┐
        │  Engagement        │
        │  Tracker           │
        │                    │
        │  Per-video metrics │
        │  Per-project signal│
        │  Per-style analysis│
        │                    │
        │  (future: feeds    │
        │   agent system)    │
        └────────────────────┘
```

---

## Open Decisions

- **Public-facing brand**: Rally? Something else for the social accounts?
- **Video length**: 15s, 30s, 60s, 90s? Test all, let data decide.
- **Voice/persona**: Consistent narrator or vary by style?
- **Tech stack**: Fresh decision based on current best options for each component.
- **Music/audio licensing**: Trending sounds have licensing implications. Needs research.
- **First 10 projects**: Curate the initial list to kick off generation.
