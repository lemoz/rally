#!/usr/bin/env python3
"""Test RunComfy lipsync v2 on a Seedance-generated anime clip.

Proves that GovClip's lipsync approach works on anime faces:
  Seedance 2.0 video (no lip sync) + Japanese VO → RunComfy lipsync → lip-synced output
"""

import os
import subprocess
import sys
import uuid
from pathlib import Path

# Add pipeline/ to path
sys.path.insert(0, str(Path(__file__).parent))

from pipeline.runcomfy_lipsync import submit_lipsync, wait_for_completion, download_file

# --- Config ---
VIDEO = "/tmp/glasswing_anime_final/scene3/beat1_dario_norm.mp4"
AUDIO = "/Users/cdossman/rally/rally-poc/project-b/audio/anime/v2_dario_built_jp.mp3"
OUTPUT = "/tmp/glasswing_anime_v2/dario_lipsync_test.mp4"
GCS_BUCKET = "govclip-temp-files"


def load_env(path: str) -> None:
    """Load .env file into os.environ."""
    if not os.path.exists(path):
        return
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, val = line.split("=", 1)
            val = val.strip().strip("'\"")
            os.environ.setdefault(key, val)


def get_duration(path: str) -> float:
    """Get media file duration via ffprobe."""
    r = subprocess.run(
        ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", path],
        capture_output=True, text=True,
    )
    return float(r.stdout.strip())


def upload_to_gcs(local_path: str, gcs_name: str) -> str:
    """Upload file to GCS and return public URL."""
    gcs_path = f"gs://{GCS_BUCKET}/lipsync/{gcs_name}"
    print(f"  Uploading {os.path.basename(local_path)} → {gcs_path}")
    result = subprocess.run(
        ["gsutil", "cp", local_path, gcs_path],
        capture_output=True, text=True, timeout=120,
    )
    if result.returncode != 0:
        raise RuntimeError(f"GCS upload failed: {result.stderr[:300]}")
    return f"https://storage.googleapis.com/{GCS_BUCKET}/lipsync/{gcs_name}"


def main():
    # Load credentials
    load_env("/Users/cdossman/rally/.env")
    load_env("/Users/cdossman/.env")

    api_token = os.environ.get("RUNCOMFY_API_TOKEN", "")
    if not api_token:
        print("ERROR: RUNCOMFY_API_TOKEN not set", file=sys.stderr)
        sys.exit(1)

    # Verify inputs exist
    for path, label in [(VIDEO, "Video"), (AUDIO, "Audio")]:
        if not os.path.exists(path):
            print(f"ERROR: {label} not found: {path}", file=sys.stderr)
            sys.exit(1)

    # Get durations
    vid_dur = get_duration(VIDEO)
    aud_dur = get_duration(AUDIO)
    sync_mode = "bounce" if vid_dur < aud_dur else "cut_off"
    print(f"\n=== RunComfy Lipsync Test ===")
    print(f"Video: {VIDEO} ({vid_dur:.2f}s)")
    print(f"Audio: {AUDIO} ({aud_dur:.2f}s)")
    print(f"Sync mode: {sync_mode}")

    # Upload to GCS
    print(f"\n--- Uploading to GCS ---")
    job_id = uuid.uuid4().hex[:8]
    video_url = upload_to_gcs(VIDEO, f"rally_test_{job_id}_video.mp4")
    audio_url = upload_to_gcs(AUDIO, f"rally_test_{job_id}_audio.mp3")
    print(f"  Video URL: {video_url}")
    print(f"  Audio URL: {audio_url}")

    # Submit lipsync job
    print(f"\n--- Submitting to RunComfy ---")
    response = submit_lipsync(
        video_url=video_url,
        audio_url=audio_url,
        api_token=api_token,
        sync_mode=sync_mode,
    )
    request_id = response.get("request_id") or response.get("id", "")
    print(f"  Request ID: {request_id}")

    # Poll for completion
    print(f"\n--- Waiting for completion (up to 15 min) ---")
    result = wait_for_completion(
        request_id=request_id,
        api_token=api_token,
    )
    print(f"  Status: {result.status}")
    print(f"  Output keys: {list(result.output.keys())}")

    # Extract output URL
    output_url = (
        result.output.get("video")
        or result.output.get("video_url")
        or result.output.get("output_video_url")
        or result.output.get("output", "")
    )
    if not output_url:
        print(f"ERROR: No output URL in result: {result.output}", file=sys.stderr)
        sys.exit(1)

    # Download result
    print(f"\n--- Downloading result ---")
    output_path = Path(OUTPUT)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    download_file(output_url, output_path)

    if not output_path.exists():
        print("ERROR: Output file not created", file=sys.stderr)
        sys.exit(1)

    out_dur = get_duration(str(output_path))
    fsize = output_path.stat().st_size / (1024 * 1024)
    print(f"\n=== DONE ===")
    print(f"Output: {OUTPUT}")
    print(f"Duration: {out_dur:.2f}s")
    print(f"Size: {fsize:.1f} MB")
    print(f"\nOriginal: {VIDEO}")
    print(f"Compare these two files to evaluate lip sync quality.")

    # Open in Finder
    subprocess.run(["open", "-R", str(output_path)])


if __name__ == "__main__":
    main()
