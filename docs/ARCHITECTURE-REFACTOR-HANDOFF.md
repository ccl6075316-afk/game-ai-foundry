# 架构梳理与重构交接 — 2026-08-20

> **读者**：下一任接手的 AI / 维护者。  
> **背景**：用户与 Agent 讨论「目标模式、GUI/CLI 边界、prompt-crafter、单条重试、是否重构」的结论汇总。  
> **侧重**：现状、已实现、待做、优先级；**不重复** [`AI-HANDOFF.md`](AI-HANDOFF.md) 命令大全。  
> **姊妹**：[`HOST-CHAT-PRODUCT.md`](HOST-CHAT-PRODUCT.md) · [`AGENT-ROUTING.md`](AGENT-ROUTING.md) · [`ITERATIVE-PRODUCTION.md`](ITERATIVE-PRODUCTION.md)

---

## 0. 用户核心诉求（一句话）

**用户目标是「跑通」**：点运行资产生成 → 中间出错应自动修、自动续跑；Agent 应执行修复而非只报 errno。  
**前面重（brief / prompt / 图）是正常的**；代码（玩法实现）应相对轻。当前痛点是 **边界糊、编排散、能力被角色+白名单拆碎**，不是 validate 本身不该存在。

---

## 1. 核心数据流（抛开 GUI）

```text
策划 export
  → brief.json（+ 分册 scenes/systems/assets/*.json）
       ↓
项目经理 pipeline plan
  → pipeline/manifest.json（任务 DAG）
       ↓
pipeline run
  → plans/*.json（prompt-crafter handoff → image-generator 用）
  → output/*（原图 / nobg / 序列帧）
  → assets-manifest.json（资产表 → assemble / 程序员）
       ↓
godot assemble → dev-context → C# 玩法（相对轻）
```

| 阶段 | 权威产物 | 消费者 |
|------|----------|--------|
| 策划 | `brief.json` | plan、prompt craft、下游只读 |
| 项目经理 | `manifest.json` + `plans/*.json` | 生图 / 抠图 / assemble |
| pipeline 跑完 | `output/` + `assets-manifest.json` | Godot、资产审查、派工 |

**prompt / 资产表不是终态**；终态是图能过检、能进 Godot。

---

## 2. 三类「校验不过」与正确修法

| 层 | 门禁 | 该怎么「改到过」 | 不该怎么做 |
|----|------|------------------|------------|
| **Brief** | `brief validate` / export | 策划 `brief chat autofix` → validate → export | 绕过 export 门禁 |
| **生图 validate** | `image generate --validate` → **exit 2** | 改 **prompt/plan** → `reset` → `run --run-prompts` 再生成 | 调松 OpenCV 阈值「假过」 |
| **抠图 validate** | `image validate-matting` → exit 2 | 重生成或调 matting；reset 后续 task | 同上 |

**exit 2 语义**：可修复软失败；pipeline **故意暂停**（`stop_on_fail`），须 `pipeline reset` 后再 `run`。  
**validation 失败的标准路径**（见 `cli/pipeline_heal.py` `kind=validation`）：

```bash
pipeline reset --task-id <id> --cascade
pipeline run --manifest <manifest> --jobs 4 --run-prompts
```

默认 `pipeline run` **不带 `--run-prompts`** 会 skip prompt-crafter 角色——这是省钱默认，也是 validation 失败后「修不了 prompt」的常见根因。

---

## 3. 现状：三层已存在但未收口

```text
┌─────────────────────────────────────────────────────────┐
│  GUI：App.tsx (~5k) + Electron main.mjs (~3.3k)          │
│  展示 + 聊天 + 部分编排（目标模式、safe 串跑、PM 建议）    │
└───────────────────────────┬─────────────────────────────┘
                            │ IPC → spawn CLI
┌───────────────────────────▼─────────────────────────────┐
│  隐式「桥接层」散落三处：                                  │
│  • CLI：agent_turn, handoff, pipeline_heal, safe_cli      │
│  • Electron：ACP、record-turn、agent prompt（曾 IT-only） │
│  • App.tsx：executeSafeActionChain, attemptPipelineAutoRepair │
└───────────────────────────┬─────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────┐
│  CLI 引擎（~194 py 模块）：brief / prompt_craft / pipeline │
└─────────────────────────────────────────────────────────┘
```

**模糊点**

- GUI 与 CLI 都在做 host 编排（heal、goal loop、dispatch）。
- `agent turn` 在 CLI 里但主要服务 GUI 聊天。
- `safe_cli` 白名单：PM 可 `pipeline reset/run`、`config set`，**不可** `prompt craft`（须 `--run-prompts` 间接 craft）。
- 六角色文档 vs 实际常用命令（brief / pipeline / host）认知负担高。

---

## 4. 本会话已实现（main 上待续）

### 4.1 目标模式（GUI）

- **`handleRun`**：失败后自动 diagnose → heal → 串跑 `fix_commands` → 必要时调 PM Agent → 续跑（最多 2 轮）。
- **`attemptPipelineAutoRepair`**：与「项目经理处理失败」共用逻辑。
- **`pipeline_heal.build_fix_command_chain`**：`fix_commands` / `auto_fix_without_agent`；handoff 注入 `--manifest`。

### 4.2 ACP 与 dispatch 收口

