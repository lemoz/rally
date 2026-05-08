"""Multi-batch storyboard chain for renders longer than Seedance's 15s ceiling.

Splits a plan into N segments of <=12s each, generates one storyboard poster
(gpt-image-2) per segment, calls Seedance once per segment with the poster as
the first-frame seed, then stitches the segment clips with FFmpeg concat.

Each segment runs through its own audio assembly (per-shot VOs, Whisper-aligned
captions, music bed), so audio drives timing inside each segment. Segment
boundaries are hard cuts — visual punch of a new beat starting.

Usage:
    from pipeline.multi_batch import render_multi_batch
    render_multi_batch("project-rally/rally_014.json", "output/rally_014/")
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .config import load_all_env, require_key
from .elevenlabs_client import generate_speech
from .ffmpeg_assembly import (
    ClipSpec,
    assemble_video,
    normalize_clip,
)
from .gcs import upload_to_gcs
from .openai_image_client import generate_image as generate_openai_image
from .segmind_client import generate_video
from .timing import (
    DEFAULT_MAX_SEGMENT_DURATION_S,
    Segment,
    compute_total_target,
    measure_vo_durations,
    plan_segments,
    snap_shot_durations,
)
from .whisper_client import group_words_into_phrases, transcribe_with_word_timestamps


@dataclass
class MultiBatchResult:
    output_path: str
    segments: list[Segment]
    total_duration_s: float
    cost_usd: float


# -------------------- Entry point --------------------

def render_multi_batch(
    plan_path: str | Path,
    output_dir: str | Path | None = None,
    *,
    poster_prompt_builder=None,
    segment_video_prompt_builder=None,
    skip_captions: bool = False,
) -> MultiBatchResult:
    """Render a plan as a chain of Seedance segments.

    `poster_prompt_builder(plan, segment, prior_segment_recap) -> str` returns
    the gpt-image-2 prompt for the storyboard poster of one segment.

    `segment_video_prompt_builder(plan, segment, prior_segment_recap) -> str`
    returns the Seedance text prompt that mirrors the poster.

    Both have sensible defaults that derive prompts from per-shot fields
    (`image_prompt`, `video_prompt`, `vo_text`, `subtitle`).
    """
    load_all_env()
    plan_path = Path(plan_path)
    plan = json.loads(plan_path.read_text())
    shots = plan["shots"]

    output_dir = Path(output_dir or plan.get("output_dir") or f"output/{plan['project']}")
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "audio").mkdir(exist_ok=True)
    (output_dir / "segments").mkdir(exist_ok=True)
    (output_dir / "posters").mkdir(exist_ok=True)
    (output_dir / "captions").mkdir(exist_ok=True)
    (output_dir / "clips_norm").mkdir(exist_ok=True)

    openai_key = require_key("OPENAI_API_KEY")
    segmind_key = require_key("SEGMIND_API_KEY")
    elevenlabs_key = require_key("ELEVENLABS_API_KEY")

    cost = 0.0

    # 1. Generate per-shot VOs
    print("--- Multi-batch step 1: generate per-shot VOs ---", flush=True)
    for shot in shots:
        if not shot.get("vo_text"):
            continue
        out = output_dir / "audio" / f"{shot['name']}.mp3"
        if out.exists():
            print(f"  [{shot['name']}] cached", flush=True)
            continue
        result = generate_speech(
            text=shot["vo_text"],
            voice=shot.get("vo_voice", "Liam"),
            api_key=elevenlabs_key,
        )
        out.write_bytes(result.audio_bytes)
        print(f"  [{shot['name']}] {result.char_count} chars", flush=True)

    # 2. Measure + snap + plan segments
    print("\n--- Multi-batch step 2: measure VO + plan segments ---", flush=True)
    measured = measure_vo_durations(shots, str(output_dir))
    snapped = snap_shot_durations(shots, measured)
    measured_total = compute_total_target(shots, snapped, transition_duration=0)
    segments = plan_segments(shots, snapped, max_segment_duration_s=DEFAULT_MAX_SEGMENT_DURATION_S)
    print(f"  measured_total = {measured_total:.1f}s, {len(segments)} segment(s):", flush=True)
    for seg in segments:
        print(f"    {seg.segment_id}: {len(seg.shot_names)} shots, {seg.target_duration:.1f}s", flush=True)

    # 3. Per-segment generation
    print("\n--- Multi-batch step 3: generate posters + Seedance clips per segment ---", flush=True)
    poster_builder = poster_prompt_builder or _default_poster_prompt
    video_builder = segment_video_prompt_builder or _default_video_prompt
    segment_clips: list[Path] = []
    prior_recap: str | None = None
    for seg in segments:
        clip = _generate_segment(
            plan=plan,
            segment=seg,
            shots_by_name={s["name"]: s for s in shots},
            snapped=snapped,
            output_dir=output_dir,
            poster_prompt=poster_builder(plan, seg, prior_recap),
            video_prompt=video_builder(plan, seg, prior_recap),
            openai_key=openai_key,
            segmind_key=segmind_key,
        )
        segment_clips.append(clip)
        cost += 0.19  # poster
        cost += sum(snapped.get(n, 5) for n in seg.shot_names) * 0.054  # video
        prior_recap = _summarize_segment_for_recap(seg, shots_by_name={s["name"]: s for s in shots})

    # 4. Optional Whisper captions per segment (using per-segment concat audio)
    segment_caption_phrases: dict[str, Optional[list[dict]]] = {}
    if not skip_captions:
        print("\n--- Multi-batch step 4: Whisper captions per segment ---", flush=True)
        for seg in segments:
            seg_audio = output_dir / "audio" / f"{seg.segment_id}_concat.mp3"
            _concat_segment_audio(seg, output_dir, seg_audio)
            cache = output_dir / "captions" / f"{seg.segment_id}.json"
            if cache.exists():
                segment_caption_phrases[seg.segment_id] = json.loads(cache.read_text()).get("phrases")
                print(f"  [{seg.segment_id}] cached", flush=True)
                continue
            try:
                t = transcribe_with_word_timestamps(seg_audio, openai_key)
                phrases = group_words_into_phrases(t.words)
                cache.write_text(json.dumps({"text": t.text, "phrases": phrases}, indent=2))
                segment_caption_phrases[seg.segment_id] = phrases
                print(f"  [{seg.segment_id}] {len(phrases)} phrase(s)", flush=True)
            except Exception as exc:
                print(f"  [{seg.segment_id}] FAILED: {exc}", flush=True)
                segment_caption_phrases[seg.segment_id] = None

    # 5. Assemble — one ClipSpec per segment
    print("\n--- Multi-batch step 5: assembly ---", flush=True)
    music_path: Optional[str] = None
    music_volume = 0.40
    music = plan.get("music")
    if music and music.get("path"):
        mp = music["path"]
        music_path = str(Path(__file__).parent.parent / mp) if not os.path.isabs(mp) else mp
        music_volume = float(music.get("volume", music_volume))

    clip_specs: list[ClipSpec] = []
    for seg, clip_path in zip(segments, segment_clips):
        norm = output_dir / "clips_norm" / f"{seg.segment_id}.mp4"
        if not norm.exists():
            normalize_clip(str(clip_path), str(norm))
        seg_audio = output_dir / "audio" / f"{seg.segment_id}_concat.mp3"
        clip_specs.append(ClipSpec(
            video_path=str(norm),
            duration=seg.target_duration,
            vo_path=str(seg_audio) if seg_audio.exists() else None,
            subtitle=None,
            caption_phrases=segment_caption_phrases.get(seg.segment_id),
        ))

    final = output_dir / "final.mp4"
    result = assemble_video(
        clips=clip_specs,
        output_path=str(final),
        transition_duration=0.0,  # hard cuts at segment boundaries
        music_path=music_path,
        music_volume=music_volume,
    )

    print(f"\n=== Multi-batch DONE ===", flush=True)
    print(f"Final: {result.output_path}", flush=True)
    print(f"Duration: {result.total_duration:.1f}s, est. cost: ${cost:.2f}", flush=True)

    return MultiBatchResult(
        output_path=result.output_path,
        segments=segments,
        total_duration_s=result.total_duration,
        cost_usd=cost,
    )


# -------------------- Internals --------------------

def _generate_segment(
    *,
    plan: dict,
    segment: Segment,
    shots_by_name: dict[str, dict],
    snapped: dict[str, int],
    output_dir: Path,
    poster_prompt: str,
    video_prompt: str,
    openai_key: str,
    segmind_key: str,
) -> Path:
    """Produce one Seedance clip for the segment, using a generated poster as seed."""
    poster_path = output_dir / "posters" / f"{segment.segment_id}.png"
    if not poster_path.exists():
        print(f"  [{segment.segment_id}] generating poster...", flush=True)
        result = generate_openai_image(
            prompt=poster_prompt,
            api_key=openai_key,
            size="1536x1024",
            quality="high",
        )
        poster_path.write_bytes(result.image_bytes)
    else:
        print(f"  [{segment.segment_id}] poster cached", flush=True)

    clip_path = output_dir / "segments" / f"{segment.segment_id}.mp4"
    if clip_path.exists() and clip_path.stat().st_size > 10_000:
        print(f"  [{segment.segment_id}] clip cached", flush=True)
        return clip_path

    job_id = uuid.uuid4().hex[:8]
    poster_url = upload_to_gcs(
        str(poster_path),
        f"rally_multi_{segment.segment_id}_{job_id}.png",
        prefix="rally_multi",
    )

    seg_total = sum(snapped.get(n, 5) for n in segment.shot_names)
    seg_total = min(seg_total, 15)  # Seedance ceiling

    print(f"  [{segment.segment_id}] generating Seedance ({seg_total}s)...", flush=True)
    video_bytes = generate_video(
        prompt=video_prompt,
        api_key=segmind_key,
        duration=int(seg_total),
        aspect_ratio="9:16",
        first_frame_url=poster_url,
        resolution="720p",
    )
    clip_path.write_bytes(video_bytes)
    return clip_path


def _concat_segment_audio(segment: Segment, output_dir: Path, dest: Path) -> None:
    """Concatenate the segment's per-shot VO mp3s into a single mp3 with FFmpeg."""
    if dest.exists():
        return
    list_path = output_dir / "audio" / f"{segment.segment_id}_concat.txt"
    inputs = [output_dir / "audio" / f"{n}.mp3" for n in segment.shot_names]
    inputs = [p for p in inputs if p.exists()]
    if not inputs:
        return
    with list_path.open("w") as f:
        for p in inputs:
            # Escape quotes/spaces per ffmpeg concat demuxer expectations.
            safe = str(p).replace("'", r"'\''")
            f.write(f"file '{safe}'\n")
    cmd = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0",
        "-i", str(list_path),
        "-c:a", "libmp3lame", "-q:a", "2",
        str(dest),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    if result.returncode != 0:
        raise RuntimeError(f"audio concat failed: {result.stderr[-500:]}")


