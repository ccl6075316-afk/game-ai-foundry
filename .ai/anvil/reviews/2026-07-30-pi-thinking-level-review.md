# 评审报告：`2026-07-30-pi-thinking-level`

## 元数据

| 字段 | 值 |
|------|----|
| Reviewer | anvil-lead |
| MR / Commit | 未提交工作区（uncommitted） |
| Author | `/anvil:code` doers（T1–T4）+ lead（T5 文档） |
| Review Date | 2026-07-30 |
| Status | `APPROVED` |
| Spec | `docs/anvil/brainstorms/2026-07-30-pi-thinking-level.md`（confirmed） |
| Plan | `docs/anvil/plans/2026-07-30-pi-thinking-level-plan.md`（executed；路径被根 `.gitignore` 的 `plans/` 忽略，本地仍可读） |

**Loaded standards:** Anvil `/anvil:review`；Karpathy 原则；`docs/solutions` 无 Pi thinking 相关条目（lens 空）；frontend/backend domain 规则未装载（空/不适用）。

**变更规模：** Medium（~170 行业务 diff + 新单测；跨 CLI + GUI 配置契约）

**Spec 追溯：** FR1–FR6 均有对应实现；非目标（Host 直连 / Codex·Cursor Think / 展示 reasoning）未被触碰。

---

## 1. 自动化预检

| 检查项 | 命令 | 结果 | 备注 |
|--------|------|------|------|
| Lint | N/A | N/A | 无统一 lint 门禁 |
| 类型检查 | `cd gui && npm run typecheck` | PASS | `tsc --noEmit` |
| 单元测试 | `cd cli && python -m unittest test_pi_thinking_level -v` | PASS | 8/8 OK |

---

## 历史经验检查

| Source | Applied lens | Result |
|--------|--------------|--------|
| docs/solutions（thinking/pi_runtime） | 无匹配条目 | 无额外 lens |
| critical-patterns（ACP/Hermes） | 与本 diff 无关 | 未误用为 finding |

---

## 1.5 Harness / Spec 门禁

| 项 | 状态 |
|----|------|
| Spec → Plan → Diff 可追溯 | PASS |
| 非目标未越界 | PASS（无 Host completion thinking 参数） |
| 验证证据匹配风险 | PASS（CLI 行为测 + GUI typecheck） |
| Resume point | PASS（plan Code Status；本报告） |
| 无平行任务状态文件 | PASS |
| Plan 可版本化 | WARN：`plans/` gitignore 吞掉 `docs/anvil/plans/*`（既有问题，非本 diff 引入） |

---

## 2. 安全扫描

| 类别 | 发现 | 严重级别 | 状态 |
|------|------|----------|------|
| 硬编码密钥 | 无；key 仍仅 env | — | OK |
| 注入风险 | argv 枚举白名单档位 | — | OK |
| XSS 风险 | 档位为固定文案按钮 | — | OK |
| 依赖 CVE | 未改依赖 | — | N/A |
| 日志敏感数据 | 未新增打印 key 的路径 | — | OK |

**安全结论：** CLEAN

---

## 3. Karpathy 对抗式原则

| 原则 | 对抗式问题 | 作者回答（显式或推断） | 结论 | 严重级别 |
|------|------------|--------------------------|------|----------|
| Think Before Coding | 假设是否写明？ | Spec 钉死仅 Pi `--thinking`；Host/Agent 原生排除 | PASS | — |
| Simplicity First | 能否删 50%？ | 无 Host 厂商映射；无新包；四档够用 | PASS | — |
| Surgical Changes | 每行能否追溯需求？ | 变更均落在 thinking 字段/UI/argv | PASS | — |
| Goal-Driven Execution | 测试是否证明行为？ | CLI 断言 argv 含 `--thinking`+档位；破坏映射会红 | PASS | — |

**Karpathy Score:** 4/4

---

## 4. 对抗式维度评审

### 4.1 设计

| 行号 | 提问 | 作者回答 | 评审判断 | 严重级别 |
|------|------|----------|----------|----------|
| `cli/pi_runtime.py` 35–68 | 为何不进 auth overlay？ | 实例只读字段，避免扩大 `_OVERLAY_FIELDS` | 合理 | — |
| GUI 双端 normalize | TS/Py 各一份？ | 边界隔离，可接受 | PASS（漂移风险见 Low） | Low |

**维度结论：** PASS

### 4.2 功能

| 行号 | 提问 | 作者回答 | 评审判断 | 严重级别 |
|------|------|----------|----------|----------|
| `ColleagueConfigBar` persist ~219–228 | 非 Pi 是否误写字段？ | 仅 `resolvedExecutor === "pi"` 展开 | PASS | — |
| `showThinkingLevel = executor === "pi"` | 第三方 Codex 是否误显？ | 不显示 | PASS | — |
| 默认始终传 `--thinking off` | 与「省略 flag」是否等价？ | Spec 要求显式档位；Pi CLI 支持 `off` | 接受；残余风险见 Medium | Medium |
| 非法值 | normalize → off | 有单测 | PASS | — |

