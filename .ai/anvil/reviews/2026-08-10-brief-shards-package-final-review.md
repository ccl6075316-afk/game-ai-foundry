# 评审报告：Brief Catalog + Shards + Focus（整包总审）

## 元数据

| 字段 | 值 |
|------|----|
| Reviewer | anvil-lead |
| MR / Commit | 未提交工作区（`main` ahead 1；核心 `brief_shards.py` 等仍 untracked） |
| Author | 多会话：shards-search → focus P0/P1 → 下游 hydrate → 旁路收口 |
| Review Date | 2026-08-10 |
| Status | **`APPROVED`** |
| Spec | `docs/superpowers/specs/2026-08-10-brief-catalog-shards-design.md` · `…/2026-08-10-document-focus-and-stable-ids.md` |
| Plans | shards-search · focus-read · focus-write-p1 |
| Audit | `docs/anvil/brainstorms/2026-08-10-brief-shards-downstream-audit.md` |
| Prior reviews | search / p0p1 / downstream-hydrate / package-rereview（均已并入本总审） |

**Loaded standards:** Anvil review skill；Karpathy principles。

**变更规模：** Large  
- 已跟踪 diff ≈ **+1867 / −83**（27 files）  
- 未跟踪核心：`cli/brief_shards.py`（~1012 行）+ `test_brief_shards.py` + specs/plans/reviews  

---

## 1. 自动化预检

| 检查项 | 命令 | 结果 |
|--------|------|------|
| 单元测试 | `test_brief_shards` `test_host_chat` `test_topic_brainstorm` `test_brief_enrich` `test_makeability_decisions` `test_visual_target` `test_pi_foundry_tools` `test_godot_dev` `test_brief_scenes_systems` | **PASS 239** |
| Lint / 类型 | N/A | 无强制门 |

---

## 历史经验检查

| Source | Lens | Result |
|--------|------|--------|
| p0p1：deep_merge 绕 focus | 全路径 strip | **闭合**（`deep_merge_brief` 入口强制 strip） |
| hydrate review：commit/intent 旁路 | 同上 | **闭合** |
| hydrate review：brainstorm 无 root | 拒写厚结构 | **闭合** |
| package rereview：enrich / `apply_draft_replacement` | 入口 strip | **闭合** |
| 「还有同类旁路吗？」 | 写路径再扫 | scenes/systems 主路径已闸；assets 厚合并仍开放 → Suggestion |

---

## 1.5 Spec / 主路径可追溯

对照 Foundry 正常用法（策划 → 审查 → 北极星 → export → pipeline → Godot）：

| 步骤 | Spec/产品要求 | 实现 | 总审 |
|------|---------------|------|------|
| 主对话薄目录 + focus | focus Spec | `build_focus_context` + patches focus 闸 | PASS |
| 分册 IO / migrate / search | shards Spec | `brief_shards` + CLI | PASS |
| 审查见全部分册正文 | 用户钉死 | Critic hydrate | PASS |
| closer 读分册 | 下游审计 | `_hydrate_draft_for_llm` | PASS |
| enrich / brainstorm 写分册 | 单源正文 | hydrate + canonicalize / strip | PASS |
| 北极星 VR 在分册 | shards Spec | VT hydrate + upsert | PASS |
| 资产 resolve | shards Spec | `resolve_asset_specs` via `load_brief*` | PASS |
| pipeline / godot / playtest | 下游 | `load_brief_full` hydrate scenes | PASS |
| 整稿禁止改正文 | focus + shards | deep_merge + apply_draft_replacement strip | PASS |
| 工程数据迁移 | Spec 非自动 | fishing **未 migrate** | 数据轨，不挡平台 APPROVE |

非目标保持：无向量、无大 Brief 编辑器、审查不灌全量资产正文。

---

## 2. 安全扫描

