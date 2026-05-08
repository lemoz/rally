"""FFmpeg video assembly: normalize, xfade, subtitles, music."""
from __future__ import annotations

import os
import subprocess
import textwrap
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .config import get_duration


@dataclass
class ClipSpec:
    """Specification for one clip in the assembly."""
    video_path: str       # normalized clip or image-derived clip
    duration: float       # duration in seconds
    vo_path: Optional[str] = None
    subtitle: Optional[str] = None
    # Optional per-word caption windows in clip-relative seconds. Each entry:
    # {"text": "..", "start": float, "end": float}. When set, overrides the
    # static `subtitle` field with a sequence of timed drawtext blocks.
    caption_phrases: Optional[list[dict]] = None


@dataclass
class AssemblyResult:
    output_path: str
    total_duration: float
    shot_timestamps: list[tuple[float, float]]  # (start, end) per clip after xfade


def normalize_clip(input_path: str, output_path: str) -> str:
    """Normalize a clip to 1080x1920, 30fps, libx264."""
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg", "-y", "-i", input_path,
        "-vf", "scale=1080:1920:force_original_aspect_ratio=decrease,"
               "pad=1080:1920:(ow-iw)/2:(oh-ih)/2,fps=30",
        "-c:v", "libx264", "-preset", "fast", "-crf", "18",
        "-c:a", "aac", "-ar", "44100",
        "-shortest",
        output_path,
    ]
    _run_ffmpeg(cmd)
    return output_path


def image_to_clip(
    image_path: str,
    output_path: str,
    duration: float,
) -> str:
    """Create a video clip from a still image with Ken Burns zoom effect."""
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    frames = int(duration * 30)
    cmd = [
        "ffmpeg", "-y",
        "-loop", "1", "-i", image_path,
        "-vf", (
            f"zoompan=z='min(zoom+0.001,1.3)'"
            f":x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
            f":d={frames}:s=1080x1920:fps=30"
        ),
        "-t", str(duration),
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-preset", "fast", "-crf", "18",
        output_path,
    ]
    _run_ffmpeg(cmd)
    return output_path


def pad_clip_to_duration(
    input_path: str,
    output_path: str,
    target_duration: float,
) -> str:
    """Pad a clip by cloning the final frame until target_duration."""
    current_duration = get_duration(input_path)
    pad_duration = max(0.0, target_duration - current_duration)
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    if pad_duration <= 0.001:
        cmd = ["ffmpeg", "-y", "-i", input_path, "-c", "copy", output_path]
    else:
        cmd = [
            "ffmpeg", "-y", "-i", input_path,
            "-vf", f"tpad=stop_mode=clone:stop_duration={pad_duration:.3f}",
            "-t", f"{target_duration:.3f}",
            "-c:v", "libx264", "-preset", "fast", "-crf", "18",
            "-an",
            output_path,
        ]
    _run_ffmpeg(cmd)
    return output_path


def assemble_video(
    *,
    clips: list[ClipSpec],
    output_path: str,
    transition_duration: float = 0.4,
    music_path: Optional[str] = None,
    music_volume: float = 0.22,
) -> AssemblyResult:
    """Assemble clips into a final video with xfade, audio, subtitles, and music.

    Returns AssemblyResult with the output path and per-shot timestamps.
    """
    if not clips:
        raise ValueError("No clips to assemble")

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    durations = [c.duration for c in clips]

    if len(clips) == 1:
        return _assemble_single(clips[0], output_path, music_path, music_volume)

    # Build video filter chain. Dialogue-heavy cuts can set transition_duration=0
    # to avoid overlapping speech during visual crossfades.
    if transition_duration <= 0:
        xfade_filter, timestamps = _build_concat_chain(durations)
    else:
        xfade_filter, timestamps = _build_xfade_chain(durations, transition_duration)
    total_duration = timestamps[-1][1]

    # Build subtitle filter. Use text files rather than inline drawtext text so
    # apostrophes and line breaks cannot corrupt the filtergraph.
    subtitle_dir = Path(output_path).parent / "subtitle_text"
    sub_filters = _build_subtitle_filters(clips, timestamps, subtitle_dir)

    # Build full filtergraph
    filter_parts = [xfade_filter]
    video_label = f"[v{len(clips) - 1}]"

    if sub_filters:
        filter_parts.append(f"{video_label}{sub_filters}[vsub]")
        video_label = "[vsub]"

    filtergraph = ";".join(filter_parts)

    # Build audio: concat all VO with silence padding, then mix with music
    audio_filter, audio_inputs = _build_audio_filter(
        clips, timestamps, total_duration, music_path, music_volume,
    )
    if audio_filter:
        filtergraph += ";" + audio_filter

    # Build ffmpeg command
    cmd = ["ffmpeg", "-y"]

    # Video inputs
    for c in clips:
        cmd += ["-i", c.video_path]

    # Audio inputs (VO files)
    for c in clips:
        if c.vo_path:
            cmd += ["-i", c.vo_path]

    # Music input
    if music_path:
        cmd += ["-i", music_path]

    cmd += ["-filter_complex", filtergraph]

    # Map outputs — filtergraph output pads need brackets
    cmd += ["-map", video_label]
    if audio_filter:
        cmd += ["-map", "[aout]"]

    cmd += [
        "-c:v", "libx264", "-preset", "fast", "-crf", "18",
        "-c:a", "aac", "-ar", "44100",
        "-t", str(total_duration),
        output_path,
    ]
    _run_ffmpeg(cmd)

    return AssemblyResult(
        output_path=output_path,
        total_duration=total_duration,
        shot_timestamps=timestamps,
    )


