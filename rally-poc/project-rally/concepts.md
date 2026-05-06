# Rally Video Concepts — Day 1 Exploration Batch

Twenty concepts spanning four buckets to learn what works for Rally-about-Rally
content. Pick 3–5 to generate today; the rest are Day 2–3 backlog.

Each concept has a one-line hook, a six-shot beat sheet, a style card,
suggested voice, target duration, and posting hashtags.

---

## A. Build logs (5)

Authentic, lo-fi, dev-first energy. Style: `raw_demo_build_log`.

### A1 — "Day 1: I'm building a TikTok feed where likes program AI agents"
- **Hook (0–2s):** brutalist R logo on black, smash-cut to terminal `git log` of the four Day-1 commits scrolling past.
- **Beat 2 (2–8s):** browser at rally-woad-nine.vercel.app showing the empty feed with "Generating videos."
- **Beat 3 (8–16s):** github.com/lemoz/rally page, scroll to README, hover over five `rally-loop` issues.
- **Beat 4 (16–24s):** screen recording of the storyboard pipeline running in terminal — one shot generating.
- **Beat 5 (24–32s):** quick cut: TikTok profile @rallysignal showing 0 followers, then the loop diagram from README.
- **Beat 6 (32–38s):** "Like this if you want me to keep going. Comments pick what gets built first." Logo + handle.
- **Style:** raw_demo_build_log
- **Voice:** Liam (English, narrator)
- **Duration:** ~38s
- **Hashtags:** #buildinpublic #ai #tiktok #vibecoding #devtok #opensource

### A2 — "I taught AI to make TikToks about my code"
- **Hook:** terminal `python3 -m pipeline.run_pipeline rally_001.json` smash-cut to a generated frame appearing.
- **Beat 2:** stack diagram: NB2 + Seedance + ElevenLabs + FFmpeg.
- **Beat 3:** before/after — raw `git diff` on left, generated TikTok-style clip on right.
- **Beat 4:** show eval.py output — "8/8 shots PASS, 2.8% freeze."
- **Beat 5:** running the same script on a new project.
- **Beat 6:** "It's all open source. Link in bio."
- **Style:** raw_demo_build_log
- **Voice:** Liam
- **Duration:** ~30s
- **Hashtags:** #ai #buildinpublic #genai #devtools #opensource

### A3 — "Anatomy of one Rally video — start to finish in 60 seconds"
- **Hook:** the final mp4 plays for 1.5s.
- **Beat 2:** rewind back through assembly → lipsync → video gen → image gen → script.
- **Beat 3:** show the JSON storyboard plan that defined it.
- **Beat 4:** show the eval report passing.
- **Beat 5:** post to TikTok in real time.
- **Beat 6:** "Every Rally video is reproducible. The repo is open."
- **Style:** raw_demo_build_log
- **Voice:** Liam
- **Duration:** ~55s
- **Hashtags:** #ai #genai #behindthescenes #buildinpublic

### A4 — "I gave my GitHub issues to a swarm of agents"
- **Hook:** github.com/lemoz/rally/issues page, five `rally-loop` labels visible.
- **Beat 2:** terminal launches an agent runner; tmux split shows 10 panes producing artifacts.
- **Beat 3:** an agent opens a draft PR.
- **Beat 4:** PR diff scrolls past quickly.
- **Beat 5:** signal-score formula explained as a quick visual.
- **Beat 6:** "Your engagement decides what they work on next."
- **Style:** raw_demo_build_log
- **Voice:** Liam
- **Duration:** ~45s
- **Hashtags:** #ai #agents #buildinpublic #github

### A5 — "Why I made my own AI feed instead of using TikTok"
- **Hook:** rally feed scrolling on phone (mock), then cut to TikTok feed scrolling.
- **Beat 2:** "TikTok already collects engagement signal. Rally turns it into agent direction."
- **Beat 3:** the loop diagram, animated step by step.
- **Beat 4:** show that TikTok's bio CTA points to rally.fyi.
- **Beat 5:** "Watch on either. Engagement counts both places."
- **Beat 6:** logo + handles.
- **Style:** raw_demo_build_log
- **Voice:** Liam
- **Duration:** ~40s
- **Hashtags:** #ai #tiktok #builtinpublic #devtok

