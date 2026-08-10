# Brief Catalog + Shards Implementation Plan

> **SUPERSEDED（2026-08-10）**：请改用 [`2026-08-10-foundry-brief-shards-search-plan.md`](./2026-08-10-foundry-brief-shards-search-plan.md)（含结构化搜索 + description 瘦身纪律）。下文仅作历史参考。

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `brief.json` a thin catalog (id + title/name + path); put scene / system / asset bodies in shard files; load by focus so host-chat and pipeline stop stuffing the full draft every turn.

**Architecture:** New `cli/brief_shards.py` owns catalog refs, shard IO, legacy detection, and migrate. `brief.py` normalize accepts catalog-shaped entries; `load_brief*` resolves asset specs from shard paths when catalog mode. Host-chat injects catalog + focused shard only. Pipeline/prompt craft call `resolve_asset_specs(brief_path)`.

**Tech Stack:** Python 3.11+, existing `unittest`, Click CLI under `brief_cmds.py`, JSON on disk under `projects/<slug>/`.

**Spec:** [`docs/superpowers/specs/2026-08-10-brief-catalog-shards-design.md`](../../superpowers/specs/2026-08-10-brief-catalog-shards-design.md)

## Global Constraints

- Catalog entries for scenes/systems/assets may only contain mapping fields: `id`, `title`|`name`, `path` — no dual-written body fields.
- Shard file is the sole source of truth for body content; validate fails on missing path or id mismatch.
- Legacy thick briefs remain readable with warnings; new writes use catalog + shards.
- Tuning tables stay inside `systems/<id>.json` (no third-layer tuning store in v1).
- No large GUI editor in this plan.

## File map

| File | Responsibility |
|------|----------------|
| `cli/brief_shards.py` | Ref types, path resolve, load/save shards, legacy detect, migrate, `resolve_asset_specs` |
| `cli/test_brief_shards.py` | Unit tests for shards + migrate + resolve |
| `cli/brief.py` | Catalog-aware `normalize_scenes` / `normalize_systems` / asset ref normalize; wire load helpers |
| `cli/brief_cmds.py` | `brief shard migrate` (and optional `brief shard status`) |
| `cli/host_chat.py` | Focus + catalog/shard context injection; write patches to shards |
| `cli/test_host_chat.py` | Focus payload size / shard write tests |
| `cli/asset_pipeline.py` / callers of `load_brief` | Prefer `resolve_asset_specs` when catalog |
| `docs/AI-HANDOFF.md` | Short note: brief = catalog; shards = body |

---

### Task 1: Catalog ref helpers + shard IO

**Files:**
- Create: `cli/brief_shards.py`
- Create: `cli/test_brief_shards.py`

**Interfaces:**
- Produces:
  - `is_catalog_ref(entry: dict) -> bool`
  - `is_legacy_scene_entry(entry: dict) -> bool` (has body keys without usable path)
  - `project_root_for_brief(brief_path: Path) -> Path`
  - `resolve_shard_path(project_root: Path, rel: str) -> Path`
  - `load_json_shard(path: Path) -> dict[str, Any]`
  - `save_json_shard(path: Path, data: dict[str, Any]) -> None`
  - `CATALOG_SCENE_KEYS = frozenset({"id", "title", "path"})`
  - `CATALOG_SYSTEM_KEYS = frozenset({"id", "title", "path"})`
  - `CATALOG_ASSET_KEYS = frozenset({"id", "name", "path"})`

- [ ] **Step 1: Write failing tests**

```python
# cli/test_brief_shards.py
import json
import tempfile
import unittest
from pathlib import Path

from brief_shards import (
    is_catalog_ref,
    is_legacy_scene_entry,
    load_json_shard,
    resolve_shard_path,
    save_json_shard,
)


class TestBriefShardsIo(unittest.TestCase):
    def test_catalog_ref_detection(self) -> None:
        self.assertTrue(
            is_catalog_ref({"id": "a", "title": "A", "path": "scenes/a.json"})
        )
        self.assertTrue(
            is_legacy_scene_entry(
                {"id": "a", "title": "A", "summary": "long", "notes": "x"}
            )
        )

    def test_roundtrip_shard(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            rel = "scenes/hall.json"
            path = resolve_shard_path(root, rel)
            save_json_shard(path, {"id": "hall", "title": "Hall", "summary": "s"})
            data = load_json_shard(path)
            self.assertEqual(data["id"], "hall")
            self.assertTrue(path.is_file())
```