# -- Internal helpers ------------------------------------------------------

def _assemble_single(
    clip: ClipSpec,
    output_path: str,
    music_path: Optional[str],
    music_volume: float,
) -> AssemblyResult:
    """Handle the trivial single-clip case."""
    cmd = ["ffmpeg", "-y", "-i", clip.video_path]
    filters = []
    input_idx = 1

    if clip.vo_path:
        cmd += ["-i", clip.vo_path]
        input_idx += 1

    if music_path:
        cmd += ["-i", music_path]

    # Build filters
    if clip.subtitle:
        subtitle_path = _write_subtitle_file(
            clip.subtitle,
            Path(output_path).parent / "subtitle_text",
            "single",
        )
        filters.append(_build_subtitle_drawtext(clip.subtitle, textfile_path=subtitle_path))

    if filters:
        cmd += ["-vf", ",".join(filters)]

    # Audio mixing. Use amix duration=shortest with an explicit -t cap so the
    # output never extends past the video clip when music is longer than the clip.
    if clip.vo_path and music_path:
        vo_idx = 1
        music_idx = 2
        cmd += [
            "-filter_complex",
            f"[{music_idx}:a]volume={music_volume},"
            f"afade=t=in:st=0:d=2,afade=t=out:st={max(0, clip.duration - 3):.2f}:d=3[m];"
            f"[{vo_idx}:a][m]amix=inputs=2:duration=shortest[aout]",
            "-map", "0:v", "-map", "[aout]",
        ]
    elif clip.vo_path:
        cmd += ["-map", "0:v", "-map", "1:a"]
    elif music_path:
        music_idx = 1
        cmd += [
            "-filter_complex",
            f"[{music_idx}:a]volume={music_volume}[aout]",
            "-map", "0:v", "-map", "[aout]",
        ]

    cmd += [
        "-c:v", "libx264", "-preset", "fast", "-crf", "18",
        "-c:a", "aac", "-ar", "44100",
        "-t", f"{clip.duration:.3f}",
        output_path,
    ]
    _run_ffmpeg(cmd)

    return AssemblyResult(
        output_path=output_path,
        total_duration=clip.duration,
        shot_timestamps=[(0, clip.duration)],
    )


def _build_xfade_chain(
    durations: list[float],
    transition_dur: float,
) -> tuple[str, list[tuple[float, float]]]:
    """Build the xfade filter chain for N clips.

    Returns (filtergraph_string, list_of_(start, end)_timestamps).
    """
    n = len(durations)
    parts = []
    timestamps = []

    # First xfade
    offset = durations[0] - transition_dur
    parts.append(
        f"[0:v][1:v]xfade=transition=fade:duration={transition_dur}"
        f":offset={offset:.3f}[v1]"
    )

    # Track cumulative time
    cum_start = 0.0
    timestamps.append((0.0, durations[0]))

    for i in range(2, n):
        prev_label = f"v{i - 1}"
        curr_label = f"v{i}"
        # Offset = total visible duration so far - transition_dur
        offset = sum(durations[:i]) - (i) * transition_dur + transition_dur - transition_dur
        # Simpler: offset = sum of durations[0..i-1] - (i-1)*transition_dur - transition_dur
        #        = sum(durations[:i]) - i * transition_dur
        offset = sum(durations[:i]) - i * transition_dur
        parts.append(
            f"[{prev_label}][{i}:v]xfade=transition=fade:duration={transition_dur}"
            f":offset={offset:.3f}[{curr_label}]"
        )

    # Compute timestamps accounting for xfade overlaps
    timestamps = []
    for i in range(n):
        start = sum(durations[:i]) - i * transition_dur
        if i > 0:
            start += transition_dur  # overlap region belongs to both
            start = sum(durations[:i]) - i * transition_dur
        end = start + durations[i]
        # But the effective end for the last clip is:
        # total_duration = sum(durations) - (n-1) * transition_dur
        timestamps.append((max(0, start), end))

    # Correct: actual total = sum(durations) - (n-1)*transition_dur
    total = sum(durations) - (n - 1) * transition_dur
    # Fix last timestamp
    timestamps[-1] = (timestamps[-1][0], total)

    return ";".join(parts), timestamps


