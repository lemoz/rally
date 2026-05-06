"""RunComfy lipsync v2 API integration."""
from __future__ import annotations

import json
import shutil
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

DEFAULT_BASE_URL = "https://model-api.runcomfy.net/v1"
MODEL_PATH = "models/sync/sync/lipsync/v2"
DEFAULT_POLL_SECONDS = 8
DEFAULT_TIMEOUT_SECONDS = 900
REQUEST_TIMEOUT = 60

TERMINAL_STATES = {"completed", "failed", "cancelled"}


class RunComfyError(RuntimeError):
    """Base error for RunComfy API failures."""


class RunComfyRetryableError(RunComfyError):
    """Retryable HTTP error."""


@dataclass(frozen=True)
class LipsyncResult:
    """Result of a completed lipsync job."""

    request_id: str
    status: str
    output: dict = field(default_factory=dict)


def submit_lipsync(
    *,
    video_url: str,
    audio_url: str,
    api_token: str,
    sync_mode: str = "cut_off",
    base_url: str = DEFAULT_BASE_URL,
) -> dict:
    """Submit a lipsync job and return the raw response dict."""
    url = f"{base_url.rstrip('/')}/{MODEL_PATH}"
    payload: dict = {
        "video_url": video_url,
        "audio_url": audio_url,
    }
    if sync_mode:
        payload["sync_mode"] = sync_mode
    return _post_json(url, payload, api_token)


def wait_for_completion(
    *,
    request_id: str,
    api_token: str,
    base_url: str = DEFAULT_BASE_URL,
    poll_seconds: int = DEFAULT_POLL_SECONDS,
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
) -> LipsyncResult:
    """Poll until the request reaches a terminal state and return results."""
    base = base_url.rstrip("/")
    status_url = f"{base}/requests/{request_id}/status"
    result_url = f"{base}/requests/{request_id}/result"
    start = time.time()

    while True:
        elapsed = time.time() - start
        if elapsed > timeout_seconds:
            raise RunComfyError(
                f"Timed out after {timeout_seconds}s waiting for request {request_id}"
            )

        status_resp = _get_json(status_url, api_token)
        status = status_resp.get("status", "")
        print(f"  [{int(elapsed)}s] request {request_id}: {status}")

        if status in TERMINAL_STATES:
            break

        time.sleep(poll_seconds)

    result_resp = _get_json(result_url, api_token)
    result_status = result_resp.get("status", status)
    error_msg = result_resp.get("error", "")

    if result_status == "failed" or error_msg:
        raise RunComfyError(
            f"Request {request_id} failed: {error_msg or result_resp}"
        )
    if result_status not in ("completed",):
        raise RunComfyError(f"Request {request_id} ended with status: {result_status}")

    output = result_resp.get("output", {})
    return LipsyncResult(request_id=request_id, status=result_status, output=output)


def download_file(source_url: str, destination: Path) -> Path:
    """Download a file from a URL to a local path."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    parsed = urllib.parse.urlparse(source_url)
    if parsed.scheme in ("", "file"):
        source_path = Path(parsed.path)
        if source_path.exists():
            shutil.copyfile(source_path, destination)
            return destination
    with urllib.request.urlopen(source_url, timeout=REQUEST_TIMEOUT) as response:
        with destination.open("wb") as handle:
            shutil.copyfileobj(response, handle)
    return destination


# -- internal helpers --------------------------------------------------------


_DEFAULT_HEADERS = {
    "User-Agent": "creative-generation/1.0",
    "Accept": "application/json",
}


def _post_json(url: str, payload: dict, api_token: str) -> dict:
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        headers={
            **_DEFAULT_HEADERS,
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_token}",
        },
        method="POST",
    )
    return _do_request(request)


def _get_json(url: str, api_token: str) -> dict:
    request = urllib.request.Request(
        url,
        headers={
            **_DEFAULT_HEADERS,
            "Authorization": f"Bearer {api_token}",
        },
        method="GET",
    )
    return _do_request(request)


def _do_request(request: urllib.request.Request) -> dict:
    try:
        with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT) as response:
            raw = response.read().decode("utf-8")
    except urllib.error.HTTPError as error:
        status = error.code
        text = error.read().decode("utf-8") if error.fp else ""
        message = f"RunComfy API error {status}: {text}".strip()
        if status in {408, 429} or 500 <= status <= 599:
            raise RunComfyRetryableError(message) from error
        raise RunComfyError(message) from error
    except urllib.error.URLError as error:
        raise RunComfyRetryableError(f"Network error: {error}") from error

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as error:
        raise RunComfyError(f"Invalid JSON from RunComfy: {raw[:200]}") from error

    if not isinstance(parsed, dict):
        raise RunComfyError(f"Unexpected response shape: {type(parsed)}")
    return parsed
