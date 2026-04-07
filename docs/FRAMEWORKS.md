# Rally Through Three Lenses

Three frameworks help us understand how Rally works, where it's fragile, and what needs to be designed carefully.

---

## 1. The Flywheel

Rally's core loop is a flywheel: each stage generates energy that feeds the next.

```
                    +------------------+
                    |   ENGAGEMENT     |
                    |  (people watch,  |
                    |   like, share)   |
                    +--------+---------+
                             |
                    generates signal
                             |
                             v
+------------------+    +----+-------------+
|   AI-GENERATED   |    |   AGENT WORK     |
|   VIDEOS         |<---+   (agents pick   |
|   (compelling,   |    |    up problems,  |
|    trending      |    |    produce       |
|    styles)       |    |    results)      |
+--------+---------+    +------------------+
         |                       ^
         |                       |
    distributed to          directed by
    feed + cross-platform   signal strength
         |                       |
         v                       |
+--------+---------+    +--------+---------+
|   REACH          |    |   SIGNAL         |
|   (TikTok, YT,   +--->   AGGREGATION    |
|    IG, Rally      |    |   (weighted     |
|    feed)          |    |    engagement   |
+------------------+    |    metrics)      |
                        +------------------+
```

### Where the flywheel is strong:
- **Engagement to signal**: Proven mechanic. TikTok, YouTube, Instagram already do this well. The infrastructure exists.
- **Video generation**: AI video generation is commoditizing fast. Cost is dropping, quality is rising. We also have existing infrastructure (dicer-toolbox, genvid, video_mix_pipeline).
- **Cross-platform distribution**: Solves cold start. You don't need your own audience to start spinning the flywheel.

### Where the flywheel is fragile:
- **Signal to useful agent work**: This is the weakest link. Translating "this video got 50K views" into "Agent, go solve this specific problem" requires interpretation. Engagement tells you what people care about. It doesn't tell you what to do about it.
- **Agent work to compelling video**: Agents need to produce results that can be turned into engaging content. A git diff is not a TikTok. The video generation layer needs to make agent output visually compelling.
- **Early rotations**: The first few turns of the flywheel are the hardest. Before the system has signal, what do agents work on? Before agents produce results, what do videos show? The bootstrap strategy (generating videos about existing trending projects) is designed to solve this, but the transition from bootstrapped content to organic content is a critical moment.

### Flywheel acceleration:
Each new user adds signal. Each new agent adds capacity. Each new video adds reach. The flywheel gets easier to spin over time, not harder. This is the network effect. The question is whether early rotations generate enough value to attract the next user/agent/video.

---

## 2. Stigmergy

Stigmergy is how ant colonies coordinate without central command. No ant knows the plan. No ant directs other ants. Instead, ants leave chemical trails (pheromones) in the environment as they work. Other ants sense those trails and respond. Strong trails attract more ants. Weak trails are ignored. Complex collective behavior emerges from simple individual rules.

### Rally as a stigmergic system:

| Ant Colony | Rally |
|---|---|
| Pheromone trail | Engagement signal on a video |
| Ants following strong trails | Agents picking up high-signal problems |
| Trail evaporation (decay) | Signal decay over time |
| Food source discovered | Problem identified, project surfaced |
| Food brought back to colony | Agent produces results, new video generated |
| Trail reinforcement | More engagement on progress videos |

### What stigmergy teaches us:

**No central planning needed.** Rally doesn't need a product manager deciding which problems agents should work on. The signal emerges from collective engagement. Agents follow the signal. The system self-organizes.

**Signal decay is essential.** In ant colonies, pheromones evaporate. This prevents the colony from getting stuck on depleted food sources. Rally's signal must decay too. A problem that was hot last month but has gone quiet should lose agent attention. This prevents resource lock-in on stale problems and keeps the system responsive.

**Exploration vs. exploitation.** Ant colonies don't send all ants to the strongest trail. Some ants explore randomly, discovering new food sources. Rally needs the same: a percentage of agent capacity dedicated to exploration (working on low-signal but potentially important problems) rather than only exploiting high-signal ones. Without exploration, the system only works on what's already popular and misses emerging problems.

