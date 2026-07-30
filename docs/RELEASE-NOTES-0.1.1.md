# Game AI Foundry v0.1.1

**主更新：Windows 安装版自动更新 + 可选目录 / 干净卸载；对话可停；侧栏可拖宽**

相对 [`v0.1.0`](RELEASE-NOTES-0.1.0.md)。

## 下载

| 平台 | 文件 | 说明 |
|------|------|------|
| **Windows x64（推荐）** | `Game-AI-Foundry-0.1.1-setup.exe` | NSIS：可选安装目录、可卸载卸干净、**应用内自动更新** |
| **Windows x64** | `Game-AI-Foundry-0.1.1-win-x64.zip` | 解压即用；**无**自动更新，需手动换包 |
| **Windows x64** | `Game-AI-Foundry-0.1.1-portable.exe` | 便携版；无自动更新 |
| **macOS arm64** | `Game-AI-Foundry-0.1.1-mac-arm64.zip` | 手动解压；首次可能需「仍要打开」；**暂无**应用内自动更新 |

> Windows 未签名：可能 SmartScreen 提示。macOS 未公证：需右键打开 /「仍要打开」。

## 新功能 / 修复

- **Windows 自动更新**：仅 `*-setup.exe`；启动后检查 GitHub Releases，顶栏「重启安装」；设置 → 本机可手动检查
- **NSIS 安装体验**：可选安装目录；可选当前用户 / 所有用户；开始菜单 + 桌面快捷方式
- **干净卸载**：卸载清除安装目录、`%APPDATA%` / `%LOCALAPPDATA%` 下 `game-ai-foundry-gui`、以及 `%USERPROFILE%\.gamefactory`（外置 Godot 工程目录不删）；升级安装不删用户数据
- **对话停止**：忙时输入框变为停止，可中断 CLI / ACP 本轮
- **侧栏拖宽**：文档 / 看板 / 资产可拖拽调宽并记住宽度
- **文档面板**：区分中文说明 / 工作草稿 JSON / 策划笔记；修复 focus 粘住导致点其它文档回弹

## 纯净机使用（Windows 推荐）

1. 安装 **`Game-AI-Foundry-0.1.1-setup.exe`**（自选目录）
2. **设置** → Provider 填 LLM API Key；等待顶部芯片变绿
3. 与策划落实 brief → 项目经理 `/plan` `/run`；环境问题找 IT
4. 以后有新版会提示更新；macOS 用户请到本页手动下 zip

说明 → 本文件 · 打包策略 → [`RELEASE.md`](RELEASE.md)

## 已知限制

- 同 v0.1.0：未代码签名 / macOS 未公证；Mac / zip / portable **不做**应用内自动更新
- IT 不改 Foundry 源码 / 大段玩法 C#（仍回 Cursor / 程序员）
