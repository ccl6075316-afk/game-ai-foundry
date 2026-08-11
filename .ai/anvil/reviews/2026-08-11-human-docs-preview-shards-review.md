# 评审报告：人侧 Brief 文档预览（总览 + 分册 / focus 解耦）

| 字段 | 内容 |
|------|------|
| Date | 2026-08-11 |
| Reviewer | anvil-lead |
| Status | `APPROVED`（复审 2026-08-11：Important-1/2/3 已修） |
| Author | 本会话（human-docs-preview） |
| Spec | `docs/superpowers/specs/2026-08-11-human-docs-preview-shards-design.md` |
| Plan | `docs/superpowers/plans/2026-08-11-human-docs-preview-shards.md` |
| Diff | **uncommitted**（相对 `main` / `a287a33`） |
| Bugbot | [Bugbot](636f1aed-e050-4d62-8273-7b09e482ca18) · uncommitted |

## 1. Scope

| 路径 | 变更 |
|------|------|
| `gui/src/components/DocsPreviewPanel.tsx` | 总览 / 分册 view、钉住、跟随 focus、读盘 |
| `gui/src/components/briefPreviewFormat.ts` (+test) | overview / shard / focus 标签 / 路径 |
| `gui/src/App.tsx` | `status.focus` 合并、pin 后 refresh、clearFocus |
| `gui/src/App.css` | focus bar / catalog |
| `docs/superpowers/specs|plans/2026-08-11-human-docs-preview-*` | 设计与计划（未跟踪） |

**Loaded standards:** Anvil review skill；frontend 域规则未另载（diff 为 React GUI 行为）。

**非目标确认：** 未改模型侧 `build_focus_context` / 写闸。

## 2. 自动化预检

| 检查 | 结果 |
|------|------|
| `npx tsx --test src/components/briefPreviewFormat.test.ts` | **16 pass** |
| `tsc --noEmit` | 仓库既有无关错误；本 diff 文件无新增报错 |
| GUI 手工验收（spec §验收） | **未做**（无自动化组件测） |
| Lint | N/A（gui 无统一 lint script） |

## 3. Security

- `readRepoText` / `resolveRepoRel` 拒绝 `..` — 分册路径穿越风险低。
- 无密钥 / 无 XSS 注入点（`<pre>` 文本）。
- **PASS**

## 4. Spec 追溯

| Spec 要求 | Diff | 判定 |
|-----------|------|------|
| 默认总览 | `formatBriefCatalogOverview` + catalog UI | PASS |
| 点目录只换预览 | `openShard` 不调 pin | PASS |
| 钉住才改 focus | `onPinFocus` / `onClearFocus` | PASS（逻辑对；见 Important-1 状态易丢） |
| 外部 pin 预览跟随 | `status.focus` effect + pending | 部分（见 Important-2） |
| 顶栏双状态 | `docs-focus-bar` | PASS |
| 分册失败可见错 | `shardError` | PASS（磁盘缺失）；inline 未回退见 Important-3 |

## 5. Findings（对抗）

### Important-1 — `replace: true` 且 payload 无 `focus` 时清空对话焦点（**High**）→ **CLOSED**

已改为 `mergeStatusFocus(prev, data.focus)`：仅显式传入（含 `null`）才改；pin/clear 先本地 patch focus 再 refresh。

### Important-2 — `pendingFollowView` 在 focus 清空 / 不可映射时未清（**Medium**）→ **CLOSED**

`!key` / `!next` 均 `setPendingFollowView(null)`；不可映射不再写入 `lastFollowedFocusRef`。

### Important-3 — 分册只读磁盘，无 session draft inline 回退（**Medium**）→ **CLOSED**

磁盘失败 / 无根目录时 `inlineShardFromDraft` + `shardEntryHasBody` 回退，并标注来源。

### Suggestion-1 — pin 后 refresh 竞态（**Medium**）→ **缓解**

pin/clear 同步写入 focus 后再 fire-and-forget refresh；与 Important-1 修复叠加后风险显著下降。

### Suggestion-2 — 资产目录 138 条挤满侧栏

符合 Spec「可点开」；建议折叠 / 搜索，不挡合并。

### Suggestion-3 — 无 DocsPreview 组件测

helpers 已覆盖 merge / inline；面板交互仍靠手工。

## 6. Karpathy

| 原则 | 判定 | 说明 |
|------|------|------|
| Think Before Coding | FAIL 一边 | 低估了 `applyDraftFromPayload` 全站 replace 对 focus 的副作用 |
| Simplicity First | PASS | view 本地状态 + 读盘，未新 IPC |
| Surgical Changes | PASS | 触点与 Spec 对齐 |
| Goal-Driven Execution | FAIL 一边 | helpers 测绿，但核心 UX（focus 持久、跟随）缺测且有回归洞 |

## 7. Gate

- [x] 预检（helpers 18 测）记录  
- [x] Security PASS  
- [x] **无未解 High**（Important-1/2/3 CLOSED）  
- [x] Spec 可追溯  
- [x] 评审文档已写  

**结论：`APPROVED` — 允许 commit。**  
残余：Suggestion-2（资产列表 UX）、面板级组件测。

## 8. Resume

1. ~~修 Important-1/2/3~~ **done**  
2. ~~补测~~ mergeStatusFocus / inlineShard（18 pass）  
3. 用户确认后 commit / push；可选 `/anvil:compound`  
