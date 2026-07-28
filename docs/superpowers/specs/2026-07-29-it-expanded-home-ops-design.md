# 工程 Spec：IT 加宽能力 + 默认信任本会话（家庭运维）

## 执行元数据

- **Status**：implemented
- **Workflow Stage**：verify
- **Created**：2026-07-29
- **Updated**：2026-07-29（实现完成）
- **Confirmed By**：用户选 E；信任默认开；pipeline run=B；用户「确认」审阅本 Spec
- **Source Of Truth Until**：实现以 [`docs/superpowers/plans/2026-07-29-it-expanded-home-ops.md`](../plans/2026-07-29-it-expanded-home-ops.md) 为准（本 Spec 已落地）
- **Change Log**：初稿；用户确认后挂 plan；Task 1–5 实现

## 背景

今日 IT（Pi + `FOUNDRY_TOOL`）白名单偏窄：doctor / setup / pipeline diagnose·heal·reset / 少量 brief 工具。  
用户明确：**家里大半运维应找 IT**，只有改 Foundry 源码、大产品设计才回 Cursor；权限卡片反正一路批准，**不要因怕权限而少加工具**。

已定决策：

| 项 | 决定 |
|----|------|
| 能力目标 | E — IT 成为家庭运维（工程/brief 导出前/流水线/环境/资产指引） |
| 架构 | 加宽白名单为主 + 少量 GUI 快捷按钮 |
| 权限 | **IT 默认「信任本会话」**（等同现有「本会话允许」预开，变更工具少打断） |
| `pipeline run` | **B** — 信任本会话后 IT **可以**跑（烧钱可接受，用户自担） |
| 硬禁止 | 任意 shell；改 Foundry/Electron/Pi **源码**；改玩法 `games/` C#（仍归程序员）；路径逃逸 |

## 目标

1. **扩大 IT 白名单**，覆盖近期常回 Cursor 的运维类问题（同步草稿、中文说明、导出前审查、看板/流水线、环境、资产审查只读）。  
2. **IT 实例默认信任本会话**：变更类 `FOUNDRY_TOOL` 不再逐条弹卡（或首开会话时自动写入 session-allow）；仍保留「每次确认」可选。  
3. **允许** `pipeline run`（及合理 jobs/flags）在 IT profile + 信任会话下执行。  
4. 重写 IT skill 为**家庭运维剧本**（先结论、再工具、再中文短答）。  
5. GUI：IT 配置条默认信任；可选 3～5 个快捷动作（同步草稿 / 中文说明 / 环境检测 / 看板诊断 / 跑资产）。

## 非目标

- IT 改 `gui/`、`cli/`、Electron、Pi 源码（仍回 Cursor）。  
- IT 当程序员大段改 `games/**/*.cs`（仍归程序员 / Hermes·Codex）。  
- 任意 shell / 任意绝对路径写盘。  
- 策划（brief profile）自动继承 IT 全量白名单（策划仍窄；export 门闩不变）。  
- 永久全局「永远允许所有工具不审计」（本会话信任即可；审计日志仍要）。

## 当前架构约束

- IT 默认 executor = Pi；工具经 `pi_foundry_tools.py` 白名单 +（可选）GUI permission bridge。  
- 已有卡片：允许一次 / 本回合 / **本会话** / 拒绝。  
- `pipeline run` **今日不在** `_ALLOWED_PREFIXES`。  
- Brief 草稿已可落盘 `brief.draft.json`；`brief zh-doc` 可导出前生成中文说明。

## 方案

**采用：IT profile 宽白名单 + 默认 session-trust + 允许 pipeline run（信任下）。**

### A. 白名单加宽（IT profile）

在现有 IT 前缀上增加（只读可不弹卡；变更类走信任或卡片）：

| 前缀 | 用途 | 变更？ |
|------|------|--------|
| `brief chat bind` | 绑工程 / 灌草稿 | 是（会话） |
| `brief chat zh-doc` | 导出前中文说明 | 是（写 md） |
| `brief chat autofix` | 修导出 gaps | 是（会话草稿） |
| `brief chat makeability` | 制作完备性审查 | 否/轻 |
| `brief chat enrich` | 补全细节（可选） | 是 |
| `brief chat status` | 已有 | 否 |
| `brief validate` | 已有 | 否 |
| `project external list` / `detect` | 外置工程 | 否 |
| `assets review list` | 资产审查表 | 否 |
| `pipeline plan` | 生成清单 | 是 |
| `pipeline run` | **新增**跑资产 | 是（烧钱） |
| `pipeline diagnose` / `status` / `heal` / `reset` | 已有 | heal/reset 是 |

