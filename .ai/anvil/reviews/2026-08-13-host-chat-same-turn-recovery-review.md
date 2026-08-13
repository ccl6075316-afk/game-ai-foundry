# 评审报告：`2026-08-13-host-chat-same-turn-recovery`

## 元数据

| 字段 | 值 |
|------|----|
| Reviewer | anvil-lead |
| MR / Commit | WORKTREE（未提交） |
| Author | 本会话实现 |
| Review Date | 2026-08-13 |
| Status | `APPROVED` |

**Loaded standards:** `anvil/skills/review/SKILL.md`、`anvil/rules/karpathy.md`、`anvil/rules/domains/backend.md`（TBD）、`anvil/rules/domains/frontend.md`（TBD）

**审查范围:**
- 宿主主对话「先出结果、同轮收口」：空/烂 JSON、无草稿补丁、整表改写、非法 focus、落实空稿
- 审查答卡落盘 CAS → rebase 到当前磁盘稿；写入后自动再跑制作审查
- enrich 成功后自动再跑制作审查
- **不做：** 动画切分（用户搁置）；不提交（用户规则优先于 Anvil §8 自动提交）

---

## 1. 自动化预检

| 检查项 | 命令 | 结果 | 备注 |
|--------|------|------|------|
| Lint | IDE diagnostics `cli/host_chat.py` | PASS | 无新诊断 |
| 类型检查 | GUI `tsc` | N/A | 本 diff 无 GUI；既有 happy-dom / TS5097 与本次无关 |
| 单元测试 | `python3 -m unittest test_host_chat test_brief_enrich test_makeability_decisions test_llm_json -q` | PASS | 217 ok |

---

## 历史经验检查

| Source | Applied lens | Result |
|--------|--------------|--------|
| `anvil-learnings-researcher` | 插件内无该 researcher | 跳过；定点检索 `docs/solutions` / 既有 makeability review |
| `.ai/anvil/reviews/2026-08-05-makeability-repeat-confirm-review.md` | CAS 失败不得声称 verified/ok；session 答案仍要落盘 | 答卡路径改为 rebase 后 persist；失败仍降级 `draft_persisted=false`；`save_session` CAS 拒绝覆盖行为未改 |
| `.ai/anvil/reviews/2026-08-13-video-providers-and-brief-patch-heal-review.md` | 挡住由策划同轮修，不外挂 Agent；用户看到结果不是校验原文 | 本 diff 把剩余 dump 口子收进同一原则；审查中修了「部分成功却报失败」 |

**使用规则：** 历史 learning 只作 lens；下列 finding 均引用 current diff。

---

## 1.5 Harness / Spec 追溯

| 项 | 结论 |
|----|------|
| 工程 spec | **无**独立 `docs/anvil/brainstorms`；范围来自用户确认「不要报错给我，同轮解决；挡住由策划修」 |
| 非目标 | 动画切分未做 |
| Plan resume | 轻量任务；SoT = `host_chat.py` + `resources/skills/orchestrator/host-chat.md` |
| 并行状态源 | 无新增 `docs/solutions` |

---

## 2. 安全扫描

| 类别 | 发现 | 严重级别 | 状态 |
|------|------|----------|------|
| 硬编码密钥 | 无 | — | PASS |
| 注入风险 | rebase 仍走 `apply_brief_patches` 硬校验（`../escape` / 稳定 id） | — | PASS |
| XSS 风险 | 无 GUI HTML 插入 | — | PASS |
| 依赖 CVE | 无新依赖 | — | PASS |
| 日志敏感数据 | `_last_llm_raw.txt` 仍可转储最多 200k 模型原文（既有） | Low | 可接受；本 diff 未扩大 |

**安全结论：** CLEAN

---

## 3. Karpathy 对抗式原则

| 原则 | 对抗式问题 | 作者回答（显式或推断） | 结论 | 严重级别 |
|------|------------|--------------------------|------|----------|
| Think Before Coding | 整表 scenes 被剥掉但标题已写入时，是否还算「写入失败」？ | 初版把 `_rewrite_needs_patches` 放进 `_planner_write_pending`，标题已落仍同轮重试并可能对用户说「还没写进侧栏」。审查中改为仅当本轮剥正文且 **fingerprint 未变** 才 `_rewrite_retry_now`。 | PASS | High→已修 |
| Simplicity First | 自动再审能否少一层 `except Exception`？ | 审查中收窄为 `HostChatError, PromptCraftError`；enrich 测试改为显式 mock `_try_rerun`。 | PASS | Medium→已修 |
| Surgical Changes | 430+ 行 host_chat 是否都服务「先出结果」？ | 是：dump 口子、commit 空稿、CAS rebase、自动再审；无视频/动画/GUI。 | PASS | — |
| Goal-Driven Execution | 测试在实现写错时会不会挂？ | 空 JSON / 落实空稿 / 无草稿补丁 / 非法 focus / 标题+剥场景不重试 / CAS rebase 保 External 标题 均有行为断言。 | PASS | — |