**已检查关键边界：**
- [x] 空输入 / null 输入
- [x] 非法值
- [x] 无 instance_id
- [ ] 竞态（get-modify-save 为既有 persist 模式，未新增特有竞态）
- [x] 外部依赖失败（沿用既有 Pi 错误路径）

**维度结论：** PASS（含非阻塞 Medium）

### 4.3 复杂度

无投机抽象；`_pi_cli_model_and_thinking` 消除两处重复拼接。

**维度结论：** PASS

### 4.4 命名

`thinking_level` / `normalize_thinking_level` / `--thinking` 与 Spec 一致；UI「Thinking」aria-label 可接受。

**维度结论：** PASS

### 4.5 注释

`AgentInstanceRecord.thinking_level` 短注释说明 Pi CLI 语义；无废话 TODO。

**维度结论：** PASS

### 4.6 风格

复用 `pi-model-chip__tier*`；与高中低一致。无无关格式化大扫除。

**维度结论：** PASS

### 4.7 上下文

系统健康中性偏好：配置契约扩展小、文档一句、测试覆盖运行时。`docs/anvil/plans` 被 ignore 为既有债，不因本 MR 恶化产品代码。

**维度结论：** PASS

### 4.8 测试

| 行号 | 提问 | 作者回答 | 评审判断 | 严重级别 |
|------|------|----------|----------|----------|
| `test_pi_thinking_level.py` | 故意改档位映射会否失败？ | 会（断言 argv） | PASS | — |
| GUI serialize/load | 有无单测？ | Plan 允许无 harness；仅 typecheck | 技术债 | Medium |

**维度结论：** PASS（Medium 非阻塞）

---

## 5. 发现项摘要

### Critical（阻塞提交）

| # | 维度 | 行号 | 描述 | 必须动作 |
|---|------|------|------|----------|
| — | — | — | 无 | — |

### High（阻塞提交）

| # | 维度 | 行号 | 描述 | 必须动作 |
|---|------|------|------|----------|
| — | — | — | 无 | — |

### Medium（强烈建议修复）

| # | 维度 | 行号 | 描述 | 必须动作 |
|---|------|------|------|----------|
| M1 | 4.2 / 4.8 | Pi argv 全局 | 即便 `off` 也始终传 `--thinking off`（相对旧行为多一个 flag）。与 Spec 一致，但若某模型/Pi 版本对显式 `off` 行为异常，需实机确认。 | 实机点一次关/高；异常再改为「仅非 off 时注入」 |
| M2 | 4.8 | GUI | 无 `agentInstances` serialize/load 单测 | 后续补 round-trip；不阻塞 |

### Low / Nit（可选）

| # | 维度 | 行号 | 描述 | 必须动作 |
|---|------|------|------|----------|
| L1 | 设计 | TS+Py normalize | 双端枚举可能漂移 | 改档时同步两端 |
| L2 | Harness | `.gitignore` `plans/` | `docs/anvil/plans/*` 无法入库 | 另开任务改为 `^plans/` 或 `!docs/anvil/plans/` |
| L3 | Nit | test L46 | `resolve_pi_thinking_level(cfg, "it-1",)` 多余逗号 | 可顺手删 |

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
| Spec 可追溯 | [x] |

### 结论

- [x] **APPROVE** — 无阻塞项；M1/M2 不阻塞合并
- [ ] **BLOCK**

### 评审备注

- 用户规则要求「未明确说提交则不 commit」：本评审 **允许提交**，但 **未自动创建 commit**。请回复「提交」后由 lead 按写集提交。
- 建议提交后可 `/anvil:compound`（可选）：记录「Pi `--thinking` 与实例 `thinking_level`；Host 直连另议」。
- 手动验收：打开策划/IT Pi 同事 → 切换关/低/中/高 → 重启对话确认档位保持 →（可选）日志/进程列表确认 argv。

### 建议提交写集

- `cli/pi_runtime.py`
- `cli/test_pi_thinking_level.py`
- `gui/src/settings/agentInstances.ts`
- `gui/src/settings/hireColleague.ts`
- `gui/src/components/ColleagueConfigBar.tsx`
- `gui/src/components/HireColleagueModal.tsx`
- `docs/GUI-CONFIG.md`
- `docs/anvil/brainstorms/2026-07-30-pi-thinking-level.md`
- `.ai/anvil/reviews/2026-07-30-pi-thinking-level-review.md`
- （plan 若需入库须先修 gitignore）
