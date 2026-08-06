"""Brief Tab host-chat — progressive draft while chatting; freeze on 落实/export.

Sessions live at plans/conversations/brief/<session_id>.json.
Context: summary + recent messages; compress when over character budget.
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from collections.abc import Callable
from typing import Any

from brief import (
    AssetSpec,
    AssetType,
    ProjectContext,
    animation_graph_to_dict,
    apply_deterministic_brief_fixes,
    audit_brief_for_export,
    character_clip_names,
    characters_requiring_animation_graph,
    finalize_brief_export,
    parse_animation_graphs,
    parse_assets_for_audit,
    validate_brief_for_export,
)
from external_projects import get_external_by_id, is_external_brief_key, parse_external_brief_key
from llm_config import resolve_host_api_settings
from llm_json import LlmJsonError, parse_llm_json_object
from project_paths import paths_for_brief_key
from prompt_craft import PromptCraftError, chat_text_completion
from makeability_decisions import (
    MAX_AUTO_REPAIR_ATTEMPTS,
    apply_whole_card_verifier_results,
    assert_critic_decision_checks_protocol,
    canonicalize_decision_checks,
    complete_critic_ledger_checks,
    decisions_for_verifier,
    decision_key_alias_map_from_gaps,
    decision_key_alias_map_from_checks,
    enrich_intent_gaps,
    ensure_decision_ledger,
    filter_intent_gaps_for_display,
    gap_id_map_from_specs,
    invalidate_verified_ledger_for_patches,
    ledger_blocks_export,
    ledger_for_prompt,
    mark_keys_repair_failed,
    merge_critic_decision_checks,
    merge_decision_key_alias_maps,
    normalize_decision_checks,
    normalize_occurrences,
    normalize_write_paths,
    detail_gap_stable_key,
    ensure_detail_gaps_shown_list,
    partition_detail_gaps_for_display,
    record_gap_answers,
    reconcile_intent_gaps_with_ledger,
    remove_verified_gaps_from_review,
    repair_answers_from_ledger,
    repair_failed_gaps_for_display,
    required_paths_by_key_from_gaps,
    resolve_gaps_for_answers,
    suppress_intent_gaps_by_ledger,
    update_ledger_status,
    validate_occurrences_strict,
    verifier_path_failure_detail,
    verifier_reported_all_keys,
)
from shared_context import asset_to_dict, project_to_dict

_REPO_ROOT = Path(__file__).resolve().parent.parent
_HOST_CHAT_SKILL = _REPO_ROOT / "resources" / "skills" / "orchestrator" / "host-chat.md"
_COMMIT_BRIEF_SKILL = _REPO_ROOT / "resources" / "skills" / "orchestrator" / "commit-brief.md"
_MAKEABILITY_CRITIC_SKILL = (
    _REPO_ROOT / "resources" / "skills" / "orchestrator" / "makeability-critic.md"
)
_BRIEF_ENRICH_SKILL = _REPO_ROOT / "resources" / "skills" / "orchestrator" / "brief-enrich.md"
MAKEABILITY_SCHEMA_VERSION = 2
_ANIM_GRAPH_SKILL = (
    _REPO_ROOT / "resources" / "skills" / "orchestrator" / "brief-animation-graphs.md"
)
_EXAMPLE_BRIEF = _REPO_ROOT / "resources" / "asset-brief.example.json"
_CONV_DIR = _REPO_ROOT / "plans" / "conversations" / "brief"

# Context budget (characters of conversation payload, not tokens).
# Day-long brief chats need more headroom; older turns still compress to summary.
_CHAR_BUDGET = 48_000
_RECENT_KEEP = 40

_COMMIT_BRIEF_RE = re.compile(
    r"(落实\s*(成)?\s*brief|写成\s*brief|导出\s*brief|定稿|生成\s*brief|"
    r"可以开项目|按这个开项目|开始做这个游戏|freeze\s*brief|commit\s*brief)",
    re.IGNORECASE,
)
_COMMIT_DOC_RE = re.compile(
    r"(整理成.{0,12}(文档|markdown|md|设计说明|方案书|纪要)|"
    r"写成.{0,12}(文档|markdown|md|设计说明)|"
    r"输出.{0,8}(文档|说明|纪要)|"
    r"commit\s*doc|save\s*(as\s*)?(doc|markdown))",
    re.IGNORECASE,
)
_COMMIT_DOC_SKILL = _REPO_ROOT / "resources" / "skills" / "orchestrator" / "commit-doc.md"


class HostChatError(RuntimeError):
    """Raised when host-chat session or LLM step fails."""


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def conversations_dir() -> Path:
    return _CONV_DIR


def sanitize_session_id(raw: str) -> str:
    s = (raw or "").strip()
    if not s:
        raise HostChatError("session_id is required.")
    cleaned = re.sub(r"[^a-zA-Z0-9._-]+", "-", s).strip("-")
    if not cleaned or cleaned in {".", ".."}:
        raise HostChatError(f"Invalid session_id: {raw!r}")
    return cleaned[:80]


def session_path_for_id(session_id: str, *, base_dir: Path | None = None) -> Path:
    sid = sanitize_session_id(session_id)
    root = base_dir or _CONV_DIR
    return root / f"{sid}.json"


def new_session(session_id: str | None = None) -> dict[str, Any]:
    sid = sanitize_session_id(session_id) if session_id else uuid.uuid4().hex[:12]
    now = _utc_now()
    return {
        "id": sid,
        "role": "brief",
        "created_at": now,
        "updated_at": now,
        "messages": [],
        "last_choices": [],
        "mode": "chat",
        "pending_mode": None,
        "intent_hint": "none",
        "summary": "",
        "draft_brief": None,
        "draft_document": None,
        "ready_to_export": False,
        "gaps": [],
        "compressed_count": 0,
        "bound_brief_rel": None,
        "project_slug": None,
    }


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _slug_from_brief_rel(brief_rel: str, *, workspace: Path | None = None) -> str:
    n = brief_rel.replace("\\", "/").lstrip("./")
    if is_external_brief_key(n):
        ext_id = parse_external_brief_key(n)
        if ext_id:
            ws = (workspace or _repo_root()).resolve()
            entry = get_external_by_id(ws, ext_id)
            if entry:
                name = str(entry.get("display_name") or "").strip()
                if name:
                    return name
                return ext_id
        return ext_id or "game"
    m = re.match(r"^projects/([^/]+)/", n, re.I)
    if m:
        return m.group(1)
    stem = Path(n).stem.replace("-brief", "")
    return stem or "game"


def _brief_candidates_for_rel(
    brief_rel: str,
    *,
    repo_root: Path | None = None,
    workspace: Path | None = None,
) -> list[Path]:
    """Prefer working draft over frozen export so bind/sync cannot clobber chat edits."""
    root = (repo_root or _repo_root()).resolve()
    ws = (workspace or root).resolve()
    rel = brief_rel.replace("\\", "/").lstrip("./")
    if is_external_brief_key(rel):
        paths = paths_for_brief_key(rel, ws)
        brief_abs = Path(paths["brief"]).resolve()
        return [brief_abs.parent / "brief.draft.json", brief_abs]
    parent = (root / rel).parent
    return [parent / "brief.draft.json", root / rel]


def load_project_draft_from_disk(
    brief_rel: str,
    *,
    repo_root: Path | None = None,
    workspace: Path | None = None,
) -> dict[str, Any] | None:
    """Load working draft; prefer brief.draft.json, fall back to exported brief.json."""
    try:
        candidates = _brief_candidates_for_rel(
            brief_rel,
            repo_root=repo_root,
            workspace=workspace,
        )
    except ValueError:
        return None
    for candidate in candidates:
        if not candidate.is_file():
            continue
        try:
            data = json.loads(candidate.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(data, dict):
            continue
        if not (data.get("project") or data.get("assets")):
            continue
        out = {k: copy.deepcopy(v) for k, v in data.items() if k != "brief_meta"}
        return out
    return None


def resolve_bound_brief_output_path(
    session: dict[str, Any],
    *,
    repo_root: Path | None = None,
    workspace: Path | None = None,
) -> Path | None:
    """Absolute brief.json path for bound project (external or repo-relative)."""
    bound = str(session.get("bound_brief_rel") or "").strip()
    if not bound:
        return None
    root = (repo_root or _repo_root()).resolve()
    ws = (workspace or root).resolve()
    rel = bound.replace("\\", "/").lstrip("./")
    if is_external_brief_key(rel):
        try:
            paths = paths_for_brief_key(rel, ws)
        except ValueError:
            return None
        return Path(paths["brief"]).resolve()
    return (root / rel).resolve()


def _draft_richness(draft: dict[str, Any] | None) -> tuple[int, int, int, int]:
    """Cheap size signal: assets / scenes / systems / serialized length."""
    if not isinstance(draft, dict) or not draft:
        return (0, 0, 0, 0)
    assets = draft.get("assets") if isinstance(draft.get("assets"), list) else []
    project = draft.get("project") if isinstance(draft.get("project"), dict) else {}
    scenes = project.get("scenes") if isinstance(project.get("scenes"), list) else []
    systems = project.get("systems") if isinstance(project.get("systems"), list) else []
    try:
        nbytes = len(json.dumps(draft, ensure_ascii=False, separators=(",", ":")))
    except (TypeError, ValueError):
        nbytes = 0
    return (len(assets), len(scenes), len(systems), nbytes)


def _remember_disk_draft(
    session: dict[str, Any],
    draft: dict[str, Any],
    *,
    draft_path: Path | None = None,
) -> None:
    """Record fingerprint/mtime so later turns can detect external disk changes."""
    session["draft_disk_fingerprint"] = draft_fingerprint(draft)
    if draft_path is not None:
        try:
            session["draft_disk_mtime_ns"] = draft_path.stat().st_mtime_ns
        except OSError:
            session.pop("draft_disk_mtime_ns", None)
    else:
        session.pop("draft_disk_mtime_ns", None)


def _should_flush_session_draft_to_disk(
    session: dict[str, Any],
    flush_rel: str,
    *,
    repo_root: Path | None = None,
    workspace: Path | None = None,
) -> bool:
    """False when disk was updated externally (e.g. git pull) and is ahead of session."""
    draft = session.get("draft_brief")
    if not isinstance(draft, dict) or not draft:
        return False
    disk = load_project_draft_from_disk(
        flush_rel, repo_root=repo_root, workspace=workspace
    )
    if not disk:
        return True
    disk_fp = draft_fingerprint(disk)
    session_fp = draft_fingerprint(draft)
    tracked = str(session.get("draft_disk_fingerprint") or "").strip()
    if tracked and disk_fp != tracked:
        # Disk changed since we last loaded/persisted — never clobber it with stale session.
        return False
    if not tracked:
        disk_rich = _draft_richness(disk)
        session_rich = _draft_richness(draft)
        if disk_rich > session_rich:
            # Legacy sessions without fingerprint: prefer the richer on-disk draft.
            return False
        if disk_fp != session_fp and session_rich <= disk_rich:
            # Ambiguous divergent disk — do not flush without a tracked fingerprint.
            return False
    return True


def persist_project_draft(
    session: dict[str, Any],
    *,
    repo_root: Path | None = None,
    workspace: Path | None = None,
) -> Path | None:
    """Write session draft_brief to projects/…/brief.draft.json (or external root).

    Compare-and-swap: refuse to overwrite when disk changed since last load/persist
    and no longer matches the session's tracked fingerprint (LLM-window race).
    """
    draft = session.get("draft_brief")
    if not isinstance(draft, dict) or not draft:
        return None
    if not (draft.get("project") or draft.get("assets")):
        return None
    brief_path = resolve_bound_brief_output_path(
        session, repo_root=repo_root, workspace=workspace
    )
    if brief_path is None:
        return None
    draft_path = brief_path.parent / "brief.draft.json"
    tracked = str(session.get("draft_disk_fingerprint") or "").strip()
    if draft_path.is_file():
        try:
            disk_raw = json.loads(draft_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            disk_raw = None
        if isinstance(disk_raw, dict) and disk_raw:
            disk_fp = draft_fingerprint(disk_raw)
            session_fp = draft_fingerprint(draft)
            if tracked and disk_fp != tracked and session_fp != disk_fp:
                raise HostChatError(
                    "brief.draft.json 在持久化前已被外部修改，且与会话草稿不一致；"
                    "已拒绝覆盖。请先同步磁盘或对齐后再保存。"
                )
            if tracked and disk_fp != tracked and session_fp == tracked:
                # Session still at last-known disk; disk moved under us — refuse clobber.
                raise HostChatError(
                    "brief.draft.json 在 LLM/编辑期间已被外部修改；已拒绝用过期会话覆盖。"
                )
            if not tracked and disk_fp != session_fp:
                # Legacy: allow only when session is strictly richer (attach flush).
                if _draft_richness(draft) <= _draft_richness(disk_raw):
                    raise HostChatError(
                        "brief.draft.json 已存在且与会话草稿不同，且会话无磁盘指纹；"
                        "已拒绝覆盖。请先加载绑定草稿后再保存。"
                    )
    try:
        draft_path.parent.mkdir(parents=True, exist_ok=True)
        out = {k: copy.deepcopy(v) for k, v in draft.items() if k != "brief_meta"}
        draft_path.write_text(
            json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    except OSError:
        return None
    _remember_disk_draft(session, out, draft_path=draft_path)
    # Keep Chinese companion in sync with the machine draft (no LLM on every save).
    try:
        from brief_zh_doc import write_brief_zh_document

        write_brief_zh_document(brief_path, out, config={}, use_llm=False)
    except Exception:
        pass
    return draft_path


def sync_session_draft_from_disk(
    session: dict[str, Any],
    *,
    repo_root: Path | None = None,
    workspace: Path | None = None,
    force: bool = False,
) -> bool:
    """Reload bound project draft when disk changed (git pull / external edit).

    Cost is a local JSON read (skipped when mtime matches). Negligible vs an LLM turn.
    Returns True when session.draft_brief was replaced from disk.
    """
    rel = _norm_brief_rel(session.get("bound_brief_rel"))
    if not rel:
        return False
    root = (repo_root or _repo_root()).resolve()
    ws = (workspace or root).resolve()
    brief_path = resolve_bound_brief_output_path(
        session, repo_root=root, workspace=ws
    )
    draft_path = brief_path.parent / "brief.draft.json" if brief_path is not None else None
    if draft_path is not None and draft_path.is_file() and not force:
        try:
            mtime = draft_path.stat().st_mtime_ns
        except OSError:
            mtime = None
        if (
            mtime is not None
            and session.get("draft_disk_mtime_ns") == mtime
            and str(session.get("draft_disk_fingerprint") or "").strip()
            and isinstance(session.get("draft_brief"), dict)
            and session["draft_brief"]
        ):
            return False
    disk = load_project_draft_from_disk(rel, repo_root=root, workspace=ws)
    if not disk:
        return False
    fp = draft_fingerprint(disk)
    tracked = str(session.get("draft_disk_fingerprint") or "").strip()
    has_session_draft = (
        isinstance(session.get("draft_brief"), dict) and bool(session["draft_brief"])
    )
    if not force and tracked and tracked == fp and has_session_draft:
        if draft_path is not None and draft_path.is_file():
            try:
                session["draft_disk_mtime_ns"] = draft_path.stat().st_mtime_ns
            except OSError:
                pass
        return False

    session_fp = draft_fingerprint(session["draft_brief"]) if has_session_draft else ""
    if (
        not force
        and tracked
        and fp != tracked
        and has_session_draft
        and session_fp
        and session_fp != tracked
        and session_fp != fp
    ):
        raise HostChatError(
            "绑定的 brief.draft.json 与会话 draft 均已变更且不一致，"
            "请先对齐后再继续（或使用 force 从磁盘覆盖）。"
        )

    take_disk = False
    if force:
        take_disk = True
    elif tracked and tracked != fp:
        # Disk changed since last load/persist (git pull / external edit).
        take_disk = True
    elif not has_session_draft:
        take_disk = True
    elif not tracked and _draft_richness(disk) > _draft_richness(session.get("draft_brief")):
        # Legacy session: prefer richer on-disk draft after pull.
        take_disk = True

    if take_disk:
        session["draft_brief"] = disk
        _remember_disk_draft(session, disk, draft_path=draft_path)
        return True
    return False


def attach_bound_project(
    session: dict[str, Any],
    brief_rel: str | None,
    *,
    repo_root: Path | None = None,
    workspace: Path | None = None,
    hydrate_draft: bool = True,
) -> None:
    """Bind GUI project; sync draft ↔ disk (flush only when safe, then load)."""
    if not brief_rel or not str(brief_rel).strip():
        return
    root = (repo_root or _repo_root()).resolve()
    ws = (workspace or root).resolve()
    prev = _norm_brief_rel(session.get("bound_brief_rel"))
    rel = _norm_brief_rel(brief_rel)
    # Flush in-session draft before hydrate so GUI edits are not discarded —
    # but never overwrite a disk draft that changed externally (git pull).
    if (
        hydrate_draft
        and isinstance(session.get("draft_brief"), dict)
        and session["draft_brief"]
    ):
        flush_rel = prev or rel
        if flush_rel and _should_flush_session_draft_to_disk(
            session, flush_rel, repo_root=root, workspace=ws
        ):
            session["bound_brief_rel"] = flush_rel
            persist_project_draft(session, repo_root=root, workspace=ws)
    session["bound_brief_rel"] = rel
    session["project_slug"] = _slug_from_brief_rel(rel, workspace=ws)
    if not hydrate_draft:
        return
    disk = load_project_draft_from_disk(rel, repo_root=root, workspace=ws)
    if disk:
        session["draft_brief"] = disk
        brief_path = resolve_bound_brief_output_path(
            session, repo_root=root, workspace=ws
        )
        draft_path = (
            brief_path.parent / "brief.draft.json" if brief_path is not None else None
        )
        _remember_disk_draft(session, disk, draft_path=draft_path)
    else:
        # Bound to an empty project folder — don't keep another game's draft
        session["draft_brief"] = None
        session["draft_document"] = None
        session.pop("draft_disk_fingerprint", None)
        session.pop("draft_disk_mtime_ns", None)


def _norm_brief_rel(brief_rel: str | None) -> str:
    return str(brief_rel or "").replace("\\", "/").strip().lstrip("./")


def load_session(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise HostChatError(f"Session not found: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise HostChatError("Session file must be a JSON object.")
    return data


def save_session(
    path: Path,
    session: dict[str, Any],
    *,
    persist_draft: bool = True,
) -> None:
    """Persist session JSON. Draft CAS failures must not block session durability.

    Order: attempt draft sync (updates fingerprints in-memory), then always write
    the session file so decision_ledger answers survive disk conflicts (H1).
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    session["updated_at"] = _utc_now()
    if persist_draft:
        try:
            persist_project_draft(session)
            session.pop("last_draft_persist_error", None)
        except HostChatError as exc:
            # Session ledger / answers still must land on disk.
            session["last_draft_persist_error"] = str(exc)
    path.write_text(json.dumps(session, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def list_sessions(*, base_dir: Path | None = None) -> list[dict[str, Any]]:
    root = base_dir or _CONV_DIR
    if not root.is_dir():
        return []
    out: list[dict[str, Any]] = []
    for path in sorted(root.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        if not isinstance(data, dict):
            continue
        msgs = data.get("messages") or []
        title = ""
        draft = data.get("draft_brief") if isinstance(data.get("draft_brief"), dict) else {}
        project = draft.get("project") if isinstance(draft.get("project"), dict) else {}
        if project.get("title"):
            title = str(project["title"])[:36]
        else:
            for m in msgs:
                if isinstance(m, dict) and m.get("role") == "user":
                    title = str(m.get("content") or "")[:36]
                    break
        out.append(
            {
                "id": data.get("id") or path.stem,
                "path": str(path),
                "title": title or path.stem,
                "message_count": len(msgs) if isinstance(msgs, list) else 0,
                "ready_to_export": bool(data.get("ready_to_export")),
                "has_draft": bool(draft),
                "updated_at": data.get("updated_at") or "",
            }
        )
    return out


def _asset_merge_key(item: dict[str, Any]) -> str:
    for field in ("id", "name"):
        raw = str(item.get(field) or "").strip()
        if raw:
            return raw.lower()
    return ""


def _graph_merge_key(item: dict[str, Any]) -> str:
    for field in ("id", "character_asset", "name"):
        raw = str(item.get(field) or "").strip()
        if raw:
            return raw.lower()
    return ""


def _merge_dict_list_by_key(
    base_list: list[Any],
    incoming_list: list[Any],
    key_fn,
    *,
    preserve_nonempty_keys: frozenset[str] | None = None,
) -> list[Any]:
    """Upsert incoming items onto base by key; never drop base items missing from incoming.

    ``preserve_nonempty_keys``: empty-string incoming values do not clobber a non-empty
    base value (e.g. model clearing ``visual_reference`` after a visual-target pick).
    """
    protect = preserve_nonempty_keys or frozenset()
    out: list[Any] = [copy.deepcopy(x) for x in base_list]
    index: dict[str, int] = {}
    for i, item in enumerate(out):
        if not isinstance(item, dict):
            continue
        key = key_fn(item)
        if key and key not in index:
            index[key] = i
    for item in incoming_list:
        if not isinstance(item, dict):
            continue
        key = key_fn(item)
        if key and key in index:
            merged = copy.deepcopy(out[index[key]])
            for sk, sv in item.items():
                if sv is None:
                    continue
                if (
                    sk in protect
                    and isinstance(sv, str)
                    and not sv.strip()
                    and str(merged.get(sk) or "").strip()
                ):
                    continue
                if isinstance(sv, dict) and isinstance(merged.get(sk), dict):
                    nested = copy.deepcopy(merged[sk])
                    nested.update(sv)
                    merged[sk] = nested
                else:
                    merged[sk] = copy.deepcopy(sv)
            out[index[key]] = merged
        else:
            out.append(copy.deepcopy(item))
            if key:
                index[key] = len(out) - 1
    return out


def _project_list_item_key(item: dict[str, Any]) -> str:
    for field in ("id", "name", "title"):
        raw = str(item.get(field) or "").strip()
        if raw:
            return raw.lower()
    return ""


_PROJECT_LIST_MERGE_KEYS = frozenset({"scenes", "systems"})


_NARRATIVE_PROJECT_KEYS = frozenset(
    {
        "description",
        "gameplay_loop",
        "session_goal",
        "art_direction",
        "presentation_notes",
    }
)


def _prefer_richer_string(base: Any, incoming: Any) -> Any:
    """Keep established narrative if the model returns an empty or much thinner rewrite."""
    if not isinstance(incoming, str):
        return copy.deepcopy(incoming)
    if not isinstance(base, str):
        return incoming
    inc = incoming.strip()
    base_s = base.strip()
    if not inc and base_s:
        return base
    if (
        base_s
        and len(base_s) > 100
        and len(inc) < max(40, int(len(base_s) * 0.5))
    ):
        return base
    return incoming


def deep_merge_brief(
    base: dict[str, Any] | None,
    incoming: dict[str, Any] | None,
) -> dict[str, Any] | None:
    """Merge incoming draft onto base.

    - ``assets`` / ``animation_graphs``: upsert by id/name (never drop prior rows just
      because the model omitted them this turn).
    - ``project.scenes`` / ``project.systems``: same upsert-by-id behaviour.
    - Long narrative project strings: empty / much-shorter rewrites do not clobber base.
    """
    if not incoming:
        return copy.deepcopy(base) if isinstance(base, dict) else None
    if not isinstance(base, dict) or not base:
        return copy.deepcopy(incoming)

    out = copy.deepcopy(base)
    for key, value in incoming.items():
        if value is None:
            continue
        if key == "assets" and isinstance(value, list):
            base_assets = out.get("assets") if isinstance(out.get("assets"), list) else []
            out[key] = _merge_dict_list_by_key(base_assets, value, _asset_merge_key)
        elif key == "animation_graphs" and isinstance(value, list):
            base_graphs = (
                out.get("animation_graphs")
                if isinstance(out.get("animation_graphs"), list)
                else []
            )
            out[key] = _merge_dict_list_by_key(base_graphs, value, _graph_merge_key)
        elif isinstance(value, dict) and isinstance(out.get(key), dict):
            merged = copy.deepcopy(out[key])
            for sk, sv in value.items():
                if sv is None:
                    continue
                if isinstance(sv, dict) and isinstance(merged.get(sk), dict):
                    nested = copy.deepcopy(merged[sk])
                    nested.update(sv)
                    merged[sk] = nested
                elif (
                    key == "project"
                    and sk in _PROJECT_LIST_MERGE_KEYS
                    and isinstance(sv, list)
                ):
                    base_list = (
                        merged.get(sk) if isinstance(merged.get(sk), list) else []
                    )
                    merged[sk] = _merge_dict_list_by_key(
                        base_list,
                        sv,
                        _project_list_item_key,
                        preserve_nonempty_keys=(
                            frozenset({"visual_reference"})
                            if sk == "scenes"
                            else frozenset()
                        ),
                    )
                elif key == "project" and sk in _NARRATIVE_PROJECT_KEYS:
                    merged[sk] = _prefer_richer_string(merged.get(sk), sv)
                elif (
                    key == "project"
                    and sk == "visual_reference"
                    and isinstance(sv, str)
                    and not sv.strip()
                    and str(merged.get(sk) or "").strip()
                ):
                    # Keep picked global north-star; models often emit "".
                    continue
                else:
                    merged[sk] = copy.deepcopy(sv)
            out[key] = merged
        else:
            out[key] = copy.deepcopy(value)
    return out


def _load_skill(path: Path, fallback: str) -> str:
    if path.is_file():
        return path.read_text(encoding="utf-8")
    return fallback


def _example_brief_snippet() -> str:
    if not _EXAMPLE_BRIEF.is_file():
        return "{}"
    data = json.loads(_EXAMPLE_BRIEF.read_text(encoding="utf-8"))
    return json.dumps(data, ensure_ascii=False, indent=2)[:2500]


def _parse_llm_json(text: str) -> dict[str, Any]:
    try:
        return parse_llm_json_object(text, soft_prose_fallback=True)
    except LlmJsonError as exc:
        raise HostChatError(str(exc)) from exc


def draft_fingerprint(draft: dict[str, Any]) -> str:
    """Canonical JSON sha256 hex for makeability stale checks."""
    canonical = json.dumps(draft, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


# Narration that claims the draft was updated this turn (talk-without-write gate).
_DRAFT_WRITE_CLAIM_RE = re.compile(
    r"(?:"
    r"(?:已|刚刚|本轮|这轮|刚).{0,32}(?:写进|写入|落进|落到|落盘|同步到).{0,16}(?:草稿|draft|侧栏)"
    r"|(?:写进|写入|落进|落到).{0,12}(?:草稿|draft)"
    r"|用补丁.{0,48}(?:真正)?写"
    r"|补丁真写"
    r"|真正落到草稿"
    r"|已按你的(?:决定|拍板).{0,20}写"
    r"|已同步到"
    r")",
    re.I,
)
_DRAFT_WRITE_CLAIM_NEG_RE = re.compile(
    r"(?:不可|不要|别|未|没有|还没|不会).{0,12}(?:声称)?(?:已)?(?:写入|写进|落盘)",
    re.I,
)

_TALK_WITHOUT_WRITE_NOTE = (
    "\n\n—— **宿主拦截：只说不写**\n"
    "你本轮口头声称已写入/落盘草稿，但 JSON 里没有生效的 `brief_patches` "
    "（也没有改动 `draft_brief`）。侧栏草稿**未变**。\n"
    "请下一轮只返回 `artifact.brief_patches` 定点改字段；不要再说「已写入」。"
)


def looks_like_draft_write_claim(text: str) -> bool:
    """True when assistant prose claims the working draft was written this turn."""
    raw = (text or "").strip()
    if not raw:
        return False
    if _DRAFT_WRITE_CLAIM_NEG_RE.search(raw) and not re.search(
        r"(?:这轮|本轮|刚刚|刚用补丁).{0,24}(?:写|落)", raw
    ):
        # Pure policy / negation lines ("不可声称已写入") — not a write claim.
        if not _DRAFT_WRITE_CLAIM_RE.search(raw):
            return False
        # Mixed: admission of past failure + claim of current write still counts.
    return bool(_DRAFT_WRITE_CLAIM_RE.search(raw))


def _draft_fp(session: dict[str, Any]) -> str:
    draft = session.get("draft_brief")
    if isinstance(draft, dict) and draft:
        return draft_fingerprint(draft)
    return ""


def validate_enriched_draft(candidate: Any) -> dict[str, Any]:
    """Minimal validity for LLM enriched draft — no fixed screens/tuning schema."""
    if not isinstance(candidate, dict):
        raise HostChatError("Enriched draft must be a JSON object.")
    project = candidate.get("project")
    if not isinstance(project, dict):
        raise HostChatError("Enriched draft must contain a project object.")
    return candidate


def merge_asset_proposals(draft: dict[str, Any], proposals: list[dict]) -> dict[str, Any]:
    """Merge asset proposals into draft by name (case-insensitive); returns new copy."""
    out = copy.deepcopy(draft)
    if not proposals:
        return out

    assets_raw = out.get("assets")
    assets: list[Any] = list(assets_raw) if isinstance(assets_raw, list) else []
    name_to_idx: dict[str, int] = {}
    for idx, item in enumerate(assets):
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "").strip()
        if name and name.lower() not in name_to_idx:
            name_to_idx[name.lower()] = idx

    for proposal in proposals:
        if not isinstance(proposal, dict):
            continue
        name = str(proposal.get("name") or "").strip()
        if not name:
            continue
        key = name.lower()
        if key in name_to_idx:
            idx = name_to_idx[key]
            existing = assets[idx] if isinstance(assets[idx], dict) else {}
            merged = dict(existing)
            merged.update(proposal)
            assets[idx] = merged
        else:
            assets.append(copy.deepcopy(proposal))
            name_to_idx[key] = len(assets) - 1

    out["assets"] = assets
    return out


def apply_draft_replacement(
    session: dict[str, Any],
    candidate: dict[str, Any],
    *,
    asset_proposals: list[dict] | None = None,
) -> dict[str, Any]:
    """Apply enriched draft onto session with backup; clear export readiness.

    Preserves prior assets by merging candidate/proposal assets into the old
    draft (LLM often omits the full assets[] on thicken). Other top-level keys
    and project fields are overlaid from the candidate.
    """
    validated = validate_enriched_draft(candidate)

    old_draft = session.get("draft_brief")
    previous_fingerprint: str | None = None
    if isinstance(old_draft, dict):
        session["draft_brief_backup"] = copy.deepcopy(old_draft)
        previous_fingerprint = draft_fingerprint(old_draft)
        new_draft = copy.deepcopy(old_draft)
        for key, value in validated.items():
            if key == "assets":
                continue
            if key == "project" and isinstance(value, dict) and isinstance(new_draft.get("project"), dict):
                merged_project = dict(new_draft["project"])
                merged_project.update(value)
                new_draft["project"] = merged_project
            else:
                new_draft[key] = copy.deepcopy(value)
        cand_assets = validated.get("assets")
        if isinstance(cand_assets, list):
            new_draft = merge_asset_proposals(
                new_draft,
                [a for a in cand_assets if isinstance(a, dict)],
            )
    else:
        session["draft_brief_backup"] = None
        new_draft = copy.deepcopy(validated)

    if asset_proposals:
        new_draft = merge_asset_proposals(new_draft, asset_proposals)

    session["draft_brief"] = new_draft
    session["ready_to_export"] = False

    assets = new_draft.get("assets")
    asset_count = len(assets) if isinstance(assets, list) else 0
    fingerprint = draft_fingerprint(new_draft)
    return {
        "ok": True,
        "fingerprint": fingerprint,
        "previous_fingerprint": previous_fingerprint,
        "asset_count": asset_count,
    }


def _brief_enrich_critique_system() -> str:
    return (
        "You are Brief Enrich Critic. Read draft_brief and optional user_hint. "
        "Identify player-visible presentation gaps (UI flow, HUD, feedback, parameter names needed). "
        "Keep project.description as a short product overview; do NOT ask to dump systems rules into description. "
        "When screens/flows are discussed or missing, note gaps for optional project.scenes[] "
        "(id, title, optional summary / ui_panel_ids). "
        "When cross-screen rules (time, economy, unlocks, etc.) are discussed or missing, note gaps for "
        "optional project.systems[] (id, title, optional summary). "
        "When UI panels are discussed or missing from draft, note gaps for optional project.ui_panels[] "
        "(id, title, slots as short string lists — not long prose). Do NOT require wireframe files. "
        "Do NOT require fixed schema keys like screens[] or tuning_needs[]. "
        "Reply with JSON only: {\"gaps\": [{\"area\": \"...\", \"description\": \"...\", \"priority\": \"high|medium|low\"}]}"
    )


def _brief_enrich_system() -> str:
    return _load_skill(
        _BRIEF_ENRICH_SKILL,
        "You are Brief Enricher. Reply with JSON only: draft_brief, asset_proposals, summary.",
    )


def _normalize_asset_proposals(raw: Any) -> list[dict[str, Any]]:
    if not isinstance(raw, list):
        return []
    out: list[dict[str, Any]] = []
    for item in raw:
        if isinstance(item, dict):
            out.append(dict(item))
    return out


def run_brief_enrich(
    session: dict[str, Any],
    *,
    hint: str | None = None,
    temperature: float = 0.7,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Two-step brief thicken: critique gaps → enriched draft merge via DraftMergeGuard."""
    cfg = config or {}
    draft = session.get("draft_brief")
    if not isinstance(draft, dict) or not draft:
        raise HostChatError("No draft_brief yet. Chat about the game first, then run enrich.")

    draft_before = copy.deepcopy(draft)
    user_hint = str(hint or "").strip() or None

    api = resolve_host_api_settings(cfg)
    if not api.get("api_key"):
        raise HostChatError("Brief enrich unavailable: configure API key (OpenRouter/host).")

    critique_payload: dict[str, Any] = {"draft_brief": draft}
    if user_hint:
        critique_payload["user_hint"] = user_hint
    critique_user = json.dumps(critique_payload, ensure_ascii=False, indent=2)

    llm_kwargs: dict[str, Any] = {
        "model": str(api["model"]),
        "api_key": str(api["api_key"]),
        "api_base": str(api["api_base"]),
        "proxy": api.get("proxy"),
        "timeout": 180,
        "temperature": temperature,
    }

    try:
        gaps_raw = chat_text_completion(
            messages=[
                {"role": "system", "content": _brief_enrich_critique_system()},
                {"role": "user", "content": critique_user},
            ],
            **llm_kwargs,
        )
        gaps_parsed = _parse_llm_json(gaps_raw or "")
    except (PromptCraftError, HostChatError) as exc:
        raise HostChatError(str(exc)) from exc

    enrich_payload: dict[str, Any] = {
        "draft_brief": draft,
        "identified_gaps": gaps_parsed.get("gaps") if isinstance(gaps_parsed, dict) else gaps_parsed,
    }
    if user_hint:
        enrich_payload["user_hint"] = user_hint
    enrich_user = json.dumps(enrich_payload, ensure_ascii=False, indent=2)

    try:
        enrich_raw = chat_text_completion(
            messages=[
                {"role": "system", "content": _brief_enrich_system()},
                {"role": "user", "content": enrich_user},
            ],
            **llm_kwargs,
        )
        enrich_parsed = _parse_llm_json(enrich_raw or "")
    except (PromptCraftError, HostChatError) as exc:
        session["draft_brief"] = draft_before
        raise HostChatError(str(exc)) from exc

    candidate = enrich_parsed.get("draft_brief")
    asset_proposals = _normalize_asset_proposals(enrich_parsed.get("asset_proposals"))
    summary = str(enrich_parsed.get("summary") or "").strip()

    try:
        merge_summary = apply_draft_replacement(
            session,
            candidate,
            asset_proposals=asset_proposals or None,
        )
    except HostChatError:
        session["draft_brief"] = draft_before
        raise

    session["last_enrich_at"] = _utc_now()

    assistant_message = summary or "Brief 细节已加厚。"
    assistant_message += " 建议再运行「制作审查」(brief chat makeability) 确认可导出。"

    return {
        "ok": True,
        "summary": summary,
        "assistant_message": assistant_message,
        "fingerprint": merge_summary["fingerprint"],
        "previous_fingerprint": merge_summary.get("previous_fingerprint"),
        "asset_count": merge_summary.get("asset_count", 0),
        "session_id": session.get("id"),
        "ready_to_export": bool(session.get("ready_to_export")),
    }


def _makeability_critic_system() -> str:
    return _load_skill(
        _MAKEABILITY_CRITIC_SKILL,
        "You are Makeability Critic. Reply with JSON only: intent_gaps, detail_gaps, suggested_defaults.",
    )


def _normalize_gap_list(raw: Any, *, field: str) -> list[dict[str, Any]]:
    if not isinstance(raw, list):
        raise HostChatError(f"Makeability critic returned invalid {field}: expected array.")
    out: list[dict[str, Any]] = []
    for item in raw:
        if not isinstance(item, dict):
            raise HostChatError(f"Makeability critic returned invalid {field} item: expected object.")
        out.append(dict(item))
    return out


def _validate_fresh_critic_intent_gaps(intent_gaps: list[dict[str, Any]]) -> None:
    for index, gap in enumerate(intent_gaps):
        if not isinstance(gap, dict):
            raise HostChatError(
                f"Makeability critic intent_gaps[{index}] must be an object."
            )
        occ = gap.get("occurrences")
        if not isinstance(occ, list) or not occ:
            raise HostChatError(
                f"Makeability critic intent_gaps[{index}] missing non-empty occurrences."
            )
        try:
            validate_occurrences_strict(occ, field=f"intent_gaps[{index}].occurrences")
        except ValueError as exc:
            raise HostChatError(f"Makeability critic {exc}") from exc
        wp = gap.get("write_paths")
        if not isinstance(wp, list) or not wp:
            raise HostChatError(
                f"Makeability critic intent_gaps[{index}] missing non-empty write_paths."
            )
        write_paths = normalize_write_paths(wp)
        write_set = {p.lower() for p in write_paths}
        for occ_row in normalize_occurrences(gap.get("occurrences")):
            relation = str(occ_row.get("relation") or "").strip().lower()
            if relation not in {"duplicate", "conflict"}:
                continue
            path = str(occ_row.get("path") or "").strip().lower()
            if path and path not in write_set:
                raise HostChatError(
                    "Makeability critic intent_gaps["
                    f"{index}] duplicate/conflict path {occ_row.get('path')!r} "
                    "must appear in write_paths."
                )


def _build_makeability_review(
    parsed: dict[str, Any],
    *,
    fingerprint: str,
    session: dict[str, Any] | None = None,
) -> dict[str, Any]:
    raw_intent = _normalize_gap_list(parsed.get("intent_gaps"), field="intent_gaps")
    _validate_fresh_critic_intent_gaps(raw_intent)
    intent_gaps = enrich_intent_gaps(raw_intent)
    if session is not None:
        intent_gaps = reconcile_intent_gaps_with_ledger(session, intent_gaps)
    detail_gaps = _normalize_gap_list(parsed.get("detail_gaps"), field="detail_gaps")
    suggested_defaults = _normalize_gap_list(parsed.get("suggested_defaults"), field="suggested_defaults")
    raw_decision_checks = parsed.get("decision_checks")
    decision_checks = normalize_decision_checks(raw_decision_checks)
    if session is not None:
        gap_aliases = decision_key_alias_map_from_gaps(intent_gaps)
        # Path-subset check aliasing disabled (H3); keep call for explicit API stability.
        check_aliases = decision_key_alias_map_from_checks(session, decision_checks)
        alias_map = merge_decision_key_alias_maps(gap_aliases, check_aliases)
        decision_checks = canonicalize_decision_checks(decision_checks, alias_map)
        try:
            assert_critic_decision_checks_protocol(session, decision_checks)
        except ValueError as exc:
            raise HostChatError(str(exc)) from exc
        decision_checks = complete_critic_ledger_checks(session, decision_checks)
        if decision_checks:
            merge_critic_decision_checks(
                session,
                decision_checks,
                current_draft_fingerprint=fingerprint,
            )
        intent_gaps = suppress_intent_gaps_by_ledger(session, intent_gaps)
        repair_gaps = repair_failed_gaps_for_display(session)
        repair_answers = repair_answers_from_ledger(session)
    else:
        repair_gaps = []
        repair_answers = []
    return {
        "schema_version": MAKEABILITY_SCHEMA_VERSION,
        "reviewed_at": _utc_now(),
        "draft_fingerprint": fingerprint,
        "intent_gaps": intent_gaps,
        "detail_gaps": detail_gaps,
        "suggested_defaults": suggested_defaults,
        "decision_checks": decision_checks,
        "repair_gaps": repair_gaps,
        "repair_answers": repair_answers,
    }


def format_makeability_review_details(
    review: dict[str, Any] | None,
    *,
    session: dict[str, Any] | None = None,
) -> str:
    """Human-readable makeability gaps for session messages / CLI."""
    if not isinstance(review, dict) or not review:
        return ""
    lines: list[str] = []
    intent_gaps = review.get("intent_gaps") if isinstance(review.get("intent_gaps"), list) else []
    detail_gaps = review.get("detail_gaps") if isinstance(review.get("detail_gaps"), list) else []
    if intent_gaps:
        lines.append("意图缺口（须在本对话内拍板）：")
        for gap in intent_gaps:
            if not isinstance(gap, dict):
                continue
            gid = str(gap.get("id") or "").strip()
            question = str(gap.get("question") or "（未描述）").strip()
            prefix = f"`{gid}` · " if gid else ""
            lines.append(f"- {prefix}{question}")
            why = str(gap.get("why_blocking") or "").strip()
            if why:
                lines.append(f"  - {why}")
            choices = gap.get("choices")
            if isinstance(choices, list) and choices:
                choice_txt = " / ".join(str(c).strip() for c in choices if str(c).strip())
                if choice_txt:
                    lines.append(f"  - 选项：{choice_txt}")
        lines.append("")
    if detail_gaps:
        gaps_to_list = detail_gaps
        skipped = 0
        if session is not None:
            gaps_to_list, skipped = partition_detail_gaps_for_display(session, detail_gaps)
        if gaps_to_list:
            lines.append("施工细节（导出后进 production，PM 可补暂定值）：")
            for gap in gaps_to_list:
                if not isinstance(gap, dict):
                    continue
                gid = str(gap.get("id") or "").strip()
                topic = str(gap.get("topic") or "（未描述）").strip()
                prefix = f"`{gid}` · " if gid else ""
                lines.append(f"- {prefix}{topic}")
        if skipped:
            if gaps_to_list:
                lines.append(
                    f"（另有 {skipped} 条施工细节此前已列过，完整列表仍见 makeability review。）"
                )
            else:
                lines.append(
                    f"（{skipped} 条施工细节缺口与上次相同，不再重复列出；仍见 review.detail_gaps。）"
                )
    return "\n".join(lines).strip()


def _compute_ready_to_export(session: dict[str, Any]) -> bool:
    draft = session.get("draft_brief")
    draft_fp = draft_fingerprint(draft) if isinstance(draft, dict) and draft else None
    if ledger_blocks_export(session, current_draft_fingerprint=draft_fp):
        return False
    if not isinstance(draft, dict) or not draft:
        return False
    if _audit_draft_gaps(draft):
        return False
    review = session.get("makeability_review")
    if not isinstance(review, dict) or not review:
        return False
    if str(review.get("draft_fingerprint") or "") != draft_fingerprint(draft):
        return False
    intent_raw = review.get("intent_gaps")
    if isinstance(intent_raw, list) and intent_raw:
        open_intent = suppress_intent_gaps_by_ledger(session, intent_raw)
        if open_intent:
            return False
    return True


def assert_makeability_exportable(session: dict[str, Any]) -> dict[str, Any]:
    """Require fresh makeability review with no open intent gaps before export."""
    review = session.get("makeability_review")
    if not isinstance(review, dict) or not review:
        raise HostChatError(
            "尚未进行制作审查。请先运行「制作审查」(brief chat makeability) 后再导出。"
        )
    draft = session.get("draft_brief")
    if not isinstance(draft, dict) or not draft:
        raise HostChatError("No draft_brief in session. Chat about the game first, then 落实成 brief.")
    current_fp = draft_fingerprint(draft)
    review_fp = str(review.get("draft_fingerprint") or "")
    if review_fp != current_fp:
        raise HostChatError(
            "制作审查已过期（draft 已变更）。请重新运行「制作审查」后再导出。"
        )
    if ledger_blocks_export(session, current_draft_fingerprint=current_fp):
        raise HostChatError(
            "仍有制作审查决定未验证写入（pending/applied/repair_failed），不可导出。"
        )
    intent_gaps = review.get("intent_gaps")
    if isinstance(intent_gaps, list) and intent_gaps:
        open_intent = suppress_intent_gaps_by_ledger(session, intent_gaps)
        if open_intent:
            raise HostChatError(
                f"仍有 {len(open_intent)} 条意图缺口未关闭，不可导出。请在策划对话内补齐后重新审查。"
            )
    return review


def makeability_sidecar_path(
    brief_rel_or_path: str | Path,
    repo_root: Path | None = None,
    workspace: Path | None = None,
) -> Path:
    """Resolve makeability.json beside bound project or exported brief."""
    root = (repo_root or _repo_root()).resolve()
    ws = (workspace or root).resolve()
    raw = str(brief_rel_or_path).replace("\\", "/").strip().lstrip("./")
    if is_external_brief_key(raw):
        paths = paths_for_brief_key(raw, ws)
        return Path(paths["brief"]).parent / "makeability.json"
    m = re.match(r"^projects/([^/]+)/", raw, re.I)
    if m:
        return (root / "projects" / m.group(1) / "makeability.json").resolve()
    p = Path(brief_rel_or_path)
    if not p.is_absolute():
        p = (root / p).resolve()
    else:
        p = p.resolve()
    return p.parent / "makeability.json"


def write_makeability_sidecar(path: Path, review: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(review, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def run_makeability_review(
    session: dict[str, Any],
    *,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Independent sub-LLM review of draft_brief; writes session['makeability_review']."""
    cfg = config or {}
    draft = session.get("draft_brief")
    if not isinstance(draft, dict) or not draft:
        raise HostChatError("No draft_brief yet. Chat about the game first, then run makeability review.")

    draft_before = copy.deepcopy(draft)
    fingerprint = draft_fingerprint(draft)
    project_raw = draft.get("project") if isinstance(draft.get("project"), dict) else {}
    genre = str(project_raw.get("genre") or "").strip()

    ensure_decision_ledger(session)
    user_payload = {
        "genre": genre,
        "draft_brief": draft,
        "decision_ledger": ledger_for_prompt(session),
        "source_of_truth_note": (
            "project.systems / project.scenes / project.ui_panels and decision_ledger "
            "are authoritative for rules; description and gameplay_loop are summaries only."
        ),
    }
    user_text = json.dumps(user_payload, ensure_ascii=False, indent=2)
    system = _makeability_critic_system()

    api = resolve_host_api_settings(cfg)
    if not api.get("api_key"):
        raise HostChatError(
            "Makeability critic unavailable: configure API key (OpenRouter/host)."
        )
    try:
        raw = chat_text_completion(
            model=str(api["model"]),
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user_text},
            ],
            api_key=str(api["api_key"]),
            api_base=str(api["api_base"]),
            proxy=api.get("proxy"),
            timeout=180,
        )
    except PromptCraftError as exc:
        raise HostChatError(str(exc)) from exc

    try:
        parsed = _parse_llm_json(raw or "")
        review = _build_makeability_review(parsed, fingerprint=fingerprint, session=session)
    except HostChatError:
        if session.get("draft_brief") != draft_before:
            session["draft_brief"] = draft_before
        raise

    session["makeability_review"] = review
    intent_count = len(review["intent_gaps"])
    detail_count = len(review["detail_gaps"])
    repair_gaps = review.get("repair_gaps") if isinstance(review.get("repair_gaps"), list) else []
    repair_count = len(repair_gaps)

    if session.get("draft_brief") != draft_before:
        session["draft_brief"] = draft_before

    session["ready_to_export"] = _compute_ready_to_export(session)

    assistant_message = (
        f"制作审查完成：{intent_count} 条意图缺口，{detail_count} 条施工细节缺口。"
    )
    if intent_count:
        assistant_message += " 意图未关前不可交接项目经理。"
    elif detail_count:
        assistant_message += " 施工细节将进 production，PM 可补暂定值。"
    if repair_count:
        assistant_message += (
            f" 另有 {repair_count} 条已答决定验证失败，请在卡片中「重试写入」"
            "（无需重新选题）。"
        )
    details = format_makeability_review_details(review, session=session)
    if details:
        assistant_message = f"{assistant_message}\n\n{details}"

    # Persist into conversation so the main host-chat agent sees Critic findings
    # on the next user turn (GUI display alone does not update session.messages).
    messages = list(session.get("messages") or [])
    messages.append({"role": "assistant", "content": assistant_message})
    session["messages"] = messages

    return {
        "ok": True,
        "review": review,
        "intent_count": intent_count,
        "detail_count": detail_count,
        "repair_count": repair_count,
        "ready_to_export": bool(session.get("ready_to_export")),
        "session_id": session.get("id"),
        "assistant_message": assistant_message,
        "draft_brief": session.get("draft_brief"),
        "message_count": len(messages),
    }


_MAKEABILITY_ANSWER_SYSTEM = """You close Makeability intent gaps by writing brief patches.
The user answered structured gap cards (not free chat). Reply with JSON only:
{
  "assistant_message": "short Chinese summary of what you wrote into the draft",
  "brief_patches": [ /* set / upsert_asset / add_asset / upsert_graph / upsert_system / upsert_scene / upsert_ui_panel */ ]
}
Rules:
- Patch current_draft_brief so each answered gap is decided everywhere it appears.
- open_intent_gaps may include occurrences (canonical|duplicate|conflict) and write_paths: you MUST patch every write_paths entry in one response (description, gameplay_loop, scenes, systems, ui_panels as listed).
- You may shorten or remove stale duplicate/conflict prose instead of repeating detailed rules in every path.
- Prefer upsert_system / upsert_scene / upsert_ui_panel for list rows; use set for scalar fields.
- Phrases like 先不用解锁 / 直接解锁 / 开局可进 / no unlock = hall enterable from start, NO building purchase lock.
- Do not invent decisions the user did not make. Do not put numeric tables into brief prose.
- Do not return a full draft_brief. Do not return decision_checks (a separate Verifier will run).
"""

_MAKEABILITY_VERIFIER_SYSTEM = """You are Makeability Verifier — independent from the gap closer.
Read candidate_draft_brief and pending_decisions (user answers, target_paths, write_paths, occurrences).
Reply with JSON only:
{
  "decision_checks": [
    {
      "decision_key": "system.scope.rule",
      "gap_id": "gap_id",
      "status": "satisfied | missing | conflict",
      "evidence_paths": ["project.systems[id=x].notes"],
      "unresolved_paths": ["project.description"]
    }
  ]
}
Rules:
- One decision_checks row per pending_decisions entry (same decision_key).
- Scan the whole candidate draft for duplicate/conflicting occurrences of the same decision (including paths not listed).
- satisfied only if the draft clearly encodes the user's answer_text at every required write_path and no listed occurrence still conflicts.
- List any duplicate/conflict you still find in unresolved_paths (even if status would otherwise be satisfied).
- missing if not reflected at a required path; conflict if draft contradicts the answer.
- evidence_paths must list every write_path you verified; omitting a required write_path means not satisfied.
"""


def _normalize_makeability_answers(raw: Any) -> list[dict[str, str]]:
    if isinstance(raw, str):
        text = raw.strip()
        if not text:
            return []
        try:
            raw = json.loads(text)
        except json.JSONDecodeError as exc:
            raise HostChatError(f"Invalid answers JSON: {exc}") from exc
    if not isinstance(raw, list) or not raw:
        raise HostChatError("answers must be a non-empty JSON array of {gap_id, choice?, note?}")
    out: list[dict[str, str]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        gap_id = str(item.get("gap_id") or item.get("id") or "").strip()
        if not gap_id:
            continue
        choice = str(item.get("choice") or item.get("selected") or "").strip()
        note = str(item.get("note") or item.get("text") or "").strip()
        if not choice and not note:
            continue
        out.append({"gap_id": gap_id, "choice": choice, "note": note})
    if not out:
        raise HostChatError("No usable answers (need gap_id plus choice and/or note).")
    return out


def _answer_makeability_failure_result(
    session: dict[str, Any],
    *,
    normalized: list[dict[str, str]],
    touched_keys: list[str],
    reason: str,
) -> dict[str, Any]:
    if touched_keys:
        mark_keys_repair_failed(session, touched_keys)
    messages = list(session.get("messages") or [])
    assistant_message = f"答案已保存，但写入草稿失败：{reason} 可在卡片中重试写入。"
    messages.append({"role": "assistant", "content": assistant_message})
    session["messages"] = messages
    session["ready_to_export"] = False
    review = session.get("makeability_review")
    rem_intent = (
        review.get("intent_gaps")
        if isinstance(review, dict) and isinstance(review.get("intent_gaps"), list)
        else []
    )
    return {
        "ok": False,
        "repair_failed": True,
        "verified_ids": [],
        "repair_failed_ids": [r["gap_id"] for r in normalized],
        "closed_ids": [],
        "remaining_intent_count": len(rem_intent),
        "assistant_message": assistant_message,
        "draft_brief": session.get("draft_brief"),
        "review": session.get("makeability_review"),
        "ready_to_export": False,
        "session_id": session.get("id"),
        "message_count": len(messages),
        "fingerprint_match": False,
        "draft_persisted": False,
        "draft_persist_error": reason,
    }


def _persist_answer_draft_or_mark(
    session: dict[str, Any],
    *,
    verified_ids: list[str],
    expected_keys: list[str],
    normalized: list[dict[str, str]],
) -> tuple[bool, str | None]:
    """Try to flush session draft to disk after answer patches.

    Unbound sessions have nothing to flush (treated as persisted). Bound sessions
    must succeed CAS write or callers must not claim verified success.
    """
    _ = verified_ids, expected_keys, normalized
    bound = _norm_brief_rel(session.get("bound_brief_rel"))
    if not bound:
        session.pop("last_draft_persist_error", None)
        return True, None
    try:
        out = persist_project_draft(session)
    except HostChatError as exc:
        err = str(exc)
        session["last_draft_persist_error"] = err
        return False, err
    if out is None:
        err = "无法写入 brief.draft.json（缺少可落盘草稿字段或绑定路径）。"
        session["last_draft_persist_error"] = err
        return False, err
    session.pop("last_draft_persist_error", None)
    return True, None


def answer_makeability_gaps(
    session: dict[str, Any],
    answers: Any,
    *,
    config: dict[str, Any] | None = None,
    persist_after_record: Callable[[dict[str, Any]], None] | None = None,
) -> dict[str, Any]:
    """Apply structured gap-card answers via closer + independent verifier LLM."""
    cfg = config or {}
    draft = session.get("draft_brief")
    if not isinstance(draft, dict) or not draft:
        raise HostChatError("No draft_brief yet. Chat about the game first, then run makeability.")
    review = session.get("makeability_review")
    if not isinstance(review, dict) or not review:
        raise HostChatError("No makeability review yet. Run「制作审查」first.")

    normalized = _normalize_makeability_answers(answers)
    gaps_by_id = resolve_gaps_for_answers(session, normalized)
    for row in normalized:
        if row["gap_id"] not in gaps_by_id:
            raise HostChatError(f"Unknown or unrecoverable gap_id: {row['gap_id']}")
    if not gaps_by_id:
        raise HostChatError("No usable gaps for these answers.")

    ensure_decision_ledger(session)
    touched_keys = record_gap_answers(session, normalized, gaps_by_id)
    if persist_after_record is not None:
        persist_after_record(session)

    specs = decisions_for_verifier(session, gaps_by_id, normalized)
    gap_id_map = gap_id_map_from_specs(specs)
    expected_keys = list(dict.fromkeys(touched_keys))
    required_paths_by_key = required_paths_by_key_from_gaps(gaps_by_id, session=session)

    try:
        api = resolve_host_api_settings(cfg)
    except Exception as exc:
        return _answer_makeability_failure_result(
            session,
            normalized=normalized,
            touched_keys=touched_keys,
            reason=str(exc),
        )

    def _llm(system: str, user_payload: dict[str, Any]) -> dict[str, Any]:
        if not api.get("api_key"):
            raise HostChatError(
                "Makeability answer unavailable: configure API key (OpenRouter/host)."
            )
        try:
            raw = chat_text_completion(
                model=str(api["model"]),
                messages=[
                    {"role": "system", "content": system},
                    {
                        "role": "user",
                        "content": json.dumps(user_payload, ensure_ascii=False, indent=2),
                    },
                ],
                api_key=str(api["api_key"]),
                api_base=str(api["api_base"]),
                proxy=api.get("proxy"),
                timeout=180,
            )
        except PromptCraftError as exc:
            raise HostChatError(str(exc)) from exc
        except Exception as exc:
            raise HostChatError(str(exc)) from exc
        return _parse_llm_json(raw or "")

    def _call_closer(
        draft_snapshot: dict[str, Any],
        answer_rows: list[dict[str, str]],
        gaps: list[dict[str, Any]],
        *,
        repair_note: str = "",
    ) -> dict[str, Any]:
        user_payload = {
            "current_draft_brief": draft_snapshot,
            "open_intent_gaps": gaps,
            "user_answers": answer_rows,
            "decision_ledger": ledger_for_prompt(session),
            "instruction": (
                "Write brief_patches that encode these answers into the draft."
                + (f" Repair pass: {repair_note}" if repair_note else "")
            ),
        }
        return _llm(_MAKEABILITY_ANSWER_SYSTEM, user_payload)

    def _run_verifier(
        candidate_draft: dict[str, Any],
    ) -> tuple[list[str], list[str], list[str], bool]:
        """Returns verified_ids, failed_ids, path_notes, protocol_error.

        protocol_error=True when verifier omitted keys / returned unusable rows —
        do not spend closer repair rounds on that (M2).
        """
        user_payload = {
            "candidate_draft_brief": candidate_draft,
            "pending_decisions": specs,
            "decision_ledger": ledger_for_prompt(session),
        }
        parsed = _llm(_MAKEABILITY_VERIFIER_SYSTEM, user_payload)
        raw_checks = normalize_decision_checks(parsed.get("decision_checks"))
        raw_complete = verifier_reported_all_keys(expected_keys, raw_checks)
        protocol_error = not raw_complete
        cand_fp = draft_fingerprint(candidate_draft)
        path_notes = verifier_path_failure_detail(
            raw_checks,
            required_paths_by_key,
            expected_keys=expected_keys,
        )
        verified, failed = apply_whole_card_verifier_results(
            session,
            expected_keys,
            raw_checks,
            gap_id_for_key=gap_id_map,
            raw_complete=raw_complete,
            verified_draft_fingerprint=cand_fp,
            required_paths_by_key=required_paths_by_key,
        )
        return verified, failed, path_notes, protocol_error

    if not api.get("api_key"):
        return _answer_makeability_failure_result(
            session,
            normalized=normalized,
            touched_keys=touched_keys,
            reason="configure API key (OpenRouter/host)",
        )

    parsed: dict[str, Any] | None = None
    patches: list[dict[str, Any]] = []
    try:
        parsed = _call_closer(
            draft,
            normalized,
            [gaps_by_id[r["gap_id"]] for r in normalized],
        )
        patches = _extract_brief_patches(parsed) or []
        if not patches:
            return _answer_makeability_failure_result(
                session,
                normalized=normalized,
                touched_keys=touched_keys,
                reason="Gap closer returned no brief_patches; draft unchanged.",
            )
    except (HostChatError, PromptCraftError) as exc:
        return _answer_makeability_failure_result(
            session,
            normalized=normalized,
            touched_keys=touched_keys,
            reason=str(exc),
        )

    assert parsed is not None
    try:
        session["draft_brief"] = apply_brief_patches(draft, patches)
        for key in touched_keys:
            update_ledger_status(session, key, status="applied")
        verified_ids, repair_failed_ids, path_notes, protocol_error = _run_verifier(
            session["draft_brief"]
        )
    except (HostChatError, PromptCraftError) as exc:
        return _answer_makeability_failure_result(
            session,
            normalized=normalized,
            touched_keys=touched_keys,
            reason=str(exc),
        )

    repair_rows = [r for r in normalized if r["gap_id"] in repair_failed_ids]
    attempt = 0
    last_path_notes = path_notes if repair_failed_ids else []
    # Protocol errors (missing verifier rows) must not burn closer repair budget.
    while (
        repair_rows
        and not protocol_error
        and attempt < MAX_AUTO_REPAIR_ATTEMPTS
    ):
        attempt += 1
        repair_detail = "; ".join(last_path_notes) if last_path_notes else ""
        try:
            reparsed = _call_closer(
                session["draft_brief"],
                repair_rows,
                [gaps_by_id[r["gap_id"]] for r in repair_rows],
                repair_note=(
                    "prior patches missed these gaps; use saved user answers"
                    + (f"; path gaps: {repair_detail}" if repair_detail else "")
                ),
            )
            repatches = _extract_brief_patches(reparsed) or []
            if not repatches:
                break
            session["draft_brief"] = apply_brief_patches(session["draft_brief"], repatches)
            patches.extend(repatches)
            for key in expected_keys:
                update_ledger_status(session, key, status="applied")
            (
                verified_ids,
                repair_failed_ids,
                last_path_notes,
                protocol_error,
            ) = _run_verifier(session["draft_brief"])
            repair_rows = [r for r in normalized if r["gap_id"] in repair_failed_ids]
        except (HostChatError, PromptCraftError):
            break

    # Memory verifier success is not enough — bound project draft must hit disk (H1).
    draft_persisted, draft_persist_error = _persist_answer_draft_or_mark(
        session,
        verified_ids=verified_ids,
        expected_keys=expected_keys,
        normalized=normalized,
    )
    if draft_persist_error and verified_ids:
        # Downgrade: answers kept, but do not claim verified write.
        mark_keys_repair_failed(session, expected_keys)
        repair_failed_ids = list(
            dict.fromkeys(
                [*(repair_failed_ids or []), *[r["gap_id"] for r in normalized]]
            )
        )
        verified_ids = []
    elif verified_ids:
        remove_verified_gaps_from_review(session, verified_ids)

    assistant_message = str(parsed.get("assistant_message") or "").strip() or (
        "已按审查选项写入工作草稿。"
    )
    if draft_persist_error:
        assistant_message += (
            f"\n\n（草稿未写入磁盘：{draft_persist_error} "
            "答案已保存在会话中，可对齐磁盘后重试写入。）"
        )
    if repair_failed_ids:
        assistant_message += (
            f"\n\n（{len(repair_failed_ids)} 条答案已保存但未能验证写入，可重试写入。）"
        )
    elif verified_ids and draft_persisted:
        assistant_message = assistant_message.rstrip() + (
            "\n\n（宿主：已关闭已验证的意图缺口；草稿已变，请再点「制作审查」确认后再导出。）"
        )

    messages = list(session.get("messages") or [])
    messages.append({"role": "assistant", "content": assistant_message})
    session["messages"] = messages
    session["ready_to_export"] = _compute_ready_to_export(session)

    remaining = session.get("makeability_review") or {}
    rem_intent = remaining.get("intent_gaps") if isinstance(remaining, dict) else []
    rem_count = len(rem_intent) if isinstance(rem_intent, list) else 0

    ok = not repair_failed_ids and rem_count == 0 and draft_persisted
    return {
        "ok": ok,
        "repair_failed": bool(repair_failed_ids) or bool(draft_persist_error),
        "verified_ids": verified_ids,
        "repair_failed_ids": repair_failed_ids,
        "closed_ids": verified_ids,
        "remaining_intent_count": rem_count,
        "assistant_message": assistant_message,
        "draft_brief": session.get("draft_brief"),
        "review": session.get("makeability_review"),
        "ready_to_export": bool(session.get("ready_to_export")),
        "session_id": session.get("id"),
        "message_count": len(messages),
        "fingerprint_match": False,
        "draft_persisted": draft_persisted,
        "draft_persist_error": draft_persist_error,
    }


def user_requests_commit_brief(text: str | None) -> bool:
    if not text or not text.strip():
        return False
    return bool(_COMMIT_BRIEF_RE.search(text.strip()))


def user_requests_commit_doc(text: str | None) -> bool:
    if not text or not text.strip():
        return False
    # Prefer brief freeze when both patterns could match.
    if user_requests_commit_brief(text):
        return False
    return bool(_COMMIT_DOC_RE.search(text.strip()))


def resolve_mode(session: dict[str, Any], user_message: str | None) -> str:
    pending = session.get("pending_mode")
    if pending == "commit_brief":
        return "commit_brief"
    if pending == "commit_doc":
        return "commit_doc"
    if session.get("mode") == "commit_brief" and session.get("draft_brief"):
        if user_message and user_requests_commit_brief(user_message):
            return "commit_brief"
        if user_message and re.search(r"(继续落实|改一下 brief|更新 brief|导出)", user_message, re.I):
            return "commit_brief"
    if session.get("mode") == "commit_doc" and session.get("draft_document"):
        if user_message and user_requests_commit_doc(user_message):
            return "commit_doc"
        if user_message and re.search(r"(继续整理|改一下文档|更新文档|保存文档)", user_message, re.I):
            return "commit_doc"
    if user_requests_commit_brief(user_message):
        return "commit_brief"
    if user_requests_commit_doc(user_message):
        return "commit_doc"
    if session.get("intent_hint") == "commit_brief" and user_message:
        if re.search(r"^(好|行|可以|确认|嗯|ok|yes|落实)", user_message.strip(), re.I):
            return "commit_brief"
    if session.get("intent_hint") == "commit_doc" and user_message:
        if re.search(r"^(好|行|可以|确认|嗯|ok|yes|整理)", user_message.strip(), re.I):
            return "commit_doc"
    return "chat"


def _messages_char_len(messages: list[dict[str, Any]], summary: str) -> int:
    n = len(summary or "")
    for m in messages:
        if isinstance(m, dict):
            n += len(str(m.get("content") or ""))
    return n


def _compress_prompt(
    existing_summary: str,
    old_messages: list[dict[str, Any]],
    *,
    decision_ledger: list[dict[str, Any]] | None = None,
) -> str:
    ledger = decision_ledger if isinstance(decision_ledger, list) else []
    ledger_keys = [
        str(row.get("decision_key") or "").strip()
        for row in ledger
        if isinstance(row, dict) and str(row.get("decision_key") or "").strip()
    ]
    ledger_block = (
        json.dumps(ledger, ensure_ascii=False, indent=2)
        if ledger
        else "（无 — 宿主未注入 decision_ledger）"
    )
    exclude = ""
    if ledger_keys:
        exclude = (
            "下列 decision_ledger 条目已有用户答案，为权威来源（宿主单独注入 planner），"
            f"**禁止**写入摘要：{', '.join(ledger_keys)}。\n"
        )
    return (
        "你是对话摘要器。将下列「较早对话」压成一段中文摘要，供后续 Brief 创建助手使用。\n"
        "规则：\n"
        "- 摘要只保留 decision_ledger **未覆盖**的讨论、待定项与用户偏好。\n"
        "- 不得把 ledger 中已有答案的制作审查决定复述进摘要（即使对话里出现过）。\n"
        f"{exclude}"
        "- 丢掉客套与重复脑暴。\n"
        "- 标明这些尚未落实为 brief，不是契约。\n"
        "- 只输出摘要正文，不要 JSON。\n\n"
        f"decision_ledger（勿写入 conversation_summary）：\n{ledger_block}\n\n"
        f"已有摘要：\n{existing_summary or '（无）'}\n\n"
        f"较早对话：\n{json.dumps(old_messages, ensure_ascii=False, indent=2)}"
    )


def maybe_compress_session(session: dict[str, Any], config: dict[str, Any]) -> bool:
    """If over budget, summarize older messages and keep recent ones. Returns True if compressed."""
    messages = list(session.get("messages") or [])
    summary = str(session.get("summary") or "")
    if _messages_char_len(messages, summary) <= _CHAR_BUDGET:
        return False
    if len(messages) <= _RECENT_KEEP:
        return False

    old = messages[: -_RECENT_KEEP]
    recent = messages[-_RECENT_KEEP :]
    api = resolve_host_api_settings(config)
    if not api.get("api_key"):
        session["summary"] = (summary + "\n" if summary else "") + (
            f"（已截断较早 {len(old)} 条消息，摘要失败：无 API Key）"
        )
        session["messages"] = recent
        session["compressed_count"] = int(session.get("compressed_count") or 0) + len(old)
        return True

    try:
        raw = chat_text_completion(
            model=str(api["model"]),
            messages=[
                {"role": "system", "content": "You compress chat history. Reply with plain summary text only."},
                {"role": "user", "content": _compress_prompt(summary, old, decision_ledger=ledger_for_prompt(session))},
            ],
            api_key=str(api["api_key"]),
            api_base=str(api["api_base"]),
            proxy=api.get("proxy"),
            timeout=90,
        )
        new_summary = (raw or "").strip()
        if not new_summary:
            raise HostChatError("empty compression")
        session["summary"] = new_summary
        session["messages"] = recent
        session["compressed_count"] = int(session.get("compressed_count") or 0) + len(old)
        return True
    except (HostChatError, PromptCraftError, OSError, ValueError):
        session["summary"] = (summary + "\n" if summary else "") + (
            f"（已截断较早 {len(old)} 条消息；自动摘要失败，仅保留近 {_RECENT_KEEP} 条原文）"
        )
        session["messages"] = recent
        session["compressed_count"] = int(session.get("compressed_count") or 0) + len(old)
        return True


def _animation_graphs_skill_block() -> str:
    """Always inject clip-name contract for chat / commit_brief (autofix uses chat)."""
    body = _load_skill(
        _ANIM_GRAPH_SKILL,
        "animation_graphs: use Godot clip names from assets (suffix after character_), "
        "never states[], never asset full names in from/to/then.",
    )
    return f"\n\n---\n\n{body}\n"


def _system_prompt(mode: str) -> str:
    if mode == "commit_brief":
        skill = _load_skill(
            _COMMIT_BRIEF_SKILL,
            "Commit the conversation into a Foundry brief. Output JSON only.",
        )
        return (
            f"{skill}"
            f"{_animation_graphs_skill_block()}"
            f"## Example brief\n\n```json\n{_example_brief_snippet()}\n```\n\n"
            "Respond with ONLY valid JSON matching the schema in the skill. No markdown outside JSON."
        )
    if mode == "commit_doc":
        skill = _load_skill(
            _COMMIT_DOC_SKILL,
            "Commit the conversation into a markdown document. Output JSON only.",
        )
        return (
            f"{skill}\n\n"
            "Respond with ONLY valid JSON matching the schema in the skill. No markdown outside JSON."
        )
    skill = _load_skill(
        _HOST_CHAT_SKILL,
        "You are a Brief creation chat assistant. Output JSON only. "
        "When discussing a game, emit progressive draft_brief; ready_to_export false until freeze.",
    )
    return (
        f"{skill}"
        f"{_animation_graphs_skill_block()}"
        "Respond with ONLY valid JSON matching the schema in the skill. No markdown outside JSON."
    )


def _build_user_payload(session: dict[str, Any], mode: str) -> dict[str, Any]:
    if mode == "commit_brief":
        instruction = (
            "Synthesize/refine draft_brief from the full conversation and current_draft_brief. "
            "Fill reasonable defaults. Set ready_to_export only if contract-complete."
        )
    elif mode == "commit_doc":
        instruction = (
            "Synthesize a complete markdown document from the conversation and current_draft_document. "
            "Put full body in artifact.body. ready_to_export true when content is savable."
        )
    else:
        instruction = (
            "Continue chatting. Prefer surgical updates: when clarifying 1–3 points "
            "(e.g. closing makeability gaps), set artifact.brief_patches and omit or "
            "null draft_brief — do NOT return a thinned full brief. "
            "Ops: set {path,value}, upsert_asset {match,set}, add_asset {value}, "
            "upsert_graph {match,set}. "
            "If latest_makeability_review is present and fingerprint_match is true and "
            "the user is answering those questions / picking choices: write decisions with "
            "artifact.brief_patches (prefer upsert_system / upsert_scene / upsert_ui_panel "
            "for list rows), set artifact.closed_intent_gap_ids to the closed gap ids, "
            "and acknowledge any remaining open gaps. "
            "If fingerprint_match is false, do NOT re-ask old intent_gaps — tell the user "
            "to re-run 制作审查. "
            "Phrases like 先不用解锁 / 直接解锁 / 开局可进 mean no building unlock purchase; "
            "patch the draft to enterable-from-start, never invent a paid unlock flow. "
            "Only return a FULL artifact.draft_brief for major redesigns / first draft. "
            "When drafting a design note (not Foundry brief), you may also set "
            "artifact.draft_document {title, format, body}. ready_to_export must be false. "
            "Pure tech Q&A with no game design: artifact may be null."
        )
    payload: dict[str, Any] = {
        "mode": mode,
        "conversation": session.get("messages") or [],
        "instruction": instruction,
    }
    summary = str(session.get("summary") or "").strip()
    if summary:
        payload["conversation_summary"] = summary
        payload["summary_note"] = (
            "Earlier turns were compressed; summary is not a frozen brief. "
            "If conversation_summary conflicts with current_draft_brief or decision_ledger, "
            "trust draft_brief + decision_ledger (systems/scenes/ui_panels + ledger 优先)."
        )
    ledger = ledger_for_prompt(session)
    if ledger:
        payload["decision_ledger"] = ledger
        payload["decision_ledger_note"] = (
            "decision_ledger 记录用户已在制作审查卡片拍板的决定；"
            "verified 条目不得当作未决 intent 重新提问。"
            "conversation_summary 不得覆盖 ledger。"
        )
    if session.get("draft_brief"):
        payload["current_draft_brief"] = session.get("draft_brief")
    if session.get("draft_document"):
        payload["current_draft_document"] = session.get("draft_document")
    review = session.get("makeability_review")
    if isinstance(review, dict) and review:
        draft = session.get("draft_brief")
        fingerprint_match = False
        if isinstance(draft, dict) and draft:
            fingerprint_match = (
                str(review.get("draft_fingerprint") or "") == draft_fingerprint(draft)
            )
        intent_gaps = (
            review.get("intent_gaps") if isinstance(review.get("intent_gaps"), list) else []
        )
        # Stale review must not keep injecting closed/outdated intent questions into
        # the planner — that causes "水族馆还要解锁" loops after the draft already fixed it.
        intent_gaps = filter_intent_gaps_for_display(session, intent_gaps)
        if not fingerprint_match:
            intent_gaps = []
        payload["latest_makeability_review"] = {
            "fingerprint_match": fingerprint_match,
            "note": (
                "独立制作审查（子 LLM Critic）的结果。用户按缺口提问/作答时必须对照此对象："
                "用 brief_patches（含 upsert_system / upsert_scene / upsert_ui_panel）"
                "写入玩法决定，并在 artifact.closed_intent_gap_ids 列出已关闭的缺口 id；"
                "detail_gaps 只说明将进 production，勿写进 brief 散文。"
                "fingerprint_match=false 表示审查已过期：intent_gaps 已清空（勿再追问旧缺口），"
                "应提示用户重新「制作审查」。"
                "用户说「先不用解锁 / 直接解锁 / 先做成开着」= 无建筑购买门闩，写入开局可进，"
                "不要理解成「要做付费解锁流程」。"
            ),
            "intent_gaps": intent_gaps,
            "detail_gaps": review.get("detail_gaps") if isinstance(review.get("detail_gaps"), list) else [],
            "suggested_defaults": (
                review.get("suggested_defaults")
                if isinstance(review.get("suggested_defaults"), list)
                else []
            ),
            "reviewed_at": review.get("reviewed_at"),
        }
    bound = str(session.get("bound_brief_rel") or "").strip()
    if bound:
        payload["bound_project"] = {
            "brief_rel": bound,
            "slug": session.get("project_slug") or _slug_from_brief_rel(bound),
            "note": (
                "GUI 已绑定此工程。续写 current_draft_brief 时必须属于该项目；"
                "若存在 brief.draft.json / brief.json，已载入为 current_draft_brief。"
                "导出写入该 brief_rel。不要当成别的游戏（例如黑哨）。"
            ),
        }
    if session.get("_talk_without_write"):
        payload["host_nudge"] = (
            "上一轮你声称写进草稿，但宿主检测到 brief_patches / draft 未变（只说不写）。"
            "本轮必须用 artifact.brief_patches 定点落盘；禁止只口头说「已写入」。"
            "制作审查只读草稿，聊天记录不算数。"
        )
    return payload


def validate_brief_dict(data: dict[str, Any]) -> dict[str, Any]:
    project = ProjectContext.from_dict(data.get("project", {}))
    assets_raw = data.get("assets") or []
    if not assets_raw:
        raise HostChatError("Brief must contain at least one asset.")
    assets = [AssetSpec.from_dict(item) for item in assets_raw]
    graphs = parse_animation_graphs(data)
    validate_brief_for_export(project, assets, animation_graphs=graphs)
    out: dict[str, Any] = {
        "project": project_to_dict(project),
        "assets": [asset_to_dict(a) for a in assets],
    }
    if graphs:
        out["animation_graphs"] = [animation_graph_to_dict(g) for g in graphs]
    return out


def _set_path_value(root: dict[str, Any], path: str, value: Any) -> None:
    """Set dotted path on nested dicts, creating dict parents as needed."""
    parts = [p for p in str(path or "").split(".") if p]
    if not parts:
        raise HostChatError("brief patch set requires a non-empty path")
    cur: Any = root
    for part in parts[:-1]:
        nxt = cur.get(part) if isinstance(cur, dict) else None
        if not isinstance(nxt, dict):
            nxt = {}
            if not isinstance(cur, dict):
                raise HostChatError(f"Cannot set path through non-object: {path}")
            cur[part] = nxt
        cur = nxt
    if not isinstance(cur, dict):
        raise HostChatError(f"Cannot set leaf on non-object: {path}")
    cur[parts[-1]] = copy.deepcopy(value)


def _match_record(item: dict[str, Any], match: dict[str, Any], fields: tuple[str, ...]) -> bool:
    for field in fields:
        want = str(match.get(field) or "").strip().lower()
        if not want:
            continue
        have = str(item.get(field) or "").strip().lower()
        if have and have == want:
            return True
    return False


def _upsert_list_item(
    root: dict[str, Any],
    *,
    path: str,
    match: dict[str, Any],
    fields: dict[str, Any],
    match_fields: tuple[str, ...] = ("id", "name"),
) -> None:
    """Upsert one object inside a nested list (scenes / systems / ui_panels / …)."""
    parts = [p for p in str(path or "").split(".") if p]
    if not parts:
        raise HostChatError("upsert_list requires a non-empty path")
    parent: Any = root
    for part in parts[:-1]:
        nxt = parent.get(part) if isinstance(parent, dict) else None
        if not isinstance(nxt, dict):
            nxt = {}
            if not isinstance(parent, dict):
                raise HostChatError(f"Cannot upsert_list through non-object: {path}")
            parent[part] = nxt
        parent = nxt
    leaf = parts[-1]
    if not isinstance(parent, dict):
        raise HostChatError(f"Cannot upsert_list on non-object: {path}")
    items = parent.get(leaf)
    if not isinstance(items, list):
        items = []
    items = list(items)
    found = False
    for i, item in enumerate(items):
        if isinstance(item, dict) and _match_record(item, match, match_fields):
            merged = copy.deepcopy(item)
            merged.update(copy.deepcopy(fields))
            items[i] = merged
            found = True
            break
    if not found:
        row = copy.deepcopy(fields)
        for field in match_fields:
            if match.get(field) and field not in row:
                row[field] = match[field]
        items.append(row)
    parent[leaf] = items


def apply_brief_patches(
    draft: dict[str, Any] | None,
    patches: list[Any] | None,
) -> dict[str, Any]:
    """Apply surgical patches onto a brief draft (code-edit style, not full rewrite).

    Supported ops:
    - ``set``: ``{"op":"set","path":"project.session_goal","value":"..."}``
    - ``upsert_asset``: ``{"op":"upsert_asset","match":{"id":"rod"},"set":{...}}``
    - ``add_asset``: ``{"op":"add_asset","value":{...}}``
    - ``upsert_graph``: ``{"op":"upsert_graph","match":{"character_asset":"carp"},"set":{...}}``
    - ``upsert_list``: ``{"op":"upsert_list","path":"project.systems","match":{"id":"aquarium"},"set":{...}}``
      (also ``upsert_scene`` / ``upsert_system`` / ``upsert_ui_panel`` shorthand)
    """
    if not isinstance(draft, dict) or not draft:
        raise HostChatError("brief_patches require an existing draft_brief")
    if not isinstance(patches, list) or not patches:
        return copy.deepcopy(draft)

    out = copy.deepcopy(draft)
    for raw in patches:
        if not isinstance(raw, dict):
            continue
        op = str(raw.get("op") or "").strip().lower()
        if op == "set":
            _set_path_value(out, str(raw.get("path") or ""), raw.get("value"))
        elif op == "upsert_asset":
            match = raw.get("match") if isinstance(raw.get("match"), dict) else {}
            fields = raw.get("set") if isinstance(raw.get("set"), dict) else {}
            if not match or not fields:
                continue
            assets = out.get("assets") if isinstance(out.get("assets"), list) else []
            assets = list(assets)
            found = False
            for i, item in enumerate(assets):
                if isinstance(item, dict) and _match_record(item, match, ("id", "name")):
                    merged = copy.deepcopy(item)
                    merged.update(copy.deepcopy(fields))
                    assets[i] = merged
                    found = True
                    break
            if not found:
                row = copy.deepcopy(fields)
                for field in ("id", "name"):
                    if match.get(field) and field not in row:
                        row[field] = match[field]
                assets.append(row)
            out["assets"] = assets
        elif op == "add_asset":
            value = raw.get("value")
            if not isinstance(value, dict):
                continue
            assets = out.get("assets") if isinstance(out.get("assets"), list) else []
            assets = list(assets)
            assets.append(copy.deepcopy(value))
            out["assets"] = assets
        elif op == "upsert_graph":
            match = raw.get("match") if isinstance(raw.get("match"), dict) else {}
            fields = raw.get("set") if isinstance(raw.get("set"), dict) else {}
            if not match or not fields:
                continue
            graphs = (
                out.get("animation_graphs")
                if isinstance(out.get("animation_graphs"), list)
                else []
            )
            graphs = list(graphs)
            found = False
            for i, item in enumerate(graphs):
                if isinstance(item, dict) and _match_record(
                    item, match, ("character_asset", "id", "name")
                ):
                    merged = copy.deepcopy(item)
                    merged.update(copy.deepcopy(fields))
                    graphs[i] = merged
                    found = True
                    break
            if not found:
                row = copy.deepcopy(fields)
                for field in ("character_asset", "id", "name"):
                    if match.get(field) and field not in row:
                        row[field] = match[field]
                graphs.append(row)
            out["animation_graphs"] = graphs
        elif op in (
            "upsert_list",
            "upsert_scene",
            "upsert_system",
            "upsert_ui_panel",
        ):
            match = raw.get("match") if isinstance(raw.get("match"), dict) else {}
            fields = raw.get("set") if isinstance(raw.get("set"), dict) else {}
            if not match or not fields:
                continue
            path = str(raw.get("path") or "").strip()
            if not path:
                path = {
                    "upsert_scene": "project.scenes",
                    "upsert_system": "project.systems",
                    "upsert_ui_panel": "project.ui_panels",
                }.get(op, "")
            if not path:
                continue
            _upsert_list_item(out, path=path, match=match, fields=fields)
        else:
            continue
    return out


def _extract_brief_patches(parsed: dict[str, Any]) -> list[Any] | None:
    artifact = parsed.get("artifact")
    for container in (artifact if isinstance(artifact, dict) else None, parsed):
        if not isinstance(container, dict):
            continue
        for key in ("brief_patches", "draft_patches"):
            raw = container.get(key)
            if isinstance(raw, list) and raw:
                return raw
    return None


def _extract_closed_intent_gap_ids(parsed: dict[str, Any]) -> list[str]:
    """Gap ids the planner claims were closed this turn (host strips them from review)."""
    found: list[str] = []
    seen: set[str] = set()

    def _take(raw: Any) -> None:
        if not isinstance(raw, list):
            return
        for item in raw:
            gid = str(item or "").strip()
            if gid and gid not in seen:
                seen.add(gid)
                found.append(gid)

    artifact = parsed.get("artifact")
    for container in (artifact if isinstance(artifact, dict) else None, parsed):
        if not isinstance(container, dict):
            continue
        for key in (
            "closed_intent_gap_ids",
            "closed_intent_gaps",
            "closed_gaps",
        ):
            _take(container.get(key))
    return found


_CLOSED_GAP_ID_RE = re.compile(
    r"(?:关闭|拍板|关掉|closed?)\s*[`「\"']?([a-z][a-z0-9_]{2,})[`」\"']?",
    re.IGNORECASE,
)
_BACKTICK_GAP_ID_RE = re.compile(r"`([a-z][a-z0-9_]{2,})`")


def _infer_closed_intent_gap_ids(
    assistant_message: str,
    open_ids: list[str],
) -> list[str]:
    """Best-effort: if prose names an open gap id as closed, treat it as closed."""
    if not open_ids or not assistant_message:
        return []
    open_set = {gid.lower(): gid for gid in open_ids if gid}
    hit: list[str] = []
    seen: set[str] = set()
    for rx in (_CLOSED_GAP_ID_RE, _BACKTICK_GAP_ID_RE):
        for m in rx.finditer(assistant_message):
            key = m.group(1).lower()
            if key in open_set and key not in seen:
                seen.add(key)
                hit.append(open_set[key])
    return hit


_MAKEABILITY_CLOSED_NOTE = (
    "\n\n（宿主：已把你本轮拍板的意图缺口从审查列表移除；"
    "草稿已变，请再点一次「制作审查」确认 intent 为空后再导出。）"
)


def reconcile_makeability_after_draft_write(
    session: dict[str, Any],
    *,
    closed_ids: list[str] | None = None,
    assistant_message: str = "",
) -> tuple[list[str], str]:
    """After draft patches, drop closed intent_gaps so UI/LLM stop re-asking stale ones.

    Export still requires a fresh makeability run (fingerprint will not match).
    Returns (actually_closed_ids, possibly_amended assistant_message).
    """
    review = session.get("makeability_review")
    if not isinstance(review, dict) or not review:
        return [], assistant_message
    intent_raw = review.get("intent_gaps")
    if not isinstance(intent_raw, list) or not intent_raw:
        return [], assistant_message

    open_ids = [
        str(g.get("id") or "").strip()
        for g in intent_raw
        if isinstance(g, dict) and str(g.get("id") or "").strip()
    ]
    wanted = [str(x).strip() for x in (closed_ids or []) if str(x).strip()]
    if not wanted:
        wanted = _infer_closed_intent_gap_ids(assistant_message, open_ids)
    if not wanted:
        return [], assistant_message

    wanted_set = {w.lower() for w in wanted}
    kept: list[Any] = []
    closed: list[str] = []
    for gap in intent_raw:
        if not isinstance(gap, dict):
            kept.append(gap)
            continue
        gid = str(gap.get("id") or "").strip()
        if gid and gid.lower() in wanted_set:
            closed.append(gid)
            continue
        kept.append(gap)

    if not closed:
        return [], assistant_message

    review = copy.deepcopy(review)
    review["intent_gaps"] = kept
    # Force fingerprint mismatch until the next makeability run.
    review["draft_fingerprint"] = f"stale-after-close:{draft_fingerprint(session.get('draft_brief') if isinstance(session.get('draft_brief'), dict) else {})}"
    session["makeability_review"] = review
    session["ready_to_export"] = False

    msg = assistant_message
    if _MAKEABILITY_CLOSED_NOTE.strip() not in msg:
        msg = msg.rstrip() + _MAKEABILITY_CLOSED_NOTE
    return closed, msg


def _extract_draft(parsed: dict[str, Any]) -> dict[str, Any] | None:
    artifact = parsed.get("artifact")
    if isinstance(artifact, dict):
        draft = artifact.get("draft_brief")
        if isinstance(draft, dict):
            return draft
    draft = parsed.get("draft_brief")
    if isinstance(draft, dict):
        return draft
    return None


def _normalize_document(raw: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    body = str(raw.get("body") or "").strip()
    title = str(raw.get("title") or "").strip() or "未命名文档"
    if not body and not raw.get("title"):
        return None
    return {
        "title": title,
        "format": str(raw.get("format") or "markdown").strip() or "markdown",
        "body": body,
    }


def _extract_document(parsed: dict[str, Any]) -> dict[str, Any] | None:
    artifact = parsed.get("artifact")
    if isinstance(artifact, dict):
        if artifact.get("kind") == "document" or artifact.get("body"):
            doc = _normalize_document(
                {
                    "title": artifact.get("title"),
                    "format": artifact.get("format"),
                    "body": artifact.get("body"),
                }
            )
            if doc:
                return doc
        nested = artifact.get("draft_document")
        doc = _normalize_document(nested if isinstance(nested, dict) else None)
        if doc:
            return doc
    return _normalize_document(
        parsed.get("draft_document") if isinstance(parsed.get("draft_document"), dict) else None
    )


def _extract_gaps(parsed: dict[str, Any]) -> list[str]:
    raw = parsed.get("gaps")
    if not isinstance(raw, list):
        return []
    return [str(g).strip() for g in raw if str(g).strip()][:20]


def _call_llm(
    session: dict[str, Any],
    mode: str,
    config: dict[str, Any],
    *,
    instance_id: str | None = None,
) -> dict[str, Any]:
    system = _system_prompt(mode)
    user_text = json.dumps(_build_user_payload(session, mode), ensure_ascii=False, indent=2)

    raw: str | None = None
    backend = "host"
    try:
        from pi_runtime import (
            PiRuntimeError,
            resolve_brief_executor,
            run_pi_brief_turn_with_tools,
        )

        if resolve_brief_executor(config) == "pi":
            allow_export = mode == "commit_brief" and bool(session.get("ready_to_export"))
            try:
                sid = str(session.get("id") or "brief")
                # Persist mid-turn so export/status tools can read the session file.
                try:
                    save_session(session_path_for_id(sid), session)
                except (HostChatError, OSError):
                    pass
                raw = run_pi_brief_turn_with_tools(
                    system_prompt=system,
                    user_text=user_text,
                    session_id=sid,
                    config=config,
                    allow_export=allow_export,
                    timeout_sec=240.0,
                    instance_id=instance_id,
                )
                backend = "pi"
                session.pop("_brief_llm_pi_error", None)
            except PiRuntimeError as exc:
                # One Pi attempt only — fall back to Host (avoid double paid calls).
                session["_brief_llm_pi_error"] = str(exc)[:500]
                raw = None
                backend = "host"
    except ImportError:
        raw = None
        backend = "host"

    if raw is None:
        api = resolve_host_api_settings(config)
        if not api.get("api_key"):
            raise HostChatError(
                "Brief LLM unavailable: configure API key (OpenRouter/host) "
                "or embed Pi (`node scripts/prepare_embedded_pi.mjs`)."
            )
        try:
            raw = chat_text_completion(
                model=str(api["model"]),
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user_text},
                ],
                api_key=str(api["api_key"]),
                api_base=str(api["api_base"]),
                proxy=api.get("proxy"),
                timeout=180,
            )
            backend = "host"
        except PromptCraftError as exc:
            raise HostChatError(str(exc)) from exc

    session["_brief_llm_backend"] = backend
    parsed = _parse_llm_json(raw)
    note = str(parsed.get("notes_for_host") or "")
    if note.startswith("recovered") and isinstance(raw, str):
        try:
            dump = _CONV_DIR / "_last_llm_raw.txt"
            dump.parent.mkdir(parents=True, exist_ok=True)
            dump.write_text(raw[:200_000], encoding="utf-8")
        except OSError:
            pass
    return parsed


def _infer_choices_from_message(text: str, *, max_n: int = 6) -> list[str]:
    """If LLM forgot JSON choices, recover option lines from assistant prose."""
    line_re = re.compile(
        r"^(?:[-*•]|\d+[.)、]|[A-Da-d][.)、]|选项\s*[A-Da-d\d])\s*(.+)$"
    )
    found: list[str] = []
    for raw in (text or "").splitlines():
        line = raw.strip()
        if not line:
            continue
        m = line_re.match(line)
        if not m:
            continue
        opt = m.group(1).strip().strip("*").rstrip("。；;")
        if len(opt) < 2 or len(opt) > 80:
            continue
        if opt not in found:
            found.append(opt)
        if len(found) >= max_n:
            break
    return found if len(found) >= 2 else []


def _apply_parsed(session: dict[str, Any], parsed: dict[str, Any], mode: str) -> dict[str, Any]:
    assistant_message = str(parsed.get("assistant_message", "")).strip()
    if not assistant_message:
        # Prefer keeping the turn alive over hard-failing the GUI.
        note = str(parsed.get("notes_for_host") or "").strip()
        assistant_message = (
            "（模型没有返回可读回复，草稿未改动。请再发一句，或说「再整理一遍」。）"
            + (f"\n\n_{note}_" if note else "")
        )

    choices = parsed.get("choices") or []
    if not isinstance(choices, list):
        choices = []
    choices = [str(c).strip() for c in choices if str(c).strip()][:6]
    if not choices:
        # Recover A/B/1/2 style lines from prose so GUI can render chips
        choices = _infer_choices_from_message(assistant_message)

    intent = str(parsed.get("intent_hint") or "none").strip() or "none"
    ready = bool(parsed.get("ready_to_export"))
    gaps = _extract_gaps(parsed)
    incoming = _extract_draft(parsed)
    patches = _extract_brief_patches(parsed)
    incoming_doc = _extract_document(parsed)
    fp_before = _draft_fp(session)

    if mode == "chat":
        # Ignore model-claimed ready_to_export; real readiness is live-audited below.
        ready = False
        prefer_patches = bool(session.get("_autofix_prefer_patches"))
        # Prefer surgical patches when answering review gaps / small clarifications.
        # If patches are present, do NOT apply a possibly thinned full draft_brief.
        if patches:
            base = (
                session.get("draft_brief")
                if isinstance(session.get("draft_brief"), dict)
                else None
            )
            if base is None and incoming:
                base = incoming
            if base is None:
                assistant_message += "\n\n（收到定点补丁但还没有草稿，请先聊出一版 draft。）"
            else:
                try:
                    session["draft_brief"] = apply_brief_patches(base, patches)
                    invalidate_verified_ledger_for_patches(session, patches)
                    session["ready_to_export"] = False
                except HostChatError as exc:
                    assistant_message += f"\n\n（草稿补丁未应用：{exc}）"
        elif incoming:
            # Autofix: reject huge assets[] rewrites (models truncate mid-JSON).
            merge_incoming = incoming
            if prefer_patches:
                inc_assets = incoming.get("assets")
                base_draft = (
                    session.get("draft_brief")
                    if isinstance(session.get("draft_brief"), dict)
                    else None
                )
                base_n = (
                    len(base_draft.get("assets") or [])
                    if isinstance(base_draft, dict)
                    else 0
                )
                if isinstance(inc_assets, list) and len(inc_assets) > 30 and base_n > 30:
                    merge_incoming = {
                        k: v for k, v in incoming.items() if k != "assets"
                    }
                    assistant_message += (
                        "\n\n（自动修已忽略超大 assets[] 整表重写；"
                        "请改用 artifact.brief_patches。）"
                    )
            session["draft_brief"] = deep_merge_brief(
                session.get("draft_brief") if isinstance(session.get("draft_brief"), dict) else None,
                merge_incoming,
            )
        if incoming_doc:
            session["draft_document"] = incoming_doc
        session["mode"] = "chat"
        if intent == "commit_brief":
            session["pending_mode"] = "commit_brief"
        elif intent == "commit_doc":
            session["pending_mode"] = "commit_doc"
        else:
            session["pending_mode"] = None
    elif mode == "commit_doc":
        if incoming_doc is None:
            ready = False
            assistant_message += "\n\n（整理文档轮未返回正文，请再说要写入文档的要点。）"
        else:
            session["draft_document"] = incoming_doc
            if ready and not incoming_doc.get("body"):
                ready = False
                assistant_message += "\n\n（文档正文为空，我们继续补全。）"
        session["mode"] = "commit_doc"
        session["pending_mode"] = None
    else:
        if incoming is None:
            ready = False
            assistant_message += "\n\n（落实轮未返回 draft_brief，请再说明要冻结的玩法要点。）"
        else:
            merged = deep_merge_brief(
                session.get("draft_brief") if isinstance(session.get("draft_brief"), dict) else None,
                incoming,
            )
            draft = merged or incoming
            if ready:
                try:
                    draft = validate_brief_dict(draft)
                except (HostChatError, ValueError) as exc:
                    ready = False
                    assistant_message += f"\n\n（草案尚未完整：{exc}，我们继续补几项。）"
            session["draft_brief"] = draft
            session["mode"] = "commit_brief"
        if incoming_doc:
            session["draft_document"] = incoming_doc
        session["pending_mode"] = None

    fp_after = _draft_fp(session)
    draft_changed = bool(fp_after) and fp_after != fp_before
    if mode == "chat":
        if draft_changed:
            session.pop("_talk_without_write", None)
            closed_ids = _extract_closed_intent_gap_ids(parsed)
            # Single open gap + any successful patch while answering review → close it.
            review_before = session.get("makeability_review")
            if (
                not closed_ids
                and patches
                and isinstance(review_before, dict)
            ):
                intent_raw = review_before.get("intent_gaps")
                open_ids = [
                    str(g.get("id") or "").strip()
                    for g in (intent_raw if isinstance(intent_raw, list) else [])
                    if isinstance(g, dict) and str(g.get("id") or "").strip()
                ]
                if len(open_ids) == 1:
                    closed_ids = open_ids
                elif open_ids and re.search(
                    r"(拍板|关闭|关掉|写进(?:工作)?草稿|已同步)",
                    assistant_message,
                ):
                    closed_ids = open_ids
            _, assistant_message = reconcile_makeability_after_draft_write(
                session,
                closed_ids=closed_ids,
                assistant_message=assistant_message,
            )
        elif looks_like_draft_write_claim(assistant_message):
            session["_talk_without_write"] = True
            if _TALK_WITHOUT_WRITE_NOTE.strip() not in assistant_message:
                assistant_message = assistant_message.rstrip() + _TALK_WITHOUT_WRITE_NOTE
        else:
            # Keep prior nudge until a successful write; don't clear on pure Q&A.
            pass
    elif draft_changed:
        session.pop("_talk_without_write", None)
        if mode == "commit_brief":
            closed_ids = _extract_closed_intent_gap_ids(parsed)
            _, assistant_message = reconcile_makeability_after_draft_write(
                session,
                closed_ids=closed_ids,
                assistant_message=assistant_message,
            )

    # Prefer live audit of the merged draft over LLM-reported gaps (which go stale).
    live_gaps = _audit_draft_gaps(
        session.get("draft_brief") if isinstance(session.get("draft_brief"), dict) else None
    )
    if live_gaps:
        session["gaps"] = live_gaps
    elif gaps:
        session["gaps"] = gaps
    elif mode in ("chat", "commit_brief", "commit_doc"):
        session["gaps"] = []

    # Contract readiness is audit-driven. Chat must not permanently clear a green brief
    # just because the model omitted ready_to_export (GUI export button depends on this).
    draft_ok = (
        isinstance(session.get("draft_brief"), dict) and bool(session.get("draft_brief"))
    )
    if mode == "chat":
        ready = draft_ok and not live_gaps
    elif mode == "commit_brief":
        ready = bool(ready) and draft_ok and not live_gaps
    elif live_gaps:
        ready = False

    messages = list(session.get("messages") or [])
    messages.append({"role": "assistant", "content": assistant_message})
    session["messages"] = messages
    session["last_choices"] = choices
    session["intent_hint"] = intent
    session["ready_to_export"] = ready

    return {
        "assistant_message": assistant_message,
        "choices": choices,
        "mode": session.get("mode") or mode,
        "intent_hint": intent,
        "draft_brief": session.get("draft_brief"),
        "draft_document": session.get("draft_document"),
        "ready_to_export": ready,
        "gaps": session.get("gaps") or [],
        "message_count": len(messages),
        "session_id": session.get("id"),
        "compressed_count": int(session.get("compressed_count") or 0),
        "llm_backend": session.get("_brief_llm_backend"),
        "llm_pi_error": session.get("_brief_llm_pi_error"),
    }


def run_turn(
    session: dict[str, Any],
    *,
    user_message: str | None,
    config: dict[str, Any],
    instance_id: str | None = None,
    repo_root: Path | None = None,
    workspace: Path | None = None,
) -> dict[str, Any]:
    """Append user message, optionally compress, call host LLM (chat or commit)."""
    # Pull externally updated drafts (git pull) before the model sees session state.
    sync_session_draft_from_disk(
        session, repo_root=repo_root, workspace=workspace
    )
    messages: list[dict[str, Any]] = list(session.get("messages") or [])
    if user_message and user_message.strip():
        messages.append({"role": "user", "content": user_message.strip()})
    elif not messages:
        messages.append({"role": "user", "content": "你好，想先随便聊聊游戏想法。"})
    session["messages"] = messages

    maybe_compress_session(session, config)

    mode = resolve_mode(session, user_message)
    if mode == "commit_brief":
        parsed = _call_llm(session, "commit_brief", config, instance_id=instance_id)
        return _apply_parsed(session, parsed, "commit_brief")
    if mode == "commit_doc":
        parsed = _call_llm(session, "commit_doc", config, instance_id=instance_id)
        return _apply_parsed(session, parsed, "commit_doc")

    parsed = _call_llm(session, "chat", config, instance_id=instance_id)
    intent = str(parsed.get("intent_hint") or "none").strip()
    if intent in ("commit_brief", "commit_doc"):
        ack = str(parsed.get("assistant_message", "")).strip()
        incoming = _extract_draft(parsed)
        if incoming:
            session["draft_brief"] = deep_merge_brief(
                session.get("draft_brief") if isinstance(session.get("draft_brief"), dict) else None,
                incoming,
            )
        incoming_doc = _extract_document(parsed)
        if incoming_doc:
            session["draft_document"] = incoming_doc
        if ack:
            msgs = list(session.get("messages") or [])
            msgs.append({"role": "assistant", "content": ack})
            session["messages"] = msgs
        session["pending_mode"] = intent
        session["intent_hint"] = intent
        follow = "commit_brief" if intent == "commit_brief" else "commit_doc"
        parsed = _call_llm(session, follow, config, instance_id=instance_id)
        return _apply_parsed(session, parsed, follow)

    return _apply_parsed(session, parsed, "chat")


def export_brief(
    session: dict[str, Any],
    *,
    repo_root: Path | None = None,
    workspace: Path | None = None,
) -> dict[str, Any]:
    """Export validated draft; sync bound disk draft first (H1)."""
    sync_session_draft_from_disk(
        session, repo_root=repo_root, workspace=workspace
    )
    draft = session.get("draft_brief")
    if not isinstance(draft, dict) or not draft:
        raise HostChatError("No draft_brief in session. Chat about the game first, then 落实成 brief.")
    gaps = _audit_draft_gaps(draft)
    if gaps:
        session["gaps"] = gaps
        session["ready_to_export"] = False
        raise HostChatError(
            f"Brief 校验未通过（仍有 {len(gaps)} 条）。请先自动修或补齐后再导出。"
        )
    session["ready_to_export"] = True
    assert_makeability_exportable(session)
    return finalize_brief_export(draft, source="host-chat")


DEFAULT_AUTOFIX_MAX_ROUNDS = 5


def _clip_map_for_draft(draft: dict[str, Any] | None) -> dict[str, list[str]]:
    """character_asset → known Godot clip names (for autofix hints)."""
    if not isinstance(draft, dict):
        return {}
    try:
        assets_raw = draft.get("assets") or []
        assets = [AssetSpec.from_dict(item) for item in assets_raw if isinstance(item, dict)]
    except (ValueError, KeyError, TypeError):
        return {}

    out: dict[str, list[str]] = {}
    chars = set(characters_requiring_animation_graph(assets))
    # Also include any graph character even if not "required"
    for g in draft.get("animation_graphs") or []:
        if isinstance(g, dict) and g.get("character_asset"):
            chars.add(str(g["character_asset"]).strip())
    for char in sorted(chars):
        if not char:
            continue
        out[char] = sorted(character_clip_names(assets, char).keys())
    return out


def _asset_clip_lines(draft: dict[str, Any] | None) -> list[str]:
    """Human table: asset.name → Godot clip (what graphs must use)."""
    if not isinstance(draft, dict):
        return []
    lines: list[str] = []
    try:
        assets = [
            AssetSpec.from_dict(item)
            for item in (draft.get("assets") or [])
            if isinstance(item, dict)
        ]
    except (ValueError, KeyError, TypeError):
        return []
    for char in sorted(characters_requiring_animation_graph(assets)):
        clips = character_clip_names(assets, char)
        lines.append(f"角色 {char}:")
        for clip, spec in sorted(clips.items(), key=lambda kv: kv[0]):
            lines.append(f"  - assets.name={spec.name!r} → clip={clip!r}")
    return lines


def build_autofix_user_message(gaps: list[str], draft: dict[str, Any] | None) -> str:
    """Structured prompt so the model reads validator gaps without the user pasting them."""
    gap_blob = "\n".join(gaps)
    needs_graph = "animation_graph" in gap_blob or "clip" in gap_blob.lower()
    needs_hud = "hud" in gap_blob or "ui_element" in gap_blob
    needs_type = "illegal type" in gap_blob or "Unknown asset type" in gap_blob
    allowed_types = ", ".join(t.value for t in AssetType)

    lines = [
        "【自动修 brief】下面是宿主对当前 draft_brief 的校验错误。",
        "必须用 artifact.brief_patches 做定点修改（upsert_asset / set / upsert_graph）。",
        "禁止输出完整 assets[] 整表重写（会截断失败）。ready_to_export 必须为 false。",
        "",
        "硬约束：",
        f"- assets[].type 只能是：{allowed_types}。"
        "常见别名：animation/anim → character_pose；item/prop → texture（有 items[] 则 icon_kit）。",
        "- Foundry brief 没有 states[]；禁止输出 states / states[].id / states[].clip。",
    ]
    if needs_type:
        lines.append(
            "- 改 type 时用 "
            '{"op":"upsert_asset","match":{"name":"<资产名>"},"set":{"type":"character_pose"}}；'
            "同类错误可多条 patch，不要重写全部资产。"
        )
    if needs_graph:
        lines.extend(
            [
                "- animation_graphs 的 from/to/then/default_clip 只能用下面「资产→clip」表里的 clip 列，"
                "不要用资产全名、不要用中文状态 id、不要自创 clip。",
                "- 例：资产 球员_普通_跑动 的 clip 是「跑动」，transition 必须写 to:\"跑动\" "
                "而不是 \"球员_普通_跑动\"。",
                "- one-shot（animation_loop:false）作为 to 时必须有 then（通常指向 idle）。",
                "- 缺动画就用 add_asset / upsert_asset 补视频资产；有资产但图写错名就改 transitions。",
            ]
        )
    if needs_hud:
        lines.append(
            "- 每个 usage=ui_element 必须在 project.hud[] 有一条 "
            '{"asset":"<同名>","anchor":"top_left|…","description":"…"}；'
            "用 brief_patches 的 set path=project.hud，不能只口头说改了。"
        )
    lines.append("")
    lines.append("校验错误：")
    for i, g in enumerate(gaps, 1):
        lines.append(f"{i}. {g}")
    if needs_graph:
        asset_lines = _asset_clip_lines(draft)
        if asset_lines:
            lines.append("")
            lines.append("资产 → Godot clip（from/to/then/default_clip 只能用 clip 列）：")
            lines.extend(asset_lines)
        clip_map = _clip_map_for_draft(draft)
        if clip_map:
            lines.append("")
            lines.append("各角色合法 clip 集合：")
            for char, clips in clip_map.items():
                lines.append(f"- {char}: {', '.join(clips) if clips else '（无）'}")
    lines.append("")
    lines.append("请只返回 brief_patches + 简短说明；不要粘贴完整 draft_brief.assets。")
    return "\n".join(lines)


def _apply_code_autofix(session: dict[str, Any]) -> tuple[list[str], list[str], list[str]]:
    """Deterministic graph repair. Returns (gaps_before, gaps_after, notes)."""
    draft = session.get("draft_brief")
    if not isinstance(draft, dict) or not draft:
        return [], [], []
    gaps_before = _audit_draft_gaps(draft)
    fixed, notes = apply_deterministic_brief_fixes(draft)
    session["draft_brief"] = fixed
    gaps_after = _audit_draft_gaps(fixed)
    session["gaps"] = gaps_after
    return gaps_before, gaps_after, notes


def _autofix_success_payload(
    session: dict[str, Any],
    *,
    rounds_run: int,
    max_rounds: int,
    rounds: list[dict[str, Any]],
    assistant_message: str | None = None,
) -> dict[str, Any]:
    session["ready_to_export"] = True
    try:
        session["draft_brief"] = validate_brief_dict(session["draft_brief"])
    except (HostChatError, ValueError):
        session["ready_to_export"] = False
    out: dict[str, Any] = {
        "ok": True,
        "reason": "contract_complete",
        "rounds_run": rounds_run,
        "max_rounds": max_rounds,
        "gaps": [],
        "rounds": rounds,
        "draft_brief": session.get("draft_brief"),
        "ready_to_export": bool(session.get("ready_to_export")),
        "session_id": session.get("id"),
        "message_count": len(session.get("messages") or []),
    }
    if assistant_message:
        out["assistant_message"] = assistant_message
    return out


def run_autofix(
    session: dict[str, Any],
    *,
    config: dict[str, Any],
    max_rounds: int = DEFAULT_AUTOFIX_MAX_ROUNDS,
) -> dict[str, Any]:
    """Loop: deterministic graph fix → audit → LLM only if still broken."""
    if max_rounds < 1:
        raise HostChatError("max_rounds must be >= 1")
    draft = session.get("draft_brief")
    if not isinstance(draft, dict) or not draft:
        raise HostChatError("No draft_brief yet. Chat about the game first, then run autofix.")

    rounds: list[dict[str, Any]] = []
    prev_sig: tuple[str, ...] | None = None
    stuck_hits = 0

    # Round 0: code repairs clip mismatches (LLM often can't map 跑动 ↔ asset names).
    gaps_b, gaps_a, notes = _apply_code_autofix(session)
    if notes or gaps_a != gaps_b:
        rounds.append(
            {
                "round": 0,
                "kind": "deterministic",
                "gaps_before": gaps_b,
                "gaps_after": gaps_a,
                "notes": notes,
                "assistant_message": (
                    "代码已自动修补 brief（asset type / animation_graphs / project.hud 等）"
                    + (f"：{'; '.join(notes[:6])}" if notes else "。")
                ),
                "gap_count_before": len(gaps_b),
                "gap_count_after": len(gaps_a),
            }
        )
    if not gaps_a:
        return _autofix_success_payload(
            session,
            rounds_run=0,
            max_rounds=max_rounds,
            rounds=rounds,
            assistant_message=rounds[-1]["assistant_message"] if rounds else "草稿已通过校验。",
        )

    for round_i in range(1, max_rounds + 1):
        # Re-run code fix each round (LLM may reintroduce remappable wrong names).
        gaps_b, gaps_a, notes = _apply_code_autofix(session)
        if notes and gaps_a != gaps_b:
            rounds.append(
                {
                    "round": round_i,
                    "kind": "deterministic",
                    "gaps_before": gaps_b,
                    "gaps_after": gaps_a,
                    "notes": notes,
                    "assistant_message": "代码再次对齐 clip：" + "; ".join(notes[:8]),
                    "gap_count_before": len(gaps_b),
                    "gap_count_after": len(gaps_a),
                }
            )
        gaps = gaps_a
        session["gaps"] = gaps
        if not gaps:
            return _autofix_success_payload(
                session,
                rounds_run=round_i,
                max_rounds=max_rounds,
                rounds=rounds,
                assistant_message="校验已通过（代码修复）。",
            )

        sig = tuple(gaps)
        if sig == prev_sig:
            stuck_hits += 1
            if stuck_hits >= 2:
                return {
                    "ok": False,
                    "reason": "stuck",
                    "rounds_run": round_i - 1,
                    "max_rounds": max_rounds,
                    "gaps": gaps,
                    "rounds": rounds,
                    "draft_brief": session.get("draft_brief"),
                    "ready_to_export": False,
                    "session_id": session.get("id"),
                    "message_count": len(session.get("messages") or []),
                    "assistant_message": (
                        f"自动修 brief 连续 {stuck_hits} 轮错误未变化，已停止。"
                        "请人工改设定，或提高上限后再试。"
                    ),
                }
        else:
            stuck_hits = 0
        prev_sig = sig

        user_msg = build_autofix_user_message(
            gaps,
            session.get("draft_brief") if isinstance(session.get("draft_brief"), dict) else None,
        )
        session["_autofix_prefer_patches"] = True
        try:
            turn = run_turn(session, user_message=user_msg, config=config)
        finally:
            session.pop("_autofix_prefer_patches", None)
        # Mechanical aliases again — LLM may reintroduce animation/item.
        _, gaps_after, _ = _apply_code_autofix(session)
        session["gaps"] = gaps_after
        rounds.append(
            {
                "round": round_i,
                "kind": "llm",
                "gaps_before": gaps,
                "gaps_after": gaps_after,
                "assistant_message": turn.get("assistant_message"),
                "gap_count_before": len(gaps),
                "gap_count_after": len(gaps_after),
            }
        )
        if not gaps_after:
            return _autofix_success_payload(
                session,
                rounds_run=round_i,
                max_rounds=max_rounds,
                rounds=rounds,
                assistant_message=turn.get("assistant_message"),
            )

    gaps = _audit_draft_gaps(
        session.get("draft_brief") if isinstance(session.get("draft_brief"), dict) else None
    )
    session["gaps"] = gaps
    return {
        "ok": False,
        "reason": "max_rounds",
        "rounds_run": max_rounds,
        "max_rounds": max_rounds,
        "gaps": gaps,
        "rounds": rounds,
        "draft_brief": session.get("draft_brief"),
        "ready_to_export": False,
        "session_id": session.get("id"),
        "message_count": len(session.get("messages") or []),
        "assistant_message": (
            f"已跑满 {max_rounds} 轮自动修 brief，仍有 {len(gaps)} 条校验错误。"
            "可再点一次或提高 --max-rounds。"
        ),
    }


def _audit_draft_gaps(draft: dict[str, Any] | None) -> list[str]:
    """Live gaps from current draft — authoritative for status / after each merge."""
    if not isinstance(draft, dict) or not draft:
        return []
    assets, errors = parse_assets_for_audit(draft.get("assets") or [])
    try:
        project = ProjectContext.from_dict(draft.get("project") or {})
        graphs = parse_animation_graphs(draft)
    except (ValueError, KeyError, TypeError) as exc:
        errors.append(str(exc))
        return errors
    if not assets and errors:
        # Still surface project-level issues when every asset failed to parse.
        try:
            errors.extend(
                audit_brief_for_export(project, [], animation_graphs=graphs)
            )
        except (ValueError, KeyError, TypeError) as exc:
            errors.append(str(exc))
        return errors
    try:
        errors.extend(
            audit_brief_for_export(project, assets, animation_graphs=graphs)
        )
    except (ValueError, KeyError, TypeError) as exc:
        errors.append(str(exc))
    return errors


def session_status(session: dict[str, Any]) -> dict[str, Any]:
    draft = session.get("draft_brief") if isinstance(session.get("draft_brief"), dict) else {}
    assets_raw = (draft or {}).get("assets") or []
    project_raw = (draft or {}).get("project") or {}
    # Always re-audit the current draft. Stale session["gaps"] from an older LLM
    # turn must not keep showing after the user already fixed the brief.
    gaps = _audit_draft_gaps(draft if draft else None)
    session["gaps"] = gaps

    genre = project_raw.get("genre") if isinstance(project_raw, dict) else None
    gameplay = project_raw.get("gameplay_loop") if isinstance(project_raw, dict) else None
    asset_summaries: list[dict[str, str]] = []
    if isinstance(assets_raw, list):
        for item in assets_raw:
            if not isinstance(item, dict):
                continue
            name = str(item.get("name") or "").strip()
            if not name:
                continue
            asset_summaries.append(
                {
                    "name": name,
                    "type": str(item.get("type") or ""),
                    "usage": str(item.get("usage") or ""),
                }
            )

    doc = session.get("draft_document") if isinstance(session.get("draft_document"), dict) else None
    doc_title = str((doc or {}).get("title") or "") if doc else ""

    review = session.get("makeability_review")
    has_review = isinstance(review, dict) and bool(review)
    intent_count = 0
    detail_count = 0
    makeability_fingerprint_match = False
    if has_review:
        intent_raw = review.get("intent_gaps")
        detail_raw = review.get("detail_gaps")
        detail_count = len(detail_raw) if isinstance(detail_raw, list) else 0
        if draft:
            makeability_fingerprint_match = (
                str(review.get("draft_fingerprint") or "") == draft_fingerprint(draft)
            )
        # Only count intent gaps against a fresh review; stale results must not look "open".
        if makeability_fingerprint_match:
            intent_count = len(intent_raw) if isinstance(intent_raw, list) else 0
        else:
            intent_count = 0

    contract_complete = bool(draft) and not gaps
    session["ready_to_export"] = _compute_ready_to_export(session) if contract_complete else False

    return {
        "id": session.get("id"),
        "exists": True,
        "mode": session.get("mode") or "chat",
        "intent_hint": session.get("intent_hint") or "none",
        "ready_to_export": bool(session.get("ready_to_export")),
        "llm_backend": session.get("_brief_llm_backend") or None,
        "message_count": len(session.get("messages") or []),
        "title": (project_raw.get("title") if isinstance(project_raw, dict) else None) or "",
        "genre": genre or "",
        "gameplay_loop": gameplay or "",
        "asset_count": len(assets_raw) if isinstance(assets_raw, list) else 0,
        "assets": asset_summaries,
        "draft_brief": draft or None,
        "draft_document": doc,
        "document_title": doc_title,
        "has_document": bool(doc and (doc.get("body") or doc.get("title"))),
        "last_choices": session.get("last_choices") or [],
        "gaps": gaps,
        "contract_complete": contract_complete,
        "has_summary": bool(str(session.get("summary") or "").strip()),
        "compressed_count": int(session.get("compressed_count") or 0),
        "bound_brief_rel": session.get("bound_brief_rel") or None,
        "project_slug": session.get("project_slug") or None,
        "has_review": has_review,
        "intent_count": intent_count,
        "detail_count": detail_count,
        "makeability_fingerprint_match": makeability_fingerprint_match,
    }