def _default_poster_prompt(plan: dict, segment: Segment, prior_recap: str | None) -> str:
    """Default infographic-poster prompt using per-shot beats from the plan."""
    shots_by_name = {s["name"]: s for s in plan["shots"]}
    segment_shots = [shots_by_name[n] for n in segment.shot_names]
    panel_count = len(segment_shots)
    layout = "1 panel, full frame" if panel_count == 1 else (
        "2 panels side by side, 16:9 split" if panel_count == 2 else
        "3 columns x 1 row, 16:9 split"
    )
    project_name = plan.get("project", "rally").replace("_", " ").upper()
    style_id = plan.get("style_id", "psyop_anime_90s")

    panel_lines = []
    for i, shot in enumerate(segment_shots, 1):
        beat = shot.get("subtitle") or shot.get("vo_text", "")[:80]
        comp = shot.get("image_prompt", shot.get("video_prompt", ""))[:240]
        panel_lines.append(f"{i}. [{shot['name']}] beat: {beat}  composition: {comp}")

    recap = (
        f"\nContinuity: prior segment ended on '{prior_recap}'. "
        f"Maintain visual identity, palette, and character continuity from that beat."
    ) if prior_recap else ""

    return (
        f"Storyboard poster for segment {segment.segment_id} of {project_name}. "
        f"Style id: {style_id}. Wide 16:9 layout, {layout}, premium 3D stylized "
        f"rendering, deep cinematic atmosphere. Use the rally brand: rich black + "
        f"electric yellow #facc15 + glowing particle accents. "
        f"Header text: '{project_name} · {segment.segment_id} · {segment.target_duration:.1f}s'. "
        f"{recap}\n\nPanels:\n" + "\n".join(panel_lines) + (
            "\n\nFooter notes: hard-cut at segment boundary; preserve character continuity; "
            "yellow #facc15 accent across all panels."
        )
    )


