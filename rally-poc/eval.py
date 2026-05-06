#!/usr/bin/env python3
"""
Rally Video Eval System

Extracts start/mid/end frames per shot, detects frozen segments,
checks visual quality, outputs structured eval report.

Usage:
    python3 eval.py <video_path> <metadata_json_path>
    python3 eval.py video1.mp4 video1_meta.json
"""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


def extract_frame(video_path, time_s, output_path):
    """Extract a single frame at a given timestamp."""
    subprocess.run(
        ["ffmpeg", "-y", "-ss", str(time_s), "-i", video_path,
         "-frames:v", "1", "-q:v", "2", output_path],
        capture_output=True
    )
    return os.path.exists(output_path)


def get_frame_hash(frame_path):
    """Get a perceptual hash of a frame by computing average pixel value."""
    result = subprocess.run(
        ["ffmpeg", "-i", frame_path, "-vf", "scale=16:16", "-f", "rawvideo",
         "-pix_fmt", "gray", "-"],
        capture_output=True
    )
    if result.returncode != 0 or not result.stdout:
        return None
    return result.stdout


def frames_similar(hash1, hash2, threshold=0.95):
    """Compare two frame hashes. Returns True if frames are nearly identical (frozen)."""
    if hash1 is None or hash2 is None:
        return False
    if len(hash1) != len(hash2):
        return False
    matching = sum(1 for a, b in zip(hash1, hash2) if abs(a - b) < 10)
    similarity = matching / len(hash1)
    return similarity > threshold


def detect_freeze_duration(video_path, start_s, end_s, sample_interval=0.5):
    """Detect how much of a shot is frozen by sampling frames."""
    with tempfile.TemporaryDirectory() as tmpdir:
        times = []
        t = start_s + 0.2
        while t < end_s - 0.2:
            times.append(t)
            t += sample_interval

        if len(times) < 2:
            return 0.0, end_s - start_s

        # Extract all sample frames
        hashes = []
        for i, t in enumerate(times):
            fpath = os.path.join(tmpdir, f"sample_{i:04d}.jpg")
            extract_frame(video_path, t, fpath)
            hashes.append(get_frame_hash(fpath))

        # Count frozen pairs
        frozen_pairs = 0
        total_pairs = len(hashes) - 1
        for i in range(total_pairs):
            if frames_similar(hashes[i], hashes[i + 1]):
                frozen_pairs += 1

        shot_duration = end_s - start_s
        if total_pairs == 0:
            return 0.0, shot_duration

        freeze_ratio = frozen_pairs / total_pairs
        motion_duration = shot_duration * (1 - freeze_ratio)
        return freeze_ratio, motion_duration


def eval_shot(video_path, shot, tmpdir):
    """Evaluate a single shot. Returns eval dict."""
    name = shot["name"]
    start = shot["start_s"]
    end = shot["end_s"]
    duration = end - start
    shot_type = shot.get("type", "unknown")
    description = shot.get("script_description", "")
    text_bearing = shot.get("text_bearing", False)

    result = {
        "name": name,
        "type": shot_type,
        "duration_s": round(duration, 2),
        "text_bearing": text_bearing,
        "frames": {},
        "freeze_ratio": 0.0,
        "motion_duration_s": 0.0,
        "issues": [],
        "verdict": "PASS"
    }

    # Extract start/mid/end frames
    frame_times = {
        "start": start + 0.5 if duration > 1.5 else start + 0.1,
        "mid": start + duration / 2,
        "end": end - 0.5 if duration > 1.5 else end - 0.1,
    }

    for label, t in frame_times.items():
        fpath = os.path.join(tmpdir, f"{name}_{label}.jpg")
        extract_frame(video_path, t, fpath)
        result["frames"][label] = fpath

    # Check for frozen frames (compare mid vs end)
    mid_hash = get_frame_hash(result["frames"]["mid"])
    end_hash = get_frame_hash(result["frames"]["end"])
    start_hash = get_frame_hash(result["frames"]["start"])

    if frames_similar(mid_hash, end_hash):
        result["issues"].append("FROZEN: mid and end frames are identical")

    if frames_similar(start_hash, mid_hash) and frames_similar(mid_hash, end_hash):
        result["issues"].append("FULLY_FROZEN: all three frames identical — no motion detected")

    # Detailed freeze detection
    freeze_ratio, motion_dur = detect_freeze_duration(video_path, start, end)
    result["freeze_ratio"] = round(freeze_ratio, 3)
    result["motion_duration_s"] = round(motion_dur, 2)

    if freeze_ratio > 0.5:
        result["issues"].append(f"HIGH_FREEZE: {freeze_ratio*100:.0f}% of shot is frozen")

    # Check if shot is too short for its VO
    if shot_type in ("T2V", "I2V") and freeze_ratio > 0.3:
        result["issues"].append("CLIP_TOO_SHORT: video clip shorter than VO, causing freeze-frame padding")

    # Set verdict
    if any("FULLY_FROZEN" in i for i in result["issues"]):
        result["verdict"] = "FAIL"
    elif any("HIGH_FREEZE" in i or "CLIP_TOO_SHORT" in i for i in result["issues"]):
        result["verdict"] = "WARN"
    elif result["issues"]:
        result["verdict"] = "MIXED"

    return result


