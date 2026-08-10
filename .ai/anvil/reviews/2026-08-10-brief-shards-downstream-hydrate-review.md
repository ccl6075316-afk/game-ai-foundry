# 评审报告：Brief 分册下游 hydrate + closer/brainstorm 跟改

## 元数据

| 字段 | 值 |
|------|----|
| Reviewer | anvil-lead |
| MR / Commit | 未提交工作区（`main` ahead 1 + 整包未 commit） |
| Author | 本会话续作（审计下游 → closer / load_brief_full / brainstorm / Board pin） |
| Review Date | 2026-08-10 |
| Status | `SUPERSEDED` → 见 `2026-08-10-brief-shards-package-rereview.md`（复审发现 enrich 旁路） |
| Spec | `docs/superpowers/specs/2026-08-10-brief-catalog-shards-design.md` · `…/2026-08-10-document-focus-and-stable-ids.md` |
| Plans / Audit | shards-search · focus P0/P1 · `docs/anvil/brainstorms/2026-08-10-brief-shards-downstream-audit.md` |
| Prior review | `.ai/anvil/reviews/2026-08-10-brief-shards-focus-p0p1-review.md`（曾 CHANGES REQUESTED） |

**Loaded standards:** Anvil review skill；Karpathy principles（`anvil-karpathy`）。无额外 domain vendor skill（Python CLI + 少量 GUI）。

**变更规模：** Large（整包 `brief_shards` + host_chat/GUI/CLI/docs；本波侧重下游读侧）

---

## 1. 自动化预检

| 检查项 | 命令 | 结果 | 备注 |
|--------|------|------|------|
| Lint | N/A | N/A | 仓库无强制 CLI lint 门 |
| 类型检查 | N/A | N/A | Python 无统一 mypy 门 |
| 单元测试 | `python -m unittest test_brief_shards test_host_chat test_topic_brainstorm test_makeability_decisions test_visual_target test_pi_foundry_tools test_godot_dev` | **PASS 208** | 含本波新测 |

---

## 历史经验检查

| Source | Applied lens | Result |
|--------|--------------|--------|
| 前次 p0p1 review：`deep_merge` 绕过 focus | 全路径扫 `deep_merge_brief` 调用点 | chat 路径已 strip；**commit / intent 预合并仍裸 merge** → Finding #1 |
| 前次：`void pinBriefFocus` | GUI await | VT + Board 已 await；Board 仍为 click 内 fire-and-forget Promise → Suggestion |
| Spec：Brief=目录、分册=正文 | closer/load_brief_full/brainstorm 是否仍薄读 | 本波已跟；数据面 fishing 未迁 → Suggestion |

---

## 1.5 Harness / Spec 可追溯

| 检查 | 结果 |
|------|------|
| Spec → 行为 | 分册 IO、focus 读、审查 hydrate、资产 resolve — 可追溯 |
| 非目标 | 未引入向量检索；未做大 Brief 编辑器 — OK |
| 验收证据 | 单测覆盖 hydrate closer、load_brief_full summary、brainstorm canonicalize |
| Resume | 审计表已更新；剩 commit 旁路 + fishing 数据 |

---

## 2. 安全扫描

| 类别 | 发现 | 严重级别 | 状态 |
|------|------|----------|------|
| 硬编码密钥 | 无 | — | OK |
| 路径穿越 | `resolve_shard_path` 拒 `..`（既有） | — | OK |
| 工具面 | search/load 只读白名单（既有） | — | OK |
| XSS / CVE | 本波无新前端注入面 | — | OK |

**安全结论：** CLEAN

---

## 3. Karpathy 对抗式原则

| 原则 | 对抗式问题 | 作者回答（推断） | 结论 | 严重级别 |
|------|------------|------------------|------|----------|
| Think Before Coding | 假设「所有读 brief 的人都会走 hydrate」？ | `load_brief_full` 已 hydrate；但 **commit 写路径仍可整稿灌结构** | FAIL 一边 | High |
| Simplicity First | `_hydrate_draft_for_llm` 是否多余？ | 与 enrich/Critic 共用 `hydrate_brief_for_review`，薄包装合理 | PASS | — |
| Surgical Changes | `load_brief_full` 全局 hydrate 是否过宽？ | 修 godot/playtest/validate 一处通吃；代价是 pipeline 多读场景分册 | PASS（有意识） | — |
| Goal-Driven Execution | 测试是否证明「closer 看见分册 notes」？ | 有断言 closer/verifier payload 含 SHARD notes | PASS | — |

