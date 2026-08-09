# Asset Review Table Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** GUI「资产」面板：读 `assets-manifest` 展示缩略图与映射，支持行内采纳 / 重生成 / 本地替换（软 `review` 标注）。

**Architecture:** CLI 纯函数展开审查行并读写 `review` / 覆盖交付物；`assets review` 子命令供 Electron 调用；GUI 新侧栏面板与看板并列，缩略图复用 `getMediaPreview`。

**Tech Stack:** Python CLI (`assets_manifest` / 新 `asset_review.py`)、Electron IPC、React 侧栏面板、现有 `pipeline reset --cascade` + `pipeline run`。

**Spec:** [`docs/superpowers/specs/2026-07-24-asset-review-table-design.md`](../specs/2026-07-24-asset-review-table-design.md)

## Global Constraints

- 软标注 only：不阻塞 assemble / 程序员派工。
- `review` 存 `assets-manifest`：普通资产 `assets[<name>].review`；kit item `assets[<kit>].item_reviews[<slug>]`。
- 本地替换覆盖 canonical 路径；不建 `candidates/`。
- 替换不改 brief id/name。
- 无 pipeline manifest 时：可看表 + 本地替换；重生成禁用。
- 用户未要求时不要主动 `git commit`（计划里 Step Commit 仅在用户要求提交时执行）。

---

## File map

| Path | Responsibility |
|------|----------------|
| `cli/asset_review.py` | 展开行、读写 review、解析交付物路径、本地覆盖 |
| `cli/test_asset_review.py` | 单测 |
| `cli/assets_cmds.py` + `gamefactory.py` 注册 | `assets review list/accept/replace/regenerate-plan` |
| `gui/electron/main.mjs` + `preload.cjs` | IPC：list / accept / replace / regenerate |
| `gui/src/vite-env.d.ts` | 类型 |
| `gui/src/components/AssetReviewPanel.tsx` | 资产表 UI |
| `gui/src/App.tsx` | 侧栏 Tab +「打开资产表」 |
| `docs/GUI-CONFIG.md` 或 `docs/AI-HANDOFF.md` | 一句入口说明 |
| `docs/RELEASE-NOTES-UNRELEASED.md` | 草稿条目 |

---

### Task 1: CLI — 展开审查行 + review 读写

**Files:**
- Create: `cli/asset_review.py`
- Create: `cli/test_asset_review.py`
- Modify: `cli/assets_manifest.py`（仅当需导出 `_utc_now` / path helper；优先在 `asset_review` 内复用 `load/save_assets_manifest`）

**Interfaces:**
- Produces:
  - `DEFAULT_REVIEW = {"status": "pending", "source": "pipeline", "updated_at": "", "note": ""}`
  - `iter_review_rows(manifest: dict) -> list[dict]` — 每行含 `row_id`, `asset_name`, `kit_item_slug` (optional), `label`, `type`, `usage`, `preview_path_repo`, `canonical_path_repo`, `review`, `stages_summary`
  - `get_review(manifest, *, asset_name, kit_item_slug=None) -> dict`
  - `set_review(manifest, *, asset_name, kit_item_slug=None, status, source=None, note=None) -> dict`（就地改并返回 review）
  - `resolve_canonical_path(entry, *, kit_item_slug=None) -> str | None` — 优先 gameplay-ready / 含 `nobg` 的 stage，否则 raw/`image.raw`
  - `row_id_for(asset_name, kit_item_slug=None) -> str` — e.g. `knight` 或 `item_icons__sword`

**Row rules:**
- 普通资产：一行，`row_id = asset_name`。
- `brief.type == icon_kit` 且 `brief.items` 非空：每个 item 一行；`kit_item_slug = item.slug`（无 slug 则用 id）；`preview`/`canonical` 从 `stages` 里匹配同 `kit_item_slug` / `kit_item_id` 的 stage。
- 无 stages 时仍出行列，路径 `null`，`review` 默认 pending。

- [ ] **Step 1: Write failing tests**

Create `cli/test_asset_review.py`:

