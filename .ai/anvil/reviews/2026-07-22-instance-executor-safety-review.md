# 评审报告：`2026-07-22-instance-executor-safety`

## 元数据

| 字段 | 值 |
|------|----|
| Reviewer | anvil-lead |
| MR / Commit | 未提交工作区（相对 `main` / `b27a219`） |
| Author | `/anvil:code` doers + lead 文档 |
| Review Date | 2026-07-22 |
| Status | `APPROVED` |
| Spec | `docs/anvil/brainstorms/2026-07-22-instance-executor-safety.md` |
| Plan | `docs/anvil/plans/2026-07-22-instance-executor-safety-plan.md`（executed；`plans/` gitignore） |

**Loaded standards:** Anvil review skill；无 `docs/solutions` / critical-patterns；frontend/backend domain 规则未装载（空/未用）。

**变更规模：** Large（~469+/22-，跨 cli + gui + docs + config 契约）

---

## 1. 自动化预检

| 检查项 | 命令 | 结果 | 备注 |
|--------|------|------|------|
| Lint | N/A | N/A | 仓库无统一 lint 门禁于此范围 |
| 类型检查 | `cd gui && npx tsc --noEmit` | PASS | |
| 单元测试 | `python -m unittest test_agent_turn -q` | PASS | 27 tests OK |

---

## 1.5 Harness / Merge Gate

| 检查 | 结果 |
|------|------|
| Spec → Plan → Diff 可追溯 | PASS（T1–T5 对应实例覆盖目标；ACP/钳制/快照未出现） |
| 验证证据匹配风险 | PASS（CLI 行为有单测；GUI 依赖 tsc + 手测路径已文档化） |
| Resume point | PASS（plan executed；待 commit/手测） |
| 无平行状态源 | PASS（未新增 feature_list/progress 等） |

---

## 历史经验检查

| Source | Applied lens | Result |
|--------|--------------|--------|
| docs/solutions | N/A（目录不存在） | 无额外 lens |

---

## 2. 安全扫描

| 类别 | 发现 | 严重级别 | 状态 |
|------|------|----------|------|
| 硬编码密钥 | 无 | — | OK |
| 注入风险 | 无（枚举旋钮 → argv） | — | OK |
| XSS 风险 | 无（受控 option） | — | OK |
| 依赖 CVE | 未改依赖 | — | OK |
| 日志敏感数据 | 无新增密钥日志 | — | OK |

**安全结论：** CLEAN（本机用户可显式把实例调得比全局更松——Spec 已确认允许）

---

## 3. Karpathy 对抗式原则

| 原则 | 对抗式问题 | 作者回答（显式或推断） | 结论 | 严重级别 |
|------|------------|--------------------------|------|----------|
| Think Before Coding | 假设？ | 继承=缺键；resolve 只读当前 executor 相关键；yolo=false 拒绝 | PASS | — |
| Simplicity First | 能否删 50%？ | `instanceSafety.ts` 为 omit/哨兵付了代价；内联会把 Hire/ConfigBar 弄脏，保留合理 | PASS | — |
| Surgical Changes | 每行可追溯？ | CLI resolve + GUI 入口 + 文档均对 Spec 目标 | PASS | — |
| Goal-Driven Execution | 测试是否证明？ | CLI：覆盖/继承/yolo/串键/非法回退均有测；GUI 无单测（见 F1） | PASS* | Medium 债不阻塞 |

**Karpathy Score:** 4/4（GUI 测试债记入 Medium，不降门禁）

---

## 4. 对抗式维度评审

### 4.1 设计

| 行号 | 提问 | 作者回答 | 评审判断 | 严重级别 |
|------|------|----------|----------|----------|
| `instanceSafety.ts` | 新模块必要？ | 雇人+顶栏+serialize 共用 omit/哨兵 | 值得 | — |
| CLI `_instance_record` | 是否过度？ | 三 resolve 共用，最小 helper | OK | — |

**维度结论：** PASS

### 4.2 功能

