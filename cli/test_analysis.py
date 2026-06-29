"""Tester role — vision analysis and validation reports."""

from __future__ import annotations

import base64
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

from brief import load_brief_full
from llm_config import resolve_test_api_settings
from proxy_utils import http_post


class TestAnalysisError(RuntimeError):
    pass


def criteria_from_brief(brief_path: Path) -> list[dict[str, str]]:
    """Derive acceptance criteria text from brief project fields."""
    project, _assets, _graphs = load_brief_full(brief_path)
    criteria: list[dict[str, str]] = []

    def add(source: str, text: str | None) -> None:
        if text and str(text).strip():
            criteria.append({"source": source, "criterion": str(text).strip()})

    add("brief.project.title", project.title)
    add("brief.project.description", project.description)
    add("brief.project.gameplay_loop", project.gameplay_loop)
    add("brief.project.session_goal", project.session_goal)
    add("brief.project.art_direction", project.art_direction)

    if not criteria:
        criteria.append(
            {
                "source": "default",
                "criterion": "Main scene renders without obvious errors; sprites visible on screen.",
            }
        )
    return criteria


def _encode_image_b64(image_path: Path) -> str:
    data = image_path.read_bytes()
    return base64.standard_b64encode(data).decode("ascii")


def _extract_json_object(text: str) -> dict[str, Any]:
    text = text.strip()
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{[\s\S]*\}", text)
    if match:
        parsed = json.loads(match.group(0))
        if isinstance(parsed, dict):
            return parsed
    raise TestAnalysisError("Vision model did not return JSON object")


def analyze_screenshot(
    image_path: Path,
    criteria: list[dict[str, str]],
    *,
    config: dict[str, Any],
    extra_context: str | None = None,
    reference_image_path: Path | None = None,
) -> dict[str, Any]:
    """Call vision-capable LLM to evaluate screenshot against criteria."""
    settings = resolve_test_api_settings(config)
    api_key = settings.get("api_key")
    if not api_key:
        raise TestAnalysisError("No API key for test analysis (config host/test or OPENROUTER_API_KEY)")

    criteria_block = "\n".join(
        f"- [{c['source']}] {c['criterion']}" for c in criteria
    )
    system = (
        "You are a game QA tester. Compare the screenshot to acceptance criteria. "
        "Respond with JSON only: "
        '{"status":"passed"|"failed"|"inconclusive",'
        '"summary":"...",'
        '"failed_criteria":[{"source":"...","criterion":"...","evidence":"...","recommended_change":"..."}],'
        '"passed_criteria":["..."],'
        '"visual_notes":["..."]}'
    )
    user_text = (
        "Evaluate this game screenshot against the criteria below.\n\n"
        f"Criteria:\n{criteria_block}\n"
    )
    if reference_image_path is not None and reference_image_path.is_file():
        user_text += (
            "\nA second image is the Visual Target (north-star reference). "
            "Compare palette, composition, and mood — not pixel-perfect match.\n"
        )
    if extra_context:
        user_text += f"\nContext:\n{extra_context}\n"

    b64 = _encode_image_b64(image_path)
    user_content: list[dict[str, Any]] = [
        {"type": "text", "text": user_text},
        {
            "type": "image_url",
            "image_url": {"url": f"data:image/png;base64,{b64}"},
        },
    ]
    if reference_image_path is not None and reference_image_path.is_file():
        ref_b64 = _encode_image_b64(reference_image_path)
        user_content.append(
            {
                "type": "image_url",
                "image_url": {"url": f"data:image/png;base64,{ref_b64}"},
            }
        )
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": user_content},
    ]

    endpoint = str(settings["api_base"]).rstrip("/") + "/chat/completions"
    payload = {
        "model": settings["model"],
        "messages": messages,
        "temperature": 0.2,
    }
    try:
        response = http_post(
            settings.get("proxy"),
            endpoint,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=120,
        )
    except requests.RequestException as exc:
        raise TestAnalysisError(f"Vision API request failed: {exc}") from exc

    if response.status_code != 200:
        detail = response.text.strip()
        try:
            detail = response.json().get("error", {}).get("message", detail)
        except (json.JSONDecodeError, AttributeError, TypeError):
            pass
        raise TestAnalysisError(f"Vision API error (HTTP {response.status_code}): {detail}")

    try:
        content = response.json()["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
        raise TestAnalysisError("Malformed vision API response") from exc

    if isinstance(content, list):
        parts = [p.get("text", "") for p in content if isinstance(p, dict) and p.get("type") == "text"]
        content = "\n".join(parts)

    analysis = _extract_json_object(str(content))
    analysis.setdefault("status", "inconclusive")
    analysis["model"] = settings["model"]
    return analysis


def build_validation_report(
    *,
    brief_path: Path | None,
    project_path: Path,
    screenshot_path: Path | None,
    build_ok: bool,
    build_error: str | None,
    analysis: dict[str, Any] | None,
    criteria: list[dict[str, str]],
) -> dict[str, Any]:
    """Assemble Validation Report (ITERATIVE-PRODUCTION §6 shape)."""
    layers: dict[str, Any] = {
        "build": {"ok": build_ok, "error": build_error},
        "screenshot": {
            "ok": screenshot_path is not None and screenshot_path.is_file(),
            "path": str(screenshot_path) if screenshot_path else None,
        },
    }

    status = "failed"
    if build_ok and layers["screenshot"]["ok"]:
        if analysis:
            status = str(analysis.get("status", "inconclusive"))
        else:
            status = "passed" if build_ok else "failed"
    elif not build_ok:
        status = "failed"

    report: dict[str, Any] = {
        "validation_report": {
            "status": status,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "project_path": str(project_path.resolve()),
            "brief_path": str(brief_path.resolve()) if brief_path else None,
            "criteria": criteria,
            "layers": layers,
            "analysis": analysis,
            "failed_criteria": (analysis or {}).get("failed_criteria", []),
            "regressions": [],
        }
    }
    if not build_ok and build_error:
        report["validation_report"]["failed_criteria"] = [
            {
                "source": "build_validation",
                "criterion": "Godot import/build/boot succeeds",
                "evidence": build_error[:2000],
                "recommended_change": "Fix C# / scene errors before visual QA",
            }
        ]
    return report
