# 评审报告：`2026-08-21-host-layer-refactor`

## 元数据

| 字段 | 值 |
|------|----|
| Reviewer | anvil-lead |
| MR / Commit | `origin/main..HEAD`（6 commits：`73aa273`…`0b48277`） |
| Author | dual-agent code（doer + lead） |
| Review Date | 2026-08-21 |
| Status | `BLOCKED` |
| Plan | [`docs/anvil/plans/2026-08-20-host-layer-refactor-plan.md`](../../docs/anvil/plans/2026-08-20-host-layer-refactor-plan.md) |
| Loaded standards | Anvil review template；历史 lens（ARCHITECTURE / Host Plan / prior VT·host-chat reviews）；无 frontend/backend domain 专规命中 |

---

## 1. 自动化预检

| 检查项 | 命令 | 结果 | 备注 |
|--------|------|------|------|
| Lint | N/A | N/A | 仓库无统一 Python lint 门禁 |
| 类型检查 | `gui` typecheck（T4 阶段） | PARTIAL | 既有 2 个无关失败；本次改动文件无新增 lint |
| 单元测试 | `pytest test_host_* test_pipeline_heal test_safe_cli test_visual_target` | FAIL | Host/heal/safe：**全绿**；`test_visual_target` **3 fail**（`test_generate_*`，CJK assemble，见 §5 Medium） |

Host 相关子集（不含 generate）：`test_host_run_assets` + `test_host_retry_asset` + `test_pipeline_heal` + `test_safe_cli` + VT status/catalog → **PASS**。

---

## 历史经验检查

| Source | Applied lens | Result |
|--------|--------------|--------|
| Host Plan / Handoff | validation 必须 `--run-prompts` | PASS（fix_commands + deferred_run 会带 flag） |
| Host Plan | 同指纹最多 2 轮 | PASS（实现存在；纯 validation 路径测过） |
| Inventory「禁止第三套 fix」 | Host 成功/失败均 early return | PASS（`App.tsx` host 分支均 `return`） |
| safe_cli 不裸放行 craft | 仅 `host retry/run` | PASS |
| VT 单源 / 分册 VR | Electron thin wrap CLI | PASS（hydrate 已删；status 测过 shard） |
| 假成功 / CAS | `ok`/`complete` 门闩 | 见 High #1 旁证 + Medium #3 |
| code heal 后必须续跑 | heal 复位后须 `run_pipeline` | **FAIL → High #1** |
| product-host「勿假装自动重跑」 | 与 Host auto-fix 冲突 | **FAIL → Medium #2** |

---

## 2. 安全扫描

| 类别 | 发现 | 严重级别 | 状态 |
|------|------|----------|------|
| 硬编码密钥 | 无 | — | OK |
| 注入风险 | Host IPC 仍走 `runCli` + allowlist；未开放裸 shell | — | OK |
| XSS | 无新增 HTML 拼接 | — | OK |
| 依赖 CVE | 无依赖变更 | — | OK |
| 日志敏感数据 | 无新增密钥日志 | — | OK |

**安全结论：** CLEAN

---

## 3. Karpathy 对抗式原则

| 原则 | 对抗式问题 | 作者回答（显式或推断） | 结论 | 严重级别 |
|------|------------|--------------------------|------|----------|
| Think Before Coding | 未写下的假设？ | 假设「diagnose_and_heal(apply=True) 之后总能靠 fix_commands 续跑」——对 **纯 code-owned** 失败不成立（heal 后 `needs_hermes` 为空 → `can_auto_fix=False`） | FAIL | High |
| Simplicity First | 能否删 50%？ | `cli/host/` 薄封装合理；App 仍保留整段 legacy 循环作 fallback，可接受过渡 | PASS | — |
| Surgical Changes | 每行可追溯？ | T1–T6 均可对上 Plan；`visual_target` preview 字段属 T5 兼容 GUI | PASS | — |
| Goal-Driven Execution | 测试能否证伪？ | validation 路径有测；**code-heal 后无 failed、应 re-run** 无测 → 漏洞未被抓住 | FAIL | High |

