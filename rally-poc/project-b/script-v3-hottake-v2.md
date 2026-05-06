# Video 3: Project Glasswing — Hot Take (v2 - mixed media)

**Project:** Project Glasswing / Claude Mythos
**Style:** Hot Take
**Target Duration:** ~75 seconds
**Aspect Ratio:** 9:16 (1080x1920)

---

## Shot List

### Shot 1: HOOK (8s)
- **Asset type:** TEXT-TO-VIDEO
- **Prompt:** "Dark cyberpunk environment, green matrix code rain cascading down the screen, the code suddenly turns red and glitches violently, camera shakes slightly, dramatic digital corruption effect, ominous atmosphere, server room in background"
- **VO:** "An AI just found thousands of secret backdoors in every major operating system... And the company that built it says it's too dangerous to release."
- **Why T2V:** The hook needs to feel cinematic and threatening. Static text can't convey the dread. The code turning from green to red IS the story.

### Shot 2: CONTEXT (13s)
- **Asset type:** IMAGE-TO-VIDEO (animate NB2 image)
- **NB2 prompt:** "Dark cybersecurity themed graphic. Anthropic logo and Project Glasswing title at top. Scrolling source code with red highlighted vulnerability markers. Claude Mythos Preview text at bottom. Dark blue and red color scheme."
- **Video prompt:** "Code scrolls slowly upward, red vulnerability markers flash and pulse as they appear, a scanning beam sweeps across the code revealing more red highlights, ominous progression"
- **VO:** "Anthropic built a new AI model called Mythos. During testing, it autonomously discovered thousands of zero-day vulnerabilities in Windows, macOS, Linux, Chrome, Firefox... everything."
- **Why I2V:** Code scrolling with vulnerability markers lighting up is more menacing than a still.

### Shot 3: CONCEPT HERO (17s)
- **Asset type:** TEXT-TO-VIDEO + NB2 STILL (split shot)
- **T2V prompt (first 10s):** "Abstract visualization of a chain reaction, four small glowing red orbs connected by pulsing red energy beams, each orb activates the next in sequence left to right, the final connection triggers a massive red explosion of light, dark background, dramatic cybersecurity visualization"
- **NB2 still (last 7s):** Bug 1→Bug 2→Bug 3→Bug 4→FULL SYSTEM ACCESS chain diagram with "Found a 27-year-old bug for under $50"
- **VO:** "Here's what's insane. It doesn't just find bugs... it chains them together. Four separate small vulnerabilities, each harmless alone, linked into a single attack that gives full system control. It found a twenty-seven-year-old bug in OpenBSD... for less than fifty dollars of compute."
- **Why SPLIT:** The abstract chain reaction video sells the concept emotionally. Then the concrete diagram with exact text anchors it with facts. Emotion → proof.

### Shot 4: B-ROLL (12s)
- **Asset type:** IMAGE-TO-VIDEO (animate NB2 image)
- **NB2 prompt:** "$100M COMMITTED in gold text. Grid of 12 tech company logos: Apple, Microsoft, Google, AWS, NVIDIA, CrowdStrike, Cisco, Broadcom, JPMorgan Chase, Palo Alto, Linux Foundation, Intel. Dark background, gold accents."
- **Video prompt:** "The company logos illuminate one by one with golden sparkle effects, each logo glows as it activates, the $100M text shimmers, premium corporate reveal animation"
- **VO:** "Apple, Microsoft, Google, Amazon, NVIDIA... twelve companies got exclusive access. Anthropic committed a hundred million dollars to fix everything before attackers get the same capability."
- **Why I2V:** We already tested this — the logo reveal animation is fire.

### Shot 5: PROOF CARD (11s)
- **Asset type:** NB2 STILL (Ken Burns zoom)
- **NB2 prompt:** "Dark stats dashboard. Firefox Exploits Developed: 2 → 181 as centerpiece. CyberGym Success Rate 83% with progress bar. SWE-bench Verified 93.9% with progress bar. Previous model scores shown crossed out."
- **VO:** "The previous best AI model developed two Firefox exploits. Mythos developed a hundred and eighty-one. That's not incremental improvement. That's a different thing entirely."
- **Why STILL:** The 2→181 number needs to sit on screen and be absorbed. Motion would distract from the most shocking stat in the video.

### Shot 6: HOT TAKE + PAYOFF (11s)
- **Asset type:** TEXT-TO-VIDEO
- **Prompt:** "Dramatic abstract split screen, left side shows red destructive energy with shattered glass and digital corruption, right side shows blue protective energy with a glowing shield and healing code, the two sides pulse and compete, then merge into white light in the center, philosophical and cinematic"
- **VO:** "Here's the take nobody wants to hear. The same AI that can break everything... is also the only thing that can fix it fast enough. That's the paradox. And we're all living in it now."
- **Why T2V:** The paradox NEEDS to be felt, not read. Red vs blue energy merging is the visual metaphor for the entire argument. Static can't do this.

---

## Asset Generation Plan

| Shot | Type | Tool | Estimated Cost |
|------|------|------|---------------|
| 1 | T2V | Seedance 1.5 Pro | $0.13 |
| 2 | NB2 → I2V | NB2 + Seedance | $0.21 |
| 3a | T2V | Seedance 1.5 Pro | $0.13 |
| 3b | NB2 still | NB2 only | $0.08 |
| 4 | NB2 → I2V | NB2 + Seedance | $0.21 |
| 5 | NB2 still | NB2 only | $0.08 |
| 6 | T2V | Seedance 1.5 Pro | $0.13 |
| VO | 6 segments | ElevenLabs (free) | $0.00 |
| **Total** | | | **~$0.97** |

## Shot Type Summary

| Type | Count | Purpose |
|------|-------|---------|
| Text-to-video | 3 | Hook, chain reaction, paradox closer |
| Image-to-video | 2 | Code scan, partner reveal |
| NB2 still | 2 | Chain diagram (text-heavy), stats card (numbers) |
| Split shot | 1 | T2V → NB2 transition in concept hero |