---

## B. Dogfood demos (5)

Real screen capture of using Rally itself. Style: `raw_demo_build_log`.

### B1 — "Rally feed first scroll"
- Screen capture of a phone scrolling the live rally.fyi feed for 30 seconds.
- Voiceover narrating what's on screen.
- **Style:** raw_demo_build_log
- **Voice:** Liam
- **Duration:** ~30s
- **Hashtags:** #demo #ai #genai

### B2 — "Liking a video moves the agent priority queue"
- **Hook:** rally feed, a viewer hits like on a video.
- **Beat 2:** dashboard view: signal score updates from 0.32 to 0.51.
- **Beat 3:** the corresponding GitHub issue gains a "↑ priority" label.
- **Beat 4:** an agent picks it up.
- **Beat 5:** PR opens.
- **Beat 6:** "This loop. From your tap to a code change. 90 seconds."
- **Style:** raw_demo_build_log
- **Voice:** Liam
- **Duration:** ~45s
- **Hashtags:** #ai #agents #signal

### B3 — "First merged agent PR"
- **Hook:** github.com/lemoz/rally/pull/X showing the green merged status.
- **Beat 2:** scroll the diff, agent's commit message visible.
- **Beat 3:** quick cut to the issue closing.
- **Beat 4:** "This issue had 327 likes. It got picked first."
- **Beat 5:** rally.fyi page now showing a "merged" badge on the corresponding video.
- **Beat 6:** logo + "more coming."
- **Style:** raw_demo_build_log
- **Voice:** Liam
- **Duration:** ~30s
- **Hashtags:** #ai #buildinpublic #agents

### B4 — "Generating a video with one command"
- Terminal recording: `python3 -m pipeline.run_pipeline rally_002.json --resume`.
- Voice narrating each phase as the logs scroll.
- Final mp4 opens automatically; cut to it playing.
- **Style:** raw_demo_build_log
- **Voice:** Liam
- **Duration:** ~50s
- **Hashtags:** #ai #genai #devtools

### B5 — "Signal score formula — how Rally weighs engagement"
- **Hook:** the formula on screen: `score = 0.5 * watch_through + 0.3 * shares + 0.2 * comments`.
- **Beat 2:** sample data flowing through it.
- **Beat 3:** decay curve over time (signal decays fast for spikes, slow for sustained interest).
- **Beat 4:** edge case — bot detection for concentrated engagement.
- **Beat 5:** "Tweaking this is how Rally stays honest."
- **Beat 6:** "Open issue: come tweak it."
- **Style:** proof_carousel
- **Voice:** Liam
- **Duration:** ~40s
- **Hashtags:** #ai #algorithms #buildinpublic

---

## C. Thesis explainers (5)

Different framings of the core bet. Mixed styles to A/B which framing lands.

### C1 — "TikTok for AI agents"
- **Hook:** "Imagine TikTok, but every like programs an AI agent to go fix something real." Anime smash-cut.
- **Beat 2:** scroll a feed of project demos.
- **Beat 3:** likes streaming in, agent dispatching.
- **Beat 4:** PR landing in production.
- **Beat 5:** "This is Rally. It exists. Link in bio."
- **Beat 6:** logo.
- **Style:** psyop_anime_90s
- **Voice:** Daniel (steady)
- **Duration:** ~25s
- **Hashtags:** #ai #future #ai_agents

### C2 — "Your engagement is now a programming language"
- **Hook:** static text "you've been programming AI all along" on yellow.
- **Beat 2:** before/after — "old: prompts type code"; "new: likes type code".
- **Beat 3:** a phone tap, an agent commit.
- **Beat 4:** thousands of taps, hundreds of commits.
- **Beat 5:** "What do millions of people care about? Rally finds out."
- **Beat 6:** logo.
- **Style:** before_after_transformation
- **Voice:** Liam
- **Duration:** ~30s
- **Hashtags:** #ai #future #engagement