**Karpathy Score:** 2/4

---

## 4. 对抗式维度评审

### 4.1 设计：它是否应该存在？

| 行号 | 提问 | 作者回答 | 评审判断 | 严重级别 |
|------|------|----------|----------|----------|
| `cli/host/*` | Host 包是否必要？ | 从 GUI 抽编排到可测 CLI，对齐架构目标 | PASS | — |
| `App.tsx` 双路径 | 为何保留 legacy？ | Host 缺失时 fallback | PASS（过渡） | Low |

**维度结论：** PASS

### 4.2 功能：作者遗漏了什么？

| 行号 | 提问 | 作者回答 | 评审判断 | 严重级别 |
|------|------|----------|----------|----------|
| `cli/host/run_assets.py` ~192–238 | code heal 后 `failed_count=0` 怎么办？ | 直接 `needs_agent` | **错误** — 应 `run_pipeline` 续跑 | High |
| `App.tsx` ~3344–3347 | PM「处理失败」`runPrompts:false`？ | 靠 fix_commands 内 `--run-prompts` | PASS（validation） | — |
| `App.tsx` ~3352–3362 | Host `ok` 即「全部完成」？ | 未走 `showRunSuccess` 的 pending 校验 | 弱于 handleRun | Medium |
| VT generate 测试 | 本 MR 是否引入？ | `craft=False` + CJK brief 触发守卫；与 T5 status 改动无关 | 既有债 | Medium |

**已检查关键边界：**
- [x] 空输入 / null（retry 无 asset/task → ValueError）
- [x] max_rounds 指纹
- [x] needs_agent / unknown
- [ ] **code-only heal 后零失败续跑** ← 缺口
- [x] safe_cli 白名单
- [x] 外部 CLI 失败（IPC ok=false → ready false）

**维度结论：** FINDINGS

### 4.3 复杂度

| 行号 | 提问 | 作者回答 | 评审判断 | 严重级别 |
|------|------|----------|----------|----------|
| `run_assets.py` ~319 行 | 能否更短？ | fix 执行 + 循环耦合，可接受 | PASS | Nit：可抽 `_repair_once` |

**维度结论：** PASS

### 4.4 命名

| 行号 | 提问 | 作者回答 | 评审判断 | 严重级别 |
|------|------|----------|----------|----------|
| `stopped_reason=error` | auto_fix=false 时也叫 error？ | 语义略宽 | Nit | Low |

**维度结论：** PASS

### 4.5 注释

| 行号 | 提问 | 作者回答 | 评审判断 | 严重级别 |
|------|------|----------|----------|----------|
| `product-host.md:108` | 硬规则 5 与 Host 行为冲突 | T6 未改掉该句 | Medium | Medium |

**维度结论：** FINDINGS

### 4.6 风格与一致性

按任务分 commit，风格与周边 Click/IPC 一致。

**维度结论：** PASS

### 4.7 上下文

删除 Electron hydrate 双份判定 → 系统更健康。Host 收口方向正确。  
遗留：App 内 `attemptPipelineAutoRepair` 仍大段存在（fallback 需要）。

**维度结论：** PASS（带 Medium 文档债）

### 4.8 测试

| 行号 | 提问 | 作者回答 | 评审判断 | 严重级别 |
|------|------|----------|----------|----------|
| `test_host_run_assets.py` | 是否覆盖 code heal？ | 仅 validation / max_rounds / needs_agent | 缺场景 | High |
| `test_visual_target` generate | 全量红？ | 3 fail 既有 CJK | 不阻塞本 MR 设计，但污染 CI 信号 | Medium |

**维度结论：** FINDINGS

---

## 5. 发现项摘要

### Critical（阻塞提交）

（无）

### High（阻塞合并 / 阻塞 APPROVE）

