# 评审报告：`2026-08-19-it-ops-hardening`

## 元数据

| 字段 | 值 |
|------|----|
| Reviewer | anvil-lead |
| MR / Commit | 未提交工作树（相对 `ebc06c2`） |
| Author | 本会话修复 |
| Review Date | 2026-08-19 |
| Status | `APPROVED` |

**范围：** 上一轮独立审查的 P1/P2/P3 跟进：`inspect grep` 跳过否认树与扫描上限、IT prompt 压缩 pipeline 统计与去重 PM 正文、GUI 运维上下文脱敏、`--pattern` 白名单收窄、看板资产名 ellipsis、制作审查文案抽测。  
**Loaded standards：** `AGENTS.md`、Anvil review、`rules/karpathy.md`、`rules/domains/frontend.md`（TBD，无附加规则）。  
**事实源：** 上一轮审查建议 + 当前 uncommitted diff。非完整 Anvil `req→plan→code` 流，§1.5/§1.6 按跟进修复处理。  
**变更体量：** Medium（约 +204/−48，另 3 个未跟踪测试/辅助文件）。

---

## 1. 自动化预检

| 检查项 | 命令 | 结果 | 备注 |
|--------|------|------|------|
| Lint | N/A | N/A | 本仓库无统一 Python/GUI lint 门禁 |
| 类型检查 | 未跑全量 `tsc` | N/A | 既有基线错误；本次改动为小函数抽取，未扩公共契约 |
| 单元测试 | `cd cli && python -m pytest test_it_broad_read.py test_agent_turn.py test_pi_foundry_tools.py -q` | PASS | 66 passed；RTK 不可用，已回退原始输出 |
| 单元测试 | `cd gui && npx tsx --test src/chat/itOpsContext.test.ts src/chat/makeabilityCopies.test.ts && node --test electron/agent_prompt.test.mjs` | PASS | 3 + 6 |
| UI 浏览器验证 | 未开 GUI | N/A | CSS ellipsis 仅靠样式审查；看板未做端到端点击 |

---

## 历史经验检查

| Source | Applied lens | Result |
|--------|--------------|--------|
| `anvil-learnings-researcher` | 当前 Task 目录无该子代理 | 未调度；改为本地 `docs/solutions` 关键词检索 |
| `docs/solutions` inspect/grep/ops-context | 敏感注入、否认树、prompt 体积 | 无独立条目可引用；lens 来自上一轮审查清单 |
| 上一轮审查（IT inspect / 双份 PM 正文） | 是否真正跳过 `node_modules`、是否只豁免 `--pattern`、prompt 是否仍塞满 `ready_ids` | 见 §4.2 / §5：主路径已闭合；`files_scanned` 计数口径不完整 |

**使用规则：** 历史 learning 只作 lens。下列 finding 均引用当前 diff 行号。

---

## 2. 安全扫描

| 类别 | 发现 | 严重级别 | 状态 |
|------|------|----------|------|
| 硬编码密钥 | 无 | — | PASS |
| 注入风险 | `inspect grep` 不再整段 argv 放行 `\| * ?`；仅 `--pattern` 豁免。`--path cli*` 被拒（测试覆盖） | — | PASS |
| XSS 风险 | 无新 HTML 拼接；聊天注入为纯文本 | — | PASS |
| 依赖 CVE | 无依赖变更 | — | N/A |
| 日志敏感数据 | GUI `itOpsContext` 对 `sk-` / `sk-or-` 脱敏；磁盘会话仍走 `redact_secrets`。子串协议见 Low | Medium/Low | 见 §5 |

**安全结论：** CLEAN（无阻塞项）

---

## 3. Karpathy 对抗式原则

| 原则 | 对抗式问题 | 作者回答（显式或推断） | 结论 | 严重级别 |
|------|------------|--------------------------|------|----------|
| Think Before Coding | 未写下的假设？ | 假设：IT 仍需读 `output/`；GUI 有「GUI 会话尾部」时磁盘 PM 正文可丢。后者用魔串耦合 TS/Python | PASS | — |
| Simplicity First | 能否删掉 50%？ | `makeabilityCardCopies` 为可测性付出一层；体量小、有测试，值得 | PASS | — |
| Surgical Changes | 每行能否追溯审查项？ | 是。未再扩「跳过整个 output/」 | PASS | — |
| Goal-Driven Execution | 测试是否证明行为？ | grep 否认树、pattern glob、compact summary、GUI 脱敏、ops-context 转发均有行为断言。`files_scanned` 口径无测 | PASS | Medium 残留见 §5 |

