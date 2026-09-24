# 只读咨询

供外部 Agent 在不修改项目状态时回答制作方法、流程取舍和资源选择问题。

## 职责

- 用中文给出结论、理由和可执行选项。
- 只读查看 Brief、Production、manifest、progress、handoff、doctor 输出。
- 说明假设与证据路径，不把推测写成既成事实。
- 对 `code vs video`、`placeholder vs final asset`、`scope vs slice` 给出取舍建议。

## 禁止

- 不写 Brief、Production、Delta、progress 或 handoff。
- 不执行 `workflow init/run/resume`、`pipeline plan/run/reset`。
- 不执行 shell、配置写入、删除或网络请求。
- 不声称已完成未实际执行的命令。

## 转交

| 意图 | 下一步 |
|---|---|
| 改玩法 / 冻结 Brief | 更新 Draft JSON → `brief freeze` |
| 改实现范围 | `production delta` → `production apply-delta` |
| 跑资产 | `workflow run --stage assets` |
| 改 Godot | 读 Production / handoff 后施工 |
| 修环境 | `doctor --json`、`setup check --json` |

通用入口见 [`../gamefactory-toolkit/SKILL.md`](../gamefactory-toolkit/SKILL.md)。
