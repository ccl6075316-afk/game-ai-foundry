"""OpenAI-compatible async video generation (Apilio / OpenRouter / similar)."""

from __future__ import annotations

import base64
import mimetypes
import sys
import time
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse

import requests

from proxy_utils import http_get, http_post
from video_route import normalize_video_model

_MAX_REFERENCE_BYTES = 4 * 1024 * 1024
_MAX_REFERENCE_EDGE = 512


class CompatVideoError(RuntimeError):
    """Raised when a compatible video gateway call fails."""


def _api_url(api_base: str, rel: str) -> str:
    base = api_base.rstrip("/") + "/"
    return urljoin(base, rel.lstrip("/"))


def _gateway_origin(api_base: str) -> str:
    parsed = urlparse(str(api_base or "").strip())
    if parsed.scheme and parsed.netloc:
        return f"{parsed.scheme}://{parsed.netloc}"
    return ""


def _resolve_submit_url(api_base: str, rel_or_url: str) -> str:
    if rel_or_url.startswith(("http://", "https://")):
        return rel_or_url
    return _api_url(api_base, rel_or_url)


def video_vendor_family(model: str) -> str | None:
    mid = str(model or "").strip().lower()
    if mid.startswith(("wan", "wanx")) or "/wan" in mid:
        return "wan"
    if "hailuo" in mid or mid.startswith("minimax-h3"):
        return "hailuo"
    return None


def _vendor_resolution(resolution: str, family: str) -> str:
    raw = str(resolution or "720p").strip().lower().replace("p", "")
    if family == "hailuo":
        return "1080P" if raw.startswith("1080") else "768P"
    if raw.startswith("1080"):
        return "1080P"
    if raw.startswith("480"):
        return "480P"
    return "720P"


def _wan_fixed_five_seconds(model: str) -> bool:
    mid = str(model or "").strip().lower()
    return mid in {
        "wan2.2-i2v-flash",
        "wan2.2-i2v-plus",
        "wanx2.1-i2v-plus",
    }


def _auth_headers(api_key: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}


def _error_snippet(resp: requests.Response) -> str:
    text = (resp.text or "").strip().replace("\n", " ")[:200]
    try:
        body = resp.json()
        err = body.get("error") if isinstance(body, dict) else None
        if isinstance(err, dict):
            msg = err.get("message") or err.get("code") or text
            return str(msg)[:200]
        if isinstance(body, dict) and isinstance(body.get("message"), str):
            return body["message"][:200]
    except (ValueError, AttributeError):
        pass
    return text


def _resized_png_bytes(image_path: Path, max_edge: int = _MAX_REFERENCE_EDGE) -> bytes:
    import cv2

    img = cv2.imread(str(image_path), cv2.IMREAD_UNCHANGED)
    if img is None:
        raise CompatVideoError(f"Cannot read reference image: {image_path}")
    height, width = img.shape[:2]
    edge = max(int(width), int(height))
    if edge > max_edge:
        scale = max_edge / float(edge)
        img = cv2.resize(
            img,
            (max(1, int(round(width * scale))), max(1, int(round(height * scale)))),
            interpolation=cv2.INTER_AREA,
        )
    ok, buf = cv2.imencode(".png", img)
    if not ok:
        raise CompatVideoError("Failed to encode resized reference PNG")
    return bytes(buf)


def encode_reference_data_url(image_path: Path) -> str:
    path = Path(image_path)
    mime, _ = mimetypes.guess_type(str(path))
    mime = mime or "image/png"
    try:
        data = _resized_png_bytes(path)
        mime = "image/png"
    except (CompatVideoError, OSError, ValueError):
        data = path.read_bytes()
    if len(data) > _MAX_REFERENCE_BYTES:
        raise CompatVideoError(
            f"Reference image too large ({len(data)} bytes). "
            f"Max {_MAX_REFERENCE_BYTES} for inline upload."
        )
    encoded = base64.b64encode(data).decode("ascii")
    return f"data:{mime};base64,{encoded}"


