"""Volcengine Ark Seedance video generation API (async tasks)."""

from __future__ import annotations

import base64
import mimetypes
import time
from pathlib import Path
from typing import Any

import requests

from proxy_utils import create_http_session, http_get, http_post

DEFAULT_API_BASE = "https://ark.cn-beijing.volces.com/api/v3"
MAX_REFERENCE_IMAGE_BYTES = 4 * 1024 * 1024

DEFAULT_API_BASE = "https://ark.cn-beijing.volces.com/api/v3"

SEEDANCE_MODELS: dict[str, str] = {
    "pro": "doubao-seedance-2-0-260128",
    "fast": "doubao-seedance-2-0-fast-260128",
    "mini": "doubao-seedance-2-0-mini-260615",
}


class SeedanceError(RuntimeError):
    """Raised when Seedance API calls fail."""


def resolve_model(model: str) -> str:
    """Accept alias (pro/fast/mini) or full model id."""
    key = model.strip().lower()
    if key in SEEDANCE_MODELS:
        return SEEDANCE_MODELS[key]
    return model.strip()


def _api_url(api_base: str, path: str) -> str:
    return api_base.rstrip("/") + path


def _auth_headers(api_key: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {api_key}"}


def _parse_error(resp: requests.Response) -> str:
    detail = resp.text.strip()[:500]
    try:
        body = resp.json()
        err = body.get("error")
        if isinstance(err, dict):
            return str(err.get("message") or err.get("code") or detail)
        if isinstance(body.get("message"), str):
            return body["message"]
    except (ValueError, AttributeError):
        pass
    return detail


def _image_content_item_from_url(url: str, *, role: str = "first_frame") -> dict[str, Any]:
    return {
        "type": "image_url",
        "image_url": {"url": url},
        "role": role,
    }


def _image_content_item_from_path(image_path: Path, *, role: str = "first_frame") -> dict[str, Any]:
    """Encode a local image for Seedance i2v (Files API id:// is not accepted)."""
    if str(image_path).startswith(("http://", "https://")):
        return _image_content_item_from_url(str(image_path), role=role)

    data = image_path.read_bytes()
    if len(data) > MAX_REFERENCE_IMAGE_BYTES:
        raise SeedanceError(
            f"Reference image too large ({len(data)} bytes). "
            f"Max {MAX_REFERENCE_IMAGE_BYTES} for inline upload."
        )

    mime, _ = mimetypes.guess_type(str(image_path))
    mime = mime or "image/png"
    encoded = base64.b64encode(data).decode("ascii")
    return _image_content_item_from_url(f"data:{mime};base64,{encoded}", role=role)


def upload_image_file(
    image_path: Path,
    *,
    api_key: str,
    api_base: str = DEFAULT_API_BASE,
    proxy: str | None = None,
) -> dict[str, Any]:
    """Upload a local image via Files API; returns file object with id/url."""
    mime, _ = mimetypes.guess_type(str(image_path))
    mime = mime or "image/png"
    url = _api_url(api_base, "/files")
    headers = _auth_headers(api_key)
    session = create_http_session(proxy)

    with image_path.open("rb") as handle:
        resp = session.post(
            url,
            headers=headers,
            files={"file": (image_path.name, handle, mime)},
            data={"purpose": "user_data"},
            timeout=120,
        )

    if resp.status_code != 200:
        raise SeedanceError(
            f"File upload failed (HTTP {resp.status_code}): {_parse_error(resp)}"
        )

    try:
        data = resp.json()
    except ValueError as exc:
        raise SeedanceError(f"Invalid JSON from file upload: {exc}") from exc

    if not data.get("id"):
        raise SeedanceError(f"File upload response missing id: {data}")
    return data


def _image_content_item(file_obj: dict[str, Any]) -> dict[str, Any]:
    """Build Seedance content item from Files API response (when url is present)."""
    file_url = file_obj.get("url")
    if isinstance(file_url, str) and file_url.startswith("http"):
        return _image_content_item_from_url(file_url)
    raise SeedanceError(
        "Uploaded file has no public url. Use local path reference (base64 inline) instead."
    )


def build_task_payload(
    *,
    model: str,
    prompt: str,
    reference_image_item: dict[str, Any] | None = None,
    duration: int = 5,
    resolution: str = "720p",
    ratio: str = "1:1",
    generate_audio: bool = False,
    watermark: bool = False,
) -> dict[str, Any]:
    """Assemble create-task body for text-to-video or image-to-video."""
    content: list[dict[str, Any]] = [
        {"type": "text", "text": prompt.strip()},
    ]
    if reference_image_item is not None:
        content.append(reference_image_item)

    return {
        "model": resolve_model(model),
        "content": content,
        "duration": duration,
        "resolution": resolution,
        "ratio": ratio,
        "generate_audio": generate_audio,
        "watermark": watermark,
    }


def create_video_task(
    payload: dict[str, Any],
    *,
    api_key: str,
    api_base: str = DEFAULT_API_BASE,
    proxy: str | None = None,
) -> str:
    """Submit async video task; returns task id."""
    url = _api_url(api_base, "/contents/generations/tasks")
    resp = http_post(
        proxy,
        url,
        headers={**_auth_headers(api_key), "Content-Type": "application/json"},
        json=payload,
        timeout=120,
    )
    if resp.status_code != 200:
        raise SeedanceError(
            f"Create task failed (HTTP {resp.status_code}): {_parse_error(resp)}"
        )
    try:
        data = resp.json()
    except ValueError as exc:
        raise SeedanceError(f"Invalid JSON from create task: {exc}") from exc

    task_id = data.get("id")
    if not task_id:
        raise SeedanceError(f"Create task response missing id: {data}")
    return str(task_id)


def get_video_task(
    task_id: str,
    *,
    api_key: str,
    api_base: str = DEFAULT_API_BASE,
    proxy: str | None = None,
) -> dict[str, Any]:
    url = _api_url(api_base, f"/contents/generations/tasks/{task_id}")
    resp = http_get(proxy, url, headers=_auth_headers(api_key), timeout=60)
    if resp.status_code != 200:
        raise SeedanceError(
            f"Query task failed (HTTP {resp.status_code}): {_parse_error(resp)}"
        )
    try:
        return resp.json()
    except ValueError as exc:
        raise SeedanceError(f"Invalid JSON from query task: {exc}") from exc


def extract_video_url(task: dict[str, Any]) -> str | None:
    content = task.get("content")
    if isinstance(content, dict):
        url = content.get("video_url")
        if isinstance(url, str) and url:
            return url
    return None


def wait_for_video_task(
    task_id: str,
    *,
    api_key: str,
    api_base: str = DEFAULT_API_BASE,
    proxy: str | None = None,
    poll_interval: float = 10.0,
    timeout: float = 600.0,
    on_status: Any | None = None,
) -> dict[str, Any]:
    """Poll until task succeeds or fails."""
    deadline = time.time() + timeout
    last_status = ""

    while time.time() < deadline:
        task = get_video_task(task_id, api_key=api_key, api_base=api_base, proxy=proxy)
        status = str(task.get("status", "")).lower()
        if status != last_status:
            last_status = status
            if on_status:
                on_status(status, task)

        if status == "succeeded":
            return task
        if status in {"failed", "cancelled", "expired"}:
            err = task.get("error")
            msg = err if err else status
            raise SeedanceError(f"Video task {task_id} {status}: {msg}")

        time.sleep(poll_interval)

    raise SeedanceError(f"Video task {task_id} timed out after {timeout:.0f}s")


def download_video(
    video_url: str,
    output_path: Path,
    *,
    proxy: str | None = None,
) -> None:
    resp = http_get(proxy, video_url, timeout=300, stream=True)
    if resp.status_code != 200:
        raise SeedanceError(f"Download failed (HTTP {resp.status_code}): {video_url}")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(resp.content)


def generate_video(
    *,
    model: str,
    prompt: str,
    output_path: Path,
    api_key: str,
    api_base: str = DEFAULT_API_BASE,
    proxy: str | None = None,
    reference_image: Path | None = None,
    duration: int = 5,
    resolution: str = "720p",
    ratio: str = "1:1",
    generate_audio: bool = False,
    watermark: bool = False,
    poll_interval: float = 10.0,
    timeout: float = 600.0,
    status_cb: Any | None = None,
) -> dict[str, Any]:
    """End-to-end: optional local reference image → create → poll → download."""
    reference_image_item = None
    if reference_image is not None:
        reference_image_item = _image_content_item_from_path(reference_image)

    payload = build_task_payload(
        model=model,
        prompt=prompt,
        reference_image_item=reference_image_item,
        duration=duration,
        resolution=resolution,
        ratio=ratio,
        generate_audio=generate_audio,
        watermark=watermark,
    )
    task_id = create_video_task(
        payload, api_key=api_key, api_base=api_base, proxy=proxy
    )
    task = wait_for_video_task(
        task_id,
        api_key=api_key,
        api_base=api_base,
        proxy=proxy,
        poll_interval=poll_interval,
        timeout=timeout,
        on_status=status_cb,
    )
    video_url = extract_video_url(task)
    if not video_url:
        raise SeedanceError(f"Task succeeded but no video_url in response: {task}")

    download_video(video_url, output_path, proxy=proxy)
    return {"task_id": task_id, "video_url": video_url, "task": task}
