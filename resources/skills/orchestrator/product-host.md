# 分诊与派工

供外部 Agent 根据文件状态选择下一步，不依赖任何内置会话或桌面入口。

## 输入

- `workflow context/status/validate` 的 JSON。
- `production.json`、`manifest`、`progress`、`handoff`、validation report。
- 用户的 Change Request 或验收反馈。

## 决策树

```text
ok=false
  → 修输入 → workflow validate

status=blocked / failures[].kind=validation
  → 修 Brief、Production 或 manifest → workflow validate
  → 缺失状态且 next_action=derive_production → workflow init

status=pending / next_action=run
  → workflow run --stage assets

status=running
  → workflow status，不重复启动

status=paused
  → 检查阻塞原因 → workflow resume

status=failed
  → failed_ids + task result → 修因 → workflow resume --task-id

status=done / next_action=human_review
  → assets review → godot → test

status=done / next_action=none
  → 无后续 Workflow 动作

validation / regression failed
  → 读 report → 判断实现问题或设计变化 → Delta / Change Request
```

## 分诊规则

1. 输入错误：修 Brief、Production、manifest，不重跑整条 DAG。
2. Prompt validation：修 prompt/Brief；`exit 2` 后禁止 matting。
3. 网络/API：读取 `summary.runner`，修环境后定点 resume。
4. 资产未审查：仅在 `status=done` 且 `next_action=human_review` 后 review，再组装。
5. Godot scope：只做 Brief / Delta 范围。
6. 验收失败：保存 report，不能改状态冒充通过。

## 输出

```json
{
  "triage": "input|execution|validation|environment",
  "status": "<workflow status>",
  "next_action": "<command>",
  "commands": ["<exact command>"],
  "evidence": ["<path or JSON field>"],
  "risks": []
}
```

`commands` 必须是可直接执行且符合权限边界的命令；不得伪造确认参数。

通用协议见 [`../gamefactory-toolkit/SKILL.md`](../gamefactory-toolkit/SKILL.md)。
