"""Generate ASCII/table ui-wireframe.md from optional project.ui_panels."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from brief import normalize_ui_panels
from brief_shards import BRIEF_DRAFT_NAME, load_brief_dict_from_path
from llm_config import resolve_host_api_settings
from project_paths import default_paths_for_brief, repo_root
from prompt_craft import PromptCraftError, chat_text_completion

_REPO_ROOT = repo_root()
_UI_WIREFRAME_SKILL = (
    _REPO_ROOT / "resources" / "skills" / "orchestrator" / "ui-wireframe.md"
)
UI_WIREFRAME_DOC_NAME = "ui-wireframe.md"

_WIREFRAME_SYSTEM_FALLBACK = (
    "你是游戏 UI 线稿助手。根据 project.ui_panels 与 brief 上下文，"
    "输出 Markdown：用 ASCII 框图与表格描述各面板大致区位与主要区块（有什么、在哪）。"
    "不要生图、不要 JSON。输出必须是 Markdown。"
)


class UiWireframeError(RuntimeError):
    """Raised when ui-wireframe generation cannot proceed."""


def ui_wireframe_path_for(project_dir: Path) -> Path:
    """Path to ui-wireframe.md beside brief.json / brief.draft.json."""
    return Path(project_dir).resolve() / UI_WIREFRAME_DOC_NAME


def _load_skill(path: Path, fallback: str) -> str:
    if path.is_file():
        return path.read_text(encoding="utf-8")
    return fallback


def _strip_md_fence(raw: str) -> str:
    text = (raw or "").strip()
    m = re.match(r"^```(?:markdown|md)?\s*([\s\S]*?)```\s*$", text, re.I)
    if m:
        return m.group(1).strip()
    return text


def _draft_from_input(draft_or_session: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(draft_or_session, dict):
        raise UiWireframeError("invalid draft_or_session")
    if "draft_brief" in draft_or_session:
        draft = draft_or_session.get("draft_brief")
    elif draft_or_session.get("project") or draft_or_session.get("assets"):
        draft = draft_or_session
    else:
        raise UiWireframeError("no draft_brief or brief body in input")
    if not isinstance(draft, dict) or not draft:
        raise UiWireframeError("draft is empty")
    return draft


def ui_panels_from_draft(draft: dict[str, Any]) -> list[dict[str, Any]]:
    project = draft.get("project") if isinstance(draft.get("project"), dict) else {}
    return normalize_ui_panels(project.get("ui_panels"))


def _assert_safe_output_path(out_path: Path, project_dir: Path, *, root: Path) -> None:
    base = Path(project_dir).resolve()
    out = Path(out_path).resolve()
    if out.name != UI_WIREFRAME_DOC_NAME:
        raise UiWireframeError("invalid wireframe output filename")
    if out.parent != base:
        raise UiWireframeError("wireframe path must stay beside brief")
    anchor = base / "brief.json"
    paths = default_paths_for_brief(anchor, root=root)
    proj_root = paths.get("project_root")
    if proj_root is not None:
        if not out.is_relative_to(Path(proj_root).resolve()):
            raise UiWireframeError("wireframe path escapes project root")


def load_brief_for_wireframe(brief_path: Path, *, prefer_draft: bool = False) -> dict[str, Any]:
    p = Path(brief_path)
    if prefer_draft:
        if p.name.lower() == BRIEF_DRAFT_NAME.lower() and p.is_file():
            data = json.loads(p.read_text(encoding="utf-8"))
        else:
            draft = p.parent / BRIEF_DRAFT_NAME if p.is_file() else p / BRIEF_DRAFT_NAME
            if not draft.is_file():
                raise FileNotFoundError(f"No {BRIEF_DRAFT_NAME} at {draft}")
            data = json.loads(draft.read_text(encoding="utf-8"))
        if not isinstance(data, dict) or not (data.get("project") or data.get("assets")):
            raise ValueError(f"Invalid draft at {p}")
        return data
    return load_brief_dict_from_path(p)


def _wireframe_user_payload(draft: dict[str, Any], panels: list[dict[str, Any]]) -> str:
    project = draft.get("project") if isinstance(draft.get("project"), dict) else {}
    payload: dict[str, Any] = {
        "project_title": str(project.get("title") or "").strip(),
        "genre": str(project.get("genre") or "").strip(),
        "ui_panels": panels,
    }
    hud = project.get("hud")
    if isinstance(hud, list) and hud:
        payload["hud"] = hud[:20]
    return json.dumps(payload, ensure_ascii=False, indent=2)


def generate_ui_wireframe_markdown(
    draft: dict[str, Any],
    panels: list[dict[str, Any]],
    *,
    config: dict[str, Any] | None = None,
) -> str:
    cfg = config or {}
    api = resolve_host_api_settings(cfg)
    if not api.get("api_key"):
        raise UiWireframeError("UI wireframe unavailable: configure API key (OpenRouter/host).")

    system = _load_skill(_UI_WIREFRAME_SKILL, _WIREFRAME_SYSTEM_FALLBACK)
    user = (
        "根据以下 ui_panels 与上下文，写出 ui-wireframe.md 正文（Markdown）。"
        "每个面板至少一段 ASCII 或表格示意。\n\n"
        + _wireframe_user_payload(draft, panels)
    )
    try:
        raw = chat_text_completion(
            model=str(api["model"]),
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            api_key=str(api["api_key"]),
            api_base=str(api["api_base"]),
            proxy=api.get("proxy"),
            timeout=120,
        )
    except PromptCraftError as exc:
        raise UiWireframeError(str(exc)) from exc

    md = _strip_md_fence(raw or "")
    if len(md) < 40 or "#" not in md:
        raise UiWireframeError("LLM wireframe output too short or not Markdown")
    if md.lstrip().startswith("{") and '"ui_panels"' in md[:300]:
        raise UiWireframeError("LLM returned JSON instead of Markdown wireframe")
    return md.rstrip() + "\n"


def generate_ui_wireframe(
    draft_or_session: dict[str, Any],
    project_dir: Path,
    *,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Write ui-wireframe.md beside brief. Returns ok/path/panel_count or error."""
    root = _REPO_ROOT
    try:
        draft = _draft_from_input(draft_or_session)
        panels = ui_panels_from_draft(draft)
        if not panels:
            return {
                "ok": False,
                "panel_count": 0,
                "error": "project.ui_panels is empty or missing — chat about UI panels first",
            }

        base = Path(project_dir).resolve()
        out_path = ui_wireframe_path_for(base)
        _assert_safe_output_path(out_path, base, root=root)

        md = generate_ui_wireframe_markdown(draft, panels, config=config)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(md, encoding="utf-8")
        return {
            "ok": True,
            "path": str(out_path.resolve()),
            "panel_count": len(panels),
        }
    except UiWireframeError as exc:
        return {"ok": False, "panel_count": 0, "error": str(exc)}


def project_dir_for_brief_path(brief_path: Path) -> Path:
    p = Path(brief_path)
    if p.is_file():
        return p.parent.resolve()
    if p.is_dir():
        return p.resolve()
    return p.parent.resolve()
