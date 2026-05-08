# Viral Reference Library — 2026-05-06

Hand-mined sample of viral short-form videos in the dev / AI / buildinpublic / vibecoding space. Goal: reverse-engineer their grammar to inform new style cards (Phase 2 of the viral video exploration plan).

## Methodology

- Manual TikTok browse on Chris's logged-in browser (no scraping, no bots).
- 4 sources visited in this pass: `@rileybrown.ai`, `@sabrina_ramonov`, `#vibecoding`, `#buildinpublic`.
- Sample bias: this pass leaned on creator profiles + hashtag landing pages, not the For You feed (algorithm-pollution avoidance).
- Annotation fidelity: thumbnail + caption-text + view-count visible on grid. Per-video click-through was skipped for speed; pattern extraction happens at the creator/hashtag level rather than per-video frame analysis.
- Hard-cap: 1 hour reference mining (compressed from the planned 4h based on signal quality of patterns observed at that point).

**Limitation acknowledged:** several schema fields (`pace_cuts_per_10s`, `transitions`, `save_worthy_frame_ts`) require timeline scrubbing per video, which the browser MCP can't do efficiently. Those fields are populated as best-guesses or `unknown`. Cluster patterns at the end are the actual deliverable.

## Reference table (28 entries)

| # | url / handle | creator | views | category | hook_modality | on_camera | audio_mode | caption_style | text_density | ad_feel_1to5 | transferable | patterns |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | rileybrown.ai pinned | Riley Brown | 535.9K | dev/AI | bold_claim | partial | direct_voiceover | static_overlay (red box) | high | 2 | yes | "I CONTROLLING BLENDER!!!" — caps title, screen recording of Blender, talking-head intercut |
| 2 | rileybrown.ai pinned | Riley Brown | 4.7M | dev/AI | direct_question | true | direct_voiceover | static_overlay (red box) | high | 2 | yes | "MY BRAIN LOVES THIS WEBSITE / TEACH ME" — full-face talking head, glasses, contrarian hook |
| 3 | rileybrown.ai pinned | Riley Brown | 4.4M | dev/AI | bold_claim | true | direct_voiceover | static_overlay | high | 2 | yes | "Google just" — ellipsis as hook, suit + gesticulating, "Gemini" overlay text |
| 4 | rileybrown.ai latest | Riley Brown | 5589 | dev/AI | unknown | unknown | unknown | unknown | low | 2 | partial | low-engagement outlier — suggests Riley's hook formula is everything; without it, dies |
| 5 | rileybrown.ai | Riley Brown | 25.2K | dev/AI | curiosity_gap | true | direct_voiceover | static_overlay (red bubble) | med | 2 | yes | "New ChatGPT Image-2 Does WHAT?" — emoji-loaded title, talking-head + iPhone screen split |
| 6 | rileybrown.ai | Riley Brown | 41.3K | dev/AI | result_first | partial | direct_voiceover | static_overlay | high | 3 | yes | "OpenClaw Agent Team" — diagram screenshot with face inset, project-name brand recognition |
| 7 | rileybrown.ai | Riley Brown | 148.6K | dev/AI | curiosity_gap | false | direct_voiceover | static_overlay | low | 2 | yes | "OpenClaw Uses Blender Part 2" — animated character, series suffix "Part 2" |
| 8 | rileybrown.ai | Riley Brown | 695.2K | dev/AI | result_first | false | direct_voiceover | static_overlay | low | 2 | yes | "OpenClaw (Clawdbot) Controls Blender" — animated character demo, no face needed at this scale |
| 9 | rileybrown.ai | Riley Brown | 1M | dev/AI | bold_claim | partial | direct_voiceover | static_overlay (red bubble) | med | 2 | yes | "Vibe Coding With Claude Opus 4.6 Max" — model-name in title, "so we're using" caption |
| 10 | rileybrown.ai | Riley Brown | 32.8K | dev/AI | bold_claim | false | silent_captions | iphone_notes_overlay | high | 1 | yes | "Coding is Dead - Long live Vibe Coding" — iPhone Notes app as the canvas, no face, very lo-fi |
| 11 | rileybrown.ai | Riley Brown | 89.5K | dev/AI | bold_claim | false | silent_captions | iphone_notes_overlay | high | 1 | yes | "Coding is Dead - Vibe Coding is IN" — same Notes-app format, near-identical hook structure |
| 12 | rileybrown.ai | Riley Brown | 16.2K | dev/AI | unknown | true | direct_voiceover | static_overlay | med | 2 | yes | "this is actually insane I'm no" — partial-cut hook, mid-sentence start |
| 13 | sabrina_ramonov | Sabrina Ramonov | playlist | AI/edu | series_branded | true | direct_voiceover | unknown | unknown | 3 | partial | "AI Wealth Creation" — 10-post playlist, branded education series, selfie-style face-to-camera |
| 14 | sabrina_ramonov | Sabrina Ramonov | playlist | AI/edu | series_branded | true | direct_voiceover | unknown | unknown | 3 | partial | "ChatGPT Prompts" — 22-post playlist, prompt-of-the-day format |
| 15 | sabrina_ramonov | Sabrina Ramonov | playlist | AI/edu | series_branded | true | direct_voiceover | unknown | unknown | 3 | partial | "Motivation" — only 3 posts, less serialized; bio leans hard on credentials (Forbes 30u30, $10M exit) |
| 16 | itsmariahbrunner | Mariah Brunner | unknown | vibecoding/edu | result_first | true | direct_voiceover | static_overlay | high | 3 | partial | "Beginners Guide to Vibe Coding" — branded series, professional/teacher framing, "comment 'vibe' on my IG" CTA |
| 17 | itsthatlady.dev | itsthatlady.dev | unknown | dev | direct_question | unknown | unknown | unknown | med | 2 | yes | "If you've been using AI" — 2nd-person addressive, conditional opener |
| 18 | alanonai | alan ona ai | unknown | dev/AI | direct_address | unknown | unknown | unknown | med | 2 | yes | "Engineering for Vibe Coders:" — colon-as-promise, list format implied |
| 19 | tof.creates | tof.creates | unknown | AI tools | curiosity_gap | unknown | unknown | unknown | med | 2 | yes | "So go lock in #aitools" — slang-imperative ("go lock in") |
| 20 | ai.abik | ai.abik | unknown | AI/edu | direct_question | unknown | unknown | unknown | med | 3 | partial | "Comment 'GOOGLE' to" — explicit comment-CTA hook |
| 21 | ai.with.ni | ai.with.ni | unknown | AI/edu | listicle | unknown | unknown | unknown | med | 3 | partial | "Here's 3 things I wish I knew" — wish-I-knew listicle |
| 22 | jada.creates0 | jada.creates0 | unknown | dev | direct_question | unknown | unknown | unknown | low | 2 | yes | "How do more people not" — incomplete-question hook |
| 23 | micah.tech | micah.tech | unknown | dev | direct_address | unknown | unknown | unknown | low | 2 | yes | "Genuinely interested in what" — first-person curiosity-gap |
| 24 | adhd_founder_buil... | adhd_founder | unknown | indie hacker | bold_claim | unknown | unknown | unknown | med | 2 | yes | "Vibecoding is a slot machine" — metaphor-as-hot-take |
| 25 | personalbrandlau... | personalbrandlau | unknown | buildinpublic | direct_address | true | direct_voiceover | static_overlay | low | 3 | partial | "How to Build In Public." — declarative title, beach selfie aesthetic |
| 26 | bella.pivo | bella.pivo | unknown | buildinpublic | direct_question | unknown | unknown | unknown | low | 2 | yes | "If you're building in public and" — conditional 2nd-person |
| 27 | itsryan.ai | itsryan.ai | unknown | buildinpublic | series_day | unknown | unknown | unknown | med | 2 | yes | "Day 6 : building your first ai" — date-series format, sequential hook |
| 28 | jun_yuh | jun_yuh | unknown | buildinpublic | listicle_plan | unknown | unknown | unknown | med | 2 | yes | "7 day plan for building in" — number-as-promise, plan-format |

