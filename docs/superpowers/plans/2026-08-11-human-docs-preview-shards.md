# Human Docs Preview (Shards) Implementation Plan

> **For agentic workers:** Implement task-by-task. Checkbox tracking. Spec: `docs/superpowers/specs/2026-08-11-human-docs-preview-shards-design.md`.

**Goal:** Docs panel shows a catalog overview by default; opening a shard only changes local preview; explicit pin / external `pinBriefFocus` syncs conversation focus and (for external pin) preview.

**Architecture:** Keep session draft thin. Add local `DocsView` in `DocsPreviewPanel`. Load shard JSON via existing `readRepoText` under project root (`scenes|systems|assets`). Sync preview when `status.focus` identity changes. Extend overview formatter + clickable catalog UI.

**Tech Stack:** React + Electron IPC (`readRepoText`, `hostChatFocus`), existing `briefPreviewFormat` tests (node:test).

## Global Constraints

- Preview browse must not call `hostChatFocus`.
- No full hydrate of all shards into overview.
- Do not change model-side focus / write-gate semantics.
- Commits only when user asks.

---

### Task 1: Overview + shard format helpers (TDD)

**Files:** `gui/src/components/briefPreviewFormat.ts`, `briefPreviewFormat.test.ts`

- [x] Add `DocsView` type export (or keep in Docs panel; shared label helpers here)
- [x] `formatBriefCatalogOverview(draft, status)` — facade + lists marked 分册
- [x] `formatShardDocument(kind, id, raw)` — readable JSON/fields
- [x] `formatFocusLabel(focus)` / `formatDocsViewLabel(view)`
- [x] Tests for overview (no notes dump), labels, shard body

### Task 2: DocsPreviewPanel view / pin / load

**Files:** `DocsPreviewPanel.tsx`, CSS if needed

- [x] State: `docsView` overview | shard
- [x] Toolbar: 正在看 / 对话焦点 / ←总览 / 钉住给对话
- [x] Overview: clickable scene/system/asset rows
- [x] Load shard path from `activeBriefRel` + kind/id via `readRepoText`
- [x] Pin → `onPinFocus` / clear; browse never pins
- [x] Follow `status.focus` when focus key changes (pending if not on session-brief)

### Task 3: App wiring

**Files:** `App.tsx`

- [x] Pass `onPinFocus` / ensure `pinBriefFocus` supports `clear`
- [x] After board/VT pin, status refresh so Docs panel sees new focus (if not already)

### Task 4: Verify

- [x] `cd gui && npm test -- briefPreviewFormat` (or project test script)
- [ ] Manual checklist from spec §验收 (document residual)

## Resume

After Task 4: optional Anvil review; user commit/push.