def build_compat_submit_attempts(
    *,
    model: str,
    prompt: str,
    duration: int,
    resolution: str,
    ratio: str,
    generate_audio: bool,
    reference_data_url: str | None,
) -> list[tuple[str, dict[str, Any]]]:
    """Ordered (path, payload) attempts. Apilio probe first, then OpenRouter / aggregator."""
    aspect = "1:1" if str(ratio).lower() in {"", "auto", "adaptive"} else str(ratio)

    apilio_payload: dict[str, Any] = {
        "model": model,
        "prompt": prompt,
        "duration": int(duration),
        "resolution": resolution,
        "ratio": aspect,
        "generate_audio": bool(generate_audio),
    }
    if reference_data_url:
        apilio_payload["input_reference"] = reference_data_url

    openrouter_payload: dict[str, Any] = {
        "model": model,
        "prompt": prompt,
        "duration": int(duration),
        "resolution": resolution,
        "aspect_ratio": aspect,
        "generate_audio": bool(generate_audio),
    }
    if reference_data_url:
        openrouter_payload["frame_images"] = [
            {
                "type": "image_url",
                "image_url": {"url": reference_data_url},
                "frame_type": "first_frame",
            }
        ]

    aggregator_payload: dict[str, Any] = {
        "model": model,
        "prompt": prompt,
        "duration": int(duration),
        "resolution": resolution,
        "ratio": aspect,
        "generate_audio": bool(generate_audio),
    }
    if reference_data_url:
        aggregator_payload["image"] = reference_data_url
        aggregator_payload["image_urls"] = [reference_data_url]

    return [
        ("videos", apilio_payload),
        ("videos", openrouter_payload),
        ("videos/generations", aggregator_payload),
    ]


def build_vendor_submit_attempts(
    *,
    api_base: str,
    model: str,
    prompt: str,
    duration: int,
    resolution: str,
    reference_data_url: str | None,
) -> list[tuple[str, dict[str, Any]]]:
    """Apilio gpt-best vendor paths (Wan / Hailuo). Origin is host root, not /v1."""
    family = video_vendor_family(model)
    origin = _gateway_origin(api_base)
    if not family or not origin or not reference_data_url:
        return []
    if family == "wan":
        dur = 5 if _wan_fixed_five_seconds(model) else int(duration)
        return [
            (
                f"{origin}/v2/videos/generations",
                {
                    "model": model,
                    "prompt": prompt,
                    "duration": dur,
                    "resolution": _vendor_resolution(resolution, "wan"),
                    "images": [reference_data_url],
                },
            )
        ]
    return [
        (
            f"{origin}/minimax/v1/video_generation",
            {
                "model": model,
                "prompt": prompt,
                "duration": int(duration),
                "resolution": _vendor_resolution(resolution, "hailuo"),
                "first_frame_image": reference_data_url,
            },
        )
    ]


def extract_task_id(data: Any) -> str | None:
    if not isinstance(data, dict):
        return None
    for key in ("id", "task_id", "job_id", "generation_id"):
        value = data.get(key)
        if value:
            return str(value)
    for nest_key in ("data", "output"):
        nested = data.get(nest_key)
        if isinstance(nested, dict):
            found = extract_task_id(nested)
            if found:
                return found
    return None


def extract_status(data: Any) -> str:
    if not isinstance(data, dict):
        return ""
    for key in ("status", "state", "task_status"):
        value = data.get(key)
        if value:
            return str(value).strip().lower()
    for nest_key in ("data", "output"):
        nested = data.get(nest_key)
        if isinstance(nested, dict):
            found = extract_status(nested)
            if found:
                return found
    return ""


