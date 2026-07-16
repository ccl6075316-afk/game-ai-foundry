# Game AI Foundry v0.0.3

**主更新：Construction harness 工具体系** — 多轮施工与验收金字塔入 Release 包。

相对 [`v0.0.2`](RELEASE-NOTES-0.0.2.md) tag 之后合入、并随本包分发的能力。完整进度见 [`ROADMAP.md`](../ROADMAP.md)。

## 下载

| 平台 | 文件 | 说明 |
|------|------|------|
| **Windows x64** | `Game-AI-Foundry-0.0.3-win-x64.zip` | 解压后运行 `Game AI Foundry.exe` |
| **macOS arm64** | （如有 CI/本机构建再补） | 解压后运行 `Game AI Foundry.app` |

> 未签名：Windows 可能 SmartScreen 提示。zip 为当前推荐分发格式。

## 主功能 — Harness / 施工体系

面向 **多轮迭代出成品**（非一句话一次完美）：

```
brief.json
  → production.json（工程蓝图）
  → godot scaffold（可编译 C# 壳）
  → progress.json（续作账本）
  → validate · test unit · test play · test regression
```

| 命令 | 作用 |
|------|------|
| `production derive\|validate\|show` | brief → 工程蓝图 |
| `godot scaffold` | 场景 / InputMap / 占位脚本 / `tests/` xUnit |
| `project progress init\|show\|task\|validation\|note` | 本轮任务与验收写回 |
| `test unit` | L1 `dotnet test` |
| `test plan --task` / `test play` | per-task harness（`assert_*`） |
| `test regression` | 通过 plan 快照并重跑 |

文档：[`CONSTRUCTION-SYSTEM.md`](CONSTRUCTION-SYSTEM.md)

## 亦含于本包（自 v0.0.2 主干）

- Provider 多账号、执行器向导、工具链自动安装（FFmpeg / Godot .NET / .NET SDK）
- 内嵌 Python（含 rembg）— 无需本机 Node / Python

## 纯净机使用

1. 解压 zip，双击 **Game AI Foundry**
2. **设置** → 填 API Key；环境工具栏安装 FFmpeg / Godot（如缺）
3. `/brief` → `/plan` → `/run --run-prompts`
4. 施工：`production derive` → `project progress init` → `godot scaffold` → `test unit` / `test play`

## 已知限制

- Production Delta / Change Request CLI 未落地
- GUI 主聊天尚未路由到 host executor
- 视觉 QA 非硬门禁；Windows 干净机全链 E2E 待验证
- Magic Prince 等旧工程需 `pipeline plan --merge` 补 assets-manifest

## 构建机验证（本包）

- [x] Windows zip（electron-builder）
- [ ] GUI 双击全链（人工）
- [ ] 干净 VM E2E