路径约束：brief / zh-doc / export 类输出仍限 `projects/`、外置登记根、`output/`、`plans/`（与现 export 门闩同精神）。

**仍禁止：** `git` 推远程、改用户家目录任意文件、安装未知 URL 包（仅现有 `setup install` 组件）。

### B. 默认信任本会话

1. 新建/雇佣 IT 同事：`agents.instances[<it>].pi_tool_trust` 或复用 permission turn state 的 **session allow = true** 默认。  
2. 实现优先序（选一，plan 定）：  
   - **B1（推荐）**：IT 回合开始时若未显式关闭信任，permission bridge 对 mutate **自动 allow-session**；  
   - **B2**：配置 `agents.it.default_session_trust: true`，GUI 卡片默认隐藏除非用户关掉信任。  
3. 用户可在配置条关掉「信任本会话」→ 恢复逐条卡片。  
4. 审计：每次工具执行写短日志（命令前缀 + ok/err，Key 脱敏）。

### C. `pipeline run` 门闩

- 白名单加入 `("pipeline", "run")`。  
- 信任本会话：**可直接跑**（用户选 B）。  
- 未信任：仍弹卡（或要求 `--i-confirm` + 卡片）。  
- Skill 要求：跑前用一句话说明「将消耗 API / 时间」；默认 `--jobs` 合理上限（如 ≤4）。

### D. Skill / UI

- 更新 `resources/skills/it/diagnose.md` → 剧本：  
  1) 环境坏了 2) 工程/草稿不同步 3) 导出前审阅 4) 看板/任务失败 5) 跑资产  
- GUI 快捷（可选同版或紧随）：同步草稿、生成中文说明、检测环境、看板诊断、运行资产生成。  
- `gui/src/chat/roles.ts` IT 副标题改为「家庭运维：环境 / 草稿 / 流水线 / 资产审查」。

### E. 与策划分工

| 动作 | 谁 |
|------|-----|
| 聊玩法、写 draft | 策划 |
| 导出冻结 brief.json | 策划（用户明确导出）；IT **不**偷导 |
| 中文说明、autofix、makeability、绑工程、跑 pipeline | **IT 可做**（信任下） |
| 改 C# / 源码 | 程序员 / Cursor |

## 验收

1. 新 IT 会话：连续 `setup install` / `provider upsert` / `pipeline heal` **不**逐条弹卡（信任开）。  
2. IT 可 `brief chat zh-doc` + 读到工程内 `brief.zh.md`。  
3. IT 可 `pipeline run`（信任开）且日志可见。  
4. 关闭信任后恢复弹卡。  
5. 策划 profile 白名单**不**出现 `pipeline run`。  
6. 尝试逃逸路径 / 源码路径 → 拒绝。

## 风险

- 烧钱：`pipeline run` 信任后模型可能误跑 → skill 强调「用户要跑再跑」；失败可接受，用户已选 B。  
- 误绑工程：bind/zh-doc 写错目录 → 路径白名单 + 绑定 `bound_brief_rel`。  
- 权限 UX 变松：提供显式关闭信任开关。

## 实施顺序（plan 细化）

1. `pi_foundry_tools`：扩 `_ALLOWED_PREFIXES` / `_MUTATE_PREFIXES`；IT vs brief profile 分流。  
2. 默认 session-trust（IT）。  
3. Skill + roles 文案。  
4. GUI 信任开关 +（可选）快捷按钮。  
5. 单测：allowlist、trust 跳过 bridge、brief 无 pipeline run。

## 决策账本

| 项 | 决定 |
|----|------|
| 范围 | E 家庭运维 |
| 信任默认 | 开（IT） |
| pipeline run | 信任后可跑 |
| 改源码 / 玩法 C# | 否 |
| 策划 export | 仍归策划，IT 不默认 export |
