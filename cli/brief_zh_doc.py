"""Chinese companion document for an English pipeline brief.

``brief.json`` stays English for the pipeline. ``brief.zh.md`` is the human-readable
Chinese mirror — written from the **working draft before export** (so you can decide
whether to freeze), and refreshed again on export.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

BRIEF_ZH_DOC_NAME = "brief.zh.md"
BRIEF_DRAFT_NAME = "brief.draft.json"


def brief_zh_doc_path_for(brief_path: Path) -> Path:
    return Path(brief_path).resolve().parent / BRIEF_ZH_DOC_NAME


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


def load_brief_dict_from_path(path: Path) -> dict[str, Any]:
    """Load brief.json, or fall back to brief.draft.json beside it / as path."""
    p = Path(path)
    candidates: list[Path] = []
    if p.is_file():
        candidates.append(p)
        if p.name.lower() == "brief.json":
            candidates.append(p.parent / BRIEF_DRAFT_NAME)
    elif p.is_dir():
        candidates.extend([p / "brief.json", p / BRIEF_DRAFT_NAME])
    else:
        # Missing brief.json — still try draft beside the intended path
        candidates.append(p)
        candidates.append(p.parent / BRIEF_DRAFT_NAME)
        if p.name.lower() != BRIEF_DRAFT_NAME.lower():
            candidates.append(p.parent / "brief.json")
    for c in candidates:
        if not c.is_file():
            continue
        data = json.loads(c.read_text(encoding="utf-8"))
        if isinstance(data, dict) and (data.get("project") or data.get("assets")):
            return data
    raise FileNotFoundError(f"No brief or draft at {path}")


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
        "> 供人阅读、**导出前**确认玩法与资产是否够用。流水线只读英文 `brief.json`；",
        "> 未导出时本文档对应工作草稿 `brief.draft.json`。",
        "",
    ]
    if meta.get("frozen_at"):
        lines.extend(
            [f"- 冻结时间：`{meta.get('frozen_at')}`", f"- 来源：`{meta.get('source') or '—'}`", ""]
        )
    else:
        lines.extend(["- 状态：**工作草稿**（尚未导出冻结）", ""])

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
            lines.append(
                f"- `{_text(gd.get('id') or gd.get('name')) or 'graph'}`："
                f"{_text(gd.get('description')) or '—'}"
            )
        lines.append("")

    lines.extend(
        [
            "---",
            "",
            "看完若玩法/资产仍含糊：先在策划里补全或自动修，**确认后再导出** Brief。",
            "",
        ]
    )
    return "\n".join(lines)


_TRANSLATE_SYSTEM = (
    "你是游戏策划文档助手。把英文 brief JSON 写成清晰的中文 Markdown 说明，"
    "保留资产 id / 技术字段英文原样，玩法与描述用中文。"
    "不要编造 brief 里没有的系统。标题用中文。"
)


def _strip_md_fence(raw: str) -> str:
    text = (raw or "").strip()
    m = re.match(r"^```(?:markdown|md)?\s*([\s\S]*?)```\s*$", text, re.I)
    if m:
        return m.group(1).strip()
    return text


def translate_brief_to_zh_markdown(
    brief: dict[str, Any],
    *,
    config: dict[str, Any] | None = None,
    use_llm: bool = True,
) -> tuple[str, str]:
    """Return (markdown, mode) where mode is ``llm`` or ``skeleton``."""
    skeleton = render_brief_zh_skeleton(brief)
    if not use_llm:
        return skeleton, "skeleton"
    try:
        from llm_config import resolve_host_api_settings
        from prompt_craft import PromptCraftError, chat_text_completion
    except ImportError:
        return skeleton, "skeleton"

    api = resolve_host_api_settings(config or {})
    if not api.get("api_key"):
        return skeleton, "skeleton"

    user = (
        "请把下面的 brief 写成中文说明文档（Markdown），供导出前审阅：\n\n"
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
    use_llm: bool = True,
    persist_draft: bool = False,
) -> dict[str, Any]:
    """Write ``brief.zh.md`` beside the brief/draft path. Returns paths + mode."""
    path = Path(brief_path)
    data = brief if isinstance(brief, dict) else load_brief_dict_from_path(path)
    if persist_draft and isinstance(data, dict):
        draft_path = path.parent / BRIEF_DRAFT_NAME
        draft_path.parent.mkdir(parents=True, exist_ok=True)
        draft_path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    md, mode = translate_brief_to_zh_markdown(data, config=config, use_llm=use_llm)
    out = brief_zh_doc_path_for(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(md.rstrip() + "\n", encoding="utf-8")
    return {
        "zh_doc_path": str(out.resolve()),
        "zh_doc_name": BRIEF_ZH_DOC_NAME,
        "zh_doc_mode": mode,
    }