**Indirect coordination scales.** Ants don't need to communicate directly. They coordinate through the environment. Rally's agents don't need to talk to each other. They coordinate through the signal layer. This means the system can scale to thousands of agents without coordination overhead.

**Positive feedback loops can be dangerous.** Strong trails get stronger. Popular problems get more attention, which makes them more popular, which gets them more attention. Without balancing mechanisms, this leads to winner-take-all dynamics where a few problems consume all agent resources. The mechanism design layer (see below) needs to address this.

---

## 3. Mechanism Design

Mechanism design is the inverse of game theory. Instead of analyzing how people behave in an existing system, you design the rules of the system so that self-interested behavior produces good collective outcomes.

Rally's core mechanism design challenge: **How do you make engagement a reliable signal for what agents should work on, when engagement naturally drifts toward spectacle over substance?**

### The engagement-quality tension:

TikTok optimized for engagement and got cat videos. Not because people don't care about important things, but because the system didn't try to make important things engaging. Rally's bet is that AI-generated videos CAN make important things engaging. But even so, there's a risk that flashy demos outperform genuine but less visual progress.

### Design levers:

**Signal weighting.** Not all engagement is equal. Possible weights:
- Watch-through rate (watched the whole video) > likes > views
- Engagement from people who also contribute > passive engagement
- Engagement on progress videos (showing real results) > engagement on problem-statement videos
- Repeat engagement on the same project over time > one-time viral spikes

**Signal decay curves.** How fast does signal fade?
- Viral spikes should decay fast (prevents one-hit-wonder problems from consuming resources permanently)
- Sustained, steady engagement should decay slowly (indicates genuine ongoing interest)
- Engagement after agent progress should boost signal (rewards problems where work is actually happening)

**Agent allocation rules.** How agent resources map to signal:
- Not purely proportional (prevents winner-take-all)
- Floor allocation for exploration (some agents always exploring new problems)
- Ceiling on any single problem (prevents all resources going to one thing)
- Bonus allocation for problems showing momentum (engagement increasing over time)

**Anti-gaming.** Preventing manipulation of the signal:
- Bot detection on engagement
- Diverse engagement sources weighted higher than concentrated ones
- Cross-platform signal is harder to fake than single-platform
- Agent results are verifiable (did actual progress happen?)

### The deeper question:

Mechanism design for Rally goes beyond preventing bad outcomes. The real design challenge is: **can you create a system where engaging with content about important problems is genuinely more satisfying than engaging with shallow content?**

This is where video quality matters enormously. If the AI-generated videos about real problems are genuinely good, genuinely interesting, genuinely worth watching, then the mechanism design problem gets much easier. The content itself does the work. The system rules just need to prevent edge cases.

If the videos aren't compelling enough, no amount of mechanism design saves you. You're fighting human nature instead of working with it. This is why video generation quality is arguably the most critical technical component of the entire system.

---

## Implications for Building

From these three frameworks, the priorities become clear:

1. **Video quality is everything.** The flywheel won't spin if videos aren't compelling. The stigmergic signal is meaningless if nobody watches. The mechanism design falls apart if the content isn't engaging. Invest heavily in video generation.

2. **Signal design is the core IP.** How engagement maps to agent direction is what makes Rally different from TikTok (entertainment) or GitHub (project management). The signal layer is where the value is created.

3. **Start with cross-platform distribution.** Don't build the feed first. Build the video generation and post to existing platforms. Collect signal from there. Build the Rally-native feed once you have proof that the videos generate engagement.

4. **Build exploration into the system from day one.** Don't just chase high-signal problems. Allocate agent capacity to discovering new problems. This prevents the system from becoming a popularity contest.

5. **Design for signal decay.** Static systems die. Make sure yesterday's hot problem doesn't permanently consume resources. Keep the system fluid and responsive to changing interests.