def _build_concat_chain(durations: list[float]) -> tuple[str, list[tuple[float, float]]]:
    """Build a hard-cut concat filter chain for N clips."""
    input_labels = "".join(f"[{i}:v]" for i in range(len(durations)))
    output_label = f"v{len(durations) - 1}"
    parts = f"{input_labels}concat=n={len(durations)}:v=1:a=0[{output_label}]"

    timestamps = []
    start = 0.0
    for duration in durations:
        end = start + duration
        timestamps.append((start, end))
        start = end

    return parts, timestamps


def _build_subtitle_filters(
    clips: list[ClipSpec],
    timestamps: list[tuple[float, float]],
    subtitle_dir: Path,
) -> str:
    """Build chained drawtext filters for subtitles.

    Two modes per clip:
    - Per-phrase (when ClipSpec.caption_phrases set): one drawtext per phrase,
      each timed to the phrase's clip-relative window translated to global time.
      Used after Whisper word-level alignment.
    - Static (when only ClipSpec.subtitle set): one drawtext per clip held
      across the clip's full duration.
    """
    parts = []
    for idx, (clip, (start, end)) in enumerate(zip(clips, timestamps)):
        if clip.caption_phrases:
            for ph_idx, phrase in enumerate(clip.caption_phrases):
                text = phrase.get("text", "").strip()
                if not text:
                    continue
                # Phrase start/end are clip-relative; translate to global timeline.
                ph_start = start + float(phrase.get("start", 0.0))
                ph_end = start + float(phrase.get("end", 0.0))
                # Clamp to the clip window so we don't overrun shot boundaries.
                ph_start = max(start, min(ph_start, end))
                ph_end = max(start, min(ph_end, end))
                if ph_end <= ph_start:
                    continue
                phrase_path = _write_subtitle_file(
                    text, subtitle_dir, f"{idx:02d}_p{ph_idx:02d}"
                )
                parts.append(_build_subtitle_drawtext(
                    text,
                    enable=f"between(t,{ph_start:.2f},{ph_end:.2f})",
                    textfile_path=phrase_path,
                ))
        elif clip.subtitle:
            subtitle_path = _write_subtitle_file(clip.subtitle, subtitle_dir, f"{idx:02d}")
            parts.append(_build_subtitle_drawtext(
                clip.subtitle,
                enable=f"between(t,{start:.2f},{end:.2f})",
                textfile_path=subtitle_path,
            ))

    if not parts:
        return ""
    return ",".join(parts)


def _build_subtitle_drawtext(
    text: str,
    enable: Optional[str] = None,
    textfile_path: Optional[Path] = None,
) -> str:
    """Build a safe-area subtitle drawtext filter.

    Subtitles are capped to two lines where possible and placed above the
    bottom UI-safe area. The box gives anime-style subtitles readable contrast
    without letting long strings run off-frame.
    """
    wrapped = _wrap_subtitle(text)
    font_size = _subtitle_font_size(wrapped)
    text_source = (
        f"textfile={_escape_filter_path(textfile_path)}"
        if textfile_path
        else f"text='{_escape_drawtext(wrapped)}'"
    )
    parts = [
        f"drawtext={text_source}",
        f"fontsize={font_size}",
        "fontcolor=yellow",
        "line_spacing=8",
        "borderw=2",
        "bordercolor=black",
        "box=1",
        "boxcolor=black@0.72",
        "boxborderw=22",
        "x=(w-text_w)/2",
        "y=h-text_h-132",
    ]
    if enable:
        parts.append(f"enable='{enable}'")
    return ":".join(parts)


def _write_subtitle_file(text: str, subtitle_dir: Path, stem: str) -> Path:
    """Persist wrapped subtitle text for FFmpeg drawtext=textfile."""
    subtitle_dir.mkdir(parents=True, exist_ok=True)
    path = subtitle_dir / f"{stem}.txt"
    path.write_text(_wrap_subtitle(text), encoding="utf-8")
    return path