**Karpathy Score:** 4/4

---

## 4. 对抗式维度评审

### 4.1 设计：它是否应该存在？

| 行号 | 提问 | 作者回答 | 评审判断 | 严重级别 |
|------|------|----------|----------|----------|
| `cli/host_chat.py:1140` | enrich/答卡后自动再审是否该在宿主层？ | 用户要求不要再点「制作审查」；Critic 仍只读草稿，不静默改稿。 | PASS | — |
| `cli/host_chat.py:1736` | CAS 时 rebase 补丁到磁盘，是否破坏 H1？ | 不覆盖磁盘上已有字段（测例 External 标题保留），只把 closer 补丁打到当前磁盘稿。`save_session` 普通 persist 仍拒绝覆盖。 | PASS | — |

**维度结论：** PASS

---

### 4.2 功能：作者遗漏了什么？

| 行号 | 提问 | 作者回答 | 评审判断 | 严重级别 |
|------|------|----------|----------|----------|
| `_planner_write_pending` + `_rewrite_needs_patches` | 标题已合并、场景正文被剥，用户是否看到失败？ | 审查前：会。审查后：`_rewrite_retry_now` 仅「本轮剥正文且未落地」；`test_run_turn_stripped_scene_merge_does_not_retry`。下一轮 `host_nudge` 仍要求 upsert_scene。 | PASS（已修） | High→已修 |
| `cli/host_chat.py:1755` | rebase 读盘与 persist 之间磁盘再变？ | 第二次 CAS 不再 rebase（`rebased` 闩），答卡降级 + 「下次再点审查选项」。 | PASS | Medium 残余 |
| `cli/host_chat.py:4126` | 补丁失败时留下 Untitled 薄稿？ | 仅 `draft_brief is None` 时写入 bootstrap，同轮 schema 重试可覆盖；失败则侧栏出现 Untitled。 | Low | 可接受 |
| 非法 focus | 丢掉后用户是否知道 focus 没换？ | 产品要求不报 focus 错误、正文照写。 | PASS | — |

**已检查关键边界：**
- [x] 空输入 / 空 LLM / 烂 JSON
- [x] 无草稿补丁
- [x] 整表改写部分成功 vs 完全没落地
- [x] CAS / 外部改盘
- [x] 外部依赖失败（再审失败不挡写入）
- [ ] 并发双写同一 brief（既有 project lock；本 diff 未扩）

**维度结论：** PASS（High 已修）

---

### 4.3 复杂度：还能更简单吗？

| 行号 | 提问 | 作者回答 | 评审判断 | 严重级别 |
|------|------|----------|----------|----------|
| session 旗标 `_empty_model_turn` / `_rewrite_needs_patches` / `_rewrite_retry_now` / `_commit_body_missing` | 能否合成一个 enum？ | 分旗标对应不同 `host_nudge`；合成收益小。 | PASS | Nit |

**过度设计检查：**
- [x] 无投机抽象
- [x] 无未使用 hooks
- [x] 同轮恢复复用既有 `_call_llm` + `_apply_parsed`
- [x] 核心需求没有更少代码的等价实现（各 dump 口子本就分散）

**维度结论：** PASS

---

### 4.4 命名：名字是否撒谎？

| 行号 | 提问 | 作者回答 | 评审判断 | 严重级别 |
|------|------|----------|----------|----------|
| `_try_rerun_makeability_after_write` | try 暗示可失败且不抛 | 是；吞 `HostChatError/PromptCraftError`。 | PASS | — |
| `_rewrite_retry_now` vs `_rewrite_needs_patches` | 两个旗标是否易混？ | 前者=本轮要不要立刻重试；后者=下一轮 nudge。测试已分开断言。 | PASS | — |

**维度结论：** PASS

---

### 4.5 注释：提供价值，还是替坏代码找借口？

| 行号 | 提问 | 作者回答 | 评审判断 | 严重级别 |
|------|------|----------|----------|----------|
| `_persist_answer_draft_or_mark` docstring | 说明 CAS rebase 而不叫用户对齐 | WHY，不是 WHAT 复述。 | PASS | — |

