# Rally Video Rubric

Formalized scoring rubric for Rally video QA. Used by `rally-poc/pipeline/video_critic.py` to score generated videos via vision model (Gemini 2.0 Flash).

## When to use

- **After every generation pipeline run** to flag bad videos before human review
- **Before posting** any video to TikTok / IG / Shorts
- **In Phase 4 style comparisons** to triangulate Chris's gut score

The output is a triangulation, not a verdict. A 9/10 from the critic does not override Chris's gut feel that something is off. A 3/10 from the critic should make Chris pause before greenlighting.

## Eight scoring axes (1-10 each)

### 1. Native-feel
Would this blend in next to 3 unrelated dev TikToks pulled from the For You feed, or would it stand out as AI-generated / overproduced / "ad-feel"?
- 10: Indistinguishable from a hand-shot Riley Brown video
- 7: Reads as polished but plausible dev creator content
- 5: Visibly AI-generated, but not embarrassing
- 3: Clearly AI slop or ad-aesthetic
- 1: Would actively damage the @rallysignal account

### 2. Hook integrity at 2s
Does a viewer, on mute, with no prior context, understand the project or get a reason to keep watching after 2 seconds?
- 10: Stop-scrolling hook on first frame; clear premise by 2s
- 7: Strong opener; premise lands by 2s but takes effort
- 5: OK opener but premise unclear at 2s
- 3: Weak opener; viewer would scroll past
- 1: No hook; first frame tells you nothing

### 3. Save-worthy moment
Is there a single frame or beat a viewer would screenshot, share, or send to a friend?
- 10: Multiple distinct save-worthy frames; the kind of video you'd send 3 people
- 7: One clear save-worthy moment with a specific timestamp
- 5: Maybe a moment, depends on viewer
- 3: No standout moment but watchable
- 1: Nothing memorable

### 4. Visual quality
Production craft of the visuals — composition, lighting, motion, color grading, brand consistency.
- 10: Pentagram-quality visual identity, brand-coherent across all panels
- 7: Strong visuals, minor inconsistencies
- 5: Watchable but generic AI-generated look
- 3: Visible AI artifacts, weak composition
- 1: Embarrassing visual quality

### 5. Audio match
Does the music + voiceover + sound design fit the video's emotional register?
- 10: Music heightens every beat; VO and visuals breathe together
- 7: Music fits the mood; minor mismatches
- 5: Music doesn't fight the video but doesn't enhance it
- 3: Music actively undermines the visual energy
- 1: Music feels copy-pasted from a different video

### 6. Pacing
Are shot durations and cuts appropriate for the platform and content?
- 10: TikTok-native pacing; never lingers, never rushes
- 7: Slightly slow or fast in 1-2 spots
- 5: Pacing feels like a corporate explainer
- 3: Drags or rushes throughout
- 1: Unwatchably bad pacing

### 7. Caption craft
Are captions present, readable, well-timed, and reinforcing the message?
- 10: Captions are the punctuation of the video; bold, well-timed, on-brand
- 7: Solid captions; readable and timed correctly
- 5: Captions present but generic or too small
- 3: Captions buggy, mis-timed, or covering important visuals
- 1: No captions or unreadable captions

### 8. Comment-CTA strength
Does the final beat give the viewer a specific, low-friction reason to comment?
- 10: Specific, clever CTA tied to the video's content (e.g. "comment 'merge' to vote")
- 7: Clear CTA but generic
- 5: CTA exists but weak ("comment your thoughts")
- 3: Unclear or missing CTA
- 1: No CTA, no engagement bait

## Overall scoring

- **Critic verdict** = simple average of 8 axes
- **Pass threshold** = ≥ 7.0 average AND no axis below 4
- **Specific failures** = any axis with score ≤ 4 must be named in the critic notes

## Output format

The critic returns JSON with this shape:

```json
{
  "video_id": "rally_007_hook_a_contrarian",
  "overall_score": 7.4,
  "verdict": "pass",
  "axes": {
    "native_feel": {"score": 6, "notes": "..."},
    "hook_integrity": {"score": 8, "notes": "..."},
    "save_worthy_moment": {"score": 7, "notes": "best frame at 0:12"},
    "visual_quality": {"score": 8, "notes": "..."},
    "audio_match": {"score": 5, "notes": "music too dark for contrarian energy"},
    "pacing": {"score": 7, "notes": "..."},
    "caption_craft": {"score": 7, "notes": "..."},
    "comment_cta_strength": {"score": 8, "notes": "..."}
  },
  "specific_failures": ["audio_match: music doesn't fit"],
  "two_word_summary": "good hook"
}
```

## Limitations

- The critic cannot judge whether a topic is interesting; only whether the video TREATS the topic well
- The critic gives no weight to whether the *content* of the video is true; that's the source-pack agent's job
- The critic does not predict view counts; that requires real engagement data
- The critic is a *triangulation*, not a verdict. A 9/10 doesn't override Chris's gut.
