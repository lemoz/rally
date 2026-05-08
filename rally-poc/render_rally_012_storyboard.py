"""rally_012: storyboard-poster + single-Seedance-call architecture.

Inspired by the THE BARISTA technique (Dheepanratnam style):
- Generate one designed storyboard poster (GPT Image 2) with all 8 panels,
  consistent character, palette, lighting, and shot notes baked in.
- Pass that poster + a structured shot-list prompt to Seedance 2.0.
- Seedance interprets the poster as sequential beats and generates one
  continuous animated sequence — way better continuity than 6 separate
  I2V calls.

The Rally story: STOP BEING ALONE WITH AI. The 8-panel arc maps
single-player → multiplayer AI as a visual narrative.

Usage:
    cd rally-poc && python3 render_rally_012_storyboard.py
"""
from __future__ import annotations

import os
import sys
import time
import urllib.request
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
from pipeline.openai_image_client import generate_image  # noqa: E402
from pipeline.segmind_client import generate_video  # noqa: E402

load_all_env()
openai_key = require_key("OPENAI_API_KEY")
segmind_key = require_key("SEGMIND_API_KEY")
elevenlabs_key = require_key("ELEVENLABS_API_KEY")

OUTPUT_DIR = Path("output/rally_012_storyboard")
ASSETS_DIR = OUTPUT_DIR / "assets"
CLIPS_DIR = OUTPUT_DIR / "clips"
NORM_DIR = OUTPUT_DIR / "clips_norm"
AUDIO_DIR = OUTPUT_DIR / "audio"
MUSIC_DIR = Path("music")

for d in (OUTPUT_DIR, ASSETS_DIR, CLIPS_DIR, NORM_DIR, AUDIO_DIR, MUSIC_DIR):
    d.mkdir(parents=True, exist_ok=True)


# ===== Storyboard poster prompt (GPT Image 2) =====

STORYBOARD_POSTER_PROMPT = """\
Create a crisp, clean infographic storyboard poster for RALLY: STOP BEING ALONE WITH AI. \
Wide 16:9 layout, pure black background, bold yellow #facc15 typography, premium 3D \
stylized Pixar-quality rendering, deep cinematic moody atmosphere with electric yellow \
accents — rich blacks, glowing yellow highlights, subtle electric-blue rim lighting on \
characters, atmospheric particle effects.

Top header (large bold yellow text):
RALLY: STOP BEING ALONE WITH AI
TOTAL VIDEO TIME: 12 SECONDS
8 SHOTS · MOODY · CINEMATIC · CATHARTIC
Legend icons: ALONE, SIGNAL, AGENT, TOGETHER

Same Pixar-3D-stylized hooded young dev character throughout (call them DEV) — \
hoodie up, glasses, glowing yellow R-logo on screen behind them. Dark indie studio \
setting in alone shots. Establish character likeness in the first panel and preserve \
across all 8 panels.

8 panels arranged as 4 columns × 2 rows on a 16:9 sheet:

1. ALONE — DEV at desk in dim room, slumped, frustrated expression, single monitor \
glowing red error message reflected on glasses, single yellow R-logo dim in corner.

2. EVERYONE ALONE — pull-back wide shot revealing 30+ identical-looking devs at \
identical desks in a dark grid, all stuck on the same red error, isolated by their \
own pools of monitor light, no one connecting.

3. THE FEED — close-up of DEV's phone screen, glowing yellow Rally feed appears \
showing a vertical video preview of THE same problem, the R-logo centered, scroll \
indicator visible.

4. ENGAGEMENT — split-grid of devices across the world simultaneously tapping the \
yellow heart icon, yellow heart particles bursting out of every screen and rising \
upward like prayer flags into the dark sky.

5. CONVERGENCE — yellow heart particles converge from all directions through dark \
space toward a single luminous AI agent figure standing at a holographic terminal, \
the agent absorbing the energy.

6. AGENT WORKS — close-up of the AI agent figure assembling glowing yellow code \
blocks at a futuristic terminal, sparks flying, intense focus, code cascading on \
the screen behind.

7. PR LANDS — split-grid of the same devices from panel 4, but now showing green \
PR-merged checkmarks landing on every screen simultaneously, fix delivered to all.

8. TOGETHER — zoom back into ONE dev's room, but now their monitor shows green \
success, they smile, lean back, and behind them through the window we see the same \
30+ identical desks all glowing green — everyone solved together.

Footer (smaller yellow text):
VIDEO FLOW: 8 shots × ~1.5s = 12 seconds. Alone → Together.
CAMERA TIPS: tight close-up panels 1, 3, 6, 8; wide pull-back panels 2, 5, 7; \
split-grid panels 4, 7 with multi-device clarity.
LIGHT & STYLE: dim moody alone-shots in panels 1-2; warm yellow particle energy \
panels 3-5; bright catharsis green-yellow panels 7-8.
NOTE: this is the multiplayer-AI moment. Stop being alone. Story arc must be \
visceral relief at panel 8.
"""


# ===== Seedance video prompt (mirrors poster) =====

