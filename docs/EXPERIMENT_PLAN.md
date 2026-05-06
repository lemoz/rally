# Rally v1: Experiment Plan

## What We're Testing

Can AI generate short-form videos about trending tech projects in styles that actually compete for engagement on TikTok, Reels, and YouTube Shorts?

Secondary: Does style matching matter? Do certain project types pair better with certain styles?

---

## The Operator

The v1 user is **not** the viewer. It's the operator: the person (Chris + Claude) running the pipeline day-to-day.

### Operator Workflow

```
1. DISCOVER    Claude surfaces trending projects + candidate styles
     ↓
2. TRIAGE      Kill weak projects early (no visual hook, stale, no angle). Don't waste pairings.
     ↓
3. MATCH       Claude proposes project × style pairings with rationale
     ↓
4. APPROVE     Chris reviews pairings, approves/rejects/modifies (with reject reasons)
     ↓
5. GENERATE    Claude kicks off video generation for approved pairings
     ↓
6. REVIEW      Chris watches generated videos, approves/rejects/requests regen (with reject reasons)
     ↓
7. PACKAGE     Assemble publish packet: final asset, caption, hashtags, platform notes, scheduled window, tracking ID
     ↓
8. PUBLISH     Approved packets go into queue. Friend pulls from queue on their schedule. Non-blocking.
     ↓
9. MEASURE     Engagement data collected across all three platforms
     ↓
10. LEARN      Analyze results, update style library, adjust pairings
```

**Approval gates (Chris decides):**
- Which projects survive triage
- Which project × style pairings to generate
- Whether a generated video is good enough to publish

**Reject reasons (codified at both gates):**
- Gate 1 (pairing approval): weak project, bad style fit, duplicate angle, too niche, not timely
- Gate 2 (video review): hook weak, pacing off, artifacting, confusing value prop, licensing risk, bad audio, bad visual clarity

Without codified reject reasons, you can't tell whether the pipeline is failing on project choice, style choice, or output quality.

**Publish is non-blocking.** Chris approves into a queue. The friend's posting timing does not stall generation or review. The queue contains complete publish packets so the friend can post independently.

**Automated (Claude does):**
- Surface trending projects daily
- Propose pairings
- Generate videos
- Assemble publish packets for approved videos
- Collect and aggregate engagement data
- Surface learnings (which styles/projects/combos work)

---

## Platforms

Post every approved video to all three:

| Platform | Role | Why |
|----------|------|-----|
| TikTok | Primary discovery | Best algo for new accounts, fastest feedback |
| Instagram Reels | Confirmation | Different audience demo, tests breadth |
| YouTube Shorts | Long tail | Longer shelf life, better analytics dashboard |

**Tracking per platform per video:**
- Views
- Watch-through rate (% who finish)
- Likes
- Comments (count + sentiment)
- Shares
- Saves
- Follower growth attributed to video

**Aggregate metrics (the ones that matter):**
- Watch-through rate (are people staying?)
- Shares + saves (are people actively engaging, not just scrolling past?)
- Cost per publishable video (total generation cost / videos that pass review)
- Turnaround time (trending project identified → video published)
- Approval rate (videos generated / videos approved for publishing)

---

## Style Library (Manual v1)

No automated style discovery system. Start with a curated library of 5-10 styles that are reproducible with current AI video generation.

### Starter Styles (research and validate these first)

1. **Voiceover + screen recording** — narrated walkthrough of a project/demo
2. **Text overlay + music** — punchy text cards with trending audio
3. **Before/after** — "what X looked like before vs. after"
4. **Explainer** — "here's how X works in 60 seconds"
5. **Hot take / reaction** — opinionated take on a trending topic
6. **Tutorial snippet** — "you can do X in 3 steps"
7. **News flash** — breaking: X just launched/happened
8. **Comparison** — "X vs Y, which is better?"

**Per style, document:**
- Visual template (what it looks like)
- Audio template (voiceover style, music, TTS voice)
- Hook pattern (first 2 seconds)
- Duration sweet spot
- Example reference videos (links to real trending videos in this style)
- AI reproducibility notes (what tools/pipeline produces this)

**Update the library based on results.** Kill styles that don't perform. Add new ones when you spot reproducible trends.

---

## Project Discovery