- [ ] **Step 2: Run tests — expect FAIL (import / missing module)**

Run: `cd cli && python -m unittest test_brief_shards.TestBriefShardsIo -v`  
Expected: FAIL `ModuleNotFoundError` or attribute errors

- [ ] **Step 3: Implement `cli/brief_shards.py`**

```python
"""Brief catalog refs + scene/system/asset shard IO (single source of body truth)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

CATALOG_SCENE_KEYS = frozenset({"id", "title", "path"})
CATALOG_SYSTEM_KEYS = frozenset({"id", "title", "path"})
CATALOG_ASSET_KEYS = frozenset({"id", "name", "path"})
_BODY_HINT_KEYS = frozenset(
    {
        "summary",
        "notes",
        "ui_panel_ids",
        "ui_panels",
        "visual_reference",
        "tuning",
        "type",
        "usage",
        "display_size",
        "generate_method",
        "assets",
    }
)


def is_catalog_ref(entry: dict[str, Any]) -> bool:
    path = str(entry.get("path") or "").strip()
    if not path or not str(entry.get("id") or "").strip():
        return False
    keys = {k for k in entry.keys() if entry.get(k) not in (None, "", [], {})}
    # Allow only mapping keys (plus id/title/name/path)
    return bool(keys <= (CATALOG_SCENE_KEYS | CATALOG_SYSTEM_KEYS | CATALOG_ASSET_KEYS))


def is_legacy_scene_entry(entry: dict[str, Any]) -> bool:
    if is_catalog_ref(entry):
        return False
    return bool(str(entry.get("id") or "").strip()) and bool(
        _BODY_HINT_KEYS.intersection(entry.keys())
        or not str(entry.get("path") or "").strip()
    )


def project_root_for_brief(brief_path: Path) -> Path:
    from project_paths import project_root_for_brief as _root

    root = _root(brief_path)
    if root is not None:
        return root
    return brief_path.resolve().parent


def resolve_shard_path(project_root: Path, rel: str) -> Path:
    text = rel.replace("\\", "/").strip().lstrip("/")
    if not text or ".." in text.split("/"):
        raise ValueError(f"Invalid shard path: {rel!r}")
    return (project_root / text).resolve()


def load_json_shard(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Shard must be a JSON object: {path}")
    return data


def save_json_shard(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
```

- [ ] **Step 4: Run tests — expect PASS**

Run: `cd cli && python -m unittest test_brief_shards.TestBriefShardsIo -v`  
Expected: OK

- [ ] **Step 5: Commit** (if user asked for commits; otherwise leave staged note)

```bash
git add cli/brief_shards.py cli/test_brief_shards.py
git commit -m "feat: add brief shard IO and catalog ref helpers"
```

---

### Task 2: Resolve asset specs from catalog + validate refs

**Files:**
- Modify: `cli/brief_shards.py`
- Modify: `cli/test_brief_shards.py`
- Modify: `cli/brief.py` (`parse_brief_document` / new `load_brief_resolved`)

**Interfaces:**
- Consumes: Task 1 IO helpers
- Produces:
  - `load_asset_spec_file(path: Path) -> AssetSpec` (via `AssetSpec.from_dict`)
  - `resolve_asset_specs(brief_path: Path, data: dict | None = None) -> list[AssetSpec]`
  - `audit_catalog_refs(brief_path: Path, data: dict) -> list[str]` (error strings)

- [ ] **Step 1: Failing test — catalog brief resolves specs from disk**

```python
class TestResolveAssetSpecs(unittest.TestCase):
    def test_resolve_from_catalog_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            brief = root / "brief.json"
            spec_rel = "assets/eel.spec.json"
            save_json_shard(
                root / spec_rel,
                {
                    "id": "eel",
                    "name": "eel",
                    "type": "character",
                    "usage": "catch",
                    "generate_method": "image",
                    "display_size": {"width": 64, "height": 32},
                },
            )
            brief.write_text(
                json.dumps(
                    {
                        "project": {
                            "title": "T",
                            "description": "d",
                            "art_direction": "a",
                            "genre": "g",
                            "gameplay_loop": "loop",
                            "session_goal": "goal",
                            "viewport": {"width": 1280, "height": 720},
                        },
                        "assets": [
                            {"id": "eel", "name": "eel", "path": spec_rel}
                        ],
                    }
                ),
                encoding="utf-8",
            )
            from brief_shards import resolve_asset_specs

            specs = resolve_asset_specs(brief)
            self.assertEqual(len(specs), 1)
            self.assertEqual(specs[0].name, "eel")
```

