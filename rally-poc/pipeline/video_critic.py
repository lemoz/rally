"""Vision-model video critic. Uploads a video to Gemini 2.0 Flash, scores
against the 8-axis rubric in docs/VIDEO_RUBRIC.md, returns structured JSON.

Usage:
    python3 -m pipeline.video_critic <video_path> [<plan_json_path>]

The plan_json_path (optional) lets the critic see the storyboard intent —
hook strategy, voiceover script, captions — so it can score "did the
execution match the intent" rather than reverse-engineering the intent
from the video alone.
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from pipeline.config import load_all_env, require_key  # noqa: E402

GENERATIVE_MODEL = "gemini-2.5-flash"
UPLOAD_BASE = "https://generativelanguage.googleapis.com/upload/v1beta/files"
GENERATE_BASE = (
    f"https://generativelanguage.googleapis.com/v1beta/models/{GENERATIVE_MODEL}:generateContent"
)
FILES_API_BASE = "https://generativelanguage.googleapis.com/v1beta/files"


RUBRIC_PROMPT = """\
You are a TikTok video critic for the Rally project (rallysignal.co). Score the
attached short-form video against the 8-axis rubric below. Be honest. Be specific.
Treat this as a pre-launch QA pass: your job is to flag failures, not to flatter.

Context: Rally is an experimental "TikTok feed where every like programs an AI
agent" — engagement signals direct AI agents to work on real GitHub issues.
Videos are intended for the @rallysignal TikTok account and should compete
directly with dev/AI/buildinpublic TikTok creators (e.g. Riley Brown,
Sabrina Ramonov, the #vibecoding hashtag tier).

Score each axis 1-10 (10 = best). Definitions:

1. native_feel: Would this blend in on the dev TikTok For You feed (10), or
   stand out as AI slop or ad-aesthetic (1)?
2. hook_integrity: Does a muted viewer with no context understand the
   premise + want to keep watching by 2 seconds in?
3. save_worthy_moment: Is there a single frame or beat a viewer would
   screenshot or share?
4. visual_quality: Production craft — composition, lighting, motion,
   color, brand consistency. AI artifacts visible? Pentagram-quality (10) or
   embarrassing (1)?
5. audio_match: Does music + VO + sound design fit the emotional register?
6. pacing: TikTok-native pacing (10) vs corporate explainer drag (1)?
7. caption_craft: Captions present, readable, well-timed, reinforcing?
8. comment_cta_strength: Does the final beat give a specific, low-friction
   reason to comment?

Return JSON only, with this exact shape:

{
  "video_id": "<from filename or plan>",
  "overall_score": <float, simple average>,
  "verdict": "pass" | "fail",
  "axes": {
    "native_feel":          {"score": <int>, "notes": "<one sentence>"},
    "hook_integrity":       {"score": <int>, "notes": "<one sentence>"},
    "save_worthy_moment":   {"score": <int>, "notes": "<one sentence>"},
    "visual_quality":       {"score": <int>, "notes": "<one sentence>"},
    "audio_match":          {"score": <int>, "notes": "<one sentence>"},
    "pacing":               {"score": <int>, "notes": "<one sentence>"},
    "caption_craft":        {"score": <int>, "notes": "<one sentence>"},
    "comment_cta_strength": {"score": <int>, "notes": "<one sentence>"}
  },
  "specific_failures": ["<axis_name>: <reason>", ...],
  "two_word_summary": "<two words>"
}

Verdict = "pass" if overall_score >= 7.0 AND no axis score <= 4. Otherwise "fail".
"""


# ----- Gemini Files API -----

def _post(url: str, data: bytes, headers: dict) -> dict:
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=300) as resp:
        body = resp.read()
    return json.loads(body.decode("utf-8")) if body else {}


def _get(url: str) -> dict:
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode("utf-8"))


def upload_video(path: Path, api_key: str) -> dict:
    """Upload via Gemini's resumable upload API. Returns file metadata."""
    size = path.stat().st_size
    print(f"[critic] uploading {path.name} ({size // 1024} KB) to Gemini...", flush=True)

    # 1) start resumable upload session
    start_url = f"{UPLOAD_BASE}?key={api_key}"
    start_payload = json.dumps({"file": {"display_name": path.name}}).encode("utf-8")
    start_req = urllib.request.Request(
        start_url,
        data=start_payload,
        headers={
            "X-Goog-Upload-Protocol": "resumable",
            "X-Goog-Upload-Command": "start",
            "X-Goog-Upload-Header-Content-Length": str(size),
            "X-Goog-Upload-Header-Content-Type": "video/mp4",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(start_req, timeout=60) as resp:
        upload_url = resp.headers.get("X-Goog-Upload-URL")
    if not upload_url:
        raise RuntimeError("No X-Goog-Upload-URL header from start request")

    # 2) upload bytes + finalize
    body = path.read_bytes()
    finalize_req = urllib.request.Request(
        upload_url,
        data=body,
        headers={
            "X-Goog-Upload-Offset": "0",
            "X-Goog-Upload-Command": "upload, finalize",
            "Content-Length": str(size),
        },
        method="POST",
    )
    with urllib.request.urlopen(finalize_req, timeout=600) as resp:
        meta = json.loads(resp.read().decode("utf-8"))
    file_meta = meta.get("file", {})
    name = file_meta.get("name")
    if not name:
        raise RuntimeError(f"upload returned no file name: {meta}")
    print(f"[critic] uploaded as {name}", flush=True)

    # 3) poll until ACTIVE
    info_url = f"https://generativelanguage.googleapis.com/v1beta/{name}?key={api_key}"
    start = time.time()
    while True:
        if time.time() - start > 300:
            raise RuntimeError(f"file upload timeout: {name}")
        info = _get(info_url)
        state = info.get("state", "PROCESSING")
        if state == "ACTIVE":
            return info
        if state == "FAILED":
            raise RuntimeError(f"file processing failed: {info}")
        time.sleep(2)


def critique(file_meta: dict, plan_context: str, api_key: str) -> dict:
    """Send the uploaded video + rubric prompt to Gemini, return parsed JSON."""
    payload = {
        "contents": [{
            "role": "user",
            "parts": [
                {
                    "fileData": {
                        "mimeType": file_meta.get("mimeType", "video/mp4"),
                        "fileUri": file_meta["uri"],
                    },
                },
                {"text": plan_context},
                {"text": RUBRIC_PROMPT},
            ],
        }],
        "generationConfig": {
            "responseMimeType": "application/json",
            "temperature": 0.2,
        },
    }
    print("[critic] calling Gemini for scoring...", flush=True)
    url = f"{GENERATE_BASE}?key={api_key}"
    body = json.dumps(payload).encode("utf-8")
    response = _post(url, body, headers={"Content-Type": "application/json"})

    candidates = response.get("candidates", [])
    if not candidates:
        raise RuntimeError(f"no candidates in response: {response}")
    parts = candidates[0].get("content", {}).get("parts", [])
    text = "".join(p.get("text", "") for p in parts).strip()

    # Strip code fences if Gemini returned them despite responseMimeType
    cleaned = re.sub(r"^```json\s*|\s*```$", "", text, flags=re.IGNORECASE | re.MULTILINE).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"failed to parse critic JSON. Raw: {text[:600]}") from exc


def delete_uploaded_file(name: str, api_key: str) -> None:
    """Best-effort cleanup of the uploaded file."""
    url = f"https://generativelanguage.googleapis.com/v1beta/{name}?key={api_key}"
    try:
        req = urllib.request.Request(url, method="DELETE")
        urllib.request.urlopen(req, timeout=30)
    except Exception:
        pass


# ----- Plan context -----

def build_plan_context(plan_path: Path | None) -> str:
    if not plan_path or not plan_path.exists():
        return "No storyboard plan was provided. Score from the video alone."
    plan = json.loads(plan_path.read_text())
    shots = plan.get("shots", [])
    summary_lines = [
        f"Storyboard plan provided for context: {plan.get('project', plan_path.stem)}.",
        f"Style id: {plan.get('style_id', 'unspecified')}.",
        "Shot sequence (use this to evaluate execution-vs-intent, not as content to grade verbatim):",
    ]
    for i, shot in enumerate(shots, 1):
        summary_lines.append(
            f"  {i}. [{shot.get('name')}] {shot.get('duration_s', '?')}s — "
            f"VO: \"{shot.get('vo_text', '')[:100]}\" — "
            f"Caption: \"{shot.get('subtitle', '')[:80]}\""
        )
    return "\n".join(summary_lines)


# ----- Entry point -----

def main() -> None:
    if len(sys.argv) < 2:
        print(f"Usage: python3 -m pipeline.video_critic <video_path> [<plan_json>]", file=sys.stderr)
        sys.exit(2)

    load_all_env()
    api_key = require_key("GEMINI_API_KEY")

    video_path = Path(sys.argv[1]).resolve()
    plan_path = Path(sys.argv[2]).resolve() if len(sys.argv) > 2 else None
    if not video_path.exists():
        raise FileNotFoundError(f"video not found: {video_path}")

    plan_context = build_plan_context(plan_path)
    print(plan_context, flush=True)
    print("", flush=True)

    file_meta = upload_video(video_path, api_key)
    try:
        result = critique(file_meta, plan_context, api_key)
    finally:
        delete_uploaded_file(file_meta.get("name", ""), api_key)

    # Persist alongside the video
    out_path = video_path.parent / f"{video_path.stem}_critic.json"
    out_path.write_text(json.dumps(result, indent=2))

    # Print summary
    print(json.dumps(result, indent=2), flush=True)
    print(f"\n[critic] saved -> {out_path}", flush=True)


if __name__ == "__main__":
    main()