- **`prepareRoleAwareAcpPrompt`**：全角色（非仅 IT）走 `agent prompt` 构建完整 prompt。
- **`record-turn`**：扩展 `--brief --progress --target-instance-id`；`_apply_assistant_dispatch` 与 `run_turn` 共用。
- **record-turn 去重**：避免 ACP 路径重复 append user message。
- **main.mjs**：record 后用 `recordData.assistant_message`（含 dispatch 摘要）。

### 4.3 其他

- **`pmOpsContext.ts`**：PM 注入 manifest / diagnose / 日志。
- **`product-host.md`**：目标模式「先修再报」硬规则。

### 4.4 验证

- `python -m unittest test_agent_turn test_handoff test_pipeline_heal test_safe_cli` — 57 tests OK
- `node --test gui/electron/agent_prompt.test.mjs` — 7 tests OK
- **改 Electron 后须完整重启 GUI**

---

## 5. 讨论结论：该不该重构？

**要模块化重构，不要大爆炸重写。**

| 判断 | 说明 |
|------|------|
| 前面重 | ✅ 正常；brief→图是主路径 |
| 功能不清晰 | 根因是编排散、角色文档>命令文档、默认路径保守 |
| 单独桥接层 | ✅ 应命名收口为 `cli/host/`（或顶层 host 包） |
| CLI 独立 + GUI 展示 | ✅ 方向对；策略 ~90% 回 CLI host，GUI 保留聊天/权限 UX |
| validate 太重 | ❌ 门禁合理；重的是失败后编排，不是检测 |

---

## 6. prompt-crafter：消「角色」不消「模块」

| 方案 | 建议 |
|------|------|
| 用户不再感知 prompt-crafter 第七同事 | ✅ 文档上并入 pipeline 内部步骤 |
| 删除 `prompt_craft.py` / Python assemble | ❌ 会失去 CJK guard、class 硬锁、model profile |
| PM 直接 craft | ✅ 通过 **`prompt craft --asset X`** 或 **`host retry-asset --recraft-prompt`** |
| Agent 手写 plans/*.json | ⚠️ 仅作 escape hatch，非默认 |

**待做**：`safe_cli` 放行 `prompt craft`（可限 `--asset`）；或新增 `host retry-asset`。

---

## 7. 单条重试：能力已有，产品化不足

**已有**

- `pipeline reset --task-id <id>` / `--cascade`
- `pipeline suggest-retry --manifest … --asset hero`
- `pipeline run` 只跑 **ready + pending** 任务（reset 一条后不会全表重跑）

**缺失**

- validation 失败时 suggest-retry / 默认路径 **未自动带 `--run-prompts`**
- 无显式 `pipeline run --only-task`（靠 reset 间接实现，文档未强调）
- GUI 看板/资产表 **「只重跑此资产」** 一键不完整

**建议一级命令**

```bash
gamefactory.py host retry-asset --manifest … --asset hero [--recraft-prompt] [--jobs 2]
# 内部：reset(hero*) + 可选 prompt craft + run（带 run-prompts 若 validation 类）
```

---

## 8. 推荐重构优先级（给下一任 AI）

### P0 — 认知收口（几乎零架构改动）

- [ ] 本文件 + 主路径图进 [`docs/README.md`](README.md) 索引
- [ ] 明确：image exit 2 = 改 prompt 再生成

### P1 — Host 包（收益最大）

- [ ] `host run-assets --manifest … --auto-fix` ← 从 `App.tsx` `handleRun` 迁出
- [ ] `host retry-asset --asset X [--recraft-prompt]`
- [ ] GUI 按钮只调上述 JSON API

### P2 — 权限与角色文档

- [ ] `safe_cli` 加 `prompt craft`（限参数）
- [ ] `AGENT-ROUTING.md`：prompt-crafter 降级为 pipeline 步骤

### P3 — GUI 瘦身

- [ ] `App.tsx` 编排 → `pipelineHost.ts` 或删（若 P1 完成）
- [ ] `main.mjs` 仅 ACP 传输；prompt 全走 CLI

### P4 — CLI 物理分目录（慢）

- [ ] `cli/core/` vs `cli/host/` 新代码进新目录，旧文件渐进迁移

---

## 9. 下一任 AI 建议起手式

1. 读本文 + [`AI-HANDOFF.md`](AI-HANDOFF.md) §0–1 + [`resources/skills/orchestrator/product-host.md`](../resources/skills/orchestrator/product-host.md) 目标模式节。
2. 在 **`projects/fishing-2d`** 上试跑：`pipeline run` → 故意 validation 失败 → 验证目标模式 / `pipeline heal --json`。
3. 若用户要继续 **P1**：先实现 `host retry-asset` CLI + 单测，再改 GUI 调一条命令。
4. **不要**先删 prompt_craft 或 weaken image validate。

---

## 10. 相关文件索引

| 主题 | 路径 |
|------|------|
| 失败分诊 / fix_commands | `cli/pipeline_heal.py` |
| 白名单 | `cli/safe_cli.py` |
| Agent 回合 + dispatch | `cli/agent_turn.py`, `cli/handoff.py` |
| 单资产 suggest | `cli/pipeline_retry.py` |
| GUI 目标模式 | `gui/src/App.tsx`（`attemptPipelineAutoRepair`, `handleRun`） |
| ACP prompt / record | `gui/electron/main.mjs`, `gui/electron/agent_prompt.mjs` |
| PM ops 上下文 | `gui/src/chat/pmOpsContext.ts` |

---

*文档版本：2026-08-20，与 main 上 goal-mode + ACP dispatch 提交同步。*