| 类别 | 结论 |
|------|------|
| 密钥 / XSS / 新网络面 | 无 |
| 路径穿越 | `resolve_shard_path` 拒 `..` |
| 工具白名单 | search/load 只读；migrate 不进 brief 白名单 |

**安全结论：** CLEAN

---

## 3. Karpathy

| 原则 | 结论 | 备注 |
|------|------|------|
| Think Before Coding | PASS | 旁路经多轮复审收口；假设「写路径都要 strip/canonicalize」已落地 |
| Simplicity First | PASS（有债） | 无向量正确；`host_chat.py` ~3850 行膨胀为阶段债 |
| Surgical Changes | PASS | 改动可追溯 Spec / 审计表 |
| Goal-Driven Execution | PASS | 239 测覆盖 hydrate、strip、focus、canonicalize、VT |

**Karpathy Score:** 4/4（Simplicity 记债但不扣到 FAIL）

---

## 4. 对抗式维度（整包）

### 4.1 设计 — PASS
Brief=目录、分册=正文、focus=光标，边界清晰。数值表 v1 放 `systems[].tuning`，不强制第三层 — 符合 Spec。

### 4.2 功能 — PASS（已知残留见 Suggestions）
写闸：chat / commit / intent / enrich / brainstorm 对 **scenes/systems** 正文已收口。  
读闸：对话 focus；审查/closer/enrich/VT/zh/`load_brief_full` hydrate。

### 4.3 复杂度 — FINDINGS（非挡）
`host_chat` 过大；hydrate/strip 有多处薄封装（`_hydrate_draft_for_llm`）可接受。

### 4.4–4.7 — PASS
命名大体诚实；skills/docs 已跟。Board pin 已 await。

### 4.8 测试 — PASS
行为测覆盖关键旁路；非空跑。

---

## 5. 发现

### Critical / Important

无（此前 Important 均已修且有回归测）。

### Suggestions（不挡合并）

1. **GUI 常驻显示当前 `focus`**（无 focus 时提示点选）— UX。  
2. **`build_focus_context`**：`load_shard` 失败应设 `focus_error`，勿静默 `pass`。  
3. **`audit_brief_for_export`**：`audit_catalog_refs` 异常勿整段吞掉（假绿风险）。  
4. **`deep_merge` / replacement 未 strip 厚 assets** — catalog 工程应用 patches/canonicalize 写资产分册。  
5. **`host_chat` 拆模块**（focus / patches / makeability）— 可维护性。  
6. **fishing `brief shard migrate` + 瘦 description** — **产品数据轨**；平台 APPROVE ≠ 该工程已上新模型。  
7. ui_wireframe / 侧栏展开分册 — 可后置。

---

## 6. 写路径收口清单（总审核对）

| 入口 | 机制 | 状态 |
|------|------|------|
| `deep_merge_brief` | 强制 strip scenes/systems 正文 | OK |
| `apply_draft_replacement` | 强制 strip | OK |
| chat patches | `enforce_focus` + upsert 分册 | OK |
| enrich patches | upsert；整稿 canonicalize 或 strip | OK |
| brainstorm apply | canonicalize 或无 root 拒厚结构 | OK |
| closer | hydrate 读 + patches 写 | OK |
| VT pick | shard `visual_reference` | OK |

---

## 7. 裁决

**`APPROVED`**

平台侧 Catalog + Shards + Focus + 下游 Foundry 主路径读写与写闸已对齐 Spec，单测 **239 PASS**，安全干净。  
合并/提交前请把 **untracked** `brief_shards.py`、specs、plans、reviews 一并纳入版本库。

**明确不在本 APPROVE 范围内：** fishing 工程数据迁移与 description 语义搬家（建议单独任务 + 备份后 `brief shard migrate`）。

---

## 8. Resume

1. ~~平台整包~~ **APPROVED**  
2. **next（用户）**：commit 本包（含 untracked）  
3. **next（数据）**：fishing migrate  
4. （可选）Suggestions 1–5
