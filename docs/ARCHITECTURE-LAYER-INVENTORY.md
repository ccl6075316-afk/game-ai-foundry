# 三层功能归属清单 — 2026-08-20

> **读者**：下一任 AI / 维护者。  
> **目的**：把现有能力标清 **CLI 引擎 / 桥接 Host / GUI**，并标出 **要改 / 可能没用 / 该模块化**。  
> **姊妹**：策略与优先级见 [`ARCHITECTURE-REFACTOR-HANDOFF.md`](ARCHITECTURE-REFACTOR-HANDOFF.md)；**可执行 Plan** 见 [`anvil/plans/2026-08-20-host-layer-refactor-plan.md`](anvil/plans/2026-08-20-host-layer-refactor-plan.md)；命令大全见 [`AI-HANDOFF.md`](AI-HANDOFF.md)。

---

## 0. 三层约定

| 层 | 该干什么 | 不该干什么 |
|----|----------|------------|
| **CLI 引擎** | 真干活：读写 brief / manifest / plans / output，validate，生图，Godot | 不知道 Electron；不做「点一次跑通」产品循环 |
| **桥接 / Host** | 策略：失败分诊、reset 链、auto-fix、retry-asset、Agent prompt/dispatch、safe 白名单 | 不画 UI；不直接 ACP socket |
| **GUI** | 展示、聊天、权限弹窗、选工程、点按钮调 Host/CLI | 不自己拼 `pipeline reset` 策略；不复制 hydrate 逻辑 |

**现状问题：** 桥接曾散在三处；**2026-08-21 Host Plan T1–T5 已落地** `cli/host/`（retry-asset、run-assets --auto-fix）、GUI IPC 接线、VT status 单源。编排仍部分留在 `App.tsx`（P3 瘦身待续）。

```text
GUI（展示 + 部分编排）
  │ IPC → spawn
隐式桥接（散落：pipeline_heal · agent_turn · App auto-repair · Electron ACP）
  │
CLI 引擎（brief / prompt_craft / pipeline / image / godot …）
```

---

## 1. CLI 引擎（应留，少改归属）

| 能力 | 主要代码 | 说明 |
|------|----------|------|
| Brief 读写 / validate / export / shards | `brief.py`, `brief_cmds.py`, `brief_shards.py`, `host_chat.py` | 策划权威源 |
| 北极星 generate / pick / status | `visual_target.py` | CLI status 已 hydrate 分册 |
| Prompt craft | `prompt_craft.py`, `prompt_cmds.py` | **模块保留**；用户不必当「同事」 |
| Pipeline plan / run / reset | `pipeline_*.py` | 引擎；缺产品级 retry |
| 生图 / 抠图 / 视频 | `image_cmds.py`, `video_*.py`, `seedance_api.py`, `video_compat.py` | 执行器 |
| Godot assemble / scaffold / validate | `godot_*.py` | 下游 |
| Production / progress / handoff 落盘 | `production*.py`, `progress.py`, `handoff.py` | 文件总线 |
| Inspect / conversations | `inspect_*.py`, `conversations_*.py` | IT 只读 |
| Config / setup / doctor / toolchain | `config_cmds.py`, `setup_*.py`, `toolchain_*.py` | 环境 |

**不要删 / 不要削弱：** `prompt_craft.py`、image / matting validate、CJK 守卫、`pipeline_heal` 分类表。

---

## 2. 桥接层（已收进 `cli/host/`，部分 GUI 编排待瘦）

| 能力 | 今天在哪 | 目标归属 | 状态 |
|------|----------|----------|------|
| 失败分诊 / heal / `fix_commands` | `cli/pipeline_heal.py` | Host | ✅ CJK→validation（T1） |
| 目标模式 auto-repair 循环 | `cli/host/run_assets.py` + GUI IPC | `host run-assets --auto-fix` | ✅ T3/T4 |
| Safe 串跑白名单 | `cli/safe_cli.py` + Host 内部 | Host 统一 | ✅ 放行 `host *` |
| Agent 回合 / prompt / dispatch | `agent_turn.py` + Electron ACP | Host 策略 | 部分 |
| PM / IT ops 注入 | `pmOpsContext.ts` / `itOpsContext.ts` | 可并进 Host prompt builder | 待续 |
| 单资产 suggest-retry | `cli/host/retry_asset.py` + 看板/资产「重跑」 | `host retry-asset` | ✅ T2/T4 + UI |
| VT status 分册 hydrate | CLI `brief visual-target status` | **只留 CLI** | ✅ T5（删 Electron hydrate） |

---

## 3. GUI（应留展示 / UX）

| 能力 | 代码 | 说明 |
|------|------|------|
| 聊天壳、同事花名册、会话 | `ChatView`, `sessions.ts`, `roster.ts` | |
| 设置 / Provider / 执行器 UI | `SettingsPage`, `settings/*` | |
| 看板任务表、北极星条、资产审图表 | `BoardPanel`, `TaskList`, `AssetReviewPanel` | 展示 + 点按钮 |
| 文档预览 / focus | `DocsPreviewPanel` | |
| 权限卡、ACP 中途审批 | Electron ACP + `toolPermission` | **必须留 GUI** |
| Makeability 缺口卡 | `MakeabilityGapCard`, `makeabilityCopies` | UI |
| VT 芯片解析（选用 / 重做） | `vtChoiceParse`, `vtRestyleRoute` | 可留 GUI；最终执行走 CLI |

---

## 4. 要修改的（按优先级）

### P0 — 行为对，归属错

