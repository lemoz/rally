#!/usr/bin/env python3
"""Render a genuinely different OpenScreen candidate: 90s anime drama.

This uses generated anime shots for the visual world and deterministic local
cards for source-backed repo facts. It is intentionally not another screen-demo
variant.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path

from .config import get_duration, load_all_env, require_key, snap_duration
from .elevenlabs_client import ElevenLabsError, ElevenLabsRetryableError, generate_speech
from .ffmpeg_assembly import ClipSpec, assemble_video, normalize_clip
from .segmind_client import SegmindError, SegmindRetryableError, generate_video


BASE = Path(__file__).parent.parent
OUTPUT = BASE / "output" / "openscreen_anime_90s"
CLIPS = OUTPUT / "clips"
CLIPS_NORM = OUTPUT / "clips_norm"
AUDIO = OUTPUT / "audio"
TEXT = OUTPUT / "text"

FONT_BOLD = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
MAX_RETRIES = 3
RETRY_DELAY = 8


@dataclass(frozen=True)
class Shot:
    name: str
    kind: str
    duration_s: int
    voice: str
    vo_ja: str
    subtitle: str
    video_prompt: str = ""


def main() -> None:
    load_all_env()
    _ensure_dirs()

    facts = _load_github_facts()
    shots = _build_shots(facts)

    elevenlabs_key = require_key("ELEVENLABS_API_KEY")
    segmind_key = require_key("SEGMIND_API_KEY")

    print(f"Rendering OpenScreen anime candidate -> {OUTPUT}")
    _generate_audio(shots, elevenlabs_key)
    _generate_visuals(shots, segmind_key, facts)
    final = _assemble(shots)
    _run_eval(final, shots)
    print(f"Final video: {final}")


def _ensure_dirs() -> None:
    for path in (OUTPUT, CLIPS, CLIPS_NORM, AUDIO, TEXT):
        path.mkdir(parents=True, exist_ok=True)


def _load_github_facts() -> dict:
    facts_path = OUTPUT / "github_facts.json"
    url = "https://api.github.com/repos/siddharthvaddem/openscreen"
    with urllib.request.urlopen(url, timeout=20) as response:
        facts = json.loads(response.read().decode("utf-8"))
    facts_path.write_text(json.dumps(facts, indent=2), encoding="utf-8")
    return facts


def _build_shots(facts: dict) -> list[Shot]:
    stars = _compact_count(int(facts["stargazers_count"]))
    forks = _compact_count(int(facts["forks_count"]))
    license_id = facts.get("license", {}).get("spdx_id", "MIT")
    updated = facts["pushed_at"][:10]
    return [
        Shot(
            name="s01_hook_eye",
            kind="t2v",
            duration_s=5,
            voice="Alice",
            vo_ja="待って。これは本当に無料なの？",
            subtitle="Wait. This demo recorder is actually free?",
            video_prompt=(
                "Extreme close-up on a young developer's anime eyes at night, green code and a glowing screen "
                "reflected in both pupils, shocked expression, old CRT monitor flicker, dark 90s cel-shaded anime, "
                "Ghost in the Shell mood, cold blue shadows with emerald highlights, slow push-in, eyes blink once, "
                "no readable text, vertical 9:16"
            ),
        ),
        Shot(
            name="s02_flat_recording",
            kind="t2v",
            duration_s=5,
            voice="Liam",
            vo_ja="普通の画面録画は、見せ場がどこか分からない。",
            subtitle="Normal screen recordings make the viewer do the work.",
            video_prompt=(
                "A tired anime developer watches a dull gray screen recording floating in a dark room, tiny UI panels "
                "and a wandering cursor, bored expression, the room feels flat and lifeless, 90s cel-shaded anime, "
                "subtle camera drift, no readable text, vertical 9:16"
            ),
        ),
        Shot(
            name="s03_openscreen_arrives",
            kind="t2v",
            duration_s=5,
            voice="Alice",
            vo_ja="そこに、オープンソースのデモ編集レイヤーが現れる。",
            subtitle="Then an open-source demo layer appears.",
            video_prompt=(
                "The same dark anime desk erupts with emerald light as an open-source software spirit appears from "
                "the laptop screen, cursor trails turn into clean zoom frames and annotation boxes, cinematic reveal, "
                "90s cel-shaded anime, dramatic green glow, speed lines, no readable text, vertical 9:16"
            ),
        ),
        Shot(
            name="s04_demo_transforms",
            kind="t2v",
            duration_s=5,
            voice="Liam",
            vo_ja="同じ画面でも、ズームと注釈で一気に見やすくなる。",
            subtitle="Same screen. Zooms and annotations make it watchable.",
            video_prompt=(
                "Anime visualization of a boring screen recording transforming into a polished vertical product demo, "
                "cursor movement becomes bright motion trails, zoom boxes snap into place, background becomes clean and "
                "cinematic, high-energy 90s anime transformation sequence, emerald and blue lighting, no readable text, "
                "vertical 9:16"
            ),
        ),
        Shot(
            name="s05_source_proof",
            kind="proof_card",
            duration_s=6,
            voice="Daniel",
            vo_ja=f"証拠もある。GitHubで{stars}スター、{forks}フォーク、ライセンスは{license_id}。",
            subtitle=f"Source proof: {stars} stars, {forks} forks, {license_id} license.",
            video_prompt=f"{stars} stars|{forks} forks|{license_id}|active {updated}",
        ),
        Shot(
            name="s06_payoff_city",
            kind="t2v",
            duration_s=5,
            voice="Alice",
            vo_ja="有料ツールを買う前に、まずこれを試して。",
            subtitle="Before buying a paid recorder, try this first.",
            video_prompt=(
                "Final 90s anime rooftop shot at night, young developer holds a glowing laptop over a neon city, "
                "emerald light forms a stylized open-source constellation in the sky, hopeful dramatic ending, "
                "slow zoom out, cel-shaded anime, film grain, no readable text, vertical 9:16"
            ),
        ),
    ]


def _generate_audio(shots: list[Shot], api_key: str) -> None:
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = {
            pool.submit(_generate_one_audio, shot, api_key): shot.name
            for shot in shots
            if not _audio_path(shot).exists()
        }
        for future in as_completed(futures):
            name = futures[future]
            future.result()
            print(f"  [{name}] audio ready")


def _generate_one_audio(shot: Shot, api_key: str) -> None:
    path = _audio_path(shot)
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            result = generate_speech(text=shot.vo_ja, voice=shot.voice, api_key=api_key)
            path.write_bytes(result.audio_bytes)
            return
        except (ElevenLabsRetryableError, ElevenLabsError) as exc:
            if attempt >= MAX_RETRIES or isinstance(exc, ElevenLabsError):
                raise
            print(f"  [{shot.name}] audio retry {attempt}: {exc}")
            time.sleep(RETRY_DELAY)


def _generate_visuals(shots: list[Shot], api_key: str, facts: dict) -> None:
    _render_proof_cards([shot for shot in shots if shot.kind == "proof_card"], facts)
    t2v_shots = [shot for shot in shots if shot.kind == "t2v" and not _clip_path(shot).exists()]
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = {pool.submit(_generate_one_video, shot, api_key): shot.name for shot in t2v_shots}
        for future in as_completed(futures):
            name = futures[future]
            future.result()
            print(f"  [{name}] video ready")


def _generate_one_video(shot: Shot, api_key: str) -> None:
    path = _clip_path(shot)
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            duration = snap_duration(shot.duration_s)
            print(f"  [{shot.name}] Seedance T2V {duration}s attempt {attempt}")
            data = generate_video(
                prompt=shot.video_prompt,
                api_key=api_key,
                duration=duration,
                aspect_ratio="9:16",
                resolution="720p",
            )
            path.write_bytes(data)
            return
        except SegmindRetryableError as exc:
            if attempt >= MAX_RETRIES:
                raise
            print(f"  [{shot.name}] video retry {attempt}: {exc}")
            time.sleep(RETRY_DELAY)
        except SegmindError:
            raise


def _render_proof_cards(shots: list[Shot], facts: dict) -> None:
    for shot in shots:
        path = _clip_path(shot)
        if path.exists():
            continue
        stars = _compact_count(int(facts["stargazers_count"]))
        forks = _compact_count(int(facts["forks_count"]))
        license_id = facts.get("license", {}).get("spdx_id", "MIT")
        updated = facts["pushed_at"][:10]
        filters = [
            _draw_box("72", "250", "936", "980", "0x101820@0.98"),
            _draw_box("72", "250", "936", "10", "0x91ffb8@0.95"),
            _drawtext(_text_file("proof_title", "SOURCE PROOF"), 76, "white", "104", "330"),
            _drawtext(_text_file("proof_stars", f"{stars} GitHub stars"), 62, "0x91ffb8", "124", "520"),
            _drawtext(_text_file("proof_forks", f"{forks} forks"), 52, "white", "124", "650"),
            _drawtext(_text_file("proof_license", f"{license_id} license"), 52, "white", "124", "760"),
            _drawtext(_text_file("proof_active", f"active {updated}"), 46, "0xa7adb8", "124", "880"),
            _drawtext(_text_file("proof_repo", "github.com/siddharthvaddem/openscreen"), 34, "0xa7adb8", "104", "1110"),
            _drawtext(_text_file("proof_stamp", "LIVE SOURCE"), 72, "0x91ffb8", "70+160*t", "1370"),
            "eq=brightness='0.06*sin(2*PI*t)':eval=frame",
        ]
        _run([
            "ffmpeg", "-y",
            "-f", "lavfi",
            "-i", f"color=c=0x070a10:s=1080x1920:d={shot.duration_s}:r=30",
            "-vf", ",".join(filters),
            "-an",
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "18",
            "-pix_fmt", "yuv420p",
            str(path),
        ])


def _assemble(shots: list[Shot]) -> Path:
    specs = []
    for shot in shots:
        clip = _clip_path(shot)
        norm = CLIPS_NORM / f"{shot.name}.mp4"
        if not norm.exists():
            normalize_clip(str(clip), str(norm))
        specs.append(ClipSpec(
            video_path=str(norm),
            duration=get_duration(str(norm)),
            vo_path=str(_audio_path(shot)),
            subtitle=shot.subtitle,
        ))

    result = assemble_video(
        clips=specs,
        output_path=str(OUTPUT / "final.mp4"),
        transition_duration=0.0,
        music_path=None,
    )
    metadata = {"shots": []}
    for shot, (start, end) in zip(shots, result.shot_timestamps):
        metadata["shots"].append({
            "name": shot.name,
            "start_s": round(start, 2),
            "end_s": round(end, 2),
            "type": "psyop_anime_90s",
            "script_description": shot.video_prompt,
            "text_bearing": shot.kind == "proof_card",
        })
    (OUTPUT / "eval_meta.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    return Path(result.output_path)


def _run_eval(final: Path, shots: list[Shot]) -> None:
    sys.path.insert(0, str(BASE))
    from eval import print_report, run_eval  # noqa: WPS433

    metadata = json.loads((OUTPUT / "eval_meta.json").read_text())
    report = run_eval(str(final), metadata)
    (OUTPUT / "eval_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print_report(report)


def _audio_path(shot: Shot) -> Path:
    return AUDIO / f"{shot.name}.mp3"


def _clip_path(shot: Shot) -> Path:
    return CLIPS / f"{shot.name}.mp4"


def _draw_box(x: str, y: str, width: str, height: str, color: str) -> str:
    return f"drawbox=x={x}:y={y}:w={width}:h={height}:color={color}:t=fill"


def _drawtext(textfile: Path, fontsize: int, color: str, x: str, y: str) -> str:
    return (
        "drawtext="
        f"fontfile={_escape_path(FONT_BOLD)}:"
        f"textfile={_escape_path(str(textfile))}:"
        f"fontsize={fontsize}:"
        f"fontcolor={color}:"
        "line_spacing=8:"
        "borderw=3:bordercolor=black:"
        f"x={x}:y={y}"
    )


def _text_file(name: str, text: str) -> Path:
    path = TEXT / f"{name}.txt"
    path.write_text(text, encoding="utf-8")
    return path


def _escape_path(path: str) -> str:
    return path.replace("\\", "\\\\").replace(":", "\\:")


def _compact_count(value: int) -> str:
    if value >= 1000:
        return f"{value / 1000:.1f}k"
    return str(value)


def _run(cmd: list[str]) -> None:
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=900)
    if result.returncode != 0:
        tail = "\n".join(result.stderr.strip().splitlines()[-12:])
        raise RuntimeError(f"Command failed ({result.returncode}): {' '.join(cmd)}\n{tail}")


if __name__ == "__main__":
    main()
