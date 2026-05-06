#!/usr/bin/env python3
"""Render the OpenScreen raw demo style test.

This is intentionally deterministic: real repo/homepage captures, existing demo
assets, local overlays, TTS, and FFmpeg assembly. It tests the style without
spending video-generation credits.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import textwrap
import urllib.request
from dataclasses import dataclass
from pathlib import Path

from .config import get_duration, load_all_env
from .elevenlabs_client import ElevenLabsError, ElevenLabsRetryableError, generate_speech


BASE = Path(__file__).parent.parent
REPO_ROOT = BASE.parent
OUTPUT = BASE / "output" / "openscreen_raw_demo_build_log"
CAPTURES = OUTPUT / "captures"
AUDIO = OUTPUT / "audio"
CLIPS = OUTPUT / "clips"
TEXT = OUTPUT / "text"

FONT_BOLD = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
FONT_REGULAR = "/System/Library/Fonts/Supplemental/Arial.ttf"


@dataclass(frozen=True)
class Shot:
    name: str
    kind: str
    duration: float
    vo: str
    caption: str
    source: Path | None = None
    source_start: float = 0.0


def main() -> None:
    load_all_env()
    _ensure_dirs()

    facts = _load_github_facts()
    _capture_pages()

    stars = _compact_count(int(facts["stargazers_count"]))
    forks = _compact_count(int(facts["forks_count"]))
    updated = facts["pushed_at"][:10]

    demo_clip = BASE / "project-a" / "assets" / "test_kling3_editor.mp4"
    homepage = CAPTURES / "homepage.png"
    github = CAPTURES / "github_repo.png"

    shots = [
        Shot(
            name="s01_result_first",
            kind="video",
            duration=4.2,
            source=demo_clip,
            source_start=0.0,
            vo="This is OpenScreen. It makes product demos look like a paid recorder, but it is free.",
            caption="This is free?",
        ),
        Shot(
            name="s02_what_it_is",
            kind="image",
            duration=5.0,
            source=homepage,
            vo="The project says no subscriptions, no watermarks, and free for commercial use.",
            caption="Free. Open source. No account.",
        ),
        Shot(
            name="s03_fast_demo",
            kind="video",
            duration=5.2,
            source=demo_clip,
            source_start=0.2,
            vo="You get zoom effects, annotations, and polished backgrounds without setting up a studio.",
            caption="Zoom effects + annotations",
        ),
        Shot(
            name="s04_live_proof",
            kind="image",
            duration=5.2,
            source=github,
            vo=f"The GitHub repo is live: {stars} stars, MIT licensed, and active as of {updated}.",
            caption=f"Live proof: {stars} stars",
        ),
        Shot(
            name="s05_try_before_paid",
            kind="card",
            duration=4.6,
            vo="So the test is simple: before you pay for a demo recorder, try this first.",
            caption="Try this before paying",
        ),
        Shot(
            name="s06_save_it",
            kind="card",
            duration=4.0,
            vo="Save it: github dot com slash siddharthvaddem slash openscreen.",
            caption=f"OpenScreen: {stars} stars · {forks} forks",
        ),
    ]

    rendered: list[tuple[Shot, Path, float]] = []
    for shot in shots:
        audio_path = _generate_audio(shot)
        duration = max(shot.duration, get_duration(str(audio_path)) + 0.18)
        video_path = _render_video_track(shot, duration)
        segment = CLIPS / f"{shot.name}.mp4"
        _mux_audio(video_path, audio_path, segment, duration)
        rendered.append((shot, segment, duration))

    final = OUTPUT / "final.mp4"
    _concat_segments([segment for _, segment, _ in rendered], final)
    _write_eval_metadata(rendered)
    _run_eval(final)

    print(f"Final video: {final}")


def _ensure_dirs() -> None:
    for path in (OUTPUT, CAPTURES, AUDIO, CLIPS, TEXT):
        path.mkdir(parents=True, exist_ok=True)


def _load_github_facts() -> dict:
    facts_path = OUTPUT / "github_facts.json"
    url = "https://api.github.com/repos/siddharthvaddem/openscreen"
    with urllib.request.urlopen(url, timeout=20) as response:
        facts = json.loads(response.read().decode("utf-8"))
    facts_path.write_text(json.dumps(facts, indent=2), encoding="utf-8")
    return facts


def _capture_pages() -> None:
    captures = [
        (
            "https://github.com/siddharthvaddem/openscreen",
            CAPTURES / "github_repo.png",
        ),
        (
            "https://openscreen.vercel.app",
            CAPTURES / "homepage.png",
        ),
    ]
    for url, output in captures:
        if output.exists():
            continue
        _run([
            "npx", "playwright", "screenshot",
            "--viewport-size", "1280,1600",
            "--color-scheme", "dark",
            "--wait-for-timeout", "4000",
            url,
            str(output),
        ])


def _generate_audio(shot: Shot) -> Path:
    path = AUDIO / f"{shot.name}.mp3"
    if path.exists():
        return path

    api_key = os.environ.get("ELEVENLABS_API_KEY", "")
    if api_key:
        try:
            result = generate_speech(text=shot.vo, voice="Liam", api_key=api_key)
            path.write_bytes(result.audio_bytes)
            return path
        except (ElevenLabsError, ElevenLabsRetryableError) as exc:
            print(f"ElevenLabs failed for {shot.name}, falling back to say: {exc}")

    aiff = AUDIO / f"{shot.name}.aiff"
    _run(["say", "-v", "Daniel", "-o", str(aiff), shot.vo])
    _run(["ffmpeg", "-y", "-i", str(aiff), "-codec:a", "libmp3lame", "-q:a", "4", str(path)])
    return path


def _render_video_track(shot: Shot, duration: float) -> Path:
    out = CLIPS / f"{shot.name}_video.mp4"
    if shot.kind == "video":
        assert shot.source
        filters = _base_video_filters("fill")
        filters.extend(_overlay_filters(shot))
        _run([
            "ffmpeg", "-y",
            "-stream_loop", "-1",
            "-ss", f"{shot.source_start:.3f}",
            "-i", str(shot.source),
            "-t", f"{duration:.3f}",
            "-vf", ",".join(filters),
            "-an",
            "-r", "30",
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "18",
            "-pix_fmt", "yuv420p",
            str(out),
        ])
        return out

    if shot.kind == "image":
        assert shot.source
        filters = _base_video_filters("fit")
        filters.append(_slow_zoom_filter())
        filters.append(_moving_stamp_filter(f"{shot.name}_stamp", "LIVE SOURCE", "70+170*t", "1510"))
        filters.append(_brightness_pulse_filter())
        filters.extend(_overlay_filters(shot))
        _run([
            "ffmpeg", "-y",
            "-loop", "1",
            "-i", str(shot.source),
            "-t", f"{duration:.3f}",
            "-vf", ",".join(filters),
            "-an",
            "-r", "30",
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "18",
            "-pix_fmt", "yuv420p",
            str(out),
        ])
        return out

    filters = _card_filters(shot)
    filters.append(_slow_zoom_filter())
    filters.append(_moving_stamp_filter(f"{shot.name}_stamp", "SOURCE", "70+190*t", "1220"))
    filters.append(_brightness_pulse_filter())
    _run([
        "ffmpeg", "-y",
        "-f", "lavfi",
        "-i", f"color=c=0x0b0f12:s=1080x1920:d={duration:.3f}:r=30",
        "-vf", ",".join(filters),
        "-an",
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "18",
        "-pix_fmt", "yuv420p",
        str(out),
    ])
    return out


def _base_video_filters(mode: str) -> list[str]:
    if mode == "fill":
        return [
            "scale=1080:1920:force_original_aspect_ratio=increase",
            "crop=1080:1920",
            "eq=contrast=1.06:saturation=1.05",
        ]
    return [
        "scale=1080:1660:force_original_aspect_ratio=decrease",
        "pad=1080:1920:(ow-iw)/2:(oh-ih)/2:color=0x0b0f12",
        "eq=contrast=1.04:saturation=1.02",
    ]


def _overlay_filters(shot: Shot) -> list[str]:
    title_file = _text_file(f"{shot.name}_title", shot.caption)
    route_file = _text_file(
        f"{shot.name}_route",
        "raw demo · source-backed" if shot.name != "s05_try_before_paid" else "simple test",
    )
    return [
        _draw_box("56", "80", "968", "142", "black@0.55"),
        _drawtext(title_file, 58, "white", "(w-text_w)/2", "108"),
        _drawtext(route_file, 30, "0x91ffb8", "64", "170"),
        _draw_box("56", "1632", "968", "172", "black@0.66"),
        _drawtext(_text_file(f"{shot.name}_vo", _wrap(shot.vo, 34)), 42, "white", "(w-text_w)/2", "1660"),
    ]


def _slow_zoom_filter() -> str:
    """Animate still proof assets without inventing new visual content."""
    return "zoompan=z='1+0.00035*on':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:s=1080x1920:fps=30"


def _moving_stamp_filter(name: str, text: str, x: str, y: str) -> str:
    return _drawtext(_text_file(name, text), 72, "0x91ffb8", x, y)


def _brightness_pulse_filter() -> str:
    return "eq=brightness='0.06*sin(2*PI*t)':eval=frame"


def _card_filters(shot: Shot) -> list[str]:
    if shot.name == "s05_try_before_paid":
        lines = [
            _drawtext(_text_file("s05_big", "Before you pay"), 66, "white", "(w-text_w)/2", "430"),
            _drawtext(_text_file("s05_mid", "try the free open-source recorder"), 42, "0x91ffb8", "(w-text_w)/2", "535"),
            _draw_box("110", "720", "860", "320", "0x101820@0.98"),
            _drawtext(_text_file("s05_card1", "OpenScreen"), 62, "white", "(w-text_w)/2", "790"),
            _drawtext(_text_file("s05_card2", "$0 · MIT · cross-platform"), 44, "0x91ffb8", "(w-text_w)/2", "880"),
        ]
    else:
        lines = [
            _drawtext(_text_file("s06_big", "Save this repo"), 70, "white", "(w-text_w)/2", "390"),
            _drawtext(_text_file("s06_url", "github.com/siddharthvaddem/openscreen"), 36, "0x91ffb8", "(w-text_w)/2", "510"),
            _draw_box("100", "740", "880", "390", "0x101820@0.98"),
            _drawtext(_text_file("s06_card1", shot.caption), 52, "white", "(w-text_w)/2", "825"),
            _drawtext(_text_file("s06_card2", "Free · open source · no watermarks"), 42, "0x91ffb8", "(w-text_w)/2", "930"),
        ]
    lines.append(_drawtext(_text_file(f"{shot.name}_vo", _wrap(shot.vo, 34)), 42, "white", "(w-text_w)/2", "1660"))
    return lines


def _mux_audio(video_path: Path, audio_path: Path, output_path: Path, duration: float) -> None:
    _run([
        "ffmpeg", "-y",
        "-i", str(video_path),
        "-i", str(audio_path),
        "-filter_complex", "[1:a]apad[a]",
        "-map", "0:v",
        "-map", "[a]",
        "-t", f"{duration:.3f}",
        "-c:v", "copy",
        "-c:a", "aac",
        "-ar", "44100",
        str(output_path),
    ])


def _concat_segments(segments: list[Path], output: Path) -> None:
    list_path = OUTPUT / "concat.txt"
    list_path.write_text(
        "".join(f"file '{segment.resolve()}'\n" for segment in segments),
        encoding="utf-8",
    )
    _run([
        "ffmpeg", "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", str(list_path),
        "-c", "copy",
        str(output),
    ])


def _write_eval_metadata(rendered: list[tuple[Shot, Path, float]]) -> None:
    start = 0.0
    shots = []
    for shot, _segment, duration in rendered:
        end = start + duration
        shots.append({
            "name": shot.name,
            "start_s": round(start, 2),
            "end_s": round(end, 2),
            "type": "RAW_DEMO",
            "script_description": shot.caption,
            "text_bearing": True,
        })
        start = end
    (OUTPUT / "eval_meta.json").write_text(json.dumps({"shots": shots}, indent=2), encoding="utf-8")


def _run_eval(final: Path) -> None:
    sys.path.insert(0, str(BASE))
    from eval import print_report, run_eval  # noqa: WPS433

    metadata = json.loads((OUTPUT / "eval_meta.json").read_text())
    report = run_eval(str(final), metadata)
    (OUTPUT / "eval_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print_report(report)


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


def _draw_box(x: str, y: str, width: str, height: str, color: str) -> str:
    return f"drawbox=x={x}:y={y}:w={width}:h={height}:color={color}:t=fill"


def _text_file(name: str, text: str) -> Path:
    path = TEXT / f"{name}.txt"
    path.write_text(text, encoding="utf-8")
    return path


def _wrap(text: str, width: int) -> str:
    return "\n".join(textwrap.wrap(text, width=width, break_long_words=False))


def _escape_path(path: str) -> str:
    return path.replace("\\", "\\\\").replace(":", "\\:")


def _compact_count(value: int) -> str:
    if value >= 1000:
        return f"{value / 1000:.1f}k"
    return str(value)


def _run(cmd: list[str]) -> None:
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=900)
    if result.returncode != 0:
        tail = "\n".join(result.stderr.strip().splitlines()[-8:])
        raise RuntimeError(f"Command failed ({result.returncode}): {' '.join(cmd)}\n{tail}")


if __name__ == "__main__":
    main()
