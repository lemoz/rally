"""rally_003 v2: Seedance I2V with real screenshots as first-frame seeds.

The v1 attempt (FFmpeg Ken Burns on screenshots) felt visually flat — the
mostly-black landing page screenshot fights against subtle zoom motion.
v2 uses Seedance 2.0 I2V to add organic motion to each real screenshot:
cursor movements, scroll, push-in, text reveal. Same first-person script.

Usage:
    cd rally-poc && python3 render_rally_003_v2.py
"""
from __future__ import annotations

import os
import subprocess
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from pipeline.config import load_all_env, require_key  # noqa: E402
from pipeline.elevenlabs_client import generate_speech  # noqa: E402
from pipeline.ffmpeg_assembly import (  # noqa: E402
    ClipSpec,
    assemble_video,
    normalize_clip,
)
from pipeline.gcs import upload_to_gcs  # noqa: E402
from pipeline.segmind_client import generate_video  # noqa: E402

load_all_env()
segmind_key = require_key("SEGMIND_API_KEY")
elevenlabs_key = require_key("ELEVENLABS_API_KEY")

OUTPUT_DIR = Path("output/rally_003_v2_dev_pov")
ASSETS_DIR = Path("assets/captures")
SYNTH_DIR = OUTPUT_DIR / "synth"
CLIPS_DIR = OUTPUT_DIR / "clips"
NORM_DIR = OUTPUT_DIR / "clips_norm"
AUDIO_DIR = OUTPUT_DIR / "audio"
MUSIC_DIR = Path("music")

for d in (OUTPUT_DIR, SYNTH_DIR, CLIPS_DIR, NORM_DIR, AUDIO_DIR, MUSIC_DIR):
    d.mkdir(parents=True, exist_ok=True)


# Reuse synth-image renderer from v1
def render_terminal_image(
    out_path: Path,
    title: str,
    body_lines: list[str],
    *,
    width: int = 1080,
    height: int = 1920,
) -> Path:
    from PIL import Image, ImageDraw, ImageFont

    img = Image.new("RGB", (width, height), color=(0, 0, 0))
    draw = ImageDraw.Draw(img)

    candidates = [
        "/System/Library/Fonts/Menlo.ttc",
        "/System/Library/Fonts/SFNSMono.ttf",
    ]
    title_font = body_font = None
    for path in candidates:
        if Path(path).exists():
            try:
                title_font = ImageFont.truetype(path, 56)
                body_font = ImageFont.truetype(path, 36)
                break
            except OSError:
                continue
    if title_font is None:
        title_font = ImageFont.load_default()
        body_font = ImageFont.load_default()

    yellow = (250, 204, 21)
    dim_yellow = (200, 160, 0)
    draw.text((60, 320), title, font=title_font, fill=yellow)
    y = 460
    for line in body_lines:
        color = yellow if line.startswith(">") or line.startswith("[+]") else dim_yellow
        draw.text((60, y), line, font=body_font, fill=color)
        y += 56
    img.save(out_path, "PNG")
    return out_path