```python
from __future__ import annotations

import unittest
from copy import deepcopy

from asset_review import (
    get_review,
    iter_review_rows,
    resolve_canonical_path,
    set_review,
)


def _manifest():
    return {
        "manifest_version": 1,
        "assets": {
            "knight": {
                "brief": {
                    "name": "knight",
                    "type": "character",
                    "usage": "player",
                    "usage_description": "hero",
                },
                "stages": [
                    {
                        "stage": "image.raw",
                        "path_repo": "output/demo/knight_raw.png",
                        "role": "pipeline_intermediate",
                    },
                    {
                        "stage": "image.nobg",
                        "path_repo": "output/demo/knight_nobg.png",
                        "role": "gameplay_ready",
                    },
                ],
            },
            "item_icons": {
                "brief": {
                    "name": "item_icons",
                    "type": "icon_kit",
                    "usage": "item_icon",
                    "items": [
                        {"id": "sword", "slug": "sword", "usage": "item_icon"},
                        {"id": "potion", "slug": "potion", "usage": "pickup"},
                    ],
                },
                "stages": [
                    {
                        "stage": "image.nobg",
                        "path_repo": "output/demo/item_icons__sword_nobg.png",
                        "kit_item_slug": "sword",
                        "kit_item_id": "sword",
                        "role": "gameplay_ready",
                    },
                    {
                        "stage": "image.nobg",
                        "path_repo": "output/demo/item_icons__potion_nobg.png",
                        "kit_item_slug": "potion",
                        "kit_item_id": "potion",
                        "role": "gameplay_ready",
                    },
                ],
                "item_reviews": {},
            },
        },
    }


class AssetReviewTests(unittest.TestCase):
    def test_iter_rows_expands_kit(self) -> None:
        rows = iter_review_rows(_manifest())
        ids = {r["row_id"] for r in rows}
        self.assertIn("knight", ids)
        self.assertIn("item_icons__sword", ids)
        self.assertIn("item_icons__potion", ids)

    def test_canonical_prefers_nobg(self) -> None:
        m = _manifest()
        path = resolve_canonical_path(m["assets"]["knight"])
        self.assertEqual(path, "output/demo/knight_nobg.png")

    def test_set_review_accept(self) -> None:
        m = _manifest()
        rev = set_review(m, asset_name="knight", status="accepted")
        self.assertEqual(rev["status"], "accepted")
        self.assertEqual(get_review(m, asset_name="knight")["status"], "accepted")

    def test_kit_item_review_isolated(self) -> None:
        m = _manifest()
        set_review(
            m,
            asset_name="item_icons",
            kit_item_slug="sword",
            status="replaced",
            source="local_file",
        )
        self.assertEqual(
            get_review(m, asset_name="item_icons", kit_item_slug="sword")["status"],
            "replaced",
        )
        self.assertEqual(
            get_review(m, asset_name="item_icons", kit_item_slug="potion")["status"],
            "pending",
        )


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run tests — expect FAIL**

Run: `cd cli; python -m unittest test_asset_review -v`  
Expected: import / attribute errors.

- [ ] **Step 3: Implement `cli/asset_review.py`**

```python
"""Asset review rows + soft review annotations on assets-manifest."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from typing import Any

VALID_STATUS = frozenset({"pending", "accepted", "replaced"})
VALID_SOURCE = frozenset({"pipeline", "regenerate", "local_file"})


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def default_review() -> dict[str, Any]:
    return {
        "status": "pending",
        "source": "pipeline",
        "updated_at": "",
        "note": "",
    }


def row_id_for(asset_name: str, kit_item_slug: str | None = None) -> str:
    if kit_item_slug:
        return f"{asset_name}__{kit_item_slug}"
    return asset_name


def _normalize_review(raw: Any) -> dict[str, Any]:
    base = default_review()
    if not isinstance(raw, dict):
        return base
    status = str(raw.get("status") or "pending").strip().lower()
    source = str(raw.get("source") or "pipeline").strip().lower()
    if status not in VALID_STATUS:
        status = "pending"
    if source not in VALID_SOURCE:
        source = "pipeline"
    return {
        "status": status,
        "source": source,
        "updated_at": str(raw.get("updated_at") or ""),
        "note": str(raw.get("note") or ""),
    }


def get_review(
    manifest: dict[str, Any],
    *,
    asset_name: str,
    kit_item_slug: str | None = None,
) -> dict[str, Any]:
    entry = (manifest.get("assets") or {}).get(asset_name) or {}
    if kit_item_slug:
        bag = entry.get("item_reviews") if isinstance(entry.get("item_reviews"), dict) else {}
        return _normalize_review(bag.get(kit_item_slug))
    return _normalize_review(entry.get("review"))


def set_review(
    manifest: dict[str, Any],
    *,
    asset_name: str,
    status: str,
    kit_item_slug: str | None = None,
    source: str | None = None,
    note: str | None = None,
) -> dict[str, Any]:
    status_n = str(status).strip().lower()
    if status_n not in VALID_STATUS:
        raise ValueError(f"invalid review status: {status!r}")
    assets = manifest.setdefault("assets", {})
    entry = assets.setdefault(asset_name, {})
    current = get_review(manifest, asset_name=asset_name, kit_item_slug=kit_item_slug)
    if source is not None:
        source_n = str(source).strip().lower()
        if source_n not in VALID_SOURCE:
            raise ValueError(f"invalid review source: {source!r}")
        current["source"] = source_n
    if note is not None:
        current["note"] = str(note)
    current["status"] = status_n
    current["updated_at"] = _utc_now()
    if kit_item_slug:
        bag = entry.setdefault("item_reviews", {})
        if not isinstance(bag, dict):
            bag = {}
            entry["item_reviews"] = bag
        bag[kit_item_slug] = current
    else:
        entry["review"] = current
    return deepcopy(current)


def resolve_canonical_path(
    entry: dict[str, Any],
    *,
    kit_item_slug: str | None = None,
) -> str | None:
    stages = entry.get("stages") if isinstance(entry.get("stages"), list) else []
    filtered: list[dict[str, Any]] = []
    for s in stages:
        if not isinstance(s, dict):
            continue
        if kit_item_slug:
            slug = str(s.get("kit_item_slug") or "")
            kid = str(s.get("kit_item_id") or "")
            if slug != kit_item_slug and kid != kit_item_slug:
                continue
        filtered.append(s)

    def score(s: dict[str, Any]) -> tuple[int, int]:
        role = str(s.get("role") or "")
        stage = str(s.get("stage") or "")
        path = str(s.get("path_repo") or s.get("path_cli") or "")
        pri = 0
        if role == "gameplay_ready":
            pri = 3
        elif "nobg" in stage or path.endswith("_nobg.png"):
            pri = 2
        elif "raw" in stage or "_raw" in path:
            pri = 1
        return (pri, len(path))

    if not filtered:
        return None
    best = max(filtered, key=score)
    path = str(best.get("path_repo") or "").strip()
    return path or None


def iter_review_rows(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    assets = manifest.get("assets") if isinstance(manifest.get("assets"), dict) else {}
    for asset_name, entry in assets.items():
        if not isinstance(entry, dict):
            continue
        brief = entry.get("brief") if isinstance(entry.get("brief"), dict) else {}
        atype = str(brief.get("type") or "")
        items = brief.get("items") if isinstance(brief.get("items"), list) else []
        if atype == "icon_kit" and items:
            for it in items:
                if isinstance(it, dict):
                    slug = str(it.get("slug") or it.get("id") or "").strip()
                    label = str(it.get("label") or it.get("id") or slug)
                    usage = str(it.get("usage") or brief.get("usage") or "")
                else:
                    slug = str(it).strip()
                    label = slug
                    usage = str(brief.get("usage") or "")
                if not slug:
                    continue
                path = resolve_canonical_path(entry, kit_item_slug=slug)
                rows.append(
                    {
                        "row_id": row_id_for(asset_name, slug),
                        "asset_name": asset_name,
                        "kit_item_slug": slug,
                        "label": label,
                        "type": atype,
                        "usage": usage,
                        "preview_path_repo": path,
                        "canonical_path_repo": path,
                        "review": get_review(
                            manifest, asset_name=asset_name, kit_item_slug=slug
                        ),
                    }
                )
            continue
        path = resolve_canonical_path(entry)
        rows.append(
            {
                "row_id": row_id_for(asset_name),
                "asset_name": asset_name,
                "kit_item_slug": None,
                "label": str(brief.get("name") or asset_name),
                "type": atype,
                "usage": str(brief.get("usage") or ""),
                "preview_path_repo": path,
                "canonical_path_repo": path,
                "review": get_review(manifest, asset_name=asset_name),
            }
        )
    return rows
```

Also add `replace_local_file(manifest_path, *, asset_name, kit_item_slug, source_abs, repo_root) -> dict` that:
1. loads manifest
2. resolves canonical path relative to repo
3. `shutil.copy2(source, dest)`
4. `set_review(..., status="replaced", source="local_file")`
5. saves manifest
6. returns `{ok, row_id, path_repo, review}`

- [ ] **Step 4: Run tests — expect PASS**

Run: `cd cli; python -m unittest test_asset_review -v`  
Expected: OK

- [ ] **Step 5: Commit**（仅当用户要求提交时）

```bash
git add cli/asset_review.py cli/test_asset_review.py
git commit -m "feat: asset review rows and soft review annotations"
```

---

### Task 2: CLI — `assets review` 命令

**Files:**
- Create: `cli/assets_cmds.py`
- Modify: `cli/gamefactory.py` — register group near other groups
- Test: extend `cli/test_asset_review.py` with click CliRunner smoke OR keep pure-function coverage + one integration test writing temp manifest

**Interfaces:**
- Produces CLI:
  - `assets review list --manifest <assets-manifest.json> --json`
  - `assets review accept --manifest … --asset NAME [--item SLUG]`
  - `assets review replace --manifest … --asset NAME [--item SLUG] --file ABS_PATH`
  - `assets review regenerate-plan --pipeline-manifest … --asset NAME [--item SLUG] --json`  
    → returns `{reset_task_id, commands: [...]}` using existing `pipeline_retry` / task match on `asset_id` containing `NAME__SLUG` or `asset==NAME`

**Regenerate plan matching:**
- If `--item` set: prefer task whose `artifacts.kit_item_slug == item` or `asset_id` endswith `__{item}` and step `image.generate`
- Else: prefer `{asset}.image.generate` via `pipeline_retry._pick_reset_task_id`
- Commands:  
  `python gamefactory.py pipeline reset --manifest <rel> --task-id <id> --cascade`  
  `python gamefactory.py pipeline run --manifest <rel> --jobs 4`

- [ ] **Step 1: Implement `register_assets_commands(cli)` in `assets_cmds.py`**

Wire Click group `assets` → `review` subgroup with the four commands; all `--json` friendly; accept/replace call `load_assets_manifest` / `save_assets_manifest` / `set_review` / `replace_local_file`.

- [ ] **Step 2: Register in `gamefactory.py`**

```python
from assets_cmds import register_assets_commands
register_assets_commands(cli)
```

- [ ] **Step 3: Manual smoke**

```bash
cd cli
python gamefactory.py assets review list --manifest ../output/<slug>/assets-manifest.json --json
```

Expected: JSON array of rows (or empty assets object handled gracefully).

- [ ] **Step 4: Commit**（用户要求时）

```bash
git add cli/assets_cmds.py cli/gamefactory.py cli/test_asset_review.py
git commit -m "feat: assets review CLI for accept/replace/list"
```

---

### Task 3: Electron IPC + preload types

**Files:**
- Modify: `gui/electron/main.mjs`
- Modify: `gui/electron/preload.cjs`
- Modify: `gui/src/vite-env.d.ts`

**Interfaces:**
- Produces `window.gameFactory`:
  - `assetsReviewList(assetsManifestRel: string) => CliResult<{rows: ReviewRow[]}>`
  - `assetsReviewAccept(assetsManifestRel, assetName, itemSlug?: string | null)`
  - `assetsReviewReplace(assetsManifestRel, assetName, itemSlug, absFilePath)`
  - `assetsReviewRegenerate(pipelineManifestRel, assetName, itemSlug?: string | null, jobs?: number)`  
    → runs regenerate-plan then reset+run via existing `runCli`（或返回 commands 由渲染进程触发 `pipelineRun`；**推荐主进程执行 reset cascade，再复用 `pipeline-run` IPC**）

**Resolve assets-manifest path:** from pipeline manifest meta `paths.output_dir` + `/assets-manifest.json`, or accept direct rel path from GUI.

- [ ] **Step 1: Add IPC handlers** calling CLI argv, e.g.  
  `["assets", "review", "list", "--manifest", abs, "--json"]`

- [ ] **Step 2: Expose in preload + vite-env**

```typescript
export interface AssetReviewRow {
  row_id: string;
  asset_name: string;
  kit_item_slug?: string | null;
  label: string;
  type: string;
  usage: string;
  preview_path_repo: string | null;
  canonical_path_repo: string | null;
  review: {
    status: "pending" | "accepted" | "replaced";
    source: "pipeline" | "regenerate" | "local_file";
    updated_at: string;
    note: string;
  };
}
```

- [ ] **Step 3: Smoke from DevTools or temporary button** — list returns rows.

- [ ] **Step 4: Commit**（用户要求时）

---

### Task 4: `AssetReviewPanel` UI

**Files:**
- Create: `gui/src/components/AssetReviewPanel.tsx`
- Modify: `gui/src/App.tsx` — `SidePanel` 增加 `"assets"`；顶栏按钮「资产」；choice「打开资产表」
- Optional CSS in existing panel stylesheet (reuse `side-panel` / `board-panel` classes)

**UI behavior:**
- Props: `assetsManifestRel`, `pipelineManifestRel`, `busy`, `onOpenBoard`, `onAfterRegenerate`（刷新看板）
- Filter chips: all / pending / accepted / replaced；search on label/asset_name
- List: thumbnail via `getMediaPreview(preview_path_repo)`；badge for status
- Detail: large preview；usage；paths；buttons 采纳 / 重生成 / 本地替换
- 本地替换：`pickFile({ filters: [{ name: "Images", extensions: ["png","webp","jpg","jpeg"] }] })` → `assetsReviewReplace`
- 重生成：确认后 `assetsReviewRegenerate`；无 `pipelineManifestRel` 时按钮 disabled + hint
- 空态：无 manifest 时提示先跑 pipeline

- [ ] **Step 1: Implement panel component**
- [ ] **Step 2: Wire App.tsx toggle + choice handler**（镜像「打开看板」）
- [ ] **Step 3: Hand-test** — 打开资产表、筛选、采纳、本地替换缩略图变化
- [ ] **Step 4: Commit**（用户要求时）

---

### Task 5: Docs

**Files:**
- Modify: `docs/AI-HANDOFF.md` — 短节「资产审查表」
- Modify: `docs/RELEASE-NOTES-UNRELEASED.md` — 增强条目
- Modify: Spec status already `confirmed` / stage → `implement` when starting Task 1

- [ ] **Step 1: Document** GUI 入口（侧栏「资产」）、三动作、软 review、kit 分行
- [ ] **Step 2: Commit**（用户要求时）

---

## Spec coverage checklist

| Spec 要求 | Task |
|-----------|------|
| GUI 资产面板 + 缩略图/映射 | 4 |
| 软 `review` 字段 | 1 |
| kit 按 item 分行 | 1 |
| 采纳 | 1–4 |
| 本地替换覆盖路径 | 1–4 |
| 重生成 reset cascade + run | 2–4 |
| 无 pipeline 时禁重生成 | 4 |
| 非目标未纳入 | — |

## Self-review notes

- 无 TBD 占位；`item_reviews` 键与 Spec 方案 A 一致。
- 重生成不把 API key 写入 manifest；只 reset/run。
- `pipeline_retry` 对 kit 需按 item 匹配 — Task 2 写明匹配规则。

---

## Execution handoff

Plan complete and saved to `docs/superpowers/plans/2026-07-24-asset-review-table.md`.

**Two execution options:**

1. **Subagent-Driven（推荐）** — 每任务新开子代理，任务间审查  
2. **Inline Execution** — 本会话按 executing-plans 连续做完  

Which approach?