| # | 维度 | 行号 | 描述 | 必须动作 |
|---|------|------|------|----------|
| H1 | 功能 / 测试 | `cli/host/run_assets.py` 192–238；对照 `pipeline_heal.diagnose_and_heal_file` | `diagnose_and_heal_file(apply=True)` 会对 **code-owned**（如 network）先 `reset`。复位后 `post` 诊断 `needs_hermes=[]` → `can_auto_fix_without_agent=False` → Host **直接 `stopped_reason=needs_agent` 且不再 `run_pipeline`**。结果：网络类失败被「复位但永不续跑」，GUI 却以为要找 PM。与 Plan「validation 类不依赖用户再点 PM」及 code 路径自愈目标冲突。 | 1）若 `healed` 非空且 post `failed_count==0`（或无失败 items）：直接 `run_pipeline` 再判 complete；2）补单测：mock heal 返回 `healed=["x"]` + 空 needs_hermes → 断言调用了第二次 `run_pipeline` 且最终可为 complete；3）勿在「已 heal 干净」时返回 `needs_agent` |

### Medium（强烈建议修复）

| # | 维度 | 行号 | 描述 | 必须动作 |
|---|------|------|------|----------|
| M1 | 注释 / 上下文 | `resources/skills/orchestrator/product-host.md:108` | 硬规则仍写「不要假装会自动重跑失败节点」，与 Host `--auto-fix` / GUI 目标模式矛盾；PM Agent 可能误导用户。 | 改为：宿主可能已自动 reset+run；仅在 `needs_agent` / `max_rounds` 时再分诊 |
| M2 | 功能 | `gui/src/App.tsx` ~3352–3362 | 「项目经理处理失败」在 Host complete 时直接宣称「全部完成」，未复用 `showRunSuccess` 的 pending/ready 校验与画廊。 | 与 `handleRun` 成功路径对齐 |
| M3 | 测试 / CI | `cli/test_visual_target.py` `test_generate_*` | `craft=False` + 中文 brief 触发 CJK 守卫导致 3 红；**非本 MR 引入**，但污染「全量 visual_target 绿」信号。 | 另开任务：fixture 英文化或 generate 测开 craft mock；不作为本 MR 功能回滚理由 |

### Low / Nit（可选）

| # | 维度 | 行号 | 描述 | 必须动作 |
|---|------|------|------|----------|
| L1 | 设计 | `App.tsx` legacy loop | Host 常驻后可删大段 fallback（跟 follow-up） | 记入 plan follow-up |
| L2 | 命名 | `stopped_reason=error` when `auto_fix=false` | 可改为 `disabled` / `no_auto_fix` | 可选 |

---

## 6. 门禁结论

| 门禁项 | 状态 |
|--------|------|
| 所有自动化检查通过 | [ ]（Host 子集 PASS；含 generate 的 visual_target FAIL） |
| 安全扫描干净 | [x] |
| Karpathy score = 4/4 | [ ]（2/4） |
| 无未解决 Critical 问题 | [x] |
| 无未解决 High 问题 | [ ]（H1） |
| 评审文档完整 | [x] |
| Spec/Plan 可追溯 | [x]（用户确认 Plan；无独立 brainstorm — 以 Plan+Inventory 为事实源，记 process 备注） |
| 无重复状态源 | [x] |

### 结论

- [x] **BLOCK** — 合并 / APPROVE 前必须解决 **H1**（建议同批修 M1）
- [ ] **APPROVE** — 所有门禁通过，建议执行 `/anvil:compound`

### 评审备注

- 已落地提交无需 rewind；以 **fixup commit** 修 H1/M1 后再复审即可。
- T1 CJK→validation、T2/T3 CLI、T5 VT 单源、safe_cli 收紧方向正确，值得保留。
- 下一步：用户确认后派 doer 修 H1（+M1），再 `/anvil:review` 复审；通过后再 push。