SHOTS = [
    {
        "name": "s01_hook_github",
        "duration": 4,
        "image": ASSETS_DIR / "01_github_repo.png",
        "vo": "I'm building a TikTok feed where every like programs an AI agent.",
        "motion_prompt": (
            "Subtle camera push-in toward the GitHub repository page. "
            "A cursor arrow moves across the screen pointing at the README. "
            "Continuous slow forward motion, screen-recording style, 9:16 vertical."
        ),
        "subtitle": "Day 1 of Rally",
    },
    {
        "name": "s02_live_feed",
        "duration": 4,
        "image": ASSETS_DIR / "03_live_feed.png",
        "vo": "Watch this. The feed is live.",
        "motion_prompt": (
            "Slow camera push-in toward the brutalist yellow R logo at the center. "
            "Tiny yellow particles drift slowly upward. The R logo subtly pulses with light. "
            "Continuous gentle motion, dark cinematic atmosphere, 9:16 vertical."
        ),
        "subtitle": "rallysignal.co",
    },
    {
        "name": "s03_issues",
        "duration": 4,
        "image": ASSETS_DIR / "02_github_issues.png",
        "vo": "Five open issues. Each one is real work for an agent.",
        "motion_prompt": (
            "Slow vertical scroll down the GitHub issues list, revealing each issue title in turn. "
            "Cursor moves from top to bottom of the screen. "
            "Continuous downward scroll motion, screen-recording style, 9:16 vertical."
        ),
        "subtitle": "5 open agent tasks",
    },
    {
        "name": "s04_git_log",
        "duration": 4,
        "image": SYNTH_DIR / "04_git_log.png",
        "vo": "Today: eight commits, MIT license, deployed feed, three new style cards.",
        "motion_prompt": (
            "Terminal cursor blinking on a black command-line screen. "
            "Yellow text lines scroll upward slightly as if new commits are being printed. "
            "Subtle vertical scroll motion, retro terminal aesthetic, 9:16 vertical."
        ),
        "subtitle": "Day 1 shipped",
    },
    {
        "name": "s05_eval_pass",
        "duration": 4,
        "image": SYNTH_DIR / "05_eval_pass.png",
        "vo": "Tomorrow, the agent picks the highest signal issue and opens a pull request.",
        "motion_prompt": (
            "Terminal output appears line by line in yellow text on a black screen. "
            "A cursor sweeps across the bottom line as PASS appears. "
            "Subtle text-reveal motion, hacker aesthetic, 9:16 vertical."
        ),
        "subtitle": "the loop closes",
    },
    {
        "name": "s06_cta",
        "duration": 5,
        "image": SYNTH_DIR / "06_cta.png",
        "vo": "Comment merge if you'd build this.",
        "motion_prompt": (
            "The text RALLY in bold yellow pulses gently on a black background. "
            "Yellow particles drift upward across the screen. "
            "A subtle horizontal scan line sweeps from left to right. "
            "Continuous gentle motion, dramatic dark atmosphere, 9:16 vertical."
        ),
        "subtitle": "comment 'merge' to vote",
    },
]