**Karpathy Score:** 3/4（Think：commit 旁路未写进假设清单）

---

## 4. 对抗式维度评审（摘要）

### 4.1 设计

- `_hydrate_draft_for_llm` + `load_brief_full` 回填 scenes：正确绕开 `normalize_scenes` 丢正文。  
- enrich 仍 `enforce_focus=False`：与「补全可跨屏」一致，可接受。  
- **问题：** chat 用 strip，commit_brief / intent 预合并仍裸 `deep_merge_brief` — 纪律不对称。

### 4.2 功能

- closer/verifier hydrate + 指纹仍用薄 draft：正确。  
- brainstorm 无 `bound_brief_rel` → `_project_root_for_session` 为 None → **不 canonicalize**，厚 scenes 可写回 session（测试用 patch root 才绿）。  
- `build_focus_context`：`load_shard` 失败仍 `except ValueError: pass`，模型可能以为已 focus。

### 4.3–4.7

- host_chat 继续膨胀 — 阶段债，不挡本波。  
- Board pin 已 await，但缩略图 click 仍先 pin 再开灯箱；与发聊并发竞态已缓解未根除。

### 4.8 测试

- 新测覆盖 closer hydrate、load_brief_full、brainstorm 读/写 — 行为测，非空跑。  
- **缺：** commit_brief / intent 预合并 strip 回归测；无 bound root 时 brainstorm 应失败或告警的契约测。

---

## 5. 发现

### Critical

无。

### Important（合并前建议修）

1. ~~**`deep_merge_brief` 旁路仍在 commit / intent 预合并路径**~~ **已修**  
   - `deep_merge_brief` 入口统一 strip；`test_apply_parsed_commit_brief_strips_scene_bodies` 覆盖。

2. ~~**topic brainstorm 无工程绑定时静默跳过 canonicalize**~~ **已修**  
   - 无 root 且 candidate 含结构正文 → `HostChatError`；`test_apply_rejects_fat_scenes_without_project_root`。

### Suggestions

- GUI 仍无「当前 focus: scene/xxx」常驻提示（前次 Important #3 UX）。  
- `build_focus_context` load 失败应设 `focus_error`（前次 Suggestion，未改）。  
- `audit_brief_for_export` 中 `audit_catalog_refs` 异常被 `except: pass` 吞掉 — 校验假绿风险。  
- fishing **数据未 migrate** — 平台代码无法单独验收「薄目录真工程」。  
- Board pin：交互层仍是 `void (async () => await pin)()`，极端连点仍可能竞态。

---

## 6. 相对前次 review 的闭环

| 前次 Important | 本轮状态 |
|----------------|----------|
| chat `deep_merge` 改正文 | **已修**（strip） |
| `pinBriefFocus` await | **已修**（VT + Board） |
| 无 focus UX 提示 | **未修**（降为 Suggestion） |
| closer 读侧盲 | **已修**（本波） |
| godot/playtest 丢 summary | **已修**（`load_brief_full` hydrate） |
| brainstorm 不 canonicalize | **半修**（有 root 才 canon → Finding #2） |

---

## 7. 裁决

**`APPROVED`**（复审 2026-08-10）

| Finding | 修复 |
|---------|------|
| #1 commit/intent `deep_merge` 旁路 | `deep_merge_brief` **内部**强制 `_strip_structure_bodies_from_incoming`；commit 单测覆盖 |
| #2 brainstorm 无 root | 有结构正文且无 project_root → `HostChatError`；单测覆盖 |

Suggestions（GUI focus 条、`focus_error`、fishing migrate）不挡合并。

---

## 8. Resume

1. ~~Finding #1/#2~~ **done**  
2. （可选）Suggestions + fishing migrate  
3. **next**：用户确认后 commit 整包