- [ ] **Step 2: Run — expect FAIL**

- [ ] **Step 3: Implement `resolve_asset_specs` + `audit_catalog_refs` in `brief_shards.py`**

Logic sketch:

```python
def resolve_asset_specs(brief_path: Path, data: dict[str, Any] | None = None):
    from brief import AssetSpec, load_brief_document

    brief_path = brief_path.resolve()
    doc = data if data is not None else load_brief_document(brief_path)
    root = project_root_for_brief(brief_path)
    raw = doc.get("assets") or []
    if not isinstance(raw, list) or not raw:
        raise ValueError("Brief must contain an 'assets' array.")
    out = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        if is_catalog_ref(item) and "path" in item:
            shard = load_json_shard(resolve_shard_path(root, str(item["path"])))
            if str(shard.get("id") or shard.get("name") or "").strip() not in {
                str(item.get("id") or "").strip(),
                str(item.get("name") or "").strip(),
            }:
                # require shard id or name matches catalog id or name
                sid = str(shard.get("id") or "").strip()
                cid = str(item.get("id") or "").strip()
                if sid and cid and sid != cid:
                    raise ValueError(f"Asset id mismatch catalog={cid} shard={sid}")
            out.append(AssetSpec.from_dict(shard))
        else:
            out.append(AssetSpec.from_dict(item))
    return out
```

Wire `brief.load_brief_full` to try catalog resolve when first asset is catalog ref (or always call `resolve_asset_specs`).

- [ ] **Step 4: Test `audit_catalog_refs` missing file → error string**

- [ ] **Step 5: Run `python -m unittest test_brief_shards -v` — PASS**

- [ ] **Step 6: Commit**

```bash
git commit -m "feat: resolve AssetSpec list from catalog shard paths"
```

---

### Task 3: Migrate command (thick → shards + catalog)

**Files:**
- Modify: `cli/brief_shards.py` — `migrate_brief_to_shards(brief_path) -> dict`
- Modify: `cli/brief_cmds.py` — `brief shard migrate`
- Modify: `cli/test_brief_shards.py`

**Interfaces:**
- Produces: `migrate_brief_to_shards(brief_path: Path, *, backup: bool = True) -> dict[str, Any]`  
  Returns `{ok, scenes, systems, assets, backup_path?}`.

- [ ] **Step 1: Failing test**

```python
class TestMigrate(unittest.TestCase):
    def test_migrate_writes_shards_and_thins_brief(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            brief = root / "brief.json"
            brief.write_text(
                json.dumps(
                    {
                        "project": {
                            "title": "T",
                            "description": "d",
                            "art_direction": "a",
                            "genre": "g",
                            "gameplay_loop": "loop",
                            "session_goal": "goal",
                            "viewport": {"width": 1280, "height": 720},
                            "scenes": [
                                {
                                    "id": "hall",
                                    "title": "Hall",
                                    "summary": "Empty tank",
                                    "notes": "no fish",
                                }
                            ],
                            "systems": [
                                {
                                    "id": "economy",
                                    "title": "Economy",
                                    "summary": "Gold",
                                    "notes": "daily decay",
                                }
                            ],
                        },
                        "assets": [
                            {
                                "id": "eel",
                                "name": "eel",
                                "type": "character",
                                "usage": "catch",
                                "generate_method": "image",
                                "display_size": {"width": 64, "height": 32},
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            from brief_shards import migrate_brief_to_shards, is_catalog_ref

            result = migrate_brief_to_shards(brief)
            self.assertTrue(result["ok"])
            doc = json.loads(brief.read_text(encoding="utf-8"))
            self.assertTrue(is_catalog_ref(doc["project"]["scenes"][0]))
            self.assertTrue((root / "scenes" / "hall.json").is_file())
            self.assertTrue((root / "systems" / "economy.json").is_file())
            self.assertTrue((root / "assets" / "eel.spec.json").is_file())
            self.assertNotIn("summary", doc["project"]["scenes"][0])
```

- [ ] **Step 2: Implement migrate** — write shards from body fields; replace arrays with refs; optional `brief.pre-shard.json` backup next to brief.