**Karpathy Score:** 4/4

---

## 4. 对抗式维度评审

### 4.1 设计：它是否应该存在？

| 行号 | 提问 | 作者回答 | 评审判断 | 严重级别 |
|------|------|----------|----------|----------|
| `cli/inspect_ops.py:102-123` | 手写 walk 是否多余？ | `rglob` 会进否认树并跟随 symlink；`iterdir` + deny 是审查要求 | 成立 | — |
| `gui/src/chat/makeabilityCopies.ts` | 单独模块是否投机？ | App 内联无法单测去重；抽取合理 | 成立 | — |

**维度结论：** PASS

---

### 4.2 功能：作者遗漏了什么？

| 行号 | 提问 | 作者回答 | 评审判断 | 严重级别 |
|------|------|----------|----------|----------|
| `cli/inspect_ops.py:339-358` | `DEFAULT_GREP_FILE_CAP` 是否真的限制「扫描文件数」？ | `files_scanned` 仅在 UTF-8 读成功后 +1；后缀跳过 / 超大 / 解码失败不计数 | 上限管的是「读进内存的文本文件」，不是 walk/`stat` 次数。对 `output/` 大量 png/mp4 仍会枚举到底。主漏洞（`node_modules`）已用 `_iter_files_skip_denied` 堵住 | Medium |
| `cli/agent_turn.py:490-492` | `"GUI 会话尾部" in gui_ctx` 会不会误跳过磁盘正文？ | GUI 固定写入该标题 | 流水线日志若碰巧含同一短语会丢磁盘 PM；反向：无该短语时仍双份注入。协议脆弱 | Low |
| `gui/src/App.css:3389-3406` | ellipsis 在 `flex-wrap` 下是否生效？ | `min-width: 0` | 看板 `board-tasks` 有 `overflow: hidden`，大体够用；缺 `max-width: 100%` / `flex: 1` 时与 chips 同行可能仍撑开 | Low |

**已检查关键边界：**
- [x] 空输入 / null 输入（pattern 空、过长、非法正则有测）
- [x] 边界值 / 最大尺寸（pattern 256、tree limit clamp、grep file cap 语义见上）
- [x] 负数 / 非法值（limit/max_matches 仍 `max(1, …)`）
- [ ] 竞态 / 死锁（单线程 walk，不适用）
- [x] 外部依赖失败（list/diagnose 仍吞 Exception）
- [ ] 并发访问（不适用）

**维度结论：** FINDINGS（无 High）

---

### 4.3 复杂度：还能更简单吗？

| 行号 | 提问 | 作者回答 | 评审判断 | 严重级别 |
|------|------|----------|----------|----------|
| `cli/pi_foundry_tools.py:356-370` | `_drop_named_flag_values` 是否过重？ | 只服务 `--pattern` 豁免 | 比整段 grep 放行更正确，保留 | — |

**过度设计检查：**
- [x] 无投机抽象
- [x] 无未使用 hooks
- [x] 无不必要间接层（makeability 抽取有测试消费者）
- [x] 核心需求可用更少代码实现（再少会牺牲可测性）

**维度结论：** PASS

---

### 4.4 命名：名字是否撒谎？

| 行号 | 提问 | 作者回答 | 评审判断 | 严重级别 |
|------|------|----------|----------|----------|
| `cli/inspect_ops.py:381-385` | `files_scanned` 是否像「走过的文件」？ | 实为「成功读文本的文件」 | 名实略偏；与 Medium 同一根因 | Low |

**命名问题：**
- [x] 无模糊 helper/manager
- [x] 函数名不隐藏副作用
- [x] 无未解释缩写
- [ ] `files_scanned` 可从名字误判为 walk 计数

**维度结论：** FINDINGS（Low）

---

### 4.5 注释：提供价值，还是替坏代码找借口？

| 行号 | 提问 | 作者回答 | 评审判断 | 严重级别 |
|------|------|----------|----------|----------|
| `cli/pi_foundry_tools.py:388` | 注释是否说明为何只豁免 pattern？ | 是 | PASS | — |

**注释质量检查：**
- [x] 注释解释 WHY
- [x] 无不可执行 TODO
- [x] 无易失真注释
- [x] 未用注释掩盖复杂度

**维度结论：** PASS

---

### 4.6 风格与一致性

| 行号 | 问题 | 类型（Block / Nit） | 状态 |
|------|------|--------------------|------|
| `gui/src/chat/itOpsContext.ts:5` vs `cli/inspect_ops.py:34-36` | `sk-` 正则两份拷贝，日后会漂 | Nit | 接受 |