def main() -> None:
    print("--- Rendering synthetic frames (cached) ---", flush=True)
    git_log = [
        "$ git log --oneline -8",
        "",
        "b3cb81c Ship rally_001 to live feed",
        "fb69ddf Wire rallysignal.co domain",
        "cc6f0c8 Day 1: README + DAY1 log",
        "5ff3b73 Build feed app v0: scroll + KV",
        "4b3432a Scaffold Next.js web app",
        "b240c0c Add MIT license",
        "9ed49a6 Add video pipeline POC",
        "4c6f5b9 Add architecture docs",
    ]
    if not (SYNTH_DIR / "04_git_log.png").exists():
        render_terminal_image(SYNTH_DIR / "04_git_log.png", "git log", git_log)

    eval_pass = [
        "$ python3 -m pipeline.run_pipeline rally_001",
        "",
        "[+] Phase 4: Assembly",
        "[+] Phase 5: Eval",
        "",
        "EVAL REPORT: final.mp4",
        "Overall: PASS",
        "Shots: 6 PASS / 0 WARN / 0 FAIL",
        "Avg freeze ratio: 0.0%",
        "",
        "TOTAL COST: $1.46",
    ]
    if not (SYNTH_DIR / "05_eval_pass.png").exists():
        render_terminal_image(SYNTH_DIR / "05_eval_pass.png", "eval", eval_pass)

    cta_lines = [
        "Rally is open source.",
        "",
        "github.com/lemoz/rally",
        "rallysignal.co",
        "@rallysignal",
        "",
        "comment 'merge' to vote",
        "on the next agent task.",
    ]
    if not (SYNTH_DIR / "06_cta.png").exists():
        render_terminal_image(SYNTH_DIR / "06_cta.png", "Rally", cta_lines)

    # Upload all source images to GCS once
    print("\n--- Uploading screenshots to GCS ---", flush=True)
    image_urls = {}
    for shot in SHOTS:
        local = shot["image"]
        if not local.exists():
            raise FileNotFoundError(f"Missing image: {local}")
        job_id = uuid.uuid4().hex[:8]
        url = upload_to_gcs(
            str(local),
            f"rally_003_v2_{shot['name']}_{job_id}{local.suffix}",
            prefix="rally_003_v2",
        )
        image_urls[shot["name"]] = url
        print(f"  {shot['name']} -> {url[:80]}...", flush=True)

    # Generate VO per shot (cached if exists from v1)
    print("\n--- Generating VO ---", flush=True)
    v1_audio_dir = Path("output/rally_003_dev_pov/audio")
    for shot in SHOTS:
        audio_path = AUDIO_DIR / f"{shot['name']}.mp3"
        v1_audio = v1_audio_dir / f"{shot['name']}.mp3"
        if audio_path.exists():
            print(f"[vo] cached {audio_path.name}", flush=True)
            continue
        if v1_audio.exists():
            audio_path.write_bytes(v1_audio.read_bytes())
            print(f"[vo] copied from v1: {audio_path.name}", flush=True)
            continue
        result = generate_speech(text=shot["vo"], voice="Liam", api_key=elevenlabs_key)
        audio_path.write_bytes(result.audio_bytes)
        print(f"[vo] {shot['name']} -> {audio_path.name}", flush=True)

    # Generate video per shot via Seedance I2V
    print("\n--- Generating video clips via Seedance 2.0 I2V ---", flush=True)
    for shot in SHOTS:
        clip_path = CLIPS_DIR / f"{shot['name']}.mp4"
        if clip_path.exists() and clip_path.stat().st_size > 10_000:
            print(f"[video] cached {clip_path.name}", flush=True)
            continue
        print(f"[video] {shot['name']} generating ({shot['duration']}s)...", flush=True)
        video_bytes = generate_video(
            prompt=shot["motion_prompt"],
            api_key=segmind_key,
            duration=shot["duration"],
            aspect_ratio="9:16",
            first_frame_url=image_urls[shot["name"]],
        )
        clip_path.write_bytes(video_bytes)
        print(f"[video] {shot['name']} -> {clip_path.name} ({len(video_bytes)} bytes)", flush=True)

    # Normalize clips
    print("\n--- Normalizing clips ---", flush=True)
    clip_specs: list[ClipSpec] = []
    for shot in SHOTS:
        clip_path = CLIPS_DIR / f"{shot['name']}.mp4"
        norm_path = NORM_DIR / f"{shot['name']}.mp4"
        if not norm_path.exists():
            normalize_clip(str(clip_path), str(norm_path))
        clip_specs.append(
            ClipSpec(
                video_path=str(norm_path),
                duration=shot["duration"],
                vo_path=str(AUDIO_DIR / f"{shot['name']}.mp3"),
                subtitle=shot["subtitle"],
            )
        )
        print(f"[norm] {shot['name']} -> {norm_path.name}", flush=True)

    # Assemble with same music as rally_003 v1
    print("\n--- Assembling final video ---", flush=True)
    music_path = MUSIC_DIR / "rally_003_dev_pov_score.wav"
    final_path = OUTPUT_DIR / "final.mp4"
    result = assemble_video(
        clips=clip_specs,
        output_path=str(final_path),
        transition_duration=0.0,
        music_path=str(music_path) if music_path.exists() else None,
        music_volume=0.40,
    )

    print(f"\n=== rally_003 v2 DONE ===", flush=True)
    print(f"Final: {result.output_path}", flush=True)
    print(f"Duration: {result.total_duration:.1f}s", flush=True)


if __name__ == "__main__":
    main()
