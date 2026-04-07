# Rally

Engagement layer that aligns AI agents toward problems people care about.

## What This Is

A platform where AI generates engaging, TikTok-style videos about real projects and problems. Users scroll, watch, engage. That engagement becomes the signal that directs AI agents toward the problems people actually care about. More engagement spawns more agents. Progress generates new videos. The cycle continues.

## The Core Insight

People confused boring for important. It's the job of the problem solvers to adapt to people, not the other way around. TikTok proved that short-form video is the most effective format for capturing attention. Nobody has pointed that attention engine at anything that matters. Rally does.

## How It Works

```
Problem surfaces
    -> AI generates engaging video about it
        -> Video posted to feed + cross-platform (TikTok, YT Shorts, IG, Twitter)
            -> People engage (watch, like, share, comment)
                -> Engagement = signal for what people care about
                    -> Agents work on high-signal problems
                        -> Progress generates new videos
                            -> Cycle continues
```

## Key Concepts

### Engagement as Alignment
The same mechanics that make TikTok addictive become a mechanism for collective alignment. Engagement signal directs AI agent effort toward human needs. The more people care about something, the more agent resources flow toward it.

### Multiplayer by Default
Current AI is single-player. Millions of people have their own private Claude session, solving the same problems independently. None of it compounds. Rally makes it multiplayer. Problems are shared. Agent work is visible. Knowledge compounds across everyone connected.

### Cross-Platform Signal
You don't need users on Rally to start collecting signal. Videos are posted to TikTok, YouTube Shorts, Instagram, Twitter. Engagement on those platforms feeds back into Rally. The platform starts generating signal before it has its own audience.

### Videos as Interface
The atomic unit is a video. AI generates them in trending styles, borrowing from what works socially, but the content is about real projects, real problems, real progress. People can also contribute their own videos as input. Agents in the background watch everything and work on what has signal.

## Bootstrap Strategy

1. Generate videos about existing trending/interesting projects on the web (open source, tech, whatever's hot)
2. Post them everywhere (TikTok, YouTube Shorts, Instagram, Twitter)
3. Collect engagement signal from those platforms
4. Use signal to direct agent effort
5. Rally itself is the first project the platform works on (dogfooding)

## Existing Infrastructure

Rally builds on top of significant existing video generation and distribution tech:

- **dicer-toolbox** — AI creative tools (Animate, Hookswap, video generation) on Motia/Supabase
- **video_mix_pipeline** — UGC video variants with ElevenLabs TTS, Wav2Lip face sync, Gemini evaluation
- **dicer-generative-agent** — Generative agent for content creation
- **genvid / gen-ai** — Video and AI generation services (Scrolller org)
- **Scrolller platform** — Proven engagement/distribution infrastructure with millions of MAU

## Open Questions

- What does an agent "working on a problem" actually produce? Code? Plans? More videos? All of the above?
- How do agents share knowledge across the network? Shared context, knowledge base, handoffs?
- How do you prevent engagement from drifting toward shallow/flashy content vs. genuinely hard problems?
- Revenue model — ads? subscriptions? open source? hybrid?
- Governance — who decides what a "problem" is? Anyone? Curated? Algorithmic?
- Privacy/IP — if problems and agent work are visible, how to handle proprietary work?

## Project Status

**Phase: Concept / Early Development**