def check_transitions(video_path, shots, tmpdir):
    """Check for jarring transitions between consecutive shots."""
    transition_results = []

    for i in range(len(shots) - 1):
        s1 = shots[i]
        s2 = shots[i + 1]
        boundary = s1["end_s"]

        # Extract frames just before and after the cut
        before_path = os.path.join(tmpdir, f"trans_{i}_before.jpg")
        after_path = os.path.join(tmpdir, f"trans_{i}_after.jpg")

        extract_frame(video_path, boundary - 0.1, before_path)
        extract_frame(video_path, boundary + 0.1, after_path)

        before_hash = get_frame_hash(before_path)
        after_hash = get_frame_hash(after_path)

        is_smooth = frames_similar(before_hash, after_hash, threshold=0.7)

        transition_results.append({
            "from": s1["name"],
            "to": s2["name"],
            "at_s": round(boundary, 2),
            "smooth": is_smooth,
            "type": "crossfade" if is_smooth else "hard_cut"
        })

    return transition_results


def run_eval(video_path, metadata):
    """Run full eval on a video."""
    shots = metadata["shots"]

    with tempfile.TemporaryDirectory() as tmpdir:
        # Eval each shot
        shot_results = []
        for shot in shots:
            result = eval_shot(video_path, shot, tmpdir)
            shot_results.append(result)

        # Check transitions
        transitions = check_transitions(video_path, shots, tmpdir)

        # Compute summary
        total_shots = len(shot_results)
        passing = sum(1 for r in shot_results if r["verdict"] == "PASS")
        warnings = sum(1 for r in shot_results if r["verdict"] == "WARN")
        failures = sum(1 for r in shot_results if r["verdict"] == "FAIL")
        hard_cuts = sum(1 for t in transitions if t["type"] == "hard_cut")

        avg_freeze = sum(r["freeze_ratio"] for r in shot_results) / total_shots if total_shots else 0

        report = {
            "video_path": video_path,
            "summary": {
                "total_shots": total_shots,
                "pass": passing,
                "warn": warnings,
                "fail": failures,
                "hard_cuts": hard_cuts,
                "avg_freeze_ratio": round(avg_freeze, 3),
                "overall": "PASS" if failures == 0 and warnings == 0 else ("WARN" if failures == 0 else "FAIL")
            },
            "shots": shot_results,
            "transitions": transitions,
        }

        # Copy frame files to persistent location
        eval_dir = os.path.join(os.path.dirname(video_path), "eval_frames")
        os.makedirs(eval_dir, exist_ok=True)
        for shot_result in shot_results:
            for label, fpath in shot_result["frames"].items():
                if os.path.exists(fpath):
                    dest = os.path.join(eval_dir, os.path.basename(fpath))
                    subprocess.run(["cp", fpath, dest], capture_output=True)
                    shot_result["frames"][label] = dest

    return report


def print_report(report):
    """Print human-readable eval report."""
    s = report["summary"]
    print(f"\n{'='*60}")
    print(f"EVAL REPORT: {os.path.basename(report['video_path'])}")
    print(f"{'='*60}")
    print(f"Overall: {s['overall']}")
    print(f"Shots: {s['pass']} PASS / {s['warn']} WARN / {s['fail']} FAIL (of {s['total_shots']})")
    print(f"Hard cuts: {s['hard_cuts']}")
    print(f"Avg freeze ratio: {s['avg_freeze_ratio']*100:.1f}%")
    print()

    for shot in report["shots"]:
        icon = {"PASS": "+", "WARN": "~", "FAIL": "X", "MIXED": "?"}[shot["verdict"]]
        freeze_pct = shot["freeze_ratio"] * 100
        print(f"  [{icon}] {shot['name']} ({shot['type']}, {shot['duration_s']}s)")
        print(f"      Motion: {shot['motion_duration_s']}s / {shot['duration_s']}s ({100-freeze_pct:.0f}% active)")
        if shot["issues"]:
            for issue in shot["issues"]:
                print(f"      ! {issue}")
        print()

    if report["transitions"]:
        print("  Transitions:")
        for t in report["transitions"]:
            icon = "~" if t["smooth"] else "X"
            print(f"    [{icon}] {t['from']} -> {t['to']} at {t['at_s']}s ({t['type']})")
    print()


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(f"Usage: {sys.argv[0]} <video_path> <metadata_json>")
        sys.exit(1)

    video_path = sys.argv[1]
    meta_path = sys.argv[2]

    with open(meta_path) as f:
        metadata = json.load(f)

    report = run_eval(video_path, metadata)
    print_report(report)

    # Save JSON report
    report_path = video_path.replace(".mp4", "_eval.json")
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2, default=str)
    print(f"JSON report saved to: {report_path}")
