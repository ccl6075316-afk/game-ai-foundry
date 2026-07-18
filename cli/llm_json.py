"""Robust extraction of a JSON object from LLM text.

Handles: markdown fences, nested objects, preamble/trailing prose,
trailing commas, smart quotes, raw newlines inside strings, BOM,
and lightly truncated braces.
"""

from __future__ import annotations

import json
import re
from typing import Any


class LlmJsonError(ValueError):
    """Raised when no JSON object can be recovered from model output."""


def _strip_bom(text: str) -> str:
    return text.lstrip("\ufeff").strip()


def _strip_fence_wrappers(text: str) -> str:
    """Remove outer ``` / ```json wrappers when the whole payload is fenced."""
    t = text.strip()
    m = re.match(r"^```(?:json|JSON)?\s*\n?(.*?)\n?```\s*$", t, re.DOTALL)
    if m:
        return m.group(1).strip()
    # Leading fence without requiring closing at end (truncated replies).
    m2 = re.match(r"^```(?:json|JSON)?\s*\n?(.*)$", t, re.DOTALL)
    if m2 and "{" in m2.group(1):
        inner = m2.group(1)
        if "```" in inner:
            inner = inner.rsplit("```", 1)[0]
        return inner.strip()
    return t


def _extract_balanced_object(text: str) -> str | None:
    """Return the first top-level `{...}` substring with string-aware scanning."""
    start = text.find("{")
    if start < 0:
        return None
    depth = 0
    in_string = False
    escape = False
    for i in range(start, len(text)):
        ch = text[i]
        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[start : i + 1]
    # Truncated: return from start so repair can close braces.
    if depth > 0:
        return text[start:]
    return None


def _escape_raw_controls_in_strings(text: str) -> str:
    """Escape raw control chars inside JSON strings (common LLM mistake)."""
    out: list[str] = []
    in_string = False
    escape = False
    for ch in text:
        if in_string:
            if escape:
                out.append(ch)
                escape = False
                continue
            if ch == "\\":
                out.append(ch)
                escape = True
                continue
            if ch == '"':
                in_string = False
                out.append(ch)
                continue
            if ch == "\n":
                out.append("\\n")
                continue
            if ch == "\r":
                out.append("\\r")
                continue
            if ch == "\t":
                out.append("\\t")
                continue
            if ord(ch) < 32:
                out.append(f"\\u{ord(ch):04x}")
                continue
            out.append(ch)
            continue
        if ch == '"':
            in_string = True
        out.append(ch)
    return "".join(out)


def _repair_common(text: str) -> str:
    t = text
    # Smart / CJK quotes → ASCII
    for a, b in (
        ("\u201c", '"'),
        ("\u201d", '"'),
        ("\u2018", "'"),
        ("\u2019", "'"),
        ("\u300c", '"'),
        ("\u300d", '"'),
        ("\uff02", '"'),
    ):
        t = t.replace(a, b)
    # Trailing commas before } or ]
    t = re.sub(r",(\s*[}\]])", r"\1", t)
    # JS-style line comments (rare but seen)
    t = re.sub(r"(?m)^\s*//.*?$", "", t)
    return t.strip()


def _close_truncated(text: str) -> str:
    """Best-effort close truncated JSON objects/arrays/strings."""
    t = text.rstrip()
    if not t.startswith("{"):
        return t

    in_string = False
    escape = False
    stack: list[str] = []
    for ch in t:
        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
        elif ch == "{":
            stack.append("}")
        elif ch == "[":
            stack.append("]")
        elif ch in ("}", "]") and stack and stack[-1] == ch:
            stack.pop()

    if in_string:
        t += '"'
    # Drop dangling incomplete key/value after last comma or colon
    t = re.sub(r",\s*$", "", t)
    t = re.sub(r":\s*$", ": null", t)
    while stack:
        t += stack.pop()
    return t


