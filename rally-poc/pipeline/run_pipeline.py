#!/usr/bin/env python3
"""Rally anime video pipeline: video plan JSON -> final MP4.

Usage:
    python3 -m pipeline.run_pipeline plan.json [--resume] [--skip-eval]
    python3 -m pipeline.run_pipeline plan.json --resume --regenerate-shot s3a_boardroom
    python3 -m pipeline.run_pipeline plan.json --resume --regenerate-step image --stop-after phase1
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Optional

from .config import (
    COST_ELEVENLABS,
    COST_GUARD_PER_VIDEO,
    COST_LIPSYNC_BASE,
    COST_NB2_IMAGE,
    COST_SEGMIND_PER_SECOND,
    get_duration,
    load_all_env,
    require_key,
    snap_duration,
)
from .elevenlabs_client import ElevenLabsRetryableError, generate_speech
from .fal_client import FalRetryableError, download_image, generate_image
from .ffmpeg_assembly import (
    AssemblyResult,
    ClipSpec,
    assemble_video,
    image_to_clip,
    normalize_clip,
    pad_clip_to_duration,
)
from .gcs import upload_to_gcs
from .runcomfy_lipsync import (
    RunComfyRetryableError,
    download_file,
    submit_lipsync,
    wait_for_completion,
)
from .segmind_client import SegmindRetryableError, generate_video
from .timing import (
    compute_total_target,
    drift_warning,
    measure_vo_durations,
    snap_shot_durations,
)
from .whisper_client import (
    WhisperError,
    group_words_into_phrases,
    transcribe_with_word_timestamps,
)
from .state import (
    STATUS_COMPLETED,
    STATUS_FAILED,
    STATUS_PENDING,
    STATUS_RUNNING,
    STATUS_SKIPPED,
    PipelineState,
)


MAX_RETRIES = 3
RETRY_DELAY = 8


def main():
    parser = argparse.ArgumentParser(description="Rally anime video pipeline")
    parser.add_argument("plan", help="Path to video plan JSON")
    parser.add_argument("--resume", action="store_true", help="Resume from checkpoint")
    parser.add_argument("--skip-eval", action="store_true", help="Skip eval phase")
    parser.add_argument(
        "--regenerate-shot",
        action="append",
        default=[],
        help="Reset one shot before running. Repeat or pass comma-separated names.",
    )
    parser.add_argument(
        "--regenerate-step",
        choices=("video", "lipsync", "audio", "image", "all"),
        default="video",
        help="First step to reset for --regenerate-shot; downstream cached assets are reset too.",
    )
    parser.add_argument(
        "--stop-after",
        choices=("phase1", "video", "lipsync", "assembly"),
        help="Stop after a pipeline phase so intermediate assets can be reviewed.",
    )
    parser.add_argument(
        "--skip-captions",
        action="store_true",
        help="Skip Whisper word-level caption alignment (use static subtitles instead).",
    )
    args = parser.parse_args()

    load_all_env()

    with open(args.plan) as f:
        plan = json.load(f)

    project = plan["project"]
    output_dir = plan.get("output_dir", f"output/{project}")
    shots = plan["shots"]
    music = plan.get("music")
    transition_dur = plan.get("transition_duration", 0.4)

    # Make output_dir relative to rally-poc/
    base = Path(__file__).parent.parent
    output_dir = str(base / output_dir)

    # Initialize state
    state = PipelineState.load(output_dir, project) if args.resume else PipelineState(
        project=project, output_dir=output_dir,
        started_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    )

    # Create output subdirs
    for sub in ("images", "audio", "clips", "clips_lipsync", "clips_norm"):
        Path(output_dir, sub).mkdir(parents=True, exist_ok=True)

    print(f"\n{'='*60}")
    print(f"RALLY PIPELINE: {project} ({len(shots)} shots)")
    print(f"Output: {output_dir}")
    print(f"Resume: {args.resume}")
    print(f"{'='*60}\n")

    regen_shots = _parse_regenerate_shots(args.regenerate_shot)
    if regen_shots:
        _reset_steps_for_regeneration(
            state=state,
            shots=shots,
            output_dir=output_dir,
            shot_names=regen_shots,
            start_step=args.regenerate_step,
        )
        state.save()

    # Load API keys
    fal_key = require_key("FAL_KEY")
    segmind_key = require_key("SEGMIND_API_KEY")
    elevenlabs_key = require_key("ELEVENLABS_API_KEY")
    runcomfy_token = require_key("RUNCOMFY_API_TOKEN")

    # ---- Phase 1: NB2 images + ElevenLabs VO (parallel) -----------------
    print("--- Phase 1: Image + VO generation (parallel) ---\n")

    phase1_tasks = []
    for shot in shots:
        name = shot["name"]
        needs_image = shot["type"] in ("I2V", "NB2_STILL")
        needs_vo = bool(shot.get("vo_text"))

        if needs_image:
            phase1_tasks.append(("image", shot))
        if needs_vo:
            phase1_tasks.append(("audio", shot))

    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = {}
        for step, shot in phase1_tasks:
            name = shot["name"]
            if state.is_step_done(name, step):
                _log(name, step, "skipped (already done)")
                continue

            if step == "image":
                futures[pool.submit(
                    _generate_image, shot, output_dir, fal_key, state,
                )] = (name, step)
            else:
                futures[pool.submit(
                    _generate_vo, shot, output_dir, elevenlabs_key, state,
                )] = (name, step)

        for future in as_completed(futures):
            name, step = futures[future]
            try:
                future.result()
            except Exception as e:
                _log(name, step, f"FAILED: {e}")

    state.save()
    _check_cost_guard(state)

    # ---- Timing measurement: audio drives every visual duration --------
    measured = measure_vo_durations(shots, output_dir)
    snapped = snap_shot_durations(shots, measured)
    transition_dur_for_total = transition_dur if transition_dur and transition_dur > 0 else 0.0
    measured_total = compute_total_target(
        shots, snapped, transition_duration=transition_dur_for_total
    )
    drift = drift_warning(measured_total, plan.get("target_duration_s"))
    if drift:
        print(f"  TIMING: {drift}")
    else:
        print(
            f"  TIMING: {len(measured)} shot(s) measured, snapped total = "
            f"{measured_total:.1f}s"
        )
    state.measured_vo = measured  # type: ignore[attr-defined]
    state.snapped_durations = snapped  # type: ignore[attr-defined]

    if args.stop_after == "phase1":
        print("Stopped after phase1.")
        state.print_cost_report()
        return

    # ---- Phase 2: Seedance video generation (parallel, max 2) ------------
    print("\n--- Phase 2: Video generation ---\n")

    video_shots = [s for s in shots if s["type"] in ("I2V", "T2V")]
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = {}
        for shot in video_shots:
            name = shot["name"]
            if state.is_step_done(name, "video"):
                _log(name, "video", "skipped (already done)")
                continue
            futures[pool.submit(
                _generate_video, shot, output_dir, segmind_key, state,
            )] = name

        for future in as_completed(futures):
            name = futures[future]
            try:
                future.result()
            except Exception as e:
                _log(name, "video", f"FAILED: {e}")

    state.save()
    _check_cost_guard(state)
    if args.stop_after == "video":
        print("Stopped after video generation.")
        state.print_cost_report()
        return

    # ---- Phase 3: RunComfy lipsync (sequential) --------------------------
    lipsync_shots = [s for s in shots if s.get("needs_lipsync")]
    if lipsync_shots:
        print("\n--- Phase 3: Lipsync ---\n")
        for shot in lipsync_shots:
            name = shot["name"]
            if state.is_step_done(name, "lipsync"):
                _log(name, "lipsync", "skipped (already done)")
                continue
            try:
                _run_lipsync(shot, output_dir, runcomfy_token, state)
            except Exception as e:
                _log(name, "lipsync", f"FAILED (using original clip): {e}")
                ss = state.shot(name).lipsync
                ss.status = STATUS_FAILED
                ss.error = str(e)
                state.save()
    else:
        print("\n--- Phase 3: Lipsync (no shots need it) ---\n")

    state.save()
    _check_cost_guard(state)
    if args.stop_after == "lipsync":
        print("Stopped after lipsync.")
        state.print_cost_report()
        return

    # ---- Phase 3.5: Whisper word-level caption alignment ----------------
    if not args.skip_captions:
        print("\n--- Phase 3.5: Whisper caption alignment ---\n")
        _run_caption_alignment(shots, output_dir, state)
    else:
        print("\n--- Phase 3.5: Skipped (--skip-captions) ---\n")

    # ---- Phase 4: FFmpeg assembly ----------------------------------------
    print("\n--- Phase 4: Assembly ---\n")

    clip_specs = _build_clip_specs(shots, output_dir, state)
    succeeded = [c for c in clip_specs if c is not None]

    if len(succeeded) < len(shots) * 0.5:
        print(f"ERROR: Only {len(succeeded)}/{len(shots)} shots succeeded. Aborting assembly.")
        state.save()
        sys.exit(1)

    if len(succeeded) < len(shots):
        failed_names = [s["name"] for s, c in zip(shots, clip_specs) if c is None]
        print(f"WARNING: Skipping {len(failed_names)} failed shots: {failed_names}")

    # Resolve music path
    music_path = None
    music_volume = 0.22
    if music:
        mp = music.get("path", "")
        if mp:
            music_path = str(Path(__file__).parent.parent / mp) if not os.path.isabs(mp) else mp
        music_volume = music.get("volume", 0.22)

    final_path = os.path.join(output_dir, "final.mp4")
    result = assemble_video(
        clips=succeeded,
        output_path=final_path,
        transition_duration=transition_dur,
        music_path=music_path,
        music_volume=music_volume,
    )

    state.assembly_status = STATUS_COMPLETED
    state.assembly_path = result.output_path
    state.save()

    print(f"  Assembled: {result.output_path}")
    print(f"  Duration: {result.total_duration:.1f}s")
    if args.stop_after == "assembly":
        print("Stopped after assembly.")
        state.print_cost_report()
        return

    # ---- Phase 5: Eval ---------------------------------------------------
    if not args.skip_eval:
        print("\n--- Phase 5: Eval ---\n")
        _run_eval(result, shots, clip_specs, output_dir)

    # ---- Done ------------------------------------------------------------
    state.print_cost_report()
    print(f"Final video: {result.output_path}")
    print("Done.")


# -- Phase implementations ------------------------------------------------

def _generate_image(
    shot: dict,
    output_dir: str,
    api_key: str,
    state: PipelineState,
) -> None:
    name = shot["name"]
    prompt = shot.get("image_prompt", "")
    if not prompt:
        state.shot(name).image.status = STATUS_SKIPPED
        return

    output_path = os.path.join(output_dir, "images", f"{name}.png")
    ss = state.shot(name).image
    ss.status = STATUS_RUNNING
    state.save()

    ref_images = None
    ref = shot.get("reference_image")
    if ref:
        ref_images = [_resolve_reference_image(ref, name)]

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            _log(name, "image", f"generating (attempt {attempt})...")
            result = generate_image(
                prompt=prompt,
                api_key=api_key,
                reference_images=ref_images,
            )
            download_image(result.image_url, output_path)
            ss.status = STATUS_COMPLETED
            ss.path = output_path
            ss.cost = COST_NB2_IMAGE
            ss.attempts = attempt
            _log(name, "image", f"done -> {output_path}")
            return
        except FalRetryableError as e:
            ss.attempts = attempt
            if attempt < MAX_RETRIES:
                _log(name, "image", f"retrying in {RETRY_DELAY}s: {e}")
                time.sleep(RETRY_DELAY)
            else:
                ss.status = STATUS_FAILED
                ss.error = str(e)
                raise


def _resolve_reference_image(ref: str, shot_name: str) -> str:
    """Return a public reference image URL for vendor APIs.

    fal.ai reference_images expects URL-addressable images. A local path like
    reference/dario_amodei.jpg may not fail loudly, but it will not reliably
    anchor likeness. Upload local references before sending them to the model.
    """
    if ref.startswith(("http://", "https://")):
        return ref

    base = Path(__file__).parent.parent
    ref_path = Path(ref)
    if not ref_path.is_absolute():
        ref_path = base / ref_path
    if not ref_path.exists():
        raise FileNotFoundError(f"Reference image not found for {shot_name}: {ref}")

    _log(shot_name, "image", "uploading reference image to GCS...")
    job_id = uuid.uuid4().hex[:8]
    return upload_to_gcs(
        str(ref_path),
        f"rally_{shot_name}_{job_id}_reference{ref_path.suffix}",
        prefix="references",
    )


def _generate_vo(
    shot: dict,
    output_dir: str,
    api_key: str,
    state: PipelineState,
) -> None:
    name = shot["name"]
    text = shot.get("vo_text", "")
    voice = shot.get("vo_voice", "Liam")

    if not text:
        state.shot(name).audio.status = STATUS_SKIPPED
        return

    output_path = os.path.join(output_dir, "audio", f"{name}.mp3")
    ss = state.shot(name).audio
    ss.status = STATUS_RUNNING
    state.save()

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            _log(name, "audio", f"generating VO ({voice}, attempt {attempt})...")
            result = generate_speech(
                text=text,
                voice=voice,
                api_key=api_key,
            )
            with open(output_path, "wb") as f:
                f.write(result.audio_bytes)
            ss.status = STATUS_COMPLETED
            ss.path = output_path
            ss.cost = COST_ELEVENLABS
            ss.attempts = attempt
            _log(name, "audio", f"done ({result.char_count} chars) -> {output_path}")
            return
        except ElevenLabsRetryableError as e:
            ss.attempts = attempt
            if attempt < MAX_RETRIES:
                _log(name, "audio", f"retrying in {RETRY_DELAY}s: {e}")
                time.sleep(RETRY_DELAY)
            else:
                ss.status = STATUS_FAILED
                ss.error = str(e)
                raise


def _generate_video(
    shot: dict,
    output_dir: str,
    api_key: str,
    state: PipelineState,
) -> None:
    name = shot["name"]
    prompt = shot.get("video_prompt", shot.get("image_prompt", ""))
    shot_type = shot["type"]

    # Audio drives timing: every shot with a generated VO snaps its visual
    # duration to the actual measured VO length (+ 0.3s tail buffer). This was
    # previously gated to lipsync-only shots, which caused chronic VO/visual
    # drift. The plan-level duration_s is now a hint for budget estimation.
    plan_dur = shot.get("duration_s", 5)
    target_dur = plan_dur
    audio_state = state.shot(name).audio
    if audio_state.status == STATUS_COMPLETED and audio_state.path:
        try:
            vo_dur = get_duration(audio_state.path)
            target_dur = vo_dur + 0.3
            if abs(plan_dur - vo_dur) > 1.5:
                _log(
                    name,
                    "video",
                    f"WARNING: plan duration_s ({plan_dur}s) differs from measured VO "
                    f"({vo_dur:.1f}s) by >1.5s; using VO + 0.3s buffer",
                )
            else:
                _log(name, "video", f"duration-matching to VO ({vo_dur:.1f}s)")
        except Exception:
            pass
    duration = snap_duration(target_dur)

    output_path = os.path.join(output_dir, "clips", f"{name}.mp4")
    ss = state.shot(name).video
    ss.status = STATUS_RUNNING
    state.save()

    first_frame_url = None
    if shot_type == "I2V":
        image_state = state.shot(name).image
        if image_state.status == STATUS_COMPLETED and image_state.path:
            # Need a public URL for the image — upload to fal or use existing URL
            # For now, check if the path is already a URL
            if image_state.path.startswith("http"):
                first_frame_url = image_state.path
            else:
                # The image is local — we need to upload it.
                # Use GCS as a quick workaround.
                _log(name, "video", "uploading first frame to GCS...")
                job_id = uuid.uuid4().hex[:8]
                first_frame_url = upload_to_gcs(
                    image_state.path,
                    f"rally_{name}_{job_id}_frame.png",
                    prefix="pipeline",
                )
        else:
            _log(name, "video", "WARNING: no first frame, falling back to T2V")

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            _log(name, "video", f"generating ({shot_type}, {duration}s, attempt {attempt})...")
            video_bytes = generate_video(
                prompt=prompt,
                api_key=api_key,
                duration=duration,
                first_frame_url=first_frame_url,
            )
            with open(output_path, "wb") as f:
                f.write(video_bytes)
            actual_dur = get_duration(output_path)
            cost = duration * COST_SEGMIND_PER_SECOND
            ss.status = STATUS_COMPLETED
            ss.path = output_path
            ss.cost = cost
            ss.attempts = attempt
            _log(name, "video", f"done ({actual_dur:.1f}s, ${cost:.2f}) -> {output_path}")
            return
        except SegmindRetryableError as e:
            ss.attempts = attempt
            if attempt < MAX_RETRIES:
                _log(name, "video", f"retrying in {RETRY_DELAY}s: {e}")
                time.sleep(RETRY_DELAY)
            else:
                ss.status = STATUS_FAILED
                ss.error = str(e)
                raise


def _run_lipsync(
    shot: dict,
    output_dir: str,
    api_token: str,
    state: PipelineState,
) -> None:
    name = shot["name"]
    ss = state.shot(name)

    video_state = ss.video
    audio_state = ss.audio

    if audio_state.status != STATUS_COMPLETED or not audio_state.path:
        _log(name, "lipsync", "skipped (no audio)")
        ss.lipsync.status = STATUS_SKIPPED
        return

    if video_state.status != STATUS_COMPLETED or not video_state.path:
        if shot.get("type") == "NB2_STILL":
            _create_still_lipsync_source(shot, output_dir, state)
            video_state = ss.video
            if video_state.status != STATUS_COMPLETED or not video_state.path:
                return
        else:
            _log(name, "lipsync", "skipped (no video)")
            ss.lipsync.status = STATUS_SKIPPED
            return

    output_path = os.path.join(output_dir, "clips_lipsync", f"{name}.mp4")
    ss.lipsync.status = STATUS_RUNNING
    state.save()

    # Pre-normalize video to 1080x1920@30fps BEFORE lipsync
    # (validated test used pre-normalized clips — RunComfy works better at full res)
    norm_path = os.path.join(output_dir, "clips_norm", f"{name}_prelipsync.mp4")
    if not os.path.exists(norm_path):
        _log(name, "lipsync", "pre-normalizing to 1080x1920@30fps...")
        normalize_clip(video_state.path, norm_path)
    upload_video_path = norm_path

    # Upload video + audio to GCS
    job_id = uuid.uuid4().hex[:8]
    _log(name, "lipsync", "uploading to GCS...")
    video_url = upload_to_gcs(
        upload_video_path,
        f"rally_{name}_{job_id}_video.mp4",
        prefix="lipsync",
    )
    audio_url = upload_to_gcs(
        audio_state.path,
        f"rally_{name}_{job_id}_audio.mp3",
        prefix="lipsync",
    )

    # Determine sync mode
    vid_dur = get_duration(upload_video_path)
    aud_dur = get_duration(audio_state.path)
    sync_mode = "bounce" if vid_dur < aud_dur else "cut_off"

    _log(name, "lipsync", f"submitting (video={vid_dur:.1f}s, audio={aud_dur:.1f}s, sync={sync_mode})...")
    response = submit_lipsync(
        video_url=video_url,
        audio_url=audio_url,
        api_token=api_token,
        sync_mode=sync_mode,
    )
    request_id = response.get("request_id") or response.get("id", "")
    _log(name, "lipsync", f"waiting (request_id={request_id})...")

    result = wait_for_completion(
        request_id=request_id,
        api_token=api_token,
    )

    # Extract output URL
    output_url = (
        result.output.get("video")
        or result.output.get("video_url")
        or result.output.get("output_video_url")
        or result.output.get("output", "")
    )
    if not output_url:
        raise RuntimeError(f"No output URL in lipsync result: {result.output}")

    download_file(output_url, Path(output_path))

    aud_dur = get_duration(audio_state.path)
    out_dur = get_duration(output_path)
    min_lipsync_duration = aud_dur + 0.08
    if out_dur + 0.005 < min_lipsync_duration:
        raw_path = output_path.replace(".mp4", "_raw.mp4")
        os.replace(output_path, raw_path)
        _log(name, "lipsync", f"padding final frame ({out_dur:.2f}s -> {min_lipsync_duration:.2f}s)")
        pad_clip_to_duration(raw_path, output_path, min_lipsync_duration)

    ss.lipsync.status = STATUS_COMPLETED
    ss.lipsync.path = output_path
    ss.lipsync.cost = COST_LIPSYNC_BASE
    state.save()
    _log(name, "lipsync", f"done -> {output_path}")


def _run_caption_alignment(
    shots: list[dict],
    output_dir: str,
    state: PipelineState,
) -> None:
    """Phase 3.5: Whisper word-level alignment per VO file.

    For each shot with a generated VO, transcribe with word timestamps and
    cache to output_dir/captions/<shot>.json. _build_clip_specs picks up the
    cached file and attaches `caption_phrases` to ClipSpec.

    Best-effort: if the OPENAI_API_KEY is unset OR a single shot fails,
    we fall back to the existing static `subtitle` field for that shot.
    """
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key:
        print("  WARNING: OPENAI_API_KEY not set; skipping Whisper alignment.")
        return

    captions_dir = os.path.join(output_dir, "captions")
    os.makedirs(captions_dir, exist_ok=True)

    for shot in shots:
        name = shot["name"]
        if not shot.get("vo_text"):
            continue
        audio_state = state.shot(name).audio
        if audio_state.status != STATUS_COMPLETED or not audio_state.path:
            continue

        cache_path = os.path.join(captions_dir, f"{name}.json")
        if os.path.exists(cache_path):
            _log(name, "captions", "cached")
            continue

        try:
            result = transcribe_with_word_timestamps(audio_state.path, api_key)
        except WhisperError as exc:
            _log(name, "captions", f"FAILED: {exc}")
            continue
        phrases = group_words_into_phrases(result.words)
        with open(cache_path, "w") as f:
            json.dump(
                {"text": result.text, "duration_s": result.duration_s, "phrases": phrases},
                f,
                indent=2,
            )
        _log(name, "captions", f"done ({len(phrases)} phrase(s))")


def _create_still_lipsync_source(
    shot: dict,
    output_dir: str,
    state: PipelineState,
) -> None:
    """Create a deterministic still-image source clip for lip sync.

    Real-person likeness can degrade when an image is first passed through a
    video model. For NB2_STILL talking shots, animate the reference-derived
    image directly through lip sync instead.
    """
    name = shot["name"]
    ss = state.shot(name)
    image_state = ss.image
    audio_state = ss.audio

    if image_state.status != STATUS_COMPLETED or not image_state.path:
        _log(name, "lipsync", "skipped (no image source)")
        ss.lipsync.status = STATUS_SKIPPED
        return

    audio_duration = get_duration(audio_state.path) if audio_state.path else 0.0
    source_duration = max(float(shot.get("duration_s", 4)), audio_duration + 0.5)
    source_path = os.path.join(output_dir, "clips", f"{name}_still_lipsync.mp4")
    _log(name, "lipsync", f"creating still source ({source_duration:.1f}s)")
    image_to_clip(image_state.path, source_path, source_duration)

    ss.video.status = STATUS_COMPLETED
    ss.video.path = source_path
    ss.video.cost = 0.0
    state.save()


def _build_clip_specs(
    shots: list[dict],
    output_dir: str,
    state: PipelineState,
) -> list[Optional[ClipSpec]]:
    """Build ClipSpec list from completed shots. Returns None for failed shots."""
    specs = []
    for shot in shots:
        name = shot["name"]
        ss = state.shot(name)
        shot_type = shot["type"]

        # Determine video path: lipsync > video > image (for NB2_STILL)
        video_path = None
        has_lipsync = ss.lipsync.status == STATUS_COMPLETED and ss.lipsync.path
        if has_lipsync:
            video_path = ss.lipsync.path
        elif ss.video.status == STATUS_COMPLETED and ss.video.path:
            video_path = ss.video.path

        if shot_type == "NB2_STILL":
            # Convert image to clip with Ken Burns
            if has_lipsync:
                pass
            elif ss.image.status == STATUS_COMPLETED and ss.image.path:
                clip_path = os.path.join(output_dir, "clips", f"{name}_still.mp4")
                if not os.path.exists(clip_path):
                    _log(name, "assembly", "creating Ken Burns clip from image...")
                    image_to_clip(ss.image.path, clip_path, shot["duration_s"])
                video_path = clip_path
            elif not video_path:
                specs.append(None)
                continue

        if not video_path or not os.path.exists(video_path):
            specs.append(None)
            continue

        # Lipsync clips were pre-normalized — use directly, skip re-encoding
        if has_lipsync:
            final_clip = video_path
        else:
            norm_path = os.path.join(output_dir, "clips_norm", f"{name}.mp4")
            if not os.path.exists(norm_path):
                _log(name, "assembly", "normalizing...")
                normalize_clip(video_path, norm_path)
            final_clip = norm_path

        # Authoritative duration: snapped target from VO measurement, not
        # whatever Seedance returned (which can be 4.97s for a 5s request).
        snapped_dur = getattr(state, "snapped_durations", {}).get(name)
        if snapped_dur is not None:
            duration = float(snapped_dur)
        else:
            duration = get_duration(final_clip)
        vo_path = ss.audio.path if ss.audio.status == STATUS_COMPLETED else None
        subtitle = shot.get("subtitle")

        # Attach Whisper-aligned caption phrases when available.
        caption_phrases = None
        captions_path = os.path.join(output_dir, "captions", f"{name}.json")
        if os.path.exists(captions_path):
            try:
                with open(captions_path) as f:
                    caption_phrases = json.load(f).get("phrases")
            except Exception:
                caption_phrases = None

        specs.append(ClipSpec(
            video_path=final_clip,
            duration=duration,
            vo_path=vo_path,
            subtitle=subtitle,
            caption_phrases=caption_phrases,
        ))

    return specs


def _run_eval(
    result: AssemblyResult,
    shots: list[dict],
    clip_specs: list[Optional[ClipSpec]],
    output_dir: str,
) -> None:
    """Run eval.py on the assembled video."""
    # Build metadata for eval
    metadata = {"shots": []}
    for shot, (start, end) in zip(shots, result.shot_timestamps):
        if any(c is not None for c in [clip_specs]):
            metadata["shots"].append({
                "name": shot["name"],
                "start_s": round(start, 2),
                "end_s": round(end, 2),
                "type": shot["type"],
                "script_description": shot.get("video_prompt", shot.get("image_prompt", "")),
                "text_bearing": False,
            })

    meta_path = os.path.join(output_dir, "eval_meta.json")
    with open(meta_path, "w") as f:
        json.dump(metadata, f, indent=2)

    # Import and run eval
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from eval import run_eval, print_report  # noqa: E402

    report = run_eval(result.output_path, metadata)
    print_report(report)

    report_path = os.path.join(output_dir, "eval_report.json")
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2, default=str)
    print(f"  Eval report: {report_path}")


# -- Helpers ---------------------------------------------------------------

def _log(shot: str, step: str, msg: str) -> None:
    print(f"  [{shot}] {step}: {msg}")


def _check_cost_guard(state: PipelineState) -> None:
    if state.total_cost > COST_GUARD_PER_VIDEO:
        print(f"\n  WARNING: Total cost ${state.total_cost:.2f} exceeds guard ${COST_GUARD_PER_VIDEO:.2f}")
        print(f"  Pipeline will continue but review spending.\n")


def _parse_regenerate_shots(raw_values: list[str]) -> set[str]:
    """Parse repeated or comma-separated --regenerate-shot values."""
    names: set[str] = set()
    for value in raw_values:
        for name in value.split(","):
            clean = name.strip()
            if clean:
                names.add(clean)
    return names


def _reset_steps_for_regeneration(
    *,
    state: PipelineState,
    shots: list[dict],
    output_dir: str,
    shot_names: set[str],
    start_step: str,
) -> None:
    """Reset selected shot state and downstream cached files.

    Eval-driven regeneration needs to invalidate derived assets as well as the
    primary step. For example, a new video must force a new normalized clip and
    a new lipsync output, otherwise assembly can silently reuse stale files.
    """
    known = {shot["name"]: shot for shot in shots}
    unknown = sorted(shot_names - set(known))
    if unknown:
        raise ValueError(f"Unknown --regenerate-shot name(s): {', '.join(unknown)}")

    for name in sorted(shot_names):
        shot = known[name]
        steps = _steps_to_reset(shot, start_step)
        _log(name, "regen", f"resetting {', '.join(steps)}")

        ss = state.shot(name)
        for step in steps:
            step_state = ss.step(step)
            _remove_artifact(step_state.path, output_dir)
            step_state.status = STATUS_PENDING
            step_state.path = None
            step_state.cost = 0.0
            step_state.error = None
            step_state.attempts = 0

        _remove_derived_files(name, output_dir, steps)

    state.assembly_status = STATUS_PENDING


def _steps_to_reset(shot: dict, start_step: str) -> tuple[str, ...]:
    """Return reset set for a starting step plus required downstream steps."""
    if start_step == "all":
        return ("image", "audio", "video", "lipsync")
    if start_step == "image":
        return ("image", "video", "lipsync")
    if start_step == "audio":
        if shot.get("needs_lipsync"):
            return ("audio", "video", "lipsync")
        return ("audio",)
    if start_step == "video":
        return ("video", "lipsync")
    return ("lipsync",)


def _remove_derived_files(name: str, output_dir: str, reset_steps: tuple[str, ...]) -> None:
    """Remove untracked derived files that are not directly stored in state."""
    if "video" in reset_steps or "lipsync" in reset_steps:
        _remove_artifact(os.path.join(output_dir, "clips_norm", f"{name}.mp4"), output_dir)
        _remove_artifact(os.path.join(output_dir, "clips_norm", f"{name}_prelipsync.mp4"), output_dir)
    if "lipsync" in reset_steps:
        _remove_artifact(os.path.join(output_dir, "clips_lipsync", f"{name}.mp4"), output_dir)


def _remove_artifact(path: Optional[str], output_dir: str) -> None:
    """Remove a generated file if it lives under output_dir."""
    if not path:
        return
    p = Path(path)
    if not p.is_absolute():
        p = Path(output_dir) / p
    try:
        p.resolve().relative_to(Path(output_dir).resolve())
    except ValueError:
        return
    if p.exists() and p.is_file():
        p.unlink()


if __name__ == "__main__":
    main()