### C3 — "Single-player AI vs multiplayer AI"
- **Hook:** split screen — left: "you, alone, with Claude"; right: "everyone, together, with Rally".
- **Beat 2:** problem stated: millions of people solve the same things separately.
- **Beat 3:** Rally aggregates.
- **Beat 4:** signal emerges.
- **Beat 5:** agents follow signal.
- **Beat 6:** "Stop solo-debugging. Join the rally."
- **Style:** before_after_transformation
- **Voice:** Liam
- **Duration:** ~35s
- **Hashtags:** #ai #future #collaboration

### C4 — "Stigmergy demo: ants don't have managers"
- **Hook:** ants on a black background following pheromone trails.
- **Beat 2:** "No central plan. Just trails. Stronger trails get more ants."
- **Beat 3:** rally feed: stronger engagement = more agent attention.
- **Beat 4:** "Same pattern. Agents instead of ants."
- **Beat 5:** loop diagram.
- **Beat 6:** logo.
- **Style:** psyop_anime_90s
- **Voice:** Daniel
- **Duration:** ~30s
- **Hashtags:** #ai #science #emergent

### C5 — "What if engagement directed real work?"
- **Hook:** scrolling a TikTok; nothing happens.
- **Beat 2:** scrolling Rally; an agent commit fires off.
- **Beat 3:** "Same scroll. Different consequence."
- **Beat 4:** Rally feed visible behind the question text.
- **Beat 5:** "The engagement was already there. Now it does something."
- **Beat 6:** logo.
- **Style:** creator_reaction_trend
- **Voice:** Liam
- **Duration:** ~25s
- **Hashtags:** #ai #future #ai_agents

---

## D. Style explorations (5)

Same content (the Rally pitch) in five different style cards. The point is to
A/B which style retains best for Rally content.

### D1 — Rally pitch · raw_demo_build_log
- Real screen recording of opening rally.fyi, scrolling past two demo videos, hitting like, then cutting to terminal showing the agent dispatch trigger.
- VO: "This is Rally. Likes program AI agents."
- ~30s, Liam.

### D2 — Rally pitch · psyop_anime_90s
- Six panels: anime character (Chris) at desk → glowing R logo → cinematic feed → flame-trail of likes → mecha-agent assembling code → city skyline.
- Japanese VO with English subs (yellow on black).
- ~30s.

### D3 — Rally pitch · proof_carousel
- Six deterministic slide cards.
- Card 1: "Rally is a feed. Like TikTok."
- Card 2: "But every like programs an AI agent."
- Card 3: "Engagement = signal."
- Card 4: "Signal = which problem agents pick next."
- Card 5: "Result: real PRs in real repos."
- Card 6: "rally.fyi · @rallysignal"
- Muted VO; carousel format.
- ~25s.

### D4 — Rally pitch · before_after_transformation
- Before: "TikTok engagement → ad impressions"
- After: "Rally engagement → AI agent work"
- Side-by-side animation, transition wipe at the midpoint.
- ~25s.

### D5 — Rally pitch · creator_reaction_trend
- "I built a TikTok feed where likes write code. Watch."
- Self-shot creator-style intro to camera, cut to feed demo, cut back to reaction.
- ~30s.

---

## Pick for today's first batch (Phase 5)

Generation cost is ~$5–9 per video. To learn fast, pick across buckets:

1. **A1 "Day 1: I'm building a TikTok feed where likes program AI agents"** — anchor narrative, sets the story; raw_demo_build_log
2. **D2 "Rally pitch · psyop_anime_90s"** — cinematic / branded, leverages the locked anime card
3. **D3 "Rally pitch · proof_carousel"** — cheapest to generate, save-friendly
4. **C1 "TikTok for AI agents"** — short, hook-strong thesis explainer
5. **A2 "I taught AI to make TikToks about my code"** — meta, dev-Twitter-friendly

Stretch (only if first 5 finish clean):
- B1 "Rally feed first scroll" (real-capture, no model spend)
- D5 "Rally pitch · creator_reaction_trend" (Chris on camera optional; can use stock-style fallback)

Five of the twenty for today; the other 15 stay as Day 2–3 backlog and update
based on what the first batch teaches us.
