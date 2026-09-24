---
module: "cli/workflow"
date: "2026-09-24"
problem_type: "config_issue"
severity: "high"
symptoms:
  - "GUI、Electron、内置 Agent、Hermes、Pi RPC 与 executor 和确定性 Pipeline 混在同一产品入口中。"
  - "根 CLI help 暴露 agent、agents、hermes、conversations 等内部运行时命令。"
  - "Workflow JSON 曾输出 status=error、stage=brief、next_action=review 等合同外枚举，failure 缺少 kind。"
  - "context/status/validate 被称为只读，但首次调用会使 config_changed=True。"
  - "active skill 仍调用已删除的 agents show，并出现 needs_hermes、pm_fit、GUI 看板等旧语义。"
root_cause: "产品把确定性生产工具与 GUI、会话、Agent 调度和执行器适配耦合在同一仓库入口，外部 Agent 被迫理解并依赖内部编排层，而不是消费稳定 CLI/JSON 合同。"
solution: "删除 GUI 与内置 Agent/Hermes/Pi/ACP/executor 运行时，保留既有 Brief、Production、Pipeline、Godot、Test 执行引擎，新增薄 workflow context/init/run/resume/status/validate 六命令、稳定 JSON 枚举、只读边界、init 回滚与通用 gamefactory-toolkit Skill，由外部 Agent 接管判断和编排。"
prevention: "所有外部入口必须通过稳定枚举合同、真实 root 零写入快照、init 失败回滚、active Skill 删除扫描、凭据递归脱敏和基线对比测试；不得重新引入第二状态库、Agent RPC 或品牌专属适配层。"
tags: ["external-agent", "workflow", "cli", "gui-removal", "json-contract"]
---

## Symptoms

首次复审出现的可观察行为：

```text
status=error / stage=brief / next_action=review
failure={code, message}  # 缺少 kind
config_changed=True      # workflow context 首次只读调用
```

随后 Fix D 定向测试还出现过 fixture 不匹配：

```text
ERROR: test_diagnosis_contract_uses_external_triage_fields
ValueError: Unknown task id 'hero.image.generate'
```

全量测试最终为：

```text
Ran 594 tests
FAILED (errors=4, skipped=2)
```

其中 4 个 errors 已在独立 `git archive HEAD` 基线中复现，属于既有 fixture/CJK 问题，不是本改造回归。

## Investigation Attempts

1. 先验证根 CLI、配置读取和 Workflow JSON 合同，发现“只读”命令仍触发 config migration。
2. 用真实临时项目树比较 bytes、mtime 与 config，而不是只 mock Workflow 函数，定位真实写入边界。
3. 对 `init` 分别注入 `save_manifest` 与 `save_progress` 失败，确认需要先内存构建再回滚。
4. 扫描 active Skill、当前 runtime、入口文档和 help surface，发现 `agents show`、`needs_hermes`、`pm_fit` 与 GUI 叙事残留。
5. 在基线 commit 的独立归档中复跑 4 个失败测试，证明全量 errors 未因本次改造新增。
6. 补测 `OPENAI_API_KEY=`、`--token value`、timeout、cwd、command、stdout、stderr 的递归脱敏。

## Root Cause Analysis

原架构把三类职责放在同一入口：

- 确定性生产：Brief → Production → Pipeline → Godot → Test。
- 人机界面：Electron/React GUI、看板、权限卡片。
- 内部编排：内置会话、Agent dispatch、Hermes/Pi/ACP/executor。

外部 Agent 本来只需要“读上下文、校验、初始化、运行、恢复、看状态”，却必须穿过 GUI 和内部 Agent 层；同时没有稳定 JSON 枚举，导致自动化判断依赖脆弱的自由文本。

根因不是某个 Agent 不够强，而是产品边界把执行引擎和编排主体混在了一起。

## Solution

### Before

```text
GUI / 内置会话 / Hermes / Pi / ACP / executor
             ↓
        Pipeline 执行
             ↓
     GUI 再向外部展示
```

CLI 暴露内部运行时，Workflow 合同也不稳定：

```json
{"status": "error", "stage": "brief", "next_action": "review"}
```

### After

```text
外部 Agent
   ↓
gamefactory-toolkit Skill
   ↓
workflow context/init/run/resume/status/validate --json
   ↓
既有 Brief / Production / Pipeline / Godot / Test
   ↓
manifest / progress / handoff 等权威 JSON 状态
```

稳定合同：

```json
{
  "status": "pending",
  "stage": "assets",
  "next_action": "run",
  "failures": [
    {"code": "brief_invalid", "kind": "validation", "message": "..."}
  ]
}
```

关键实现位置：

- `/Users/czl/projects/game-ai-foundry/cli/workflow/contract.py`
- `/Users/czl/projects/game-ai-foundry/cli/workflow/state.py`
- `/Users/czl/projects/game-ai-foundry/cli/workflow_cmds.py`
- `/Users/czl/projects/game-ai-foundry/resources/skills/gamefactory-toolkit/SKILL.md`

## Prevention

以后新增外部入口时必须同时提交：

1. 固定字段与合法枚举测试。
2. 真实 root 的零写入或事务/回滚测试。
3. 当前 runtime 与 active Skill 删除扫描。
4. JSON/text/timeout 全字段凭据脱敏测试。
5. 与基线 commit 对比的全量测试结论。
6. 中文架构说明；命令、路径、JSON 字段和枚举保持英文。

禁止为了兼容某个 Agent 再添加品牌专属 adapter、聊天状态、第二数据库或 RPC。

## Cross References

- Related issues: 初始 Stage 5 review 的 6 个 High 与 3 个 Medium，均已关闭。
- Related solutions: [`docs/solutions/modules/cli.md`](../modules/cli.md)
- Plan: [`docs/anvil/plans/2026-09-23-pure-workflow-toolkit-plan.md`](../../anvil/plans/2026-09-23-pure-workflow-toolkit-plan.md)
- Review: `.ai/anvil/reviews/2026-09-23-pure-workflow-toolkit-review.md`