def _wrap_subtitle(text: str) -> str:
    """Wrap subtitles for vertical 1080px output."""
    cleaned = " ".join(text.split())
    if not cleaned:
        return ""

    max_chars = 30
    lines = textwrap.wrap(
        cleaned,
        width=max_chars,
        break_long_words=False,
        break_on_hyphens=False,
    )

    if len(lines) <= 2:
        return "\n".join(lines)

    # Re-wrap a bit wider before falling back to three lines.
    lines = textwrap.wrap(
        cleaned,
        width=38,
        break_long_words=False,
        break_on_hyphens=False,
    )
    return "\n".join(lines[:3])


def _subtitle_font_size(text: str) -> int:
    """Choose a subtitle font size that stays inside the lower-third box."""
    lines = text.splitlines() or [text]
    longest = max(len(line) for line in lines)
    if len(lines) >= 3:
        return 34
    if longest > 34:
        return 38
    return 44


def _build_audio_filter(
    clips: list[ClipSpec],
    timestamps: list[tuple[float, float]],
    total_duration: float,
    music_path: Optional[str],
    music_volume: float,
) -> tuple[str, int]:
    """Build audio mixing filter.

    Returns (filter_string, number_of_extra_audio_inputs).
    """
    n_video = len(clips)
    vo_entries = []
    audio_idx = n_video  # audio inputs start after video inputs

    for clip, (start, _end) in zip(clips, timestamps):
        if clip.vo_path:
            vo_entries.append((audio_idx, start))
            audio_idx += 1

    if not vo_entries and not music_path:
        return "", 0

    parts = []
    mix_labels = []

    # Delay each VO to its shot start time
    for idx, (input_idx, start_time) in enumerate(vo_entries):
        delay_ms = int(start_time * 1000)
        label = f"vo{idx}"
        parts.append(f"[{input_idx}:a]adelay={delay_ms}|{delay_ms}[{label}]")
        mix_labels.append(f"[{label}]")

    # Mix all VO tracks
    if len(mix_labels) > 1:
        parts.append(
            f"{''.join(mix_labels)}amix=inputs={len(mix_labels)}"
            f":duration=longest:normalize=0[vmix]"
        )
        vo_label = "[vmix]"
    elif mix_labels:
        vo_label = mix_labels[0]
    else:
        vo_label = None

    # Add music
    if music_path:
        music_idx = audio_idx
        fade_out_start = max(0, total_duration - 3)
        parts.append(
            f"[{music_idx}:a]volume={music_volume},"
            f"afade=t=in:st=0:d=2,"
            f"afade=t=out:st={fade_out_start:.2f}:d=3[music]"
        )
        if vo_label:
            parts.append(f"{vo_label}[music]amix=inputs=2:duration=longest:normalize=0[aout]")
        else:
            parts.append(f"[music]anull[aout]")
    elif vo_label:
        # Rename vo label to aout
        if vo_label == "[vmix]":
            parts[-1] = parts[-1].replace("[vmix]", "[aout]")
        else:
            # Single VO, rename
            parts[-1] = parts[-1].replace(vo_label.strip("[]"), "aout")
            parts[-1] = parts[-1].rstrip(f"[{vo_label.strip('[]')}]")
            # Simpler: just re-label
            idx_str, start = vo_entries[0]
            delay_ms = int(start * 1000)
            parts[-1] = f"[{idx_str}:a]adelay={delay_ms}|{delay_ms}[aout]"

    return ";".join(parts), audio_idx - n_video + (1 if music_path else 0)


def _escape_drawtext(text: str) -> str:
    """Escape text for FFmpeg drawtext filter."""
    # Escape for FFmpeg's filter parser, not for a shell. subprocess passes the
    # filtergraph directly, so shell-style single quote escaping renders badly.
    text = text.replace("\\", "\\\\")
    text = text.replace("\n", "\\n")
    text = text.replace("'", "\\'")
    text = text.replace(":", "\\:")
    text = text.replace("%", "%%")
    return text


def _escape_filter_path(path: Path) -> str:
    """Escape a path used as an FFmpeg filter option value."""
    return str(path).replace("\\", "\\\\").replace(":", "\\:")


def _run_ffmpeg(cmd: list[str]) -> None:
    """Run an FFmpeg command, raising on failure."""
    result = subprocess.run(
        cmd,
        capture_output=True, text=True,
        timeout=600,
    )
    if result.returncode != 0:
        # Extract last 5 lines of stderr for the error message
        stderr_lines = result.stderr.strip().split("\n")
        error_tail = "\n".join(stderr_lines[-5:])
        raise RuntimeError(f"FFmpeg failed (exit {result.returncode}):\n{error_tail}")