**风格检查：**
- [x] 遵循项目风格
- [x] 无无关格式大扫除
- [x] 与周边一致

**维度结论：** PASS

---

### 4.7 上下文：系统是否更健康？

| 行号 | 提问 | 作者回答 | 评审判断 | 严重级别 |
|------|------|----------|----------|----------|
| 全 diff | 是否比 `ebc06c2` 更安全、prompt 更小？ | 否认树 + compact summary + 脱敏 + 去重 | 是 | — |

**系统健康检查：**
- [x] 看过 `inspect_ops.grep_files` / `is_allowed_argv` / `build_prompt` 全函数，不只 hunk
- [x] 无新增不当耦合（魔串是已知薄协议）
- [x] 后续改 grep/白名单更安全
- [x] 无死代码

**维度结论：** PASS

---

### 4.8 测试：证明有效，还是只是跑起来？

| 行号 | 提问 | 作者回答 | 评审判断 | 严重级别 |
|------|------|----------|----------|----------|
| `cli/test_it_broad_read.py:55-68` | 破坏「跳过 node_modules」会不会红？ | token 在 deny 树不应命中 | 会 | — |
| `cli/test_it_broad_read.py:110-112` | `--path cli*` 是否覆盖 P3？ | `assertFalse` | 会 | — |
| `cli/test_agent_turn.py` compact / skip duplicate | 破坏截断或去重会不会红？ | 会 | 未覆盖「日志含 GUI 会话尾部」误触发 | Low |
| `gui/.../itOpsContext.test.ts` | 未脱敏会不会红？ | `doesNotMatch sk-` | 会 | — |

**测试质量检查：**
- [x] 故意破坏主路径会失败
- [x] 测行为而非实现细节（whitelist 测 argv）
- [ ] §4.2 的 walk 口径无测试
- [x] 断言可读
- [x] tempfile + patch `allow_roots` 合理，非幻想 mock

**维度结论：** FINDINGS（Low/Medium 覆盖缺口，不阻塞）

---

## 5. 发现项摘要

### Critical（阻塞提交）

无。

### High（阻塞提交）

无。

### Medium（强烈建议修复）

| # | 维度 | 行号 | 描述 | 必须动作 |
|---|------|------|------|----------|
| M1 | 4.2 / 4.8 | `cli/inspect_ops.py:339-358` | `DEFAULT_GREP_FILE_CAP` 不计入后缀跳过、超大文件、解码失败；大 `output/` 仍会全量 `iterdir`/`stat` | 建议用独立 `files_visited`（含 skip）触顶即 `truncated`；或在 skip 前计数。不阻塞：否认树已跳过，匹配数仍有 cap |

### Low / Nit（可选）

| # | 维度 | 行号 | 描述 | 必须动作 |
|---|------|------|------|----------|
| L1 | 4.2 | `cli/agent_turn.py:490-492` | 用中文标题子串决定是否跳过磁盘 PM 正文 | 可选：显式 flag / 结构化 ops JSON |
| L2 | 4.4 | `cli/inspect_ops.py:381-385` | `files_scanned` 名实不符 | 随 M1 改口径或改名 |
| L3 | 4.2 | `gui/src/App.css:3398-3406` | ellipsis 未设 `max-width: 100%` | 可选加强 |
| N1 | 4.6 | `itOpsContext.ts` / `inspect_ops.py` | 脱敏正则双份 | 可接受 |

---

## 6. 门禁结论

| 门禁项 | 状态 |
|--------|------|
| 所有自动化检查通过 | [x] 范围内测试绿；全量 tsc/lint N/A |
| 安全扫描干净 | [x] |
| Karpathy score = 4/4 | [x] |
| 无未解决 Critical 问题 | [x] |
| 无未解决 High 问题 | [x] |
| 评审文档完整 | [x] |
| 全流程 spec 追溯 | [x] N/A（审查跟进，非 req/plan 交付） |

### 结论

- [x] **APPROVE** — 无 Critical/High。M1 不阻塞；上一轮 P1（否认树 / symlink / pattern 豁免 / prompt 体积 / GUI 脱敏 / 去重）已在当前 diff 落地。
- [ ] 未执行 `/anvil:compound`（本轮未产生新的可复用失败模式，除非要把「grep cap 要计 walk」写入 solutions）。

### 评审备注

- 未按 Anvil §8 自动提交：用户规则要求未明确要求时不 commit。工作树仍脏，回滚风险仍在。
- 未做看板 GUI 真机/浏览器验证；资产名 ellipsis 为 CSS 推理。
- 刻意保持：不跳过整个 `output/`。
