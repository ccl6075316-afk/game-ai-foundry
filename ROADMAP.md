# Game AI Foundry — Roadmap

## 目标

把项目收敛为外部 Agent 可直接调用的纯 CLI / Workflow 工具箱：

```text
外部 Agent → Skill → workflow CLI → brief / production / pipeline / godot / test → JSON 状态
```

判断、编排、修复由外部 Agent 承担；仓库只保留确定性契约和执行能力。

## 当前状态

### 已完成

- Brief Draft → `brief freeze` → 冻结契约。
- 场景、系统、资产分册与 Production 派生。
- `workflow context/validate/init/run/status/resume` 六命令与稳定 JSON 合同。
- Pipeline DAG、`run/resume`、资产审查、Godot、测试入口。
- 已移除的桌面客户端、内置会话与品牌专属运行时不再作为当前入口。

### 当前交付

- 通用外部 Agent Skill：[`resources/skills/gamefactory-toolkit/SKILL.md`](resources/skills/gamefactory-toolkit/SKILL.md)。
- 中文文档索引与 CLI 手册：[`docs/README.md`](docs/README.md)、[`docs/AI-HANDOFF.md`](docs/AI-HANDOFF.md)。

## 下一步

1. 完成 T7 全量测试、删除扫描和端到端 smoke。
2. 以 `manifest`、`progress`、`handoff` 为唯一状态，校验跨会话恢复。
3. 扩展 `workflow` 后续 stage 时继续复用现有 Pipeline 引擎，不新增第二套 DAG 或状态库。
4. 维护 Brief、Production Delta、Godot、test 的验收契约。

## 架构

```text
Skill（读取顺序、权限、失败分类）
  ↓
workflow context / validate / init / run / status / resume
  ↓
brief contract · production blueprint · pipeline DAG · godot · test
  ↓
brief.json · production.json · manifest · progress · handoff
```

## 文档入口

- [`README.md`](README.md)
- [`AGENTS.md`](AGENTS.md)
- [`docs/README.md`](docs/README.md)
- [`docs/AI-HANDOFF.md`](docs/AI-HANDOFF.md)
- [`docs/TOOLS.md`](docs/TOOLS.md)
- [`docs/CONSTRUCTION-SYSTEM.md`](docs/CONSTRUCTION-SYSTEM.md)
- [`docs/ITERATIVE-PRODUCTION.md`](docs/ITERATIVE-PRODUCTION.md)
