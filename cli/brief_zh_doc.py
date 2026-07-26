"""Chinese companion document for an English pipeline brief.

``brief.json`` stays English for pipeline; ``brief.zh.md`` is human-readable Chinese
written next to it on export (and listed in the Docs panel).
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

BRIEF_ZH_DOC_NAME = "brief.zh.md"


def brief_zh_doc_path_for(brief_path: Path) -> Path:
    return brief_path.resolve().parent / BRIEF_ZH_DOC_NAME


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return str(value).strip()


def render_brief_zh_skeleton(brief: dict[str, Any]) -> str:
    """Deterministic Chinese-labeled mirror of the brief (no LLM).

    Narrative fields may still be English; section titles are Chinese so the Docs
    panel is readable even when translation is unavailable.
    """
    project = _as_dict(brief.get("project"))
    assets = _as_list(brief.get("assets"))
    graphs = _as_list(brief.get("animation_graphs"))
    meta = _as_dict(brief.get("brief_meta"))
    title = _text(project.get("title")) or "未命名项目"

    lines: list[str] = [
        f"# {title}（中文说明）",
        "",
        "> 本文档与同目录 `brief.json` 对应，供人阅读；流水线只读英文 brief。",
        "",
    ]
    if meta.get("frozen_at"):
        lines.extend([f"- 冻结时间：`{meta.get('frozen_at')}`", f"- 来源：`{meta.get('source') or '—'}`", ""])

    lines.extend(
        [
            "## 项目概览",
            "",
            f"- **标题**：{title}",
            f"- **类型 / 维度**：`{_text(project.get('genre')) or '—'}` / `{_text(project.get('dimension')) or '—'}`",
            f"- **视角**：`{_text(project.get('view')) or '—'}`",
            f"- **玩家资产**：`{_text(project.get('player_asset')) or '—'}`",
            "",
            "### 简介",
            "",
            _text(project.get("description")) or "（无）",
            "",
            "### 玩法循环",
            "",
            _text(project.get("gameplay_loop")) or "（无）",
            "",
            "### 本局目标",
            "",
            _text(project.get("session_goal")) or "（无）",
            "",
            "### 美术方向",
            "",
            _text(project.get("art_direction")) or "（无）",
            "",
        ]
    )

    controls = project.get("controls")
    if isinstance(controls, dict) and controls:
        lines.extend(["### 操作", ""])
        for action, keys in controls.items():
            key_s = ", ".join(str(k) for k in keys) if isinstance(keys, list) else _text(keys)
            lines.append(f"- `{action}`：{key_s}")
        lines.append("")

    viewport = _as_dict(project.get("viewport"))
    if viewport:
        lines.extend(
            [
                "### 视口",
                "",
                f"- 宽高：{viewport.get('width', '?')} × {viewport.get('height', '?')}",
                "",
            ]
        )

    lines.extend(["## 资产列表", ""])
    if not assets:
        lines.extend(["（无资产）", ""])
    else:
        lines.extend(
            [
                "| ID | 类型 | 用途 | 说明 |",
                "|----|------|------|------|",
            ]
        )
        for raw in assets:
            a = _as_dict(raw)
            aid = _text(a.get("id") or a.get("name")) or "—"
            atype = _text(a.get("type")) or "—"
            usage = _text(a.get("usage")) or "—"
            desc = _text(a.get("usage_description") or a.get("description")).replace("|", "\\|") or "—"
            lines.append(f"| `{aid}` | {atype} | {usage} | {desc} |")
        lines.append("")

    if graphs:
        lines.extend(["## 动画图", ""])
        for g in graphs:
            gd = _as_dict(g)
            lines.append(f"- `{_text(gd.get('character') or gd.get('id') or 'graph')}`")
        lines.append("")

    lines.extend(
        [
            "---",
            "",
            "_若段落仍为英文，说明本次导出未完成翻译或翻译失败，可重新导出 Brief 再试。_",
            "",
        ]
    )
    return "\n".join(lines)


_TRANSLATE_SYSTEM = """你是游戏制作文档助手。用户会给你一份英文 Game AI Foundry brief JSON。
请输出一份**完整中文 Markdown**说明文档，要求：
1. 标题用中文（可保留英文原名作副标题）。
2. 用中文写：简介、玩法循环、本局目标、美术方向、操作说明、资产用途说明。
3. 资产 id / name、usage 枚举、路径、技术字段保留英文，用反引号包裹。
4. 结构清晰，便于在 GUI「文档」面板阅读；不要输出 JSON；不要用代码围栏包住整篇文档。
5. 文首用一两句说明：本文对应 brief.json，流水线仍以英文 brief 为准。
"""


def _strip_md_fence(text: str) -> str:
    raw = (text or "").strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:markdown|md)?\s*\n", "", raw, count=1, flags=re.I)
        raw = re.sub(r"\n```\s*$", "", raw)
    return raw.strip()


def translate_brief_to_zh_markdown(
    brief: dict[str, Any],
    *,
    config: dict[str, Any] | None = None,
) -> tuple[str, str]:
    """Return (markdown, mode) where mode is ``llm`` or ``skeleton``."""
    skeleton = render_brief_zh_skeleton(brief)
    try:
        from llm_config import resolve_host_api_settings
        from prompt_craft import PromptCraftError, chat_text_completion
    except ImportError:
        return skeleton, "skeleton"

    api = resolve_host_api_settings(config or {})
    if not api.get("api_key"):
        return skeleton, "skeleton"

    user = (
        "请把下面的 brief 写成中文说明文档（Markdown）：\n\n"
        + json.dumps(brief, ensure_ascii=False, indent=2)[:120_000]
    )
    try:
        raw = chat_text_completion(
            model=str(api["model"]),
            messages=[
                {"role": "system", "content": _TRANSLATE_SYSTEM},
                {"role": "user", "content": user},
            ],
            api_key=str(api["api_key"]),
            api_base=str(api["api_base"]),
            proxy=api.get("proxy"),
            timeout=120,
        )
    except PromptCraftError:
        return skeleton, "skeleton"
    except Exception:
        return skeleton, "skeleton"

    md = _strip_md_fence(raw)
    if len(md) < 80 or "#" not in md:
        return skeleton, "skeleton"
    return md, "llm"


def write_brief_zh_document(
    brief_path: Path,
    brief: dict[str, Any] | None = None,
    *,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Write ``brief.zh.md`` beside ``brief.json``. Returns paths + mode."""
    path = Path(brief_path)
    data = brief if isinstance(brief, dict) else json.loads(path.read_text(encoding="utf-8"))
    md, mode = translate_brief_to_zh_markdown(data, config=config)
    out = brief_zh_doc_path_for(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(md.rstrip() + "\n", encoding="utf-8")
    return {
        "zh_doc_path": str(out.resolve()),
        "zh_doc_name": BRIEF_ZH_DOC_NAME,
        "zh_doc_mode": mode,
    }
