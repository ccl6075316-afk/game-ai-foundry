# 诊断与维护

供外部 Agent 读取仓库、排查环境和修复明确授权的问题。

## 读取顺序

1. 读取 [`../gamefactory-toolkit/SKILL.md`](../gamefactory-toolkit/SKILL.md)。
2. 先运行只读命令，不猜 Key、路径或工具状态。
3. 根据 `failures[]` 定位配置、工具链、Pipeline 或工程问题。
4. 变更前确认权限边界；完成后重跑验证命令。

## 只读诊断

```bash
python cli/gamefactory.py doctor --json
python cli/gamefactory.py setup check --json
python cli/gamefactory.py inspect tree --path . --max-depth 2 --json
python cli/gamefactory.py inspect grep --path cli --pattern <pattern> --json
python cli/gamefactory.py workflow context --brief <brief> --json
python cli/gamefactory.py workflow status --manifest <manifest> --json
python cli/gamefactory.py pipeline diagnose --manifest <manifest> --json
python cli/gamefactory.py project progress show --progress <progress> --json
```

## 修复边界

- 配置：只修改 allowlist 键，并使用显式确认。
- 工具链：只安装用户明确要求的组件。
- Shell：只使用 `gamefactory shell run --i-confirm`，cwd 限制在仓库或 `~/.gamefactory`。
- 代码：先读相关文件，给出最小修改，并重跑对应测试。
- 凭据：不复制到日志、报告、Brief、manifest 或 handoff。

## 剧本

| 症状 | 先查 | 修复 |
|---|---|---|
| Provider 不可用 | `doctor --json` | 修 `provider_accounts` / `image` / `video` / `prompt` |
| 工具缺失 | `setup check --json` | `setup install <component>` |
| Brief invalid | `workflow validate` | 修 Draft / shards → freeze |
| Manifest invalid | `workflow validate` / `pipeline diagnose` | 重新 `pipeline plan`，必要时 `--merge` |
| Task failed | `failed_ids` + task result | 修输入 → `workflow resume` |
| Godot build failed | `godot validate` | 按 Production / handoff 修 |
| Test failed | validation report | 对照 Brief / Delta，修实现或提出 Change Request |

## 回答要求

- 中文、简短、可执行。
- 先给结论，再给读取过的绝对路径或命令输出。
- 明确 `ok`、`status`、`next_action`、`failures`。
- 不虚构成功，不输出凭据。
