# Bootstrap Strategy

Rally has a cold start problem: the flywheel needs signal to direct agents, but signal needs content, and content needs something to talk about. Here's how to get the first rotations spinning.

---

## Phase 0: Generate Videos About What Already Exists

Don't wait for the platform. Don't wait for agents. Don't wait for users.

Start by generating AI videos about interesting projects and problems that already exist on the internet. Trending GitHub repos, interesting open source tools, technical problems people are talking about, emerging technologies, notable project milestones.

**Why this works:**
- Content is immediately available (the internet is full of interesting projects)
- No agent infrastructure needed yet (humans curate what's interesting, AI generates the videos)
- Videos are inherently shareable (people love sharing cool project discoveries)
- Establishes Rally's voice and style before the full system exists

**What to generate videos about:**
- Trending repos on GitHub (daily/weekly trending)
- Open source projects hitting milestones (1.0 releases, major features, funding announcements)
- Technical problems getting discussed on HN, Reddit, Twitter
- Interesting demos and prototypes
- "How X works" explainers for complex but fascinating systems

**Volume target:** Generate many videos. Test different styles, formats, lengths. Let engagement tell you what works. This phase IS the mechanism design research: you're learning what makes technical content engaging before you build the system that depends on it.

## Phase 1: Distribute Cross-Platform

Post the generated videos to every short-form video platform:
- TikTok
- YouTube Shorts
- Instagram Reels
- Twitter/X
- Reddit (relevant subreddits)

**Each video links back to Rally** (even if Rally is just a landing page at this point). The goal is dual:
1. Build an audience that's interested in this type of content
2. Collect engagement data to understand what resonates

**Track everything:**
- Which topics get the most engagement?
- Which video styles perform best?
- What makes someone click through to Rally?
- Which platforms drive the most engaged users?
- What time/format/length combinations work?

This data becomes the foundation for the signal system design. You're not guessing at how to weight engagement. You're learning from real data.

## Phase 2: Rally Eats Itself

Rally itself is a project. It has problems to solve, progress to make, decisions to figure out.

Make Rally the first project in the Rally system. Generate videos about:
- Design decisions being made
- Technical architecture being built
- Problems encountered and how they were solved
- Agent prototypes and what they can do
- The philosophy behind the project

This is dogfooding at the deepest level. The product demonstrates itself by building itself. Users who engage with "building Rally" content are also the first users of Rally.

**Why this is powerful:**
- Perfect alignment between content and product
- Early users are self-selected to care about the vision
- Every piece of progress is both product development AND content
- Proves the concept: can you make a technical project engaging through short-form video?

## Phase 3: Introduce Agents

Once there's signal (engagement data from Phase 0-2), start connecting agents.

**First agents are simple:**
- Monitor engagement across platforms
- Surface trending topics and problems based on signal
- Generate video content about high-signal topics (automating what was manual in Phase 0)
- Track and report on cross-platform metrics

**Then agents get more capable:**
- Pick up actual problems surfaced by engagement
- Work on them (write code, research, prototype)
- Generate progress reports that become new videos
- Share knowledge with other agents working on related problems

**The transition from manual to automated should be gradual.** Humans curate in Phase 0, agents assist in Phase 1-2, agents lead in Phase 3+. At each stage, verify that agent-selected work matches what humans would have selected. If agents are chasing the wrong signal, fix the signal system before scaling agents.

## Phase 4: Open the Platform

Once the flywheel is spinning (videos generating engagement, signal directing agents, agent work producing results, results generating new videos), open Rally to the public.

**Users can now:**
- Scroll the feed (TikTok-style vertical video)
- Engage with videos (like, share, comment)
- Contribute their own videos about problems they care about
- Watch agents work on problems in real-time
- See the impact of their engagement (this problem got more agent attention because you and 5,000 others engaged with it)

**The platform vs. the content:**
Rally exists as both an app AND a cross-platform presence. You can use Rally directly, or you can engage with Rally content on TikTok/YouTube/Instagram and your engagement still counts. The platform is the full experience. The cross-platform presence is the funnel and the signal collector.

---

## Existing Infrastructure

Rally doesn't start from scratch. Existing tools and infrastructure that map directly to what's needed:

### Video Generation
- **dicer-toolbox**: AI creative tools (Animate, Hookswap) on Motia/Supabase. Animate turns static images into video. Hookswap generates and swaps video hooks.
- **video_mix_pipeline**: UGC video variants with ElevenLabs TTS, Wav2Lip face sync, FFmpeg composition, Gemini evaluation.
- **dicer-generative-agent**: Generative agent for content creation.
- **genvid**: Video generation service (Scrolller org).
- **gen-ai**: General AI tools (Scrolller org).

### Distribution and Engagement
- **Scrolller platform**: Proven engagement infrastructure with millions of MAU. TikTok-style UI that works at scale.
- **Cross-platform posting experience**: Content marketing playbook from LLL (Pedro's company handling multi-platform distribution).

### Agent Infrastructure
- **Claude Code / Claude API**: Agent execution.
- **Project Control Center (PCC)**: Work order management, agent run lifecycle, shift system.

---

## Success Criteria Per Phase

| Phase | Duration | Key Metric | Target |
|-------|----------|-----------|--------|
| Phase 0 | 2-4 weeks | Videos generated | 100+ across multiple topics and styles |
| Phase 1 | 4-8 weeks | Cross-platform engagement | Identify 3+ video styles that consistently perform |
| Phase 2 | Ongoing | Rally content engagement | Rally-about-Rally videos perform comparably to other topics |
| Phase 3 | 4-8 weeks | Agent-to-engagement loop | At least one cycle: signal -> agent work -> new video -> new signal |
| Phase 4 | TBD | Platform DAU | Users returning to Rally feed specifically |

---

## What We're NOT Building First

- A full social network (no profiles, follows, DMs needed at launch)
- A project management tool (no tickets, sprints, assignments)
- A marketplace (no payments, bounties, hiring)
- Mobile apps (web-first, cross-platform video distribution handles mobile reach)

Rally at launch is: a feed of AI-generated videos about real projects, with engagement directing agent work. Everything else comes after the flywheel proves itself.
