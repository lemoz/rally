"""Google Cloud Storage upload helper."""
from __future__ import annotations

import os
import subprocess

DEFAULT_BUCKET = "govclip-temp-files"
DEFAULT_PREFIX = "lipsync"


class GCSError(RuntimeError):
    pass


def upload_to_gcs(
    local_path: str,
    gcs_name: str,
    *,
    bucket: str = DEFAULT_BUCKET,
    prefix: str = DEFAULT_PREFIX,
) -> str:
    """Upload a file to GCS and return its public URL."""
    if not os.path.exists(local_path):
        raise GCSError(f"File not found: {local_path}")

    gcs_path = f"gs://{bucket}/{prefix}/{gcs_name}"
    result = subprocess.run(
        ["gsutil", "cp", local_path, gcs_path],
        capture_output=True, text=True, timeout=120,
    )
    if result.returncode != 0:
        raise GCSError(f"GCS upload failed: {result.stderr[:300]}")

    return f"https://storage.googleapis.com/{bucket}/{prefix}/{gcs_name}"
