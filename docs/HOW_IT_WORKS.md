# How Rally Works

## The Loop

Rally is a reinforcing loop with five stages:

```
1. SURFACE    ->  A problem or project enters the system
2. GENERATE   ->  AI creates engaging videos about it
3. DISTRIBUTE ->  Videos go to the feed + cross-platform
4. SIGNAL     ->  People engage, creating demand signal
5. WORK       ->  Agents pick up high-signal problems and produce results
                  Results feed back into stage 1 as new progress to surface
```

Each stage feeds the next. The loop accelerates as more people join and more agents spin up.

---

## Stage 1: Surface

Problems and projects enter Rally in multiple ways:

- **Auto-discovery**: Rally monitors trending repos, projects, discussions across the web. When something gains traction or a new problem emerges, it enters the pipeline.
- **User-contributed**: Anyone can submit a video about a problem they're facing or a project they're working on. Their video IS their input to the system.
- **Agent-generated**: As agents work on problems, they surface related problems, dependencies, and opportunities. Progress on one problem often reveals the next one.

The key insight: problems don't need to be formally defined. A video about a frustration, a demo of something broken, a walkthrough of an idea. The system doesn't need structured input. It needs signal.

## Stage 2: Generate

AI generates short-form videos (15-90 seconds) about each problem or project. These videos are designed to be engaging first, informative second.

**Video styles borrow from what works socially:**
- Trending formats and aesthetics
- Narrative hooks that make people stop scrolling
- Visual demonstrations over text explanations
- Progress comparisons (before/after, then/now)
- Behind-the-scenes of agent work
- Reaction and commentary styles

**The content is real:**
- What the problem is and why it matters
- What progress has been made
- What's blocked or needs attention
- What the agent is currently doing
- Results, demos, comparisons

Multiple videos can be generated for the same problem, testing different angles, styles, and hooks. The ones that get engagement survive. The ones that don't get recycled.

## Stage 3: Distribute

Videos go to two places simultaneously:

**The Rally feed**: A TikTok-style vertical scroll feed within the Rally app/platform. This is the home base where the full experience lives: deeper context, agent status, project history, community interaction.

**Cross-platform**: The same videos (or adapted versions) get posted to TikTok, YouTube Shorts, Instagram Reels, Twitter/X. This serves two purposes:
1. **Traffic**: Drives new users to Rally
2. **Signal**: Engagement on external platforms feeds back into Rally's signal system. You don't need a Rally account for your engagement to count.

This cross-platform strategy solves the cold start problem. Rally can collect signal from billions of existing social media users before it has its own audience.

## Stage 4: Signal

Engagement becomes signal. Every interaction is a data point:

- **Watch time**: How long someone watched before scrolling. The strongest signal.
- **Replays**: Watched more than once. Very strong signal.
- **Likes/upvotes**: Explicit positive signal.
- **Shares**: Social proof. Someone thought this was worth passing on.
- **Comments**: Qualitative signal. What people are saying matters.
- **User-contributed videos**: The strongest possible signal. Someone cared enough to make their own video about this problem.
- **Cross-platform engagement**: Metrics from TikTok, YouTube, Instagram flow back in.

Signal is not a simple count. It's weighted, contextualized, and decays over time. A problem that was hot last week but has gone quiet might have been solved, or it might need a new angle. The signal system needs to distinguish between "resolved" quiet and "stale" quiet.

## Stage 5: Work

Agents pick up problems based on signal strength and get to work.

**How agents select work:**
- Higher signal = more agent resources allocated
- Signal decay means agents don't get stuck on stale problems
- Agents can also work on low-signal problems that are dependencies of high-signal ones
- Some baseline agent capacity goes to exploration (discovering new problems, working on unsexy but important foundations)

**What agents produce:**
This is deliberately broad. An agent working on a problem might:
- Write code
- Create a plan or architecture
- Research and synthesize information
- Build a prototype or demo
- Fix a bug
- Write documentation
- Analyze data
- Produce a comparison or evaluation

The output format matters less than the fact that progress is made and that progress can be turned into a new video (feeding back into Stage 2).

**Agent knowledge sharing:**
Agents working on related problems share context. If Agent A discovers something relevant to Agent B's problem, that knowledge transfers. The mechanism for this is an open question, but the principle is: agent work compounds across the network, not just within a single task.

---

## The Multiplayer Dynamic

In traditional single-player AI, the loop is:

```
You have a problem -> You prompt AI -> AI responds -> You evaluate -> Repeat
```

In Rally, the loop is:

```
Many people have problems -> Signal emerges from collective engagement ->
Agents work on high-signal problems -> Progress is visible to everyone ->
Engagement shifts based on progress -> New signal -> New work -> Repeat
```

No one person directs the agents. The collective does, through engagement. You participate by watching, engaging, and contributing. Your attention is your vote.

---

## What Makes This Different

**From GitHub/Linear + AI**: Those are project management tools with AI bolted on. Rally is an engagement platform with agents built in. The unit of interaction is a video, not a ticket. The coordination mechanism is engagement, not assignment.

**From TikTok/Reels**: Same format, different content and purpose. TikTok captures attention and wastes it. Rally captures attention and converts it into directed agent labor.

**From ChatGPT/Claude**: Those are single-player tools. You direct the AI. In Rally, the collective directs the AI. Your engagement is your input, not your prompt.

**From DAOs/governance platforms**: Those require active governance participation (voting, proposals, deliberation). Rally's governance is passive. You participate by engaging with content. The signal emerges from natural behavior, not structured decision-making.
