#!/usr/bin/env python3
"""Render three OpenScreen style candidates.

These candidates are deterministic local renders: source-backed screenshots,
existing POC demo footage, local overlays, TTS, and FFmpeg assembly. They are
intended for style comparison before spending video-generation credits.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import textwrap
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

from .config import get_duration, load_all_env
from .elevenlabs_client import ElevenLabsError, ElevenLabsRetryableError, generate_speech


BASE = Path(__file__).parent.parent
OUTPUT_ROOT = BASE / "output" / "openscreen_style_candidates"
RAW_OUTPUT = BASE / "output" / "openscreen_raw_demo_build_log"
CAPTURES = RAW_OUTPUT / "captures"
DEMO_CLIP = BASE / "project-a" / "assets" / "test_kling3_editor.mp4"

FONT_BOLD = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
FONT_REGULAR = "/System/Library/Fonts/Supplemental/Arial.ttf"


@dataclass(frozen=True)
class Shot:
    name: str
    kind: str
    duration: float
    vo: str
    title: str
    subtitle: str = ""
    bullets: tuple[str, ...] = ()
    source: Path | None = None
    source_start: float = 0.0
    accent: str = "0x91ffb8"
    footnote: str = ""


@dataclass
class StyleRun:
    style_id: str
    shots: list[Shot]
    text_dir: Path = field(init=False)
    audio_dir: Path = field(init=False)
    clips_dir: Path = field(init=False)
    output_dir: Path = field(init=False)

    def __post_init__(self) -> None:
        self.output_dir = OUTPUT_ROOT / self.style_id
        self.text_dir = self.output_dir / "text"
        self.audio_dir = self.output_dir / "audio"
        self.clips_dir = self.output_dir / "clips"


def main() -> None:
    load_all_env()
    _ensure_shared_assets()
    facts = _load_github_facts()

    runs = [
        _proof_carousel(facts),
        _before_after_transformation(facts),
        _creator_reaction_trend(facts),
    ]
    for run in runs:
        _render_style(run)

    print("Rendered style candidates:")
    for run in runs:
        print(f"- {run.style_id}: {run.output_dir / 'final.mp4'}")


def _ensure_shared_assets() -> None:
    for path in (OUTPUT_ROOT, CAPTURES):
        path.mkdir(parents=True, exist_ok=True)
    captures = [
        ("https://github.com/siddharthvaddem/openscreen", CAPTURES / "github_repo.png"),
        ("https://openscreen.vercel.app", CAPTURES / "homepage.png"),
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


def _load_github_facts() -> dict:
    facts_path = OUTPUT_ROOT / "github_facts.json"
    url = "https://api.github.com/repos/siddharthvaddem/openscreen"
    with urllib.request.urlopen(url, timeout=20) as response:
        facts = json.loads(response.read().decode("utf-8"))
    facts_path.write_text(json.dumps(facts, indent=2), encoding="utf-8")
    return facts


def _proof_carousel(facts: dict) -> StyleRun:
    stars = _compact_count(int(facts["stargazers_count"]))
    forks = _compact_count(int(facts["forks_count"]))
    updated = facts["pushed_at"][:10]
    license_id = facts.get("license", {}).get("spdx_id", "source-backed")
    homepage = CAPTURES / "homepage.png"
    github = CAPTURES / "github_repo.png"
    return StyleRun(
        style_id="proof_carousel",
        shots=[
            Shot(
                name="s01_hook_claim",
                kind="slide_card",
                duration=4.2,
                title="The free demo recorder repo",
                subtitle=f"{stars} stars. No account required.",
                vo="OpenScreen is the rare demo recorder pitch you understand instantly: free, open source, and built for polished product demos.",
                bullets=("free", "open source", "commercial use allowed"),
                footnote="Source: GitHub repo and OpenScreen homepage",
            ),
            Shot(
                name="s02_homepage_claim",
                kind="screenshot",
                duration=4.4,
                title="It says the quiet part out loud",
                subtitle="Free. Open source. No account.",
                vo="The homepage leads with free, open source, and no account required. That is the save-worthy hook.",
                source=homepage,
                footnote="Source: openscreen.vercel.app",
            ),
            Shot(
                name="s03_demo_features",
                kind="demo_video",
                duration=5.0,
                title="The output looks social-ready",
                subtitle="zoom effects + annotations + backgrounds",
                vo="The visual promise is simple: screen recordings with zoom effects, annotations, and polished backgrounds.",
                source=DEMO_CLIP,
                source_start=0.0,
            ),
            Shot(
                name="s04_live_proof",
                kind="screenshot",
                duration=5.0,
                title=f"Live proof: {stars} stars",
                subtitle=f"{forks} forks - {license_id} - active {updated}",
                vo=f"The repo is live: {stars} stars, {forks} forks, {license_id} licensed, and active as of {updated}.",
                source=github,
                footnote="Source: GitHub API and repo page",
            ),
            Shot(
                name="s05_why_save",
                kind="slide_card",
                duration=4.2,
                title="Why save it",
                subtitle="It replaces a buying decision with a test.",
                vo="Why save it? Because before you buy another demo recorder, this gives you a credible free option to test first.",
                bullets=("no subscriptions", "no watermarks", "free for commercial use"),
                footnote="Source: project description",
            ),
            Shot(
                name="s06_try_it",
                kind="slide_card",
                duration=4.0,
                title="Try it first",
                subtitle="github.com/siddharthvaddem/openscreen",
                vo="Try it first. The repo is github dot com slash siddharthvaddem slash openscreen.",
                bullets=(f"{stars} stars", f"{forks} forks", "MIT"),
                footnote="Source: GitHub",
            ),
        ],
    )


def _before_after_transformation(facts: dict) -> StyleRun:
    stars = _compact_count(int(facts["stargazers_count"]))
    homepage = CAPTURES / "homepage.png"
    github = CAPTURES / "github_repo.png"
    return StyleRun(
        style_id="before_after_transformation",
        shots=[
            Shot(
                name="s01_after_hook",
                kind="demo_video",
                duration=4.8,
                title="AFTER: demo looks expensive",
                subtitle="show the result first",
                vo="This is the after state: a product demo that already feels polished enough to share.",
                source=DEMO_CLIP,
                source_start=0.0,
            ),
            Shot(
                name="s02_before_flat",
                kind="before_video",
                duration=4.2,
                title="BEFORE: flat screen recording",
                subtitle="tiny UI, no guided attention",
                vo="Now rewind. Most screen recordings are just a flat capture with no visual guidance.",
                source=DEMO_CLIP,
                source_start=0.2,
            ),
            Shot(
                name="s03_pain_point",
                kind="slide_card",
                duration=4.0,
                title="The viewer has to work",
                subtitle="Where do I look? Why does this matter?",
                vo="The problem is not recording. The problem is making the viewer know where to look and why it matters.",
                bullets=("no zoom cue", "weak annotations", "low share value"),
                accent="0xffb454",
            ),
            Shot(
                name="s04_intervention",
                kind="screenshot",
                duration=4.6,
                title="OpenScreen adds the layer",
                subtitle="zoom effects, annotations, backgrounds",
                vo="OpenScreen is positioned around that missing layer: zoom effects, annotations, and backgrounds.",
                source=homepage,
                footnote="Source: OpenScreen homepage",
            ),
            Shot(
                name="s05_side_by_side",
                kind="split_video",
                duration=5.2,
                title="Same demo. Different packaging.",
                subtitle="BEFORE versus AFTER",
                vo="The format is the product: same demo, but the after version packages attention instead of just capturing pixels.",
                source=DEMO_CLIP,
                source_start=0.0,
            ),
            Shot(
                name="s06_proof_payoff",
                kind="screenshot",
                duration=4.8,
                title=f"Not vaporware: {stars} stars",
                subtitle="free, open source, MIT",
                vo=f"And it is not vaporware. The GitHub repo is already at {stars} stars and MIT licensed.",
                source=github,
                footnote="Source: GitHub",
            ),
        ],
    )


def _creator_reaction_trend(facts: dict) -> StyleRun:
    stars = _compact_count(int(facts["stargazers_count"]))
    forks = _compact_count(int(facts["forks_count"]))
    homepage = CAPTURES / "homepage.png"
    github = CAPTURES / "github_repo.png"
    return StyleRun(
        style_id="creator_reaction_trend",
        shots=[
            Shot(
                name="s01_wait_free",
                kind="screenshot",
                duration=3.8,
                title="wait... this is free?",
                subtitle="OpenScreen is open source",
                vo="Wait. This is a free open-source demo recorder?",
                source=homepage,
            ),
            Shot(
                name="s02_comment_bait",
                kind="demo_video",
                duration=4.6,
                title="comment: what app is this?",
                subtitle="the answer is OpenScreen",
                vo="This is the kind of repo people ask for in the comments because the demo looks paid.",
                source=DEMO_CLIP,
                source_start=0.1,
            ),
            Shot(
                name="s03_no_account",
                kind="screenshot",
                duration=4.2,
                title="No account required",
                subtitle="that is the TikTok hook",
                vo="The no account required part is the hook. The viewer can try it without a signup wall.",
                source=homepage,
            ),
            Shot(
                name="s04_reaction_stack",
                kind="slide_card",
                duration=4.4,
                title="Why devs will save it",
                subtitle="it compresses the decision",
                vo="Why will developers save it? Because the decision is compressed into three checks.",
                bullets=("is it free?", "does it look good?", "can I use it commercially?"),
            ),
            Shot(
                name="s05_social_angle",
                kind="demo_video",
                duration=4.8,
                title="The social angle",
                subtitle="make the boring demo watchable",
                vo="The social angle is not screen recording. It is making the boring demo watchable.",
                source=DEMO_CLIP,
                source_start=0.0,
            ),
            Shot(
                name="s06_comments_next",
                kind="screenshot",
                duration=4.5,
                title=f"{stars} stars. {forks} forks.",
                subtitle="next test: real workflow capture",
                vo="If this gets comments, the next test is a real workflow capture against the paid demo tools.",
                source=github,
                footnote="Source: GitHub",
            ),
        ],
    )


def _render_style(run: StyleRun) -> None:
    for path in (run.output_dir, run.text_dir, run.audio_dir, run.clips_dir):
        path.mkdir(parents=True, exist_ok=True)

    rendered: list[tuple[Shot, Path, float]] = []
    for shot in run.shots:
        audio_path = _generate_audio(run, shot)
        duration = max(shot.duration, get_duration(str(audio_path)) + 0.18)
        video_path = _render_video_track(run, shot, duration)
        segment = run.clips_dir / f"{shot.name}.mp4"
        _mux_audio(video_path, audio_path, segment, duration)
        rendered.append((shot, segment, duration))

    final = run.output_dir / "final.mp4"
    _concat_segments(run, [segment for _, segment, _ in rendered], final)
    _write_eval_metadata(run, rendered)
    _run_eval(run, final)


def _generate_audio(run: StyleRun, shot: Shot) -> Path:
    path = run.audio_dir / f"{shot.name}.mp3"
    if path.exists():
        return path

    api_key = os.environ.get("ELEVENLABS_API_KEY", "")
    if api_key:
        try:
            result = generate_speech(text=shot.vo, voice="Liam", api_key=api_key)
            path.write_bytes(result.audio_bytes)
            return path
        except (ElevenLabsError, ElevenLabsRetryableError) as exc:
            print(f"ElevenLabs failed for {run.style_id}/{shot.name}, falling back to say: {exc}")

    aiff = run.audio_dir / f"{shot.name}.aiff"
    _run(["say", "-v", "Daniel", "-o", str(aiff), shot.vo])
    _run(["ffmpeg", "-y", "-i", str(aiff), "-codec:a", "libmp3lame", "-q:a", "4", str(path)])
    return path


def _render_video_track(run: StyleRun, shot: Shot, duration: float) -> Path:
    out = run.clips_dir / f"{shot.name}_video.mp4"
    if shot.kind == "demo_video":
        return _render_demo_video(run, shot, duration, out, mode="after")
    if shot.kind == "before_video":
        return _render_demo_video(run, shot, duration, out, mode="before")
    if shot.kind == "screenshot":
        return _render_screenshot(run, shot, duration, out)
    if shot.kind == "split_video":
        return _render_split_video(run, shot, duration, out)
    if shot.kind == "slide_card":
        return _render_slide_card(run, shot, duration, out)
    raise ValueError(f"Unknown shot kind: {shot.kind}")


def _render_demo_video(run: StyleRun, shot: Shot, duration: float, out: Path, *, mode: str) -> Path:
    assert shot.source
    filters = [
        "scale=1080:1920:force_original_aspect_ratio=increase",
        "crop=1080:1920",
        "fps=30",
    ]
    if mode == "before":
        filters.extend([
            "scale=760:1360:force_original_aspect_ratio=decrease",
            "pad=1080:1920:(ow-iw)/2:(oh-ih)/2:color=0x1b1b1b",
            "format=gray",
            "eq=contrast=0.82:brightness=-0.04",
            _brightness_pulse(),
        ])
    else:
        filters.append("eq=contrast=1.08:saturation=1.08")
    filters.extend(_standard_overlays(run, shot))
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


def _render_screenshot(run: StyleRun, shot: Shot, duration: float, out: Path) -> Path:
    assert shot.source
    filters = [
        "scale=1080:1660:force_original_aspect_ratio=decrease",
        "pad=1080:1920:(ow-iw)/2:(oh-ih)/2:color=0x0b0f12",
        "zoompan=z='1+0.00028*on':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:s=1080x1920:fps=30",
        _moving_stamp(run, shot, "LIVE SOURCE", "70+160*t", "1512"),
        _brightness_pulse(),
    ]
    filters.extend(_standard_overlays(run, shot))
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


def _render_slide_card(run: StyleRun, shot: Shot, duration: float, out: Path) -> Path:
    filters = [
        _draw_box("72", "250", "936", "900", "0x101820@0.98"),
        _draw_box("72", "250", "936", "10", f"{shot.accent}@0.95"),
        _drawtext(run, shot, "title", _wrap(shot.title, 18), 76, "white", "104", "330"),
    ]
    if shot.subtitle:
        filters.append(_drawtext(run, shot, "subtitle", _wrap(shot.subtitle, 26), 44, shot.accent, "104", "530"))

    y = 720
    for idx, bullet in enumerate(shot.bullets, start=1):
        filters.append(_drawtext(run, shot, f"bullet_{idx}", f"{idx}. {bullet}", 46, "white", "142", str(y)))
        y += 98

    if shot.footnote:
        filters.append(_drawtext(run, shot, "footnote", _wrap(shot.footnote, 38), 28, "0xa7adb8", "88", "1420"))

    filters.extend([
        _moving_stamp(run, shot, "SOURCE", "70+190*t", "1228"),
        _brightness_pulse(),
        _draw_box("56", "1632", "968", "172", "black@0.70"),
        _drawtext(run, shot, "vo", _wrap(shot.vo, 34), 42, "white", "(w-text_w)/2", "1660"),
    ])
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


def _render_split_video(run: StyleRun, shot: Shot, duration: float, out: Path) -> Path:
    assert shot.source
    title_file = _text_file(run, shot, "title", shot.title)
    subtitle_file = _text_file(run, shot, "subtitle", shot.subtitle)
    vo_file = _text_file(run, shot, "vo", _wrap(shot.vo, 34))
    filter_complex = (
        "[0:v]split=2[left][right];"
        "[left]scale=500:900:force_original_aspect_ratio=increase,crop=500:900,format=gray,eq=contrast=0.78[leftv];"
        "[right]scale=500:900:force_original_aspect_ratio=increase,crop=500:900,eq=contrast=1.12:saturation=1.12[rightv];"
        "[leftv][rightv]hstack=inputs=2[stack];"
        "[stack]pad=1080:1920:40:520:color=0x0b0f12,"
        "drawbox=x=40:y=520:w=500:h=900:color=0xff4d4d@0.12:t=fill,"
        "drawbox=x=540:y=520:w=500:h=900:color=0x91ffb8@0.12:t=fill,"
        f"{_drawtext_file(title_file, 60, 'white', '(w-text_w)/2', '150')},"
        f"{_drawtext_file(subtitle_file, 38, shot.accent, '(w-text_w)/2', '235')},"
        f"{_drawtext_literal(run, shot, 'before_label', 'BEFORE', 42, '0xff7777', '180', '1450')},"
        f"{_drawtext_literal(run, shot, 'after_label', 'AFTER', 42, '0x91ffb8', '720', '1450')},"
        "eq=brightness='0.04*sin(2*PI*t)':eval=frame,"
        "drawbox=x=56:y=1632:w=968:h=172:color=black@0.70:t=fill,"
        f"{_drawtext_file(vo_file, 42, 'white', '(w-text_w)/2', '1660')}[v]"
    )
    _run([
        "ffmpeg", "-y",
        "-stream_loop", "-1",
        "-ss", f"{shot.source_start:.3f}",
        "-i", str(shot.source),
        "-t", f"{duration:.3f}",
        "-filter_complex", filter_complex,
        "-map", "[v]",
        "-an",
        "-r", "30",
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "18",
        "-pix_fmt", "yuv420p",
        str(out),
    ])
    return out


def _standard_overlays(run: StyleRun, shot: Shot) -> list[str]:
    filters = [
        _draw_box("56", "80", "968", "158", "black@0.60"),
        _drawtext(run, shot, "title", _wrap(shot.title, 24), 54, "white", "74", "112"),
    ]
    if shot.subtitle:
        filters.append(_drawtext(run, shot, "subtitle", _wrap(shot.subtitle, 34), 32, shot.accent, "74", "182"))
    if shot.footnote:
        filters.append(_drawtext(run, shot, "footnote", _wrap(shot.footnote, 42), 26, "0xa7adb8", "70", "1548"))
    filters.extend([
        _draw_box("56", "1632", "968", "172", "black@0.70"),
        _drawtext(run, shot, "vo", _wrap(shot.vo, 34), 42, "white", "(w-text_w)/2", "1660"),
    ])
    return filters


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


def _concat_segments(run: StyleRun, segments: list[Path], output: Path) -> None:
    list_path = run.output_dir / "concat.txt"
    list_path.write_text(
        "".join(f"file '{segment.resolve()}'\n" for segment in segments),
        encoding="utf-8",
    )
    _run([
        "ffmpeg", "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", str(list_path),
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "18",
        "-c:a", "aac",
        "-ar", "44100",
        "-pix_fmt", "yuv420p",
        str(output),
    ])


def _write_eval_metadata(run: StyleRun, rendered: list[tuple[Shot, Path, float]]) -> None:
    start = 0.0
    shots = []
    for shot, _segment, duration in rendered:
        end = start + duration
        shots.append({
            "name": shot.name,
            "start_s": round(start, 2),
            "end_s": round(end, 2),
            "type": run.style_id,
            "script_description": shot.title,
            "text_bearing": True,
        })
        start = end
    (run.output_dir / "eval_meta.json").write_text(json.dumps({"shots": shots}, indent=2), encoding="utf-8")


def _run_eval(run: StyleRun, final: Path) -> None:
    sys.path.insert(0, str(BASE))
    from eval import print_report, run_eval  # noqa: WPS433

    metadata = json.loads((run.output_dir / "eval_meta.json").read_text())
    report = run_eval(str(final), metadata)
    (run.output_dir / "eval_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print_report(report)


def _draw_box(x: str, y: str, width: str, height: str, color: str) -> str:
    return f"drawbox=x={x}:y={y}:w={width}:h={height}:color={color}:t=fill"


def _drawtext(run: StyleRun, shot: Shot, key: str, text: str, fontsize: int, color: str, x: str, y: str) -> str:
    return _drawtext_file(_text_file(run, shot, key, text), fontsize, color, x, y)


def _drawtext_literal(
    run: StyleRun,
    shot: Shot,
    key: str,
    text: str,
    fontsize: int,
    color: str,
    x: str,
    y: str,
) -> str:
    return _drawtext_file(_text_file(run, shot, key, text), fontsize, color, x, y)


def _drawtext_file(textfile: Path, fontsize: int, color: str, x: str, y: str) -> str:
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


def _moving_stamp(run: StyleRun, shot: Shot, text: str, x: str, y: str) -> str:
    return _drawtext(run, shot, "moving_stamp", text, 72, shot.accent, x, y)


def _brightness_pulse() -> str:
    return "eq=brightness='0.06*sin(2*PI*t)':eval=frame"


def _text_file(run: StyleRun, shot: Shot, key: str, text: str) -> Path:
    path = run.text_dir / f"{shot.name}_{key}.txt"
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
        tail = "\n".join(result.stderr.strip().splitlines()[-12:])
        raise RuntimeError(f"Command failed ({result.returncode}): {' '.join(cmd)}\n{tail}")


if __name__ == "__main__":
    main()