| 项 | 现状 | 改法 | 状态 |
|----|------|------|------|
| 「项目经理处理失败」 | 只分诊，不执行 reset | Host：validation 类直接跑 `fix_commands`，或按钮调 `host retry-asset` | ✅ T4 |
| `pipeline run` 默认不带 `--run-prompts` | craft 失败后「修不了」 | Host 在 validation 路径强制带；GUI 文案对齐 | ✅ T1/T3 |
| VT ready 闸门 | Electron 曾读索引漏分册；现 Electron 又 hydrate 一份 | Electron 调 CLI `visual-target status`，删本地 hydrate 双份 | ✅ T5 |

### P1 — Host 包（收益最大）

| 新命令 / 模块 | 从哪抽 | GUI 变成 | 状态 |
|---------------|--------|----------|------|
| `host run-assets --auto-fix` | `handleRun` + `attemptPipelineAutoRepair` | 一次 IPC | ✅ T3/T4 |
| `host retry-asset --asset X [--recraft-prompt]` | `pipeline_retry` + reset + craft | 看板「只重跑此资产」 | ✅ T2/T4 |
| `safe_cli` 放行限参 `prompt craft` | 今天禁止 | 挂在 retry 内部，不给裸 craft | ✅ 经 `host retry-asset` |

### P2 — 文档 / 认知

| 项 | 改法 | 状态 |
|----|------|------|
| `roles.py`「七角色永不合并」 | 对内 pipeline 步骤保留；对外文档并入 pipeline | 代码未动 |
| `AGENT-ROUTING.md` / Hermes skill 名 | prompt-crafter 降为步骤，不是同事 | ✅ T6 |

### P3 — GUI 瘦身（P1 之后）

| 项 | 改法 |
|----|------|
| `App.tsx` 编排函数 | 迁出或删：`attemptPipelineAutoRepair`、`executeSafeActionChain`、`planPipelineStop`、大量 VT/pipeline 状态机 |
| `main.mjs` | 只留 spawn + ACP + 薄 IPC；业务 JSON 全来自 CLI |

---

## 5. 可能没用了 / 该降级（不是立刻删代码）

| 对象 | 判断 | 建议 |
|------|------|------|
| **用户心智里的 prompt-crafter 同事** | 产品上不需要 | 文档降级；**代码模块留** |
| **Hermes 当 IT** | 已拒 / 回退 Pi | 选项继续藏；路由残留可清 |
| **GUI 内第二套 VT status hydrate** | 与 CLI 重复 | 收敛后 Electron 这份可删 |
| **「项目经理处理失败」纯聊天分诊** | 目标模式后应少用 | 保留人工兜底；默认走 auto-fix |
| **Agent 手写 `plans/*.json`** | escape hatch | 文档标明非默认 |
| **六/七角色对外叙事** | 认知负担 | 对用户：策划 / 项目经理 / 程序员 / IT（+顾问）；其余是 pipeline 内部角色 |
| **`SettingsPanel` 大段** | 已嵌进 `SettingsPage` | 可继续瘦，不是死代码 |
| **厂商 probe mp4** | 工程产物，非 Foundry 功能 | 继续不入库 |

---

## 6. 该模块化的清单

```text
cli/host/                    ← 新建，渐进迁入
  run_assets.py              ← auto-fix 循环（现 App.tsx）
  retry_asset.py             ← reset + 可选 craft + run
  diagnose_api.py            ← 包装 pipeline_heal（可 thin wrap）
  agent_prompt.py            ← 从 agent_turn.build_prompt 抽稳定 API

cli/（引擎，少动）
  pipeline_*, prompt_craft, visual_target, brief_*, image_*, godot_*

gui/
  只调 host/pipeline IPC；VT 芯片解析可留 chat/
  electron：ACP + spawn；删业务 hydrate 副本
```

| 现在就该切 | 为什么 | 状态 |
|------------|--------|------|
| `host retry-asset` | 消「分诊完任务还在」 | ✅ |
| `host run-assets --auto-fix` | 目标模式可测、可 CLI 复现 | ✅ |
| Agent prompt 单一入口 | ACP / 非 ACP / 角色已开始分叉 | 部分 |
| VT status 单一实现 | 曾踩双份 hydrate | ✅ |

| 暂缓 | 原因 |
|------|------|
| 整包 `cli/core/` vs `cli/host/` 挪文件 | 没有稳定 Host API 前只会出大 diff |
| 先拆 `App.tsx` 为十几个文件 | 先抽 Host，再拆 UI |

---

## 7. 谁说了算（用户动作）

| 用户动作 | 今天真正决策在哪 | 目标 |
|----------|------------------|------|
| 运行资产生成 | App `handleRun` + CLI run | **Host** `run-assets --auto-fix` |
| 项目经理处理失败 | App 调 Agent + heal 只修 code 类 | **Host** 先执行 fix 链，Agent 仅 unknown |
| 选用北极星 | GUI → CLI pick | 不变（CLI） |
| 是否已选北极星 | Electron / CLI 曾不一致 | **只信 CLI status** |
| 只重跑一条资产 | 命令散，GUI 不完整 | **Host** `retry-asset` |
| 改 prompt 再生成 | 须人记得 `--run-prompts` | Host 按 kind 自动带 |

---

## 8. 验收标准（防做成「又多一层 CLI」）

1. 点「运行资产生成」后，**validation 类**失败在无人再点「项目经理处理失败」时，能 reset、带 `--run-prompts` 续跑，失败任务从看板消失。
2. 同 `task_id` + 同 `kind` 连续失败 **2 次** 则停，交给人（防偶发 LLM 烧额度）。
3. `safe_cli` 若放行 `prompt craft`：必须 `--asset`、禁止整 brief 扫；优先只挂在 `host retry-asset` 内部。
4. Electron **不再**维护独立 VT ready 判定。

---

*文档版本：2026-08-21。Host Plan T1–T6 已落地（代码 T1–T5 + 文档 T6）。*
