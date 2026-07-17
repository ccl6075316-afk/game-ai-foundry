# Game AI Foundry v0.0.5

**主更新：协作稳定性与 Hermes 可迁移配置** — 修三同事串台 / loading、Hermes 本机路径与 Provider 选择、Cursor Agent 编码。

相对 [`v0.0.4`](RELEASE-NOTES-0.0.4.md)。

## 下载

| 平台 | 文件 | 说明 |
|------|------|------|
| **Windows x64** | `Game-AI-Foundry-0.0.5-win-x64.zip` | 解压后运行 `Game AI Foundry.exe` |

> 未签名：Windows 可能 SmartScreen 提示。macOS 包需在 Apple Silicon 上另打。

## Bug 修复

- **三同事隔离**：回复写回发话时的会话；busy 按同事独立（不再一人转圈三人 loading）
- **角色头像**：策 / 经 / 程区分显示
- **Hermes skills / API**：写入 `$HERMES_HOME`（Windows 常见为 `%LOCALAPPDATA%\hermes`），避免装到错误的 `~/.hermes` 导致 `Unknown skill`
- **Hermes Provider**：角色页可单独选择要同步的生文 Provider（与「当前生文」解耦）；支持 DeepSeek / Kimi / GLM 等
- **Cursor Agent**：强制 UTF-8，避免 Windows GBK 解码失败导致程序员「无输出」
- **Release 可迁移**：Hermes SKILL 源不再烘焙本机绝对路径；`config.example` 去掉本机 Godot 路径

## 沿用 v0.0.4

- AI 公司前台（策划 / 项目经理 / 程序员）
- 分诊 handoff、一键白名单命令、Production Delta
- Construction harness、工具链自动安装、内嵌 Python（含 rembg）

## 纯净机使用

1. 解压并打开 **Game AI Foundry**
2. **设置 → Provider** 填多家 Key（可选）；**角色**里若用 Hermes，选好「Hermes 使用的 Provider」并保存
3. **环境 → 执行器** → Hermes：安装 CLI → Skills → **同步 API**（换 Provider 后可「重新同步」）
4. 与策划落实 brief → `/plan` → `/run`

## 已知限制

- 执行器 CLI 仍需本机安装（不随包内嵌）
- macOS 本版若未附 zip，请自行 `scripts/build-release.sh` 或等后续补传
