"""Persistent makeability decision ledger — stable keys, suppress repeat intent gaps."""

from __future__ import annotations

import copy
import json
import re
from datetime import datetime, timezone
from typing import Any, Callable


DECISION_STATUSES = frozenset({"pending", "applied", "verified", "repair_failed"})
MAX_AUTO_REPAIR_ATTEMPTS = 2
OCCURRENCE_RELATIONS = frozenset({"canonical", "duplicate", "conflict"})


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def resolve_decision_key(gap: dict[str, Any]) -> str:
    key = str(gap.get("decision_key") or "").strip()
    if key:
        return key
    gid = str(gap.get("id") or "").strip()
    if gid:
        return f"gap.{gid}"
    return ""


def ensure_decision_ledger(session: dict[str, Any]) -> list[dict[str, Any]]:
    raw = session.get("decision_ledger")
    if not isinstance(raw, list):
        session["decision_ledger"] = []
        return session["decision_ledger"]
    return raw


def _json_safe(value: Any) -> Any:
    try:
        json.dumps(value, ensure_ascii=False)
        return value
    except (TypeError, ValueError):
        return str(value)


def normalize_path_list(raw: Any) -> list[str]:
    if not isinstance(raw, list):
        return []
    seen: set[str] = set()
    out: list[str] = []
    for p in raw:
        text = str(p).strip()
        if not text:
            continue
        key = text.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(text)
    return out


def validate_occurrences_strict(raw: Any, *, field: str = "occurrences") -> None:
    """Fail closed: every occurrence object must carry a known relation."""
    if raw is None:
        return
    if not isinstance(raw, list):
        raise ValueError(f"{field} must be an array.")
    for index, item in enumerate(raw):
        if not isinstance(item, dict):
            raise ValueError(f"{field}[{index}] must be an object.")
        path = str(item.get("path") or "").strip()
        if not path:
            raise ValueError(f"{field}[{index}] missing non-empty path.")
        relation = str(item.get("relation") or "").strip().lower()
        if relation not in OCCURRENCE_RELATIONS:
            raise ValueError(
                f"{field}[{index}] invalid relation {item.get('relation')!r}; "
                f"expected one of {sorted(OCCURRENCE_RELATIONS)}."
            )


def normalize_occurrences(raw: Any) -> list[dict[str, Any]]:
    if not isinstance(raw, list):
        return []
    out: list[dict[str, Any]] = []
    seen_paths: set[str] = set()
    for item in raw:
        if not isinstance(item, dict):
            continue
        path = str(item.get("path") or "").strip()
        if not path:
            continue
        path_key = path.lower()
        if path_key in seen_paths:
            continue
        relation = str(item.get("relation") or "").strip().lower()
        if relation not in OCCURRENCE_RELATIONS:
            continue
        row: dict[str, Any] = {"path": path, "relation": relation}
        summary = str(item.get("current_summary") or "").strip()
        if summary:
            row["current_summary"] = summary
        out.append(row)
        seen_paths.add(path_key)
    return out


def normalize_write_paths(raw: Any) -> list[str]:
    return normalize_path_list(raw)


def required_write_paths_from_gap(gap: dict[str, Any]) -> list[str]:
    """Paths the Verifier must confirm.

    Prefer canonical ``target_paths`` so multi-location ``write_paths`` are
    best-effort sync (Closer still gets full write_paths in the prompt), not a
    hard gate that floods repair_failed.
    """
    tp = normalize_path_list(gap.get("target_paths"))
    if tp:
        return tp
    return normalize_write_paths(gap.get("write_paths"))


def sanitize_intent_gap(gap: dict[str, Any]) -> dict[str, Any]:
    g = copy.deepcopy(gap)
    occurrences = normalize_occurrences(g.get("occurrences"))
    if occurrences:
        g["occurrences"] = occurrences
    else:
        g.pop("occurrences", None)
    write_paths = normalize_write_paths(g.get("write_paths"))
    if write_paths:
        g["write_paths"] = write_paths
    elif "write_paths" in g:
        g.pop("write_paths", None)
    tp = normalize_path_list(g.get("target_paths"))
    if tp:
        g["target_paths"] = tp
    elif "target_paths" in g:
        g.pop("target_paths", None)
    if not g.get("decision_key"):
        g["decision_key"] = resolve_decision_key(g)
    return g


def _gap_snapshot(gap: dict[str, Any]) -> dict[str, Any]:
    g = sanitize_intent_gap(gap)
    snap = {
        "id": str(g.get("id") or "").strip(),
        "decision_key": resolve_decision_key(g),
        "question": str(g.get("question") or "").strip(),
        "why_blocking": str(g.get("why_blocking") or "").strip(),
    }
    tp = g.get("target_paths")
    if isinstance(tp, list) and tp:
        snap["target_paths"] = list(tp)
    occ = g.get("occurrences")
    if isinstance(occ, list) and occ:
        snap["occurrences"] = copy.deepcopy(occ)
    wp = g.get("write_paths")
    if isinstance(wp, list) and wp:
        snap["write_paths"] = list(wp)
    choices = g.get("choices")
    if isinstance(choices, list):
        snap["choices"] = [str(c).strip() for c in choices if str(c).strip()]
    return snap