VIDEO_PROMPT = """\
Use the attached RALLY storyboard image as the exact reference for character, \
palette, lighting, and shot composition. Create a 12-second 9:16 vertical \
animated sequence that follows the 8-shot storyboard exactly.

Preserve the same Pixar-3D-stylized hooded young DEV character with hoodie and \
glasses throughout. Preserve the rich-black + electric-yellow + glowing-particle \
brand aesthetic. Preserve the consistent indie dev studio setting.

Rules:
- Follow the sequence exactly from panel 1 to panel 8
- One shot per panel, approximately 1.5 seconds each
- No skipped panels, no extra elements beyond the storyboard
- Maintain character continuity throughout (same dev, same studio)
- Emphasize the emotional shift from frustrated isolation to cathartic connection
- Yellow heart particles appear in panels 3-5 as the engagement signal motif
- Green checkmark and success-glow appears in panels 7-8 as resolution motif

Shot sequence:
1. DEV alone at desk, slumped, frustrated, dim red-error glow
2. Pull-back wide: 30+ identical isolated devs in dark grid, all stuck
3. Close-up of phone showing Rally feed with yellow R-logo and the same problem
4. Split-grid of devices worldwide, yellow heart particles burst from every screen
5. Particles converge through dark space onto a single luminous AI agent figure
6. AI agent assembling glowing yellow code blocks at a holographic terminal, sparks
7. Split-grid: green PR-merged checkmarks land on every device simultaneously
8. ONE dev's room, monitor green, they smile and lean back, identical desks behind \
window all glow green — solved together

Camera:
- Close-up tight panels 1, 3, 6, 8
- Wide pull-back panels 2, 5
- Split-grid multi-device clarity panels 4, 7

Style:
- Pixar-3D stylized rendering throughout
- Rich black + electric yellow #facc15 brand palette
- Dim moody alone-shots in panels 1-2
- Warm yellow particle energy panels 3-5
- Bright catharsis green-yellow panels 7-8
- Smooth satisfying cinematic cuts
- Vertical 9:16 composition, optimized for short-form video

Goal: A beautiful 12-second visual story of single-player AI becoming multiplayer \
AI — visceral relief at the final panel. Watch a tired dev reconnect with thousands \
of others through a shared solution they all engaged with.
"""


# ===== Voiceover script =====

VOICEOVER = (
    "10,000 devs are debugging the same problem right now. "
    "All alone. Nothing compounds. "
    "Until everyone engaged with one video. "
    "An agent picked it up. "
    "And shipped the fix to all of them. "
    "That's multiplayer AI. Stop being alone."
)


def main() -> None:
    print("--- 1/4 Generating storyboard poster (GPT Image 2) ---", flush=True)
    poster_path = ASSETS_DIR / "storyboard_poster.png"
    if not poster_path.exists():
        result = generate_image(
            prompt=STORYBOARD_POSTER_PROMPT,
            api_key=openai_key,
            size="1536x1024",
            quality="high",
        )
        poster_path.write_bytes(result.image_bytes)
        print(f"  saved {poster_path} ({len(result.image_bytes) // 1024} KB, ~${result.cost_usd:.2f})", flush=True)
        if result.revised_prompt:
            print(f"  revised prompt preview: {result.revised_prompt[:200]}...", flush=True)
    else:
        print(f"  cached {poster_path}", flush=True)

    print("\n--- 2/4 Uploading poster to GCS for Seedance ---", flush=True)
    job_id = uuid.uuid4().hex[:8]
    poster_url = upload_to_gcs(
        str(poster_path),
        f"rally_012_storyboard_{job_id}.png",
        prefix="rally_012",
    )
    print(f"  {poster_url[:90]}...", flush=True)

    print("\n--- 3/4 Generating video via Seedance 2.0 with storyboard reference ---", flush=True)
    video_path = CLIPS_DIR / "rally_012_seq.mp4"
    if not video_path.exists():
        video_bytes = generate_video(
            prompt=VIDEO_PROMPT,
            api_key=segmind_key,
            duration=12,
            aspect_ratio="9:16",
            first_frame_url=poster_url,
            resolution="720p",
        )
        video_path.write_bytes(video_bytes)
        print(f"  saved {video_path} ({len(video_bytes) // 1024} KB)", flush=True)
    else:
        print(f"  cached {video_path}", flush=True)

    print("\n--- 4/4 Generating VO + Assembling final ---", flush=True)
    vo_path = AUDIO_DIR / "narrator.mp3"
    if not vo_path.exists():
        vo_result = generate_speech(text=VOICEOVER, voice="Liam", api_key=elevenlabs_key)
        vo_path.write_bytes(vo_result.audio_bytes)
        print(f"  VO saved ({vo_result.char_count} chars)", flush=True)
    else:
        print(f"  VO cached", flush=True)

    norm_path = NORM_DIR / "rally_012_seq.mp4"
    if not norm_path.exists():
        normalize_clip(str(video_path), str(norm_path))

    music_path = MUSIC_DIR / "rally_001_score.wav"
    final_path = OUTPUT_DIR / "final.mp4"
    clip = ClipSpec(
        video_path=str(norm_path),
        duration=12.0,
        vo_path=str(vo_path),
        subtitle="Stop being alone with AI",
    )
    result = assemble_video(
        clips=[clip],
        output_path=str(final_path),
        transition_duration=0.0,
        music_path=str(music_path) if music_path.exists() else None,
        music_volume=0.40,
    )

    print(f"\n=== rally_012 DONE ===", flush=True)
    print(f"Final: {result.output_path}", flush=True)
    print(f"Duration: {result.total_duration:.1f}s", flush=True)


if __name__ == "__main__":
    main()
