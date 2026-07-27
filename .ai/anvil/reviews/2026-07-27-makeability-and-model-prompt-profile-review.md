# 评审报告：`2026-07-27-makeability-and-model-prompt-profile`

## 元数据

| 字段 | 值 |
|------|-----|
| Reviewer | anvil-lead |
| MR / Commit | 工作区未提交（两刀叠放） |
| Author | anvil-code / doers |
| Review Date | 2026-07-27 |
| Status | `APPROVED_WITH_NITS` |
| Spec Trace | [`brief-makeability-critic`](../../docs/anvil/brainstorms/2026-07-27-brief-makeability-critic.md) + [`model-prompt-capability-profile`](../../docs/anvil/brainstorms/2026-07-27-model-prompt-capability-profile.md) |
| Plans | [`…-makeability…-plan`](../../docs/anvil/plans/2026-07-27-brief-makeability-critic-plan.md) · [`…-model-prompt…-plan`](../../docs/anvil/plans/2026-07-27-model-prompt-capability-profile-plan.md) |
| Loaded standards | Anvil review skill；solutions 无直接命中 makeability/profile |

---

## 1. 自动化预检

| 检查项 | 命令 | 结果 | 备注 |
|--------|------|------|------|
| Lint | N/A | N/A | |
| 类型检查 | `gui npm run typecheck` | PASS | |
| 单元测试 | makeability×3 + profile×3 + production + host_chat | PASS | **84** OK |
| GUI 单测 | `briefPreviewFormat.test.ts` | PASS | 12 OK |

---

## 历史经验检查

| Source | Applied lens | Result |
|--------|--------------|--------|
| resolve≠wire（风格栈） | profile 只改 assemble，不改 LLM fields / 不静默改 brief | PASS |
| Design vs Production | intent→brief 门闩；detail→sidecar→production.makeability | PASS |
| ACP critical-patterns | 本 diff 无关 | N/A |

---

## 1.5 Harness / Merge Gate

| 检查 | 结果 |
|------|------|
| Spec 可追溯（两刀） | PASS — makeability FR1–6；profile FR1–5 均有对应代码 |
| 非目标未越界 | PASS — 无圆桌、无用户 dialect 开关、无 generate 前重装主路径、无 `seed` profile_id |
| Resume / Code Status | PASS — 两 plan 均 executed + pause |
| 并行状态源 | PASS — 无第二套 task JSON |
| 叠刀风险 | **Nit** — 建议提交时拆成 2 commit（见下） |

---

## 2. 安全扫描

CLEAN — Critic/craft 无密钥回显；sidecar/production 为本地 JSON。

---

## 3. Karpathy

| 原则 | 结论 | |
|------|------|--|
| Think Before Coding | 意图/细节二分 + 模型档案查表，与已确认 Spec 一致 | PASS |
| Simplicity First | 无新工种；profile 六档查表；未引入大语料库 | PASS |
| Surgical Changes | 偶有 `production.py` 大块与 `asset_pipeline` 传播字段，均可追溯 | PASS |
| Goal-Driven | 门闩/sidecar/assemble 差异/匹配均有单测 | PASS |

**Karpathy Score:** 4/4

---

## 4. 对抗式维度

### 4.1 Design — PASS（附已知产品跳变）

- Makeability：子 LLM + export 门闩 + production 物化，符合方案 2。
- Profile：`volc_*` + seedream/seedance 别名，符合「不用 seed 族名」。
- **Known breaking（不挡 approve）**：`brief chat export` / GUI 保存 Brief **强制**制作审查（需 host LLM Key）。纯文件 `brief validate` / 手写 brief 不受影响。与 Spec「export 前强制」一致，发版说明须写清。

### 4.2 Functionality — PASS（Nits）

| ID | 严重度 | 发现 | 建议 |
|----|--------|------|------|
| N1 | Low | animation handoff 写了 `video_model`，未写 `video_prompt_profile_id`（only still `prompt_profile_id`） | 可选补字段；不挡 |
| N2 | Low | GUI `has_review`/`intent_count` 用 `??` 合并，部分更新若漏字段可能粘旧值 | 全量 status 路径 OK；partial patch 时注意 |
| N3 | Low | `prefer_soft_style` 几乎全档追加固定英文尾句，可能稀释精灵/UI 提示词 | 后续可按 class 收窄；非 Spec 违反 |
| N4 | Low | Critic 分类质量无测（intent vs detail） | 残留产品风险；结构门闩已测 |

门闩路径抽查：`export_brief` → `assert_makeability_exportable`（missing/stale/intent）；GUI `briefMakeabilityExportReady` 四条件；`derive` 读 sidecar — 与 Spec 一致。

### 4.3 Complexity — PASS

- `apply_video_prompt_profile` / assemble profile 分支可读。
- 未引入用户开关矩阵。

### 4.4 Naming — PASS

- `volc_image` / `volc_video` / `makeability_review` / `intent_gaps` 与 Spec 一致；无独立 `seed` profile_id。

### 4.5–4.7 Comments / Style / Context — PASS

- skill + AI-HANDOFF / HOST-CHAT / product-host / asset-planner 已跟。
- `docs/anvil/plans/` 仍被根 `.gitignore` 的 `plans/` 误伤 — **提交 plan 需 `git add -f`**（流程 Nit）。

### 4.8 Tests — PASS

84 CLI + 12 GUI format；覆盖 critic 解析、三门闩、sidecar merge、profile 匹配、gpt vs gemini assemble 差异、seedance video 后处理。

---

## 5. 发现汇总

| ID | 严重度 | 状态 | 说明 |
|----|--------|------|------|
| N1–N4 | Low | 可后续 | 见上 |
| B1 | Info | 发版注意 | host-chat 导出强制 makeability |
| B2 | Info | 提交注意 | 两刀拆 commit；plan 文件可能需 `-f` |

**无 Blocking / High 必须改项。**

---

## 6. 结论

**`APPROVED_WITH_NITS`** — 可以提交。

建议提交切分：

1. `feat: makeability critic, export gate, production merge, GUI`  
2. `feat: media prompt profiles for craft/assemble by model`

下一步：你说 **提交**（可指定拆/合）即可；Nits 不强制本轮修。