def extract_video_url(data: Any) -> str | None:
    if not isinstance(data, dict):
        return None
    for key in ("video_url", "url", "download_url"):
        value = data.get(key)
        if isinstance(value, str) and value.startswith(("http://", "https://")):
            return value
    content = data.get("content")
    if isinstance(content, dict):
        url = content.get("video_url") or content.get("url")
        if isinstance(url, str) and url.startswith(("http://", "https://")):
            return url
    output = data.get("output")
    if isinstance(output, dict):
        found = extract_video_url(output)
        if found:
            return found
    if isinstance(output, list) and output:
        first = output[0]
        if isinstance(first, str) and first.startswith(("http://", "https://")):
            return first
        if isinstance(first, dict):
            found = extract_video_url(first)
            if found:
                return found
    file_block = data.get("file")
    if isinstance(file_block, dict):
        found = extract_video_url(file_block)
        if found:
            return found
    data_list = data.get("data")
    if isinstance(data_list, str) and data_list.startswith(("http://", "https://")):
        return data_list
    if isinstance(data_list, dict):
        return extract_video_url(data_list)
    return None


def _submit_first_ok(
    *,
    api_base: str,
    api_key: str,
    proxy: str | None,
    attempts: list[tuple[str, dict[str, Any]]],
) -> tuple[str, dict[str, Any], str]:
    last_error = "no video submit attempts"
    headers = _auth_headers(api_key)
    for rel, payload in attempts:
        url = _resolve_submit_url(api_base, rel)
        try:
            resp = http_post(proxy, url, headers=headers, json=payload, timeout=120)
        except requests.RequestException as exc:
            last_error = f"compat video probe {rel}: {exc}"
            print(last_error, file=sys.stderr)
            continue
        if resp.status_code in {200, 201, 202}:
            try:
                body = resp.json()
            except ValueError:
                last_error = f"compat video probe {rel} HTTP {resp.status_code}: invalid JSON"
                print(last_error, file=sys.stderr)
                continue
            task_id = extract_task_id(body)
            if not task_id:
                last_error = f"compat video probe {rel} missing task id"
                print(last_error, file=sys.stderr)
                continue
            print(
                f"video backend=openai_compat endpoint={rel} model={payload.get('model')}",
                file=sys.stderr,
            )
            return rel, body, task_id
        snippet = _error_snippet(resp)
        last_error = f"compat video probe {rel} HTTP {resp.status_code}: {snippet}"
        print(last_error, file=sys.stderr)
    raise CompatVideoError(last_error)


def _poll_url(api_base: str, submit_rel: str, task_id: str, submit_body: dict[str, Any]) -> str:
    polling = submit_body.get("polling_url")
    if isinstance(polling, str) and polling.startswith("http"):
        return polling
    if isinstance(polling, str) and polling.startswith("/"):
        return _api_url(api_base, polling.lstrip("/"))
    submit_url = _resolve_submit_url(api_base, submit_rel)
    if "/minimax/" in submit_url:
        origin = _gateway_origin(submit_url) or _gateway_origin(api_base)
        return f"{origin}/minimax/v1/query/video_generation?task_id={task_id}"
    if "/v2/videos/generations" in submit_url:
        return f"{submit_url.rstrip('/')}/{task_id}"
    if submit_rel.rstrip("/") == "videos":
        return _api_url(api_base, f"videos/{task_id}")
    return _api_url(api_base, f"videos/generations/{task_id}")


def _content_url(api_base: str, submit_rel: str, task_id: str) -> str:
    if submit_rel.rstrip("/") == "videos":
        return _api_url(api_base, f"videos/{task_id}/content")
    return _api_url(api_base, f"videos/generations/{task_id}/content")


def wait_for_compat_task(
    *,
    poll_url: str,
    api_key: str,
    proxy: str | None,
    poll_interval: float = 10.0,
    timeout: float = 600.0,
    on_status: Any | None = None,
) -> dict[str, Any]:
    deadline = time.time() + timeout
    last_status = ""
    headers = {"Authorization": f"Bearer {api_key}"}
    while time.time() < deadline:
        resp = http_get(proxy, poll_url, headers=headers, timeout=60)
        if resp.status_code != 200:
            raise CompatVideoError(
                f"Query video task failed (HTTP {resp.status_code}): {_error_snippet(resp)}"
            )
        try:
            task = resp.json()
        except ValueError as exc:
            raise CompatVideoError(f"Invalid JSON from video poll: {exc}") from exc
        status = extract_status(task) or "unknown"
        if status != last_status:
            last_status = status
            if on_status:
                on_status(status, task)
            else:
                print(f"video task status={status}", file=sys.stderr)
        if status in {"succeeded", "success", "completed", "complete", "successed"}:
            return task if isinstance(task, dict) else {"status": status}
        if status in {"failed", "cancelled", "canceled", "expired", "error"}:
            raise CompatVideoError(f"Video task {status}: {_task_error(task)}")
        time.sleep(poll_interval)
    raise CompatVideoError(f"Video task timed out after {timeout:.0f}s")


