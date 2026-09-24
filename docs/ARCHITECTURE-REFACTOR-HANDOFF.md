# 架构收口交接

> 读者：下一任维护者或接手重构的外部 Agent。
> 事实源：[`ARCHITECTURE-LAYER-INVENTORY.md`](ARCHITECTURE-LAYER-INVENTORY.md) 与当前 CLI `--help`。

## 1. 核心结论

本项目的稳定形态不是“内置一个团队”，而是“给外部 Agent 一套窄而确定的工具”：

```text
外部 Agent 负责：理解目标 → 修 Brief/Production → 选命令 → 解释失败 → 继续编排
仓库负责：校验 → 初始化 → 执行 → 恢复 → 验收 → 写文件状态
```

任何要求外部 Agent 才能完成的判断，不应被复制成第二套状态机；任何确定性执行，也不应依赖会话记忆。

## 2. 数据流

```text
Draft JSON
  → brief freeze（brief_meta）
  → production derive（scenes / systems / assets → godot_tasks / acceptance）
  → pipeline plan（assets → DAG manifest）
  → workflow run（ready tasks → outputs + manifest）
  → assets review（交付确认）
  → godot scaffold / assemble / validate
  → test unit / play / regression
  → progress / handoff / validation report
```

改需求时：

```text
Change Request
  → production delta
  → production apply-delta --dry-run
  → production apply-delta + progress sync
  → 定点 pipeline plan --merge / reset
  → regression
```

## 3. 已收口的边界

- Composition Root 只注册确定性命令。
- Workflow 只做组合和 JSON 归一化。
- Brief 冻结后由文件契约驱动，不依赖对话历史。
- Pipeline 仍是唯一资产 DAG 引擎。
- Progress / handoff 仍是唯一续作账本。
- Godot 与 Test 回到 Brief / Delta 的验收依据。
- 已移除的桌面客户端与品牌专属运行时不再进入当前文档入口。

## 4. 三类失败与正确修法

### 4.1 输入失败

`brief_invalid`、`production_invalid`、`manifest_invalid`、`unsupported_stage`：

1. 读取 `failures[]`。
2. 修 Draft、Brief、Delta 或 manifest 生成参数。
3. 重新 `workflow validate`。
4. 状态合法后再 `init` / `run`。

### 4.2 执行失败

`task_failed`、`run_failed`、`resume_failed`、network/API：

1. 读取 `summary.manifest.failed_ids`。
2. 读取 task `result`、日志与 `summary.runner.run_exit_code`。
3. 修输入或环境。
4. 只恢复失败 task：`workflow resume --task-id <id>`。

### 4.3 验收失败

Godot build、playtest、vision、regression：

1. 保存 validation report 与证据。
2. 对照 Brief acceptance criteria / Delta。
3. 若是设计问题，产生新的 Change Request；若是实现问题，修 `godot_tasks[]`。
4. 重跑对应层级和 regression。

不要把验收失败改写成“通过”，也不要静默扩大实现范围。

## 5. 推荐接手顺序

1. 读 [`../resources/skills/gamefactory-toolkit/SKILL.md`](../resources/skills/gamefactory-toolkit/SKILL.md)。
2. 运行 `workflow --help` 与六个子命令 `--help`。
3. 读 [`AI-HANDOFF.md`](AI-HANDOFF.md) 的文件契约与铁律。
4. 对示例 Brief 运行只读 `context` / `validate`。
5. 检查 `manifest`、`progress`、`handoff` 是否仍是唯一状态。
6. 再做任何写入或执行。

## 6. 禁止回退

- 不重新引入桌面客户端作为主入口。
- 不为每个外部 Agent 写一套适配器。
- 不把状态复制到会话、缓存或新数据库。
- 不绕过 `brief freeze`、matting validation、Godot scope 或 test regression。
- 不在文档中保留已移除文件作为当前操作入口。

## 7. 相关文件

| 文件 | 用途 |
|---|---|
| [`ARCHITECTURE-LAYER-INVENTORY.md`](ARCHITECTURE-LAYER-INVENTORY.md) | 模块与状态归属 |
| [`AI-HANDOFF.md`](AI-HANDOFF.md) | 命令与文件契约 |
| [`CONSTRUCTION-SYSTEM.md`](CONSTRUCTION-SYSTEM.md) | 施工分层 |
| [`ITERATIVE-PRODUCTION.md`](ITERATIVE-PRODUCTION.md) | Delta 与回归 |
| [`../resources/skills/gamefactory-toolkit/SKILL.md`](../resources/skills/gamefactory-toolkit/SKILL.md) | 外部 Agent 协议 |