Default paths:
- scene → `scenes/{id}.json`
- system → `systems/{id}.json`
- asset → `assets/{id}.spec.json` (fallback slug from `name`)

- [ ] **Step 3: CLI**

```python
@brief_group.group("shard")
def shard_group():
    """Catalog / shard helpers for thin briefs."""

@shard_group.command("migrate")
@click.option("--brief", "brief_path", required=True, type=click.Path(exists=True, path_type=Path))
@click.option("--json", "as_json", is_flag=True)
def shard_migrate(brief_path, as_json):
    from brief_shards import migrate_brief_to_shards
    result = migrate_brief_to_shards(brief_path)
    ...
```

- [ ] **Step 4: Tests PASS + commit**

```bash
git commit -m "feat: migrate thick brief bodies into scene/system/asset shards"
```

---

### Task 4: Validate catalog refs

**Files:**
- Modify: `cli/brief.py` audit/validate path used by `brief validate`
- Modify: `cli/test_brief_shards.py` or existing validate tests

- [ ] **Step 1: Test** — catalog ref with missing file → validate reports error; id mismatch → error; legacy thick → warning only (no hard fail).

- [ ] **Step 2: Hook `audit_catalog_refs` into existing validate flow** (same place visual_reference / makeability audits run).

- [ ] **Step 3: PASS + commit**

```bash
git commit -m "feat: validate brief catalog shard paths and ids"
```

---

### Task 5: Host-chat focus + shard-scoped context

**Files:**
- Modify: `cli/host_chat.py`
- Modify: `cli/test_host_chat.py`
- Modify: `resources/skills/orchestrator/host-chat.md` (short discipline: patch shards / catalog only)

**Interfaces:**
- Session field: `focus: { "kind": "scene"|"system"|"asset"|"project", "id": str } | null`
- Payload builder includes `brief_catalog` (thin) + `focus_shard` (full JSON) only.

- [ ] **Step 1: Failing test** — build_turn_payload (or equivalent) with two scenes on disk; focus hall → other scene body absent from serialized user payload string.

- [ ] **Step 2: Implement**
  - Persist focus from user/tool or heuristic (mention scene id).
  - When applying `brief_patches` that touch scene/system/asset body: write shard file; only update catalog title/name if needed.
  - Reject patches that set forbidden body keys on catalog entries.

- [ ] **Step 3: PASS + commit**

```bash
git commit -m "feat: host-chat loads catalog + focused shard only"
```

---

### Task 6: Pipeline / prompt craft use resolved specs

**Files:**
- Grep call sites of `load_brief` / `parse_brief_document` in `asset_pipeline.py`, `prompt_cmds.py`, `visual_target.py`
- Switch to `resolve_asset_specs(brief_path)` or `load_brief` that already resolves
- Add one integration-style unittest with temp catalog brief + dry plan or craft entry

- [ ] **Step 1: Identify call sites; add test that craft/plan sees type from shard**

- [ ] **Step 2: Minimal wiring so catalog briefs don't break `AssetSpec.from_dict` on thin refs**

- [ ] **Step 3: PASS affected tests + commit**

```bash
git commit -m "feat: pipeline and prompt craft resolve assets from shards"
```

---

### Task 7: Docs

**Files:**
- Modify: `docs/AI-HANDOFF.md` — brief catalog + shard paths + migrate command
- Modify: `docs/ITERATIVE-PRODUCTION.md` — one paragraph pointing at shard layout
- Modify: spec status already confirmed

- [ ] **Step 1: Write the short sections**
- [ ] **Step 2: Commit**

```bash
git commit -m "docs: brief catalog and shard layout"
```

---

## Spec coverage check

| Spec requirement | Task |
|------------------|------|
| Thin catalog only | 1–3 |
| Shards sole body | 2–3 |
| Conflict / validate | 4 |
| Focus load host-chat | 5 |
| Migrate | 3 |
| Pipeline reads specs | 6 |
| Docs | 7 |
| Legacy readable | 2, 4 |
| No GUI editor | n/a |
| Tuning in system shard | 3 migrate preserves notes/summary; tuning field supported in system shard schema docs |

## Placeholder scan

No TBD steps; commands and code sketches are concrete. Implementers should match existing `project_paths.project_root_for_brief` and Click patterns in `brief_cmds.py`.