**维度结论：** PASS

---

### 4.6 风格与一致性

| 行号 | 问题 | 类型（Block / Nit） | 状态 |
|------|------|--------------------|------|
| — | 无风格大扫除；中文用户文案与既有宿主语气一致 | — | PASS |

**维度结论：** PASS

---

### 4.7 上下文：系统是否更健康？

| 行号 | 提问 | 作者回答 | 评审判断 | 严重级别 |
|------|------|----------|----------|----------|
| `host-chat.md` | skill 是否与代码同向？ | 已写：空 JSON / 整表 / 无草稿补丁 / 落实空稿 / 非法 focus；答卡后自动再审 + rebase。 | PASS | — |
| 用户可见文案 | 耗尽后是否仍把策划 hint 甩给用户？ | 审查前 `_user_write_failed_note` 含 `_patch_recovery_hint`。审查后用户只见短结果句；hint 留在 `host_nudge`。 | PASS（已修） | Medium→已修 |

**维度结论：** PASS

---

### 4.8 测试：证明有效，还是只是跑起来？

| 行号 | 提问 | 作者回答 | 评审判断 | 严重级别 |
|------|------|----------|----------|----------|
| `test_host_chat.py` | 故意不写补丁 / 空 JSON / 落实空稿是否失败？ | `call_count` + 草稿字段 + 「已自动改正」/「不用重复需求」。 | PASS | — |
| `test_makeability_decisions.py` | CAS rebase 是否真写入且不覆盖 External？ | 断言 `draft_persisted`、title=External、aquarium notes unlocked。 | PASS | — |
| enrich 自动再审 | 是否只 mock 掉？ | runner 测断言 `_try_rerun` 被调用一次；不在 enrich 里跑真实 Critic schema。答卡路径仍会真实调用（失败则吞掉）。 | PASS | Low：无「再审成功拼进气泡」测例 |

**维度结论：** PASS

---

## 5. 发现项摘要

### Critical（阻塞提交）

| # | 维度 | 行号 | 描述 | 必须动作 |
|---|------|------|------|----------|
| — | — | — | 无 | — |

### High（阻塞提交）

| # | 维度 | 行号 | 描述 | 必须动作 |
|---|------|------|------|----------|
| H1 | 4.2 | `_planner_write_pending` 初版 | 标题已写入仍因剥场景正文同轮重试，用户可能看到「还没写进侧栏」 | **审查中已修**：`_rewrite_retry_now` 仅本轮剥正文且未落地；部分成功只留下一轮 `host_nudge` |

### Medium（强烈建议修复）

| # | 维度 | 行号 | 描述 | 必须动作 |
|---|------|------|------|----------|
| M1 | 4.7 | `_user_write_failed_note` 初版 | 耗尽后把 schema + `【怎么改】` 甩给用户 | **审查中已修**：用户短句；hint 仅 `host_nudge` |
| M2 | 4.3 | `_try_rerun` 初版 `except Exception` | 吞掉非 LLM 异常，掩盖实现 bug | **审查中已修**：仅 `HostChatError, PromptCraftError` |

### Low / Nit（可选）

| # | 维度 | 行号 | 描述 | 必须动作 |
|---|------|------|------|----------|
| L1 | 4.2 | `cli/host_chat.py:4127` | bootstrap 标题 `Untitled`（英文） | 可改中文「未命名」；不影响写入 |
| L2 | 4.8 | enrich 再审 | 无「再审成功拼进 assistant_message」断言 | 可选补测 |
| L3 | 4.2 | rebase 后二次 CAS | 不再二次 rebase，降级请用户再点选项 | 与「不用对齐磁盘」一致，可接受 |

---

## 6. 门禁结论

| 门禁项 | 状态 |
|--------|------|
| 所有自动化检查通过 | [x] |
| 安全扫描干净 | [x] |
| Karpathy score = 4/4 | [x] |
| 无未解决 Critical 问题 | [x] |
| 无未解决 High 问题 | [x] |
| 评审文档完整 | [x] |

### 结论

- [x] **APPROVE** — 所有门禁通过；建议 `/anvil:compound`（可沉淀：部分成功不要报失败；CAS rebase 补丁而非覆盖）
- [ ] **BLOCK**

### 评审备注

- Anvil §8 要求通过后提交；**用户规则禁止未请求提交**，本任务 accepted diff 仍在 worktree，回滚风险在。要提交时再说一声。
- 动画切分仍搁置。
- GUI 需重启 / 新会话才能吃到本 diff；旧 Pi 会话不会自动套用。