def _default_video_prompt(plan: dict, segment: Segment, prior_recap: str | None) -> str:
    """Default Seedance prompt that mirrors the poster sequence."""
    shots_by_name = {s["name"]: s for s in plan["shots"]}
    segment_shots = [shots_by_name[n] for n in segment.shot_names]
    panel_count = len(segment_shots)
    style_id = plan.get("style_id", "psyop_anime_90s")
    seg_total = sum((shot.get("duration_s", 5)) for shot in segment_shots)

    sequence_lines = []
    for i, shot in enumerate(segment_shots, 1):
        sequence_lines.append(f"{i}. {shot.get('video_prompt', shot.get('image_prompt', ''))[:300]}")

    recap = (
        f"Continuity: this segment continues from a prior beat that ended on "
        f"'{prior_recap}'. Maintain visual identity and palette."
    ) if prior_recap else ""

    return (
        f"Use the attached storyboard image as the exact reference for character, "
        f"palette, lighting, and shot composition. Create a {min(seg_total, 15)}-second "
        f"9:16 vertical animated sequence that follows the {panel_count}-shot "
        f"storyboard exactly. Style: {style_id}. Brand: rich black + electric yellow "
        f"#facc15 + glowing particle accents. Hard-cut transitions on shot boundaries. "
        f"{recap}\n\nShot sequence:\n" + "\n".join(sequence_lines)
    )


def _summarize_segment_for_recap(segment: Segment, shots_by_name: dict[str, dict]) -> str:
    """One-line recap of the last shot in a segment, used as continuity hint."""
    if not segment.shot_names:
        return ""
    last_shot = shots_by_name.get(segment.shot_names[-1])
    if not last_shot:
        return ""
    return last_shot.get("subtitle") or last_shot.get("vo_text", "")[:120]


def _main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python3 -m pipeline.multi_batch <plan.json> [output_dir]", file=sys.stderr)
        sys.exit(2)
    plan_path = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else None
    render_multi_batch(plan_path, output_dir)


if __name__ == "__main__":
    _main()