def _task_error(task: Any) -> str:
    if not isinstance(task, dict):
        return str(task)
    err = task.get("error") or task.get("message")
    if isinstance(err, dict):
        return str(err.get("message") or err.get("code") or err)[:200]
    if err:
        return str(err)[:200]
    return "unknown error"


def download_compat_video(
    *,
    video_url: str | None,
    content_url: str,
    output_path: Path,
    api_key: str,
    proxy: str | None,
) -> None:
    headers = {"Authorization": f"Bearer {api_key}"}
    if video_url:
        resp = http_get(proxy, video_url, headers=headers, timeout=300, stream=True)
        if resp.status_code == 200 and resp.content:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_bytes(resp.content)
            return
    resp = http_get(proxy, content_url, headers=headers, timeout=300, stream=True)
    if resp.status_code != 200 or not resp.content:
        raise CompatVideoError(
            f"Download video failed (HTTP {resp.status_code}): {_error_snippet(resp)}"
        )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(resp.content)


def generate_compat_video(
    *,
    model: str,
    prompt: str,
    output_path: Path,
    api_key: str,
    api_base: str,
    proxy: str | None = None,
    reference_image: Path | None = None,
    duration: int = 6,
    resolution: str = "720p",
    ratio: str = "1:1",
    generate_audio: bool = False,
    poll_interval: float = 10.0,
    timeout: float = 600.0,
    status_cb: Any | None = None,
) -> dict[str, Any]:
    """Submit → poll → download MP4 on an OpenAI-compatible video gateway."""
    resolved_model = normalize_video_model(model, api_base)
    reference_data_url = None
    if reference_image is not None:
        reference_data_url = encode_reference_data_url(Path(reference_image))
    attempts = [
        *build_vendor_submit_attempts(
            api_base=api_base,
            model=resolved_model,
            prompt=prompt,
            duration=duration,
            resolution=resolution,
            reference_data_url=reference_data_url,
        ),
        *build_compat_submit_attempts(
            model=resolved_model,
            prompt=prompt,
            duration=duration,
            resolution=resolution,
            ratio=ratio,
            generate_audio=generate_audio,
            reference_data_url=reference_data_url,
        ),
    ]
    out = Path(output_path)
    try:
        rel, body, task_id = _submit_first_ok(
            api_base=api_base,
            api_key=api_key,
            proxy=proxy,
            attempts=attempts,
        )
        poll_url = _poll_url(api_base, rel, task_id, body)
        task = wait_for_compat_task(
            poll_url=poll_url,
            api_key=api_key,
            proxy=proxy,
            poll_interval=poll_interval,
            timeout=timeout,
            on_status=status_cb,
        )
        video_url = extract_video_url(task) or extract_video_url(body)
        download_compat_video(
            video_url=video_url,
            content_url=_content_url(api_base, rel, task_id),
            output_path=out,
            api_key=api_key,
            proxy=proxy,
        )
    except Exception:
        if out.is_file() and out.stat().st_size == 0:
            out.unlink(missing_ok=True)
        elif out.is_file() and not _looks_like_mp4(out):
            out.unlink(missing_ok=True)
        raise
    return {"task_id": task_id, "endpoint": rel, "model": resolved_model, "task": task}


def _looks_like_mp4(path: Path) -> bool:
    try:
        head = path.read_bytes()[:12]
    except OSError:
        return False
    return b"ftyp" in head