def _answer_text(row: dict[str, str]) -> str:
    parts: list[str] = []
    choice = str(row.get("choice") or "").strip()
    note = str(row.get("note") or "").strip()
    if choice:
        parts.append(choice)
    if note:
        parts.append(note)
    return " · ".join(parts)


def ledger_index_by_key(session: dict[str, Any]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for entry in ensure_decision_ledger(session):
        if not isinstance(entry, dict):
            continue
        key = str(entry.get("decision_key") or "").strip()
        if key:
            out[key] = entry
    return out


def verified_decision_keys(session: dict[str, Any]) -> set[str]:
    keys: set[str] = set()
    for entry in ensure_decision_ledger(session):
        if not isinstance(entry, dict):
            continue
        if str(entry.get("status") or "") == "verified":
            key = str(entry.get("decision_key") or "").strip()
            if key:
                keys.add(key)
    return keys


def _user_already_answered_keys(session: dict[str, Any]) -> set[str]:
    """Decision keys with a saved user answer — must not re-ask as intent."""
    keys: set[str] = set()
    for entry in ensure_decision_ledger(session):
        if not isinstance(entry, dict):
            continue
        status = str(entry.get("status") or "")
        if status in {"pending", "applied", "verified", "repair_failed"}:
            key = str(entry.get("decision_key") or "").strip()
            if key and str(entry.get("answer_text") or "").strip():
                keys.add(key)
    return keys


def record_gap_answers(
    session: dict[str, Any],
    answers: list[dict[str, str]],
    gaps_by_id: dict[str, dict[str, Any]],
) -> list[str]:
    """Persist user answers before closer / verification. Returns decision_keys touched."""
    ledger = ensure_decision_ledger(session)
    by_key = ledger_index_by_key(session)
    touched: list[str] = []
    now = _utc_now()
    for row in answers:
        gap_id = str(row.get("gap_id") or "").strip()
        gap = gaps_by_id.get(gap_id)
        if not isinstance(gap, dict):
            continue
        dkey = resolve_decision_key(gap)
        if not dkey:
            continue
        text = _answer_text(row)
        entry = by_key.get(dkey)
        if entry is None:
            entry = {
                "decision_key": dkey,
                "gap_id": gap_id,
                "gap_snapshot": _gap_snapshot(gap),
                "answer_text": text,
                "status": "pending",
                "evidence_paths": [],
                "updated_at": now,
            }
            ledger.append(entry)
            by_key[dkey] = entry
        else:
            entry["gap_id"] = gap_id
            entry["gap_snapshot"] = _gap_snapshot(gap)
            if text:
                entry["answer_text"] = text
            elif not str(entry.get("answer_text") or "").strip():
                entry["answer_text"] = text
            entry["status"] = "pending"
            entry["updated_at"] = now
        touched.append(dkey)
    return touched


def update_ledger_status(
    session: dict[str, Any],
    decision_key: str,
    *,
    status: str,
    evidence_paths: list[str] | None = None,
    gap_id: str | None = None,
    verified_draft_fingerprint: str | None = None,
) -> None:
    if status not in DECISION_STATUSES:
        return
    by_key = ledger_index_by_key(session)
    entry = by_key.get(decision_key)
    if entry is None:
        return
    entry["status"] = status
    entry["updated_at"] = _utc_now()
    if gap_id:
        entry["gap_id"] = gap_id
    if evidence_paths is not None:
        entry["evidence_paths"] = [_json_safe(p) for p in evidence_paths if str(p).strip()]
    if verified_draft_fingerprint is not None:
        entry["verified_draft_fingerprint"] = str(verified_draft_fingerprint).strip()
    elif status == "repair_failed":
        entry.pop("verified_draft_fingerprint", None)


def mark_keys_repair_failed(session: dict[str, Any], decision_keys: list[str]) -> None:
    for key in decision_keys:
        update_ledger_status(session, key, status="repair_failed")


def normalize_decision_checks(raw: Any) -> list[dict[str, Any]]:
    if not isinstance(raw, list):
        return []
    out: list[dict[str, Any]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        status = str(item.get("status") or "").strip().lower()
        if status not in {"satisfied", "missing", "conflict"}:
            continue
        dkey = str(item.get("decision_key") or "").strip()
        if not dkey:
            continue
        row: dict[str, Any] = {
            "decision_key": dkey,
            "status": status,
        }
        gid = str(item.get("gap_id") or "").strip()
        if gid:
            row["gap_id"] = gid
        ep = item.get("evidence_paths")
        if isinstance(ep, list):
            row["evidence_paths"] = [str(p).strip() for p in ep if str(p).strip()]
        up = item.get("unresolved_paths")
        if isinstance(up, list):
            row["unresolved_paths"] = [str(p).strip() for p in up if str(p).strip()]
        out.append(row)
    return out


def effective_decision_check_status(
    check: dict[str, Any],
    required_write_paths: list[str] | None,
) -> str:
    """Deterministic satisfaction: prose status alone is not enough."""
    status = str(check.get("status") or "").strip().lower()
    if status != "satisfied":
        return status
    unresolved = check.get("unresolved_paths")
    if isinstance(unresolved, list) and any(str(p).strip() for p in unresolved):
        return "missing"
    required = normalize_target_paths(required_write_paths or [])
    if not required:
        return "satisfied"
    evidence = normalize_target_paths(check.get("evidence_paths"))
    if not set(required).issubset(set(evidence)):
        return "missing"
    return "satisfied"


def required_paths_by_key_from_ledger(session: dict[str, Any]) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for entry in ensure_decision_ledger(session):
        if not isinstance(entry, dict):
            continue
        dkey = str(entry.get("decision_key") or "").strip()
        snap = entry.get("gap_snapshot")
        if not dkey or not isinstance(snap, dict):
            continue
        paths = required_write_paths_from_gap(snap)
        if paths:
            out[dkey] = paths
    return out


def ledger_required_path_signatures(session: dict[str, Any]) -> dict[str, tuple[str, ...]]:
    return {
        dkey: normalize_target_paths(paths)
        for dkey, paths in required_paths_by_key_from_ledger(session).items()
        if normalize_target_paths(paths)
    }


def required_paths_by_key_from_gaps(
    gaps_by_id: dict[str, dict[str, Any]],
    *,
    session: dict[str, Any] | None = None,
) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    ledger = ledger_index_by_key(session) if session is not None else {}
    for gap in gaps_by_id.values():
        if not isinstance(gap, dict):
            continue
        dkey = resolve_decision_key(gap)
        if not dkey:
            continue
        paths = required_write_paths_from_gap(gap)
        if not paths and dkey in ledger:
            snap = ledger[dkey].get("gap_snapshot")
            if isinstance(snap, dict):
                paths = required_write_paths_from_gap(snap)
        if paths:
            out[dkey] = paths
    return out


def apply_decision_checks_to_ledger(
    session: dict[str, Any],
    checks: list[dict[str, Any]],
    *,
    gap_id_for_key: dict[str, str] | None = None,
) -> tuple[list[str], list[str]]:
    """Returns (verified_gap_ids, repair_failed_gap_ids)."""
    verified: list[str] = []
    failed: list[str] = []
    gap_map = gap_id_for_key or {}
    for check in checks:
        dkey = str(check.get("decision_key") or "").strip()
        if not dkey:
            continue
        status = str(check.get("status") or "").lower()
        gid = str(check.get("gap_id") or gap_map.get(dkey) or "").strip()
        evidence = check.get("evidence_paths")
        ep_list = evidence if isinstance(evidence, list) else []
        if status == "satisfied":
            update_ledger_status(
                session,
                dkey,
                status="verified",
                evidence_paths=[str(p) for p in ep_list],
                gap_id=gid or None,
            )
            if gid:
                verified.append(gid)
        elif status in {"missing", "conflict"}:
            update_ledger_status(
                session,
                dkey,
                status="repair_failed",
                evidence_paths=[str(p) for p in ep_list],
                gap_id=gid or None,
            )
            if gid:
                failed.append(gid)
    return verified, failed


def suppress_intent_gaps_by_ledger(
    session: dict[str, Any],
    intent_gaps: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Drop intent gaps whose decision_key is verified or already answered."""
    verified = verified_decision_keys(session)
    answered = _user_already_answered_keys(session)
    skip = verified | answered
    out: list[dict[str, Any]] = []
    for gap in intent_gaps:
        if not isinstance(gap, dict):
            continue
        g = copy.deepcopy(gap)
        if not g.get("decision_key"):
            g["decision_key"] = resolve_decision_key(g)
        dkey = str(g.get("decision_key") or "").strip()
        if dkey and dkey in skip:
            continue
        out.append(g)
    return out


def filter_intent_gaps_for_display(
    session: dict[str, Any],
    intent_gaps: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """GUI / cards: hide gaps user already answered (incl. repair_failed)."""
    return suppress_intent_gaps_by_ledger(session, intent_gaps)


def enrich_intent_gaps(intent_gaps: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for gap in intent_gaps:
        if not isinstance(gap, dict):
            continue
        out.append(sanitize_intent_gap(gap))
    return out


def merge_critic_decision_checks(
    session: dict[str, Any],
    checks: list[dict[str, Any]],
    *,
    current_draft_fingerprint: str | None = None,
) -> None:
    """Promote ledger entries when critic confirms satisfied; downgrade on conflict."""
    required_by_key = required_paths_by_key_from_ledger(session)
    for check in checks:
        dkey = str(check.get("decision_key") or "").strip()
        if not dkey:
            continue
        by_key = ledger_index_by_key(session)
        entry = by_key.get(dkey)
        if entry is None:
            continue
        required = required_by_key.get(dkey)
        effective = effective_decision_check_status(check, required)
        if effective == "satisfied":
            ep = check.get("evidence_paths")
            update_ledger_status(
                session,
                dkey,
                status="verified",
                evidence_paths=ep if isinstance(ep, list) else None,
                verified_draft_fingerprint=current_draft_fingerprint,
            )
        elif effective in {"missing", "conflict"}:
            update_ledger_status(session, dkey, status="repair_failed")


def remove_verified_gaps_from_review(
    session: dict[str, Any],
    verified_gap_ids: list[str],
) -> None:
    review = session.get("makeability_review")
    if not isinstance(review, dict):
        return
    intent_raw = review.get("intent_gaps")
    if not isinstance(intent_raw, list):
        return
    wanted = {str(x).strip().lower() for x in verified_gap_ids if str(x).strip()}
    if not wanted:
        return
    kept: list[Any] = []
    for gap in intent_raw:
        if not isinstance(gap, dict):
            kept.append(gap)
            continue
        gid = str(gap.get("id") or "").strip()
        if gid and gid.lower() in wanted:
            continue
        kept.append(gap)
    review = copy.deepcopy(review)
    review["intent_gaps"] = kept
    if verified_gap_ids:
        review["draft_fingerprint"] = (
            f"stale-after-close:{review.get('draft_fingerprint') or 'unknown'}"
        )
    session["makeability_review"] = review
    session["ready_to_export"] = False


def ledger_for_prompt(session: dict[str, Any]) -> list[dict[str, Any]]:
    """JSON-safe ledger slice for LLM payloads."""
    rows: list[dict[str, Any]] = []
    for entry in ensure_decision_ledger(session):
        if not isinstance(entry, dict):
            continue
        rows.append(
            {
                "decision_key": str(entry.get("decision_key") or ""),
                "gap_id": str(entry.get("gap_id") or ""),
                "answer_text": str(entry.get("answer_text") or ""),
                "status": str(entry.get("status") or ""),
                "evidence_paths": entry.get("evidence_paths")
                if isinstance(entry.get("evidence_paths"), list)
                else [],
                "updated_at": str(entry.get("updated_at") or ""),
            }
        )
    return rows


def infer_gap_ids_from_checks(
    checks: list[dict[str, Any]],
    gaps_by_id: dict[str, dict[str, Any]],
) -> dict[str, str]:
    """Map decision_key -> gap_id from checks or open gaps."""
    out: dict[str, str] = {}
    id_by_key = {
        resolve_decision_key(g): str(g.get("id") or "").strip()
        for g in gaps_by_id.values()
        if isinstance(g, dict)
    }
    for check in checks:
        dkey = str(check.get("decision_key") or "").strip()
        gid = str(check.get("gap_id") or "").strip()
        if dkey and gid:
            out[dkey] = gid
        elif dkey and dkey in id_by_key:
            out[dkey] = id_by_key[dkey]
    return out


_PATCH_SYSTEM_ID_RE = re.compile(r'systems\[id=([^\]]+)\]|"id"\s*:\s*"([^"]+)"', re.I)


def _patch_touches_gap(patches: list[dict[str, Any]], gap: dict[str, Any]) -> bool:
    gid = str(gap.get("id") or "").strip().lower()
    dkey = resolve_decision_key(gap).lower()
    for patch in patches:
        if not isinstance(patch, dict):
            continue
        op = str(patch.get("op") or "").lower()
        if op == "upsert_system":
            match = patch.get("match")
            if isinstance(match, dict):
                mid = str(match.get("id") or "").strip().lower()
                if mid and (mid in gid or mid in dkey):
                    return True
        blob = json.dumps(patch, ensure_ascii=False).lower()
        if gid and gid in blob:
            return True
    return False


def normalize_target_paths(raw: Any) -> tuple[str, ...]:
    if not isinstance(raw, list):
        return tuple()
    return tuple(sorted({str(p).strip().lower() for p in raw if str(p).strip()}))


def ledger_unique_path_keys(session: dict[str, Any]) -> dict[tuple[str, ...], str]:
    """Normalized write_paths (else target_paths) -> canonical key when unique in ledger."""
    buckets: dict[tuple[str, ...], set[str]] = {}
    for entry in ensure_decision_ledger(session):
        if not isinstance(entry, dict):
            continue
        snap = entry.get("gap_snapshot")
        if not isinstance(snap, dict):
            continue
        sig = normalize_target_paths(snap.get("write_paths")) or normalize_target_paths(
            snap.get("target_paths")
        )
        if not sig:
            continue
        key = str(entry.get("decision_key") or "").strip()
        if key:
            buckets.setdefault(sig, set()).add(key)
    return {sig: next(iter(keys)) for sig, keys in buckets.items() if len(keys) == 1}


def ledger_unique_target_path_keys(session: dict[str, Any]) -> dict[tuple[str, ...], str]:
    """Backward-compatible alias for path-signature uniqueness map."""
    return ledger_unique_path_keys(session)


def reconcile_intent_gaps_with_ledger(
    session: dict[str, Any],
    intent_gaps: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Reuse stable decision_key when path signature uniquely matches a ledger snapshot.

    Explicit, non-gap decision_keys that differ from the ledger canonical key are kept
    distinct even if they share a JSON path (same path can hold unrelated rules).
    """
    sig_map = ledger_unique_path_keys(session)
    out: list[dict[str, Any]] = []
    for gap in intent_gaps:
        if not isinstance(gap, dict):
            continue
        g = copy.deepcopy(gap)
        sig = normalize_target_paths(g.get("write_paths")) or normalize_target_paths(
            g.get("target_paths")
        )
        llm_key = str(g.get("decision_key") or "").strip()
        if sig and sig in sig_map:
            canonical = sig_map[sig]
            explicit_other = (
                bool(llm_key)
                and not llm_key.startswith("gap.")
                and llm_key != canonical
            )
            if explicit_other:
                # Different named rule on an overlapping path — do not alias.
                out.append(g)
                continue
            g["decision_key"] = canonical
            if llm_key and llm_key != canonical:
                g["decision_key_alias"] = llm_key
        elif not g.get("decision_key"):
            g["decision_key"] = resolve_decision_key(g)
        out.append(g)
    return out


def repair_failed_gaps_for_display(session: dict[str, Any]) -> list[dict[str, Any]]:
    """Rebuild intent-gap cards for repair_failed ledger rows (Critic conflict recovery)."""
    out: list[dict[str, Any]] = []
    for entry in ensure_decision_ledger(session):
        if not isinstance(entry, dict):
            continue
        if str(entry.get("status") or "") != "repair_failed":
            continue
        if not str(entry.get("answer_text") or "").strip():
            continue
        gap_id = str(entry.get("gap_id") or "").strip()
        if not gap_id:
            continue
        snap = entry.get("gap_snapshot")
        if isinstance(snap, dict) and str(snap.get("id") or gap_id).strip():
            gap = sanitize_intent_gap(copy.deepcopy(snap))
            gap["id"] = gap_id
            if not gap.get("decision_key"):
                gap["decision_key"] = str(entry.get("decision_key") or "").strip()
        else:
            gap = sanitize_intent_gap(_synthesize_gap_from_ledger_entry(gap_id, entry))
        out.append(gap)
    return out


def repair_answers_from_ledger(session: dict[str, Any]) -> list[dict[str, str]]:
    """lastAnswers-shaped rows for repair_failed entries (GUI retry without re-pick)."""
    out: list[dict[str, str]] = []
    for entry in ensure_decision_ledger(session):
        if not isinstance(entry, dict):
            continue
        if str(entry.get("status") or "") != "repair_failed":
            continue
        gap_id = str(entry.get("gap_id") or "").strip()
        text = str(entry.get("answer_text") or "").strip()
        if not gap_id or not text:
            continue
        out.append({"gap_id": gap_id, "choice": text, "note": ""})
    return out


def decision_key_alias_map_from_checks(
    session: dict[str, Any],
    checks: list[dict[str, Any]],
) -> dict[str, str]:
    """Disabled path-subset aliasing — same JSON path can hold unrelated rules.

    Alias maps must come from explicit gap identity (decision_key_alias /
    reconcile_intent_gaps_with_ledger). Kept for call-site compatibility.
    """
    _ = session, checks
    return {}


def merge_decision_key_alias_maps(
    gap_aliases: dict[str, str],
    check_aliases: dict[str, str],
) -> dict[str, str]:
    """Merge alias maps; explicit gap aliases win over check-inferred aliases."""
    merged = dict(check_aliases)
    merged.update(gap_aliases)
    return merged


def decision_key_alias_map_from_gaps(intent_gaps: list[dict[str, Any]]) -> dict[str, str]:
    """Map Critic/LLM decision_key aliases to canonical keys from reconciled intent_gaps."""
    out: dict[str, str] = {}
    for gap in intent_gaps:
        if not isinstance(gap, dict):
            continue
        alias = str(gap.get("decision_key_alias") or "").strip()
        canonical = str(gap.get("decision_key") or "").strip()
        if alias and canonical and alias != canonical:
            out[alias] = canonical
    return out


def canonicalize_decision_checks(
    checks: list[dict[str, Any]],
    alias_to_canonical: dict[str, str],
) -> list[dict[str, Any]]:
    if not alias_to_canonical:
        return [dict(c) for c in checks if isinstance(c, dict)]
    out: list[dict[str, Any]] = []
    for check in checks:
        if not isinstance(check, dict):
            continue
        row = dict(check)
        dkey = str(row.get("decision_key") or "").strip()
        if dkey and dkey in alias_to_canonical:
            row["decision_key"] = alias_to_canonical[dkey]
        out.append(row)
    return out


def ledger_answered_decision_keys(session: dict[str, Any]) -> list[str]:
    keys: list[str] = []
    for entry in ensure_decision_ledger(session):
        if not isinstance(entry, dict):
            continue
        if not str(entry.get("answer_text") or "").strip():
            continue
        key = str(entry.get("decision_key") or "").strip()
        if key:
            keys.append(key)
    return list(dict.fromkeys(keys))


def _ledger_entry_blocks_export(
    entry: dict[str, Any],
    *,
    current_draft_fingerprint: str | None,
) -> bool:
    if not str(entry.get("answer_text") or "").strip():
        return False
    status = str(entry.get("status") or "").strip()
    if status not in DECISION_STATUSES:
        return True
    if status in {"pending", "applied", "repair_failed"}:
        return True
    if status == "verified":
        vfp = str(entry.get("verified_draft_fingerprint") or "").strip()
        if not vfp:
            return True
        if current_draft_fingerprint:
            return vfp != current_draft_fingerprint
        return False
    return True


def verified_fingerprint_stale(session: dict[str, Any], current_draft_fingerprint: str | None) -> bool:
    if not current_draft_fingerprint:
        return False
    for entry in ensure_decision_ledger(session):
        if not isinstance(entry, dict):
            continue
        if _ledger_entry_blocks_export(entry, current_draft_fingerprint=current_draft_fingerprint):
            if str(entry.get("status") or "") == "verified":
                vfp = str(entry.get("verified_draft_fingerprint") or "").strip()
                if vfp and vfp != current_draft_fingerprint:
                    return True
    return False


def ledger_blocks_export(
    session: dict[str, Any],
    *,
    current_draft_fingerprint: str | None = None,
) -> bool:
    """Fail closed: answered ledger rows must be verified with matching draft fingerprint."""
    for entry in ensure_decision_ledger(session):
        if not isinstance(entry, dict):
            continue
        if _ledger_entry_blocks_export(entry, current_draft_fingerprint=current_draft_fingerprint):
            return True
    return False


def _synthesize_gap_from_ledger_entry(gap_id: str, entry: dict[str, Any]) -> dict[str, Any]:
    """Recover a minimal gap when open review and gap_snapshot are both missing."""
    dkey = str(entry.get("decision_key") or "").strip() or f"gap.{gap_id}"
    paths = normalize_path_list(entry.get("evidence_paths"))
    gap: dict[str, Any] = {
        "id": gap_id,
        "decision_key": dkey,
        "question": (
            "（从会话账本恢复的旧审查项；若写入失败请重新运行「制作审查」。）"
        ),
        "why_blocking": "legacy_recovery",
    }
    if paths:
        gap["target_paths"] = paths
        gap["write_paths"] = list(paths)
    return gap


def resolve_gaps_for_answers(
    session: dict[str, Any],
    normalized: list[dict[str, str]],
) -> dict[str, dict[str, Any]]:
    """Map gap_id -> gap dict from open review and/or ledger snapshots (retry)."""
    review = session.get("makeability_review")
    intent_raw = (
        review.get("intent_gaps")
        if isinstance(review, dict) and isinstance(review.get("intent_gaps"), list)
        else []
    )
    open_by_id = {
        str(g.get("id") or "").strip(): g
        for g in intent_raw
        if isinstance(g, dict) and str(g.get("id") or "").strip()
    }
    ledger_by_gap: dict[str, dict[str, Any]] = {}
    for entry in ensure_decision_ledger(session):
        if not isinstance(entry, dict):
            continue
        gid = str(entry.get("gap_id") or "").strip()
        if gid:
            ledger_by_gap[gid] = entry

    gaps_by_id: dict[str, dict[str, Any]] = {}
    for row in normalized:
        gap_id = str(row.get("gap_id") or "").strip()
        if not gap_id:
            continue
        if gap_id in open_by_id:
            gaps_by_id[gap_id] = copy.deepcopy(open_by_id[gap_id])
            continue
        entry = ledger_by_gap.get(gap_id)
        if isinstance(entry, dict):
            snap = entry.get("gap_snapshot")
            if isinstance(snap, dict) and str(snap.get("id") or gap_id).strip():
                gap = copy.deepcopy(snap)
                gap["id"] = gap_id
                if not gap.get("decision_key"):
                    gap["decision_key"] = str(entry.get("decision_key") or "").strip()
                gaps_by_id[gap_id] = gap
            elif str(entry.get("answer_text") or "").strip():
                # Pre-snapshot crash sessions: still allow retry from ledger answer.
                gaps_by_id[gap_id] = _synthesize_gap_from_ledger_entry(gap_id, entry)
    return gaps_by_id


def decisions_for_verifier(
    session: dict[str, Any],
    gaps_by_id: dict[str, dict[str, Any]],
    normalized: list[dict[str, str]],
) -> list[dict[str, Any]]:
    by_key = ledger_index_by_key(session)
    specs: list[dict[str, Any]] = []
    for row in normalized:
        gap_id = str(row.get("gap_id") or "").strip()
        gap = gaps_by_id.get(gap_id)
        if not isinstance(gap, dict):
            continue
        dkey = resolve_decision_key(gap)
        entry = by_key.get(dkey)
        answer_text = str(entry.get("answer_text") or _answer_text(row)) if entry else _answer_text(row)
        tp = gap.get("target_paths")
        spec: dict[str, Any] = {
            "decision_key": dkey,
            "gap_id": gap_id,
            "answer_text": answer_text,
        }
        if isinstance(tp, list):
            spec["target_paths"] = [str(p).strip() for p in tp if str(p).strip()]
        # Expose full write_paths to the model as sync guidance; satisfaction
        # gating still uses required_write_paths_from_gap (prefers target_paths).
        full_wp = normalize_write_paths(gap.get("write_paths"))
        if not full_wp:
            full_wp = required_write_paths_from_gap(gap)
        if full_wp:
            spec["write_paths"] = full_wp
        occ = gap.get("occurrences")
        if isinstance(occ, list) and occ:
            spec["occurrences"] = copy.deepcopy(occ)
        specs.append(spec)
    return specs


def complete_decision_checks_for_keys(
    expected_keys: list[str],
    checks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    by_key: dict[str, dict[str, Any]] = {}
    for check in checks:
        dkey = str(check.get("decision_key") or "").strip()
        if dkey:
            by_key[dkey] = check
    out: list[dict[str, Any]] = []
    for key in expected_keys:
        if key in by_key:
            out.append(dict(by_key[key]))
        else:
            out.append({"decision_key": key, "status": "missing", "evidence_paths": []})
    return out


def verifier_reported_all_keys(expected_keys: list[str], raw_checks: list[dict[str, Any]]) -> bool:
    reported = {
        str(c.get("decision_key") or "").strip()
        for c in raw_checks
        if isinstance(c, dict) and str(c.get("decision_key") or "").strip()
    }
    return all(k in reported for k in expected_keys)


def verifier_path_failure_detail(
    checks: list[dict[str, Any]],
    required_paths_by_key: dict[str, list[str]],
    *,
    expected_keys: list[str] | None = None,
) -> list[str]:
    """Human-readable missing/unresolved paths for repair closer prompts."""
    by_key: dict[str, dict[str, Any]] = {}
    for check in checks:
        if not isinstance(check, dict):
            continue
        dkey = str(check.get("decision_key") or "").strip()
        if dkey:
            by_key[dkey] = check
    keys = list(expected_keys) if expected_keys is not None else list(required_paths_by_key.keys())
    lines: list[str] = []
    for dkey in keys:
        if not dkey:
            continue
        required = required_paths_by_key.get(dkey) or []
        check = by_key.get(dkey)
        if check is None:
            if required:
                lines.append(
                    f"{dkey}: missing verifier row; required {', '.join(required)}"
                )
            else:
                lines.append(f"{dkey}: missing verifier row")
            continue
        if effective_decision_check_status(check, required) == "satisfied":
            continue
        unresolved = normalize_path_list(check.get("unresolved_paths"))
        if unresolved:
            lines.append(f"{dkey}: unresolved {', '.join(unresolved)}")
        evidence = normalize_target_paths(check.get("evidence_paths"))
        missing = [p for p in required if p.lower() not in evidence]
        if missing:
            lines.append(f"{dkey}: missing evidence for {', '.join(missing)}")
    return lines


def apply_whole_card_verifier_results(
    session: dict[str, Any],
    expected_keys: list[str],
    checks: list[dict[str, Any]],
    *,
    gap_id_for_key: dict[str, str],
    raw_complete: bool,
    verified_draft_fingerprint: str | None = None,
    required_paths_by_key: dict[str, list[str]] | None = None,
) -> tuple[list[str], list[str]]:
    """Per-decision verify: satisfied keys pass; others repair_failed (no whole-card veto).

    ``raw_complete`` is retained for callers/logging; missing keys still fail only
    themselves, not siblings that already satisfied.
    """
    _ = raw_complete
    req_map = required_paths_by_key or {}
    by_key: dict[str, dict[str, Any]] = {}
    for check in checks:
        if not isinstance(check, dict):
            continue
        dkey = str(check.get("decision_key") or "").strip()
        if not dkey:
            continue
        row = dict(check)
        row["status"] = effective_decision_check_status(row, req_map.get(dkey))
        by_key[dkey] = row

    verified: list[str] = []
    failed: list[str] = []
    for dkey in expected_keys:
        gid = str(gap_id_for_key.get(dkey) or "").strip()
        check = by_key.get(dkey)
        if check is not None and str(check.get("status") or "").lower() == "satisfied":
            ep = check.get("evidence_paths")
            update_ledger_status(
                session,
                dkey,
                status="verified",
                evidence_paths=ep if isinstance(ep, list) else [],
                gap_id=gid or str(check.get("gap_id") or "").strip() or None,
                verified_draft_fingerprint=verified_draft_fingerprint,
            )
            use_gid = gid or str(check.get("gap_id") or "").strip()
            if use_gid:
                verified.append(use_gid)
            continue
        update_ledger_status(session, dkey, status="repair_failed", gap_id=gid or None)
        if gid:
            failed.append(gid)
    return list(dict.fromkeys(verified)), list(dict.fromkeys(failed))


def complete_critic_ledger_checks(
    session: dict[str, Any],
    checks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    expected = ledger_answered_decision_keys(session)
    if not expected:
        return normalize_decision_checks(checks)
    return complete_decision_checks_for_keys(expected, normalize_decision_checks(checks))


def assert_critic_decision_checks_protocol(
    session: dict[str, Any],
    checks: list[dict[str, Any]],
) -> None:
    """Require Critic to report every answered ledger key; refuse silent downgrade."""
    expected = ledger_answered_decision_keys(session)
    if not expected:
        return
    raw = normalize_decision_checks(checks)
    if not verifier_reported_all_keys(expected, raw):
        missing = [
            k
            for k in expected
            if k
            not in {
                str(c.get("decision_key") or "").strip()
                for c in raw
                if isinstance(c, dict)
            }
        ]
        raise ValueError(
            "Makeability critic decision_checks incomplete for answered ledger keys: "
            + ", ".join(missing)
        )
    for index, item in enumerate(checks if isinstance(checks, list) else []):
        if not isinstance(item, dict):
            raise ValueError(f"decision_checks[{index}] must be an object.")
        status = str(item.get("status") or "").strip().lower()
        if status and status not in {"satisfied", "missing", "conflict"}:
            raise ValueError(
                f"decision_checks[{index}] invalid status {item.get('status')!r}."
            )


def invalidate_verified_ledger_for_patches(
    session: dict[str, Any],
    patches: list[dict[str, Any]],
) -> list[str]:
    """No longer downgrade verified → repair_failed on path touch.

    Later patches / autofix were cascading false repair cards. Answers stay
    verified; Critic may still surface real conflicts on the next review.
    """
    _ = session, patches
    return []


def gap_id_map_from_specs(specs: list[dict[str, Any]]) -> dict[str, str]:
    return {
        str(s.get("decision_key") or "").strip(): str(s.get("gap_id") or "").strip()
        for s in specs
        if str(s.get("decision_key") or "").strip()
    }


def detail_gap_stable_key(gap: dict[str, Any]) -> str:
    topic = " ".join(str(gap.get("topic") or "").strip().lower().split())
    if topic:
        return f"topic:{topic}"
    gid = str(gap.get("id") or "").strip().lower()
    if gid:
        return f"id:{gid}"
    return ""


def ensure_detail_gaps_shown_list(session: dict[str, Any]) -> list[str]:
    raw = session.get("makeability_detail_gaps_shown")
    if not isinstance(raw, list):
        session["makeability_detail_gaps_shown"] = []
    return session["makeability_detail_gaps_shown"]


def partition_detail_gaps_for_display(
    session: dict[str, Any],
    detail_gaps: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], int]:
    """Split detail gaps into newly listed vs already shown in conversation."""
    shown_list = ensure_detail_gaps_shown_list(session)
    shown = set(str(x) for x in shown_list if str(x).strip())
    new: list[dict[str, Any]] = []
    skipped = 0
    for gap in detail_gaps:
        if not isinstance(gap, dict):
            continue
        key = detail_gap_stable_key(gap)
        if key and key in shown:
            skipped += 1
            continue
        new.append(gap)
        if key and key not in shown:
            shown.add(key)
            shown_list.append(key)
    return new, skipped