| 行号 | 提问 | 作者回答 | 评审判断 | 严重级别 |
|------|------|----------|----------|----------|
| `agent_turn.py` resolve_* | 无 instance_id？ | 回退全局，兼容 B v2 | OK | — |
| `ColleagueConfigBar` persist | 改 model 丢安全键？ | `safetyFieldsRef` / snapshot 合并 | OK | — |
| `omitSafetyKeysForSerialize` yolo=false | false 被当成 inherit？ | `isInheritSafetyValue` 仅哨兵/空串 | OK | — |
| `handleSafetyChange` | 非法 raw 写入？ | CLI 会忽略非法；load 会 omit | 可接受；见 F2 | Low |

**已检查关键边界：**
- [x] 空 / 缺 instance_id
- [x] 非法枚举回退
- [x] yolo 键存在性（含 false）
- [x] 跨 executor 键不串用（有测）
- [ ] GUI 竞态（手测；无自动化）
- [x] Hermes 假安全（仍拒绝）

**维度结论：** PASS（Low 不阻塞）

### 4.3 复杂度

| 行号 | 提问 | 评审判断 | 严重级别 |
|------|------|----------|----------|
| ConfigBar persist 第三参 | 略绕但解决丢键 | 可接受 | — |
| `recordWithSafetyForm` | T3/T4 是否都用？ | 可能略冗余 | Nit |

**维度结论：** PASS

### 4.4 命名

| 检查 | 结果 |
|------|------|
| `INHERIT_SAFETY` / `safetyFieldForExecutor` | 清晰 |
| resolve_* 参数 `instance_id` | 与全库一致 |

**维度结论：** PASS

### 4.5 注释

| 检查 | 结果 |
|------|------|
| `INHERIT_SAFETY` 注释强调勿落盘 | 有价值 WHY |

**维度结论：** PASS

### 4.6 风格

与既有 ConfigBar / hire 模式一致；无纯风格噪音。

**维度结论：** PASS

### 4.7 上下文

补齐 B v2 Deferred「实例覆盖」；文档同步；未引入 ACP 假路径。

**维度结论：** PASS

### 4.8 测试

| 行号 | 提问 | 评审判断 | 严重级别 |
|------|------|----------|----------|
| `TestInstanceExecutorSafety` | 破坏覆盖实现会失败？ | 会 | — |
| GUI `instanceSafety` | 无单测 | 技术债 F1 | Medium |

**维度结论：** PASS（Medium 不阻塞合并；CLI 为核心行为）

---

## 5. 发现项摘要

### Critical（阻塞提交）

（无）

### High（阻塞提交）

（无）

### Medium（强烈建议修复）

| # | 维度 | 行号 | 描述 | 必须动作 |
|---|------|------|------|----------|
| F1 | 测试 | `gui/src/settings/instanceSafety.ts` | omit / parse / inherit 哨兵无 GUI 单测 | 后续补 vitest/纯函数测；本版不阻塞 |

### Low / Nit（可选）

| # | 维度 | 行号 | 描述 | 必须动作 |
|---|------|------|------|----------|
| F2 | 功能 | `ColleagueConfigBar.tsx` `handleSafetyChange` | raw 枚举未校验即写入 | 可选对齐 option id 白名单 |
| F3 | Nit | `recordWithSafetyForm` | 导出后使用面窄 | 可保留供表单；勿再扩 |

---

## 6. 门禁结论

| 门禁项 | 状态 |
|--------|------|
| 所有自动化检查通过 | [x] |
| 安全扫描干净 | [x] |
| Karpathy score = 4/4 | [x] |
| 无未解决 Critical 问题 | [x] |
| 无未解决 High 问题 | [x] |
| Spec 可追溯 | [x] |
| 评审文档完整 | [x] |

### 结论

- [x] **APPROVE** — 所有门禁通过；允许 commit。建议稍后 `/anvil:compound`（可选）

### 评审备注

- 手测仍建议：雇人选 sandbox → 顶栏继承删键 → Hermes 关 YOLO 拒跑。
- `docs/anvil/plans/` 被 gitignore；Spec brainstorm 应随代码一并提交。