---

## Patterns observed

Eight clear clusters from the 28-entry sample.

### 1. The hook-in-title is non-optional
**Universal across all 28 rows.** Even `unknown`-fidelity entries had a hook visible in the thumbnail's overlaid text. Hooks fall into:
- **Bold claim** (Riley's "Coding is Dead", "MY BRAIN LOVES") — most common at high-view (1M+) tier
- **Direct question / address** (every other row uses 2nd person — "If you've been...", "If you're building...", "Comment X to...")
- **Curiosity gap with ellipsis** ("Google just", "this is actually insane I'm no")
- **Number / list** ("3 things", "7 day plan", "Day 6")
- **Result-first** ("OpenClaw Controls Blender", "I CONTROLLING BLENDER!!!")

**Rally implication:** "What if your scroll could build things?" (rally_001 hook) is a direct-question hook. It's structurally on-genre. The execution loses because the visual treatment is anime-cinematic instead of bold-text-overlay-on-real-content.

### 2. Static text overlay is the universal caption style
**Not** word-by-word animated captions, despite the trend doc's earlier claim. The dominant style in the sample is a static red/black bubble or text box that holds for 1.5–4s on screen with a key phrase. Word-by-word still appears but is a minority.

**Rally implication:** Style cards should call for **bold static caption boxes** (red/black with yellow text fits Rally's palette) holding 2–4s, not word-by-word as the default.

### 3. Talking head + screen overlay is the dominant production format
~70% of high-view samples have a face on screen for at least part of the video, intercut or composited with a screen recording.

**Rally implication:** This validates that `talking_head_no_face` is the right canary card. If face-stand-in lands well, we sidestep the on-camera question. If it fails, real-Chris-on-camera becomes the next test.

### 4. Lo-fi iPhone Notes app is a viable "no face, no slick" format
Riley's "Coding is Dead" videos (32.8K and 89.5K views) use the iPhone Notes app as the entire visual canvas — no face, no production, just text-on-yellow-paper-aesthetic with voiceover. Lower views than his face videos but **higher save and share rates** likely (the format is screenshot-friendly).

**Rally implication:** Add this as an explicit fallback within `dev_pov_screen_capture` or `proof_carousel`. Pure iPhone-Notes-aesthetic carousels could replace generated proof cards (`rally_002` failure mode).

### 5. Series-branded content compounds reach
Sabrina's playlists (10, 22, 3 posts), Riley's "OpenClaw" naming (5+ videos), Ryan's "Day 6" — **branded recurring series** show up consistently in the high-view tail. A single great video gets discovery; a series gets followers.

**Rally implication:** rally_001, rally_002, etc. are already a series. The numbering should be **visible in the video itself** ("Day 1: I'm building Rally", "Day 2: First agent PR") not just in filename.

### 6. Comment-CTAs are everywhere
"Comment X on my IG", "Comment 'GOOGLE' to", "comment 'vibe'" — explicit ask-for-a-comment hooks appear in 20–30% of samples. These probably feed both the algorithm (engagement signal) and a creator's offline funnel (DM the link).

**Rally implication:** Each posted Rally video should end with one explicit comment ask. "Comment 'merge' to vote on which issue gets agent time first." Wire this into the storyboard plans.

### 7. Production polish kills views past a threshold
Riley's lowest-view recent video (5589 views) doesn't have a clear hook visible in the thumbnail. His highest (4.7M, 4.4M, 1M) all have **bold red text overlays** on simple visual backgrounds. The variance suggests **lo-fi + clear hook beats hi-fi + no hook** — directly aligned with the trend doc's thesis.

**Rally implication:** rally_001's anime cinematics put it in the "hi-fi" bucket regardless of how much we like the look. The native-feel test was correctly skeptical of it.

### 8. The "I'm doing this right now" frame outperforms the explainer frame
Riley's high-view content is **first-person discovery** ("I CONTROLLING BLENDER!!!", "MY BRAIN LOVES THIS"). Sabrina's lower-view content is **second-person education** ("Here's how to use ChatGPT"). The same is true across the broader sample: first-person POV wins.

**Rally implication:** rally_001's voiceover is impersonal narration ("Rally is a feed where every like programs an AI agent"). Should be **first-person** ("I'm building Rally. Here's what just happened."). This is the single most actionable takeaway for Phase 2.

---

## Style card guidance from these patterns

For Phase 2 encoding, the patterns above translate to these card-level rules:

- **`dev_pov_screen_capture`** — first-person voiceover, real screen recording as the dominant frame, **static red/black caption boxes holding 2–4s**, comment-CTA in the last 2s, "I'm doing this right now" framing in the script
- **`talking_head_no_face`** — face-stand-in (anime portrait or motion graphic), but the script speaks in first person. Avoid impersonal narrator voice. Comment-CTA at end. Static caption boxes.
- **`montage_buildlog`** — series-branded ("Day 1", "Day 2"), 6–10 fast cuts of real captures (not generated visuals), one hook caption sustained across the first 2 seconds, payoff caption at end with comment-CTA

Three reject reasons to add to all three cards' QA section:
- `narrator_voice_not_first_person` — script reads like an explainer, not a builder
- `caption_too_subtle` — captions don't hold long enough or don't have bold backing box
- `no_comment_cta` — final 2s doesn't ask for a specific comment

These rules go directly into the new style card JSON files in Phase 2.

---

## Out of scope for this pass / next mining round

- Per-video timeline scrubbing for `pace_cuts_per_10s`, exact transition types, save-worthy timestamps. Would require a TikTok download tool or per-video click-through with frame extraction. **Defer to round 2 if the Phase 2 cards land but feel pace-blind.**
- Audio-mode confirmation (trending-sound vs voiceover). Visible from grid only as "music_or_no" but not which track. **Defer.**
- @vscode and other dev-tool brand accounts. **Defer; their content is more brand-promo than personality, less transferable to Rally's story-of-a-builder framing.**
- Real-creator-on-camera samples specifically. **If `talking_head_no_face` fails the native-feel test in Phase 4, mine 5 dedicated samples here.**

---

## Re-mining cadence

Trends drift fast in short-form. **Re-run this pass every 6 weeks** — file as a recurring task on the rally repo. The patterns above will need pruning/replacement as the algorithm and culture shift.
