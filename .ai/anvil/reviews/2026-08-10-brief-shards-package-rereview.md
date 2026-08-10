# 评审报告：Brief 分册整包（复审 / Finding 修复后）

## 元数据

| 字段 | 值 |
|------|----|
| Reviewer | anvil-lead |
| MR / Commit | 未提交工作区（`main` ahead 1 + 整包未 commit） |
| Author | 分册 + focus + 下游 hydrate；复审针对 #1/#2 修复后 |
| Review Date | 2026-08-10 |
| Status | `APPROVED`（enrich / `apply_draft_replacement` 旁路已修） |
| Spec | `docs/superpowers/specs/2026-08-10-brief-catalog-shards-design.md` · `…/2026-08-10-document-focus-and-stable-ids.md` |
| Prior | `.ai/anvil/reviews/2026-08-10-brief-shards-downstream-hydrate-review.md`（曾标 APPROVED；本轮对抗复审） |

**Loaded standards:** Anvil review skill；Karpathy principles。

**变更规模：** Large（`brief_shards` + host_chat/GUI/CLI/docs/skills；~+1780/-83 已跟踪 + 未跟踪核心模块）

---

## 1. 自动化预检

| 检查项 | 命令 | 结果 | 备注 |
|--------|------|------|------|
| 单元测试 | `test_brief_shards` · `test_host_chat` · `test_topic_brainstorm` · `test_makeability_decisions` · `test_visual_target` · `test_pi_foundry_tools` · `test_godot_dev` | **PASS 211** | |
| Lint / 类型 | N/A | N/A | 无强制门 |

---

## 历史经验检查

| Source | Applied lens | Result |
|--------|--------------|--------|
| 下游 hydrate review Finding #1 | `deep_merge_brief` 是否全路径 strip | **已闭合**：入口强制 `_strip_structure_bodies_from_incoming`（~790）；commit/intent/chat 共用 |
| 下游 hydrate review Finding #2 | brainstorm 无 root | **已闭合**：`_candidate_has_structure_bodies` → `HostChatError` |
| 「还有没有同类旁路？」 | 扫非 `deep_merge` 的整稿写路径 | **新洞**：`apply_draft_replacement`（enrich 无 patches 分支）→ Finding #1（本轮） |

---

## 1.5 Spec / Harness

| 检查 | 结果 |
|------|------|
| Spec 可追溯 | 目录+分册、focus 读、审查 hydrate、资产 resolve — OK |
| 非目标 | 无向量 / 无大编辑器 — OK |
| 证据 | 211 单测；#1/#2 有回归测 |
| 数据 | fishing 仍厚 draft — 不挡平台 APPROVE，但端到端未验收 |

---

## 2. 安全扫描

| 类别 | 发现 | 严重级别 | 状态 |
|------|------|----------|------|
| 密钥 / 注入 / XSS | 无新面 | — | OK |
| 路径穿越 | `resolve_shard_path` 拒 `..` | — | OK |

**安全结论：** CLEAN

---

## 3. Karpathy

| 原则 | 结论 | 严重级别 |
|------|------|----------|
| Think Before Coding | #1/#2 修了，但「整稿写」还有 `apply_draft_replacement` 未纳入同一假设 | FAIL 一边 | High |
| Simplicity First | strip 收进 `deep_merge_brief` 比到处打补丁更简 | PASS | — |
| Surgical Changes | 修复面与 finding 对齐 | PASS | — |
| Goal-Driven Execution | commit strip / brainstorm 拒写有测 | PASS | — |

**Karpathy Score:** 3/4

---

## 4. 对抗式抽查（修复点 + 旁路）

### 已验证闭合

| 项 | 证据 |
|----|------|
| commit/intent/chat merge 丢结构正文 | `deep_merge_brief` L790；`test_apply_parsed_commit_brief_strips_scene_bodies` |
| catalog ref 仍可合并 | `test_deep_merge_brief_allows_catalog_scene_refs` |
| brainstorm 无 root + 厚 scenes | `test_apply_rejects_fat_scenes_without_project_root` |
| closer/verifier hydrate | 既有测 + 211 绿 |
| `load_brief_full` 场景正文 | `test_load_brief_full_hydrates_catalog_scene_summary` |
| Board pin await | `App.tsx` / `BoardVtStrip` |

### 新发现边界

| 路径 | 行为 |
|------|------|
| `run_brief_enrich` 无 `brief_patches` 且 `project_root is None` | `canonicalize` 跳过 → `apply_draft_replacement` 对 `project` 做 `dict.update`，**可把 scenes/systems 正文整段写进 session** |
| 同路径有 root | canonicalize 后写薄 ref — OK |
| `deep_merge` 对 **assets** | 仍允许厚资产条目进 merge（strip 只动 scenes/systems） |

---

## 5. 发现

### Critical

无。

### Important

1. ~~**`apply_draft_replacement` / enrich 整稿分支仍可灌结构正文**~~ **已修**  
   - `apply_draft_replacement` 入口强制 `_strip_structure_bodies_from_incoming`。  
   - 单测：`test_apply_strips_fat_scene_bodies_keeps_base_catalog`、`test_enrich_full_draft_without_root_strips_scene_bodies`。

### Suggestions

- GUI 无常驻「当前 focus」指示（UX）。  
- `build_focus_context`：`load_shard` 失败仍 `except: pass`，无 `focus_error`。  
- `audit_brief_for_export`：`audit_catalog_refs` 异常被吞（`brief.py` ~2246–2247）。  
- `deep_merge` 未 strip **assets** 厚条目（catalog 工程下应用 patches/canonicalize）。  
- fishing 数据未 `brief shard migrate`。  
- `host_chat` 膨胀；P2 再拆模块。

---

## 6. 相对上轮 hydrate review

| 项 | 状态 |
|----|------|
| deep_merge 全路径 strip | **闭合** |
| brainstorm 无 root | **闭合** |
| enrich / `apply_draft_replacement` | **本轮新 Important** |
| 单测 | 211 PASS（↑） |

说明：上轮 hydrate review 文末曾写 APPROVED；**本轮对抗复审以本文件为准**，在 enrich 旁路修掉前不维持 APPROVED。

---

## 7. 裁决

**`APPROVED`**（复审修复后 2026-08-10）

| Finding | 状态 |
|---------|------|
| deep_merge / commit strip | 已闭合 |
| brainstorm 无 root | 已闭合 |
| enrich / `apply_draft_replacement` strip | **已闭合** |

Suggestions（GUI focus、`focus_error`、validate 吞异常、assets 厚合并、fishing migrate）不挡合并。

---

## 8. Resume

1. ~~enrich 旁路~~ **done**  
2. （可选）Suggestions + fishing migrate  
3. **next**：用户确认后 commit 整包
