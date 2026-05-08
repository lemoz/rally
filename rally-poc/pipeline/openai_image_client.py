"""OpenAI image generation client (gpt-image-1, aka GPT Image 2).

Better than NB2 for infographic-style storyboard posters: handles typography,
multi-panel layouts, and complex text overlays cleanly. Used by the
storyboard-poster pipeline path.

Usage:
    from pipeline.openai_image_client import generate_image
    result = generate_image(prompt="...", api_key=key, size="1536x1024")
    Path("out.png").write_bytes(result.image_bytes)
"""
from __future__ import annotations

import base64
import json
import urllib.error
import urllib.request
from dataclasses import dataclass

API_URL = "https://api.openai.com/v1/images/generations"
DEFAULT_MODEL = "gpt-image-2"
REQUEST_TIMEOUT = 300


class OpenAIImageError(RuntimeError):
    pass


class OpenAIImageRetryableError(OpenAIImageError):
    pass


@dataclass
class OpenAIImageResult:
    image_bytes: bytes
    revised_prompt: str | None
    cost_usd: float


# gpt-image-1 pricing (approximate, from OpenAI docs late 2025):
# - low quality 1024x1024: ~$0.011
# - medium quality 1024x1024: ~$0.042
# - high quality 1024x1024: ~$0.167
# - high quality 1792x1024 (or 1024x1792): ~$0.250
# - high quality 1536x1024: ~$0.190
COST_LOOKUP = {
    ("low", "1024x1024"): 0.011,
    ("medium", "1024x1024"): 0.042,
    ("high", "1024x1024"): 0.167,
    ("high", "1536x1024"): 0.190,
    ("high", "1024x1536"): 0.190,
    ("high", "1792x1024"): 0.250,
    ("high", "1024x1792"): 0.250,
}


def generate_image(
    *,
    prompt: str,
    api_key: str,
    size: str = "1536x1024",
    quality: str = "high",
    model: str = DEFAULT_MODEL,
    n: int = 1,
) -> OpenAIImageResult:
    """Generate an image via OpenAI's images endpoint. Returns image bytes."""

    payload = {
        "model": model,
        "prompt": prompt,
        "size": size,
        "quality": quality,
        "n": n,
    }
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        API_URL,
        data=body,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
            "User-Agent": "rally-pipeline/1.0",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT) as resp:
            response = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        text = e.read().decode("utf-8", errors="replace") if e.fp else ""
        msg = f"OpenAI image API error {e.code}: {text[:500]}"
        if e.code in {408, 429} or 500 <= e.code <= 599:
            raise OpenAIImageRetryableError(msg) from e
        raise OpenAIImageError(msg) from e
    except urllib.error.URLError as e:
        raise OpenAIImageRetryableError(f"Network error: {e}") from e

    data = response.get("data", [])
    if not data:
        raise OpenAIImageError(f"No image data in response: {response}")

    first = data[0]
    if first.get("b64_json"):
        image_bytes = base64.b64decode(first["b64_json"])
    elif first.get("url"):
        # Fallback: download from URL
        with urllib.request.urlopen(first["url"], timeout=120) as resp:
            image_bytes = resp.read()
    else:
        raise OpenAIImageError(f"Unexpected data shape: {first.keys()}")

    revised = first.get("revised_prompt")
    cost = COST_LOOKUP.get((quality, size), 0.0)
    return OpenAIImageResult(image_bytes=image_bytes, revised_prompt=revised, cost_usd=cost)
