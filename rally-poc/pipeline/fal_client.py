"""fal.ai API client for Nano Banana 2 image generation."""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Optional

QUEUE_URL = "https://queue.fal.run/fal-ai/nano-banana-2"
DEFAULT_POLL_SECONDS = 4
DEFAULT_TIMEOUT_SECONDS = 120
REQUEST_TIMEOUT = 60

TERMINAL_STATES = {"COMPLETED", "FAILED"}


class FalError(RuntimeError):
    pass


class FalRetryableError(FalError):
    pass


@dataclass(frozen=True)
class NB2Result:
    request_id: str
    image_url: str


def submit_nb2(
    *,
    prompt: str,
    api_key: str,
    aspect_ratio: str = "9:16",
    resolution: str = "1K",
    output_format: str = "png",
    reference_images: Optional[list[str]] = None,
) -> str:
    """Submit an NB2 generation job. Returns request_id."""
    payload: dict = {
        "prompt": prompt,
        "aspect_ratio": aspect_ratio,
        "resolution": resolution,
        "output_format": output_format,
    }
    if reference_images:
        payload["reference_images"] = [{"url": u} for u in reference_images]

    resp = _post_json(QUEUE_URL, payload, api_key)
    request_id = resp.get("request_id", "")
    if not request_id:
        raise FalError(f"No request_id in response: {resp}")
    return request_id


def wait_for_nb2(
    *,
    request_id: str,
    api_key: str,
    poll_seconds: int = DEFAULT_POLL_SECONDS,
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
) -> NB2Result:
    """Poll until the NB2 job completes and return the image URL."""
    status_url = f"{QUEUE_URL}/requests/{request_id}/status"
    start = time.time()

    while True:
        elapsed = time.time() - start
        if elapsed > timeout_seconds:
            raise FalError(f"Timed out after {timeout_seconds}s for {request_id}")

        resp = _get_json(status_url, api_key)
        status = resp.get("status", "")

        if status in TERMINAL_STATES:
            break

        time.sleep(poll_seconds)

    if status == "FAILED":
        raise FalError(f"NB2 request {request_id} failed: {resp}")

    # Fetch result
    result_url = f"{QUEUE_URL}/requests/{request_id}"
    result = _get_json(result_url, api_key)

    images = result.get("images") or result.get("output", {}).get("images", [])
    if not images:
        raise FalError(f"No images in result: {result}")

    image_url = images[0].get("url", "") if isinstance(images[0], dict) else images[0]
    if not image_url:
        raise FalError(f"No image URL in result: {result}")

    return NB2Result(request_id=request_id, image_url=image_url)


def generate_image(
    *,
    prompt: str,
    api_key: str,
    aspect_ratio: str = "9:16",
    resolution: str = "1K",
    output_format: str = "png",
    reference_images: Optional[list[str]] = None,
    poll_seconds: int = DEFAULT_POLL_SECONDS,
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
) -> NB2Result:
    """Submit + wait convenience function."""
    request_id = submit_nb2(
        prompt=prompt,
        api_key=api_key,
        aspect_ratio=aspect_ratio,
        resolution=resolution,
        output_format=output_format,
        reference_images=reference_images,
    )
    return wait_for_nb2(
        request_id=request_id,
        api_key=api_key,
        poll_seconds=poll_seconds,
        timeout_seconds=timeout_seconds,
    )


def download_image(url: str, destination: str) -> str:
    """Download an image from a URL to a local path."""
    request = urllib.request.Request(url, headers={"User-Agent": "rally-pipeline/1.0"})
    with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT) as resp:
        data = resp.read()
    with open(destination, "wb") as f:
        f.write(data)
    return destination


# -- internal helpers ------------------------------------------------------

_HEADERS = {
    "User-Agent": "rally-pipeline/1.0",
    "Accept": "application/json",
}


def _post_json(url: str, payload: dict, api_key: str) -> dict:
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        headers={
            **_HEADERS,
            "Content-Type": "application/json",
            "Authorization": f"Key {api_key}",
        },
        method="POST",
    )
    return _do_request(request)


def _get_json(url: str, api_key: str) -> dict:
    request = urllib.request.Request(
        url,
        headers={
            **_HEADERS,
            "Authorization": f"Key {api_key}",
        },
        method="GET",
    )
    return _do_request(request)


def _do_request(request: urllib.request.Request) -> dict:
    try:
        with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT) as resp:
            raw = resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        text = e.read().decode("utf-8") if e.fp else ""
        msg = f"fal.ai API error {e.code}: {text[:300]}"
        if e.code in {408, 429} or 500 <= e.code <= 599:
            raise FalRetryableError(msg) from e
        raise FalError(msg) from e
    except urllib.error.URLError as e:
        raise FalRetryableError(f"Network error: {e}") from e
    except (ConnectionError, TimeoutError, OSError) as e:
        raise FalRetryableError(f"Connection error: {e}") from e

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as e:
        raise FalError(f"Invalid JSON from fal.ai: {raw[:200]}") from e

    if not isinstance(parsed, dict):
        raise FalError(f"Unexpected response shape: {type(parsed)}")
    return parsed