def _try_load(candidate: str) -> dict[str, Any] | None:
    variants = [
        candidate,
        _repair_common(candidate),
        _escape_raw_controls_in_strings(candidate),
        _escape_raw_controls_in_strings(_repair_common(candidate)),
        _close_truncated(_repair_common(candidate)),
        _close_truncated(_escape_raw_controls_in_strings(_repair_common(candidate))),
    ]
    for variant in variants:
        if not variant:
            continue
        try:
            parsed = json.loads(variant)
        except json.JSONDecodeError:
            try:
                parsed, _ = json.JSONDecoder().raw_decode(variant)
            except json.JSONDecodeError:
                continue
        if isinstance(parsed, dict):
            return parsed
    return None


def _extract_field_string(text: str, field: str) -> str | None:
    """Best-effort pull of a string field even from broken JSON."""
    # Properly escaped JSON string
    pat = rf'"{re.escape(field)}"\s*:\s*"((?:\\.|[^"\\])*)"'
    m = re.search(pat, text)
    if m:
        try:
            return json.loads(f'"{m.group(1)}"')
        except json.JSONDecodeError:
            return m.group(1).replace("\\n", "\n").replace('\\"', '"')
    # Unescaped multiline (stop at next ,"key" or }
    pat2 = rf'"{re.escape(field)}"\s*:\s*"(.*?)"\s*[,}}\n]'
    m2 = re.search(pat2, text, re.DOTALL)
    if m2:
        return m2.group(1).strip()
    return None


def _soft_envelope(message: str, *, note: str) -> dict[str, Any]:
    return {
        "assistant_message": (message or "（模型回复无法解析为 JSON，请再说一遍或换个说法。）")[:8000],
        "choices": [],
        "mode": "chat",
        "intent_hint": "none",
        "artifact": None,
        "ready_to_export": False,
        "gaps": [],
        "notes_for_host": note,
    }


def parse_llm_json_object(
    text: str,
    *,
    soft_prose_fallback: bool = False,
) -> dict[str, Any]:
    """Parse a JSON object from LLM output. Raises LlmJsonError on failure."""
    if text is None or not str(text).strip():
        raise LlmJsonError("Empty LLM response")

    cleaned = _strip_fence_wrappers(_strip_bom(str(text)))
    candidates: list[str] = [cleaned]

    balanced = _extract_balanced_object(cleaned)
    if balanced:
        candidates.insert(0, balanced)

    # Prefer last balanced object when model prepends prose then JSON
    last_start = cleaned.rfind("\n{")
    if last_start >= 0:
        bal2 = _extract_balanced_object(cleaned[last_start + 1 :])
        if bal2:
            candidates.insert(0, bal2)

    seen: set[str] = set()
    errors: list[str] = []
    for cand in candidates:
        key = cand[:200]
        if key in seen:
            continue
        seen.add(key)
        parsed = _try_load(cand)
        if parsed is not None:
            return parsed
        try:
            json.loads(cand)
        except json.JSONDecodeError as exc:
            errors.append(str(exc))

    if soft_prose_fallback:
        recovered = _extract_field_string(cleaned, "assistant_message")
        if recovered:
            env = _soft_envelope(recovered, note="recovered_assistant_message_only")
            # Best-effort also pull draft pieces if present as nested blobs later
            return env
        prose = cleaned.strip()
        if prose and not prose.lstrip().startswith("{"):
            return _soft_envelope(prose, note="recovered_from_non_json")
        # Broken JSON starting with { — still return something chat-usable
        snippet = re.sub(r"\s+", " ", cleaned)[:500]
        return _soft_envelope(
            f"上一轮模型输出的 JSON 不完整，我没能更新草稿。请再发一句，或说「再整理一遍」。\n\n（原始片段：{snippet}…）",
            note="recovered_from_broken_json",
        )

    detail = errors[0] if errors else "unknown"
    raise LlmJsonError(f"Could not parse LLM JSON: {detail}\nRaw: {cleaned[:500]}")


def try_parse_llm_json_object(
    text: str,
    *,
    soft_prose_fallback: bool = False,
) -> dict[str, Any] | None:
    try:
        return parse_llm_json_object(text, soft_prose_fallback=soft_prose_fallback)
    except LlmJsonError:
        return None