### Sources (Claude monitors daily)
- GitHub Trending (daily + weekly)
- Hacker News front page (top 10)
- Product Hunt (top launches)
- Reddit r/programming, r/technology, r/MachineLearning (hot posts)
- Twitter/X tech accounts (viral posts)

### Per project, capture:
- What it is (one sentence)
- Why it's interesting right now (the hook)
- Key visual elements (screenshots, demos, repo)
- The "so what" for a non-technical viewer
- Trend velocity (just launched? going viral? steady interest?)

### Standing projects:
- **Rally itself** — in exploration rotation. Dogfooding. Keep out of controlled tests until round 2 (see Test Matrix).

### Selection criteria:
- Is it visually demonstrable? (Code-only projects are harder)
- Is there a clear hook? (Why should someone care in 2 seconds?)
- Is it timely? (Trending now vs. evergreen)
- Can we add a unique angle? (Not just restating what's already out there)

---

## Test Matrix

This is the experiment. Without controlled comparisons, learnings are anecdotal.

### Test 1: Style Isolation
**Same project, 3 different styles.**

Pick 3 projects. For each, generate videos in 3 different styles. Post all variants. Compare engagement across styles for the same project.

```
Project A × Style 1, Style 2, Style 3
Project B × Style 1, Style 2, Style 3
Project C × Style 1, Style 2, Style 3
= 9 videos
```

**What this tells you:** Which styles perform best regardless of project. Whether style matching matters or one style dominates.

### Test 2: Project Isolation
**Same style, 5 different project types.**

Pick the **top 2 styles** from Test 1 (not one winner — too early to crown). Generate videos for 5 different project types (open source tool, AI demo, dev tutorial, product launch, industry news). Compare engagement.

```
Top Style A × Project Type 1, 2, 3, 4, 5
Top Style B × Project Type 1, 2, 3, 4, 5
= 10 videos
```

**What this tells you:** Which project types generate the most engagement in your best styles. Whether the top 2 styles diverge on project type (one might be better for tutorials, the other for news).

### Test 3: Volume
**Remaining capacity goes to exploration.**

After the controlled tests, fill the rest of the weekly volume (30-50 total) with best-guess pairings. These are less controlled but increase surface area for discovering what works.

**What this tells you:** At volume, do the patterns from Tests 1-2 hold? What surprises emerge?

### Stagger the tests:
- **Days 1-3:** Run Test 1 (9 controlled videos + exploration videos to fill volume)
- **Day 4:** Evaluate Test 1 results, narrow to top 2 styles (provisional — not a final verdict)
- **Days 4-7:** Run Test 2 with top 2 styles (10 controlled videos + exploration)
- **End of Week 1:** Evaluate Test 2, update style library
- **Week 2+:** Iterate. New controlled tests based on learnings. Increasing volume.

### Posting discipline for controlled tests:
- **Randomize posting times.** Don't give one variant a better slot than another. Counterbalancing across 3 platforms × 9+ videos is operationally unrealistic — randomization is good enough.
- **Keep Rally out of controlled tests in round 1.** Use Rally in exploration videos only. Founder bias and self-referential audience effects would contaminate the style comparison. Bring Rally into controlled tests in round 2 once you have baseline data.

---

## Publishing Cadence

**Target: 30-50 videos per week.**

At this volume, the pipeline needs to be fast:
- Discovery: batch of 10-15 candidate projects daily
- Matching: Claude proposes pairings, Chris approves in batch
- Generation: parallel, multiple videos generating simultaneously
- Review: Chris reviews batch, approves/rejects
- Publish: friend distributes approved videos to all 3 platforms

**Daily rhythm:**
1. Morning: Claude surfaces today's trending projects + proposed pairings
2. Chris reviews, approves/rejects batch (with reject reasons)
3. Pipeline generates throughout the day
4. Evening: Chris reviews generated videos, approves/rejects (with reject reasons)
5. Approved videos packaged into publish queue (asset + caption + hashtags + platform notes + tracking ID)
6. Friend pulls from queue on their own schedule — non-blocking

**Measurement:** Friend reports back engagement numbers per video per platform. Manual for v1. No API integration needed yet.

**Randomize posting times** across platforms. Don't try to counterbalance — just don't systematically favor one variant over another.

---

## Success Metrics

**Not vanity metrics.** Views are algorithm-dependent and tell you nothing about content quality on a new account.

### Operating Metrics (what you optimize)

| Metric | Target | Why It Matters |
|--------|--------|---------------|
| Watch-through rate | >40% average | People are staying, content is compelling |
| Shares + saves per video | Track trend | Active engagement, not passive scrolling |
| Approval rate | >60% of generated videos | Pipeline is producing usable output |
| Cost per publishable video | Track, reduce over time | Economics of the pipeline |
| Turnaround time | <24hrs from trend to post | Speed matters for trending content |

### Experiment Metrics (what you learn)

| Metric | What It Tells You |
|--------|------------------|
| Engagement variance by style (same project) | Does style matching matter? |
| Engagement variance by project (same style) | Which project types work? |
| Best style × project type combos | Where to focus |
| Platform engagement correlation | Do winners on TikTok also win on Reels/Shorts? |
| Follower growth per video (secondary) | Which videos convert watchers to followers? Available in platform analytics. |

### Evaluation Cadence (three clocks)

| Clock | What you look at | What you decide |
|-------|-----------------|----------------|
| **24h** | Hook strength, obvious failures, early watch-through | Kill clearly broken videos. Spot generation issues early. |
| **72h** | Provisional ranking across styles/projects | Choose what to test next. Narrow style candidates. Not a final verdict. |
| **7d** | Locked conclusion on style/project performance | Promote or kill styles from the library. Update pairing strategy. |

- **End of Week 1:** Full operational review. Approval rate, cost per video, turnaround time.
- **End of Week 2:** Are patterns holding at volume? Pipeline getting faster/cheaper?
- **Monthly:** Strategy review. What's working, what's not, what to change.

### Failure Thresholds

| Signal | Action |
|--------|--------|
| Approval rate <30% after week 1 | Stop scaling. Fix generation quality before producing more. |
| Turnaround >48hrs consistently | Bottleneck analysis — is it discovery, generation, review, or publishing? |
| Zero videos above 20% watch-through after 2 weeks | Styles aren't working. Pause, study what IS working on the platforms, rebuild style library. |
| Review fatigue (Chris stops reviewing same-day) | Reduce volume to sustainable level. Pipeline speed means nothing if the operator gate stalls. |

---

## What This Proves (If It Works)

1. AI-generated technical content in trending styles gets real engagement on short-form platforms
2. Style matching is measurable — some styles measurably outperform others for tech content
3. The operator workflow (discover → match → generate → review → publish) is sustainable at 30-50/week
4. Cost and turnaround are viable for ongoing operation

## What Comes Next (Not In Scope)

- Automated style discovery (replace manual library with monitoring)
- Agent-directed project selection (engagement signal replaces manual curation)
- Rally platform / feed (need proof of engagement first)
- Revenue model

---

## Publish Queue Spec

Each approved video enters the queue as a **publish packet**:

```
{
  tracking_id:      deterministic ID (project_slug + style_slug + date + variant)
  video_file:       final rendered asset (mp4, 9:16)
  caption:          platform-adapted text (Claude drafts, Chris approves)
  hashtags:         per-platform hashtag sets
  platform_notes:   any platform-specific instructions
  scheduled_window: suggested posting window (randomized)
  project:          source project name + link
  style:            style used
  test_group:       "controlled_test_1" | "controlled_test_2" | "exploration"
}
```

Friend pulls packets from a shared location (Google Drive folder, Dropbox, or similar — decide before starting). Friend posts and reports back engagement numbers per video per platform within 48h of posting.

---

## Rights & Provenance (v1 Rules)

Keep it simple. Don't let this become a blocker.

- **Screenshots/demos:** Fair use for commentary/review. Credit the project.
- **Music:** Royalty-free only. No trending copyrighted audio. Use AI-generated or licensed tracks.
- **AI-generated visuals:** Fine. No real faces without consent.
- **Project logos/branding:** Acceptable for commentary. Don't imply endorsement.
- **Code snippets:** Short excerpts for explanation only.

If in doubt, skip it and pick a different visual. Speed matters more than perfection here.

---

## Open Decisions Before Starting

- [ ] Which TTS provider / voice for v1?
- [ ] Which video generation tools for v1? (Fresh evaluation needed)
- [ ] Account names for TikTok / IG / YouTube
- [ ] Who's the friend handling distribution? Any constraints on their cadence? Where does the publish queue live (shared folder)?
- [ ] Rally branding on videos? Or anonymous/neutral brand to start?
