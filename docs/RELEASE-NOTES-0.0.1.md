# Game AI Foundry v0.0.1

首个可分发 Release。

## 下载

| 平台 | 文件 | 说明 |
|------|------|------|
| **Windows x64** | `Game-AI-Foundry-0.0.1-win-x64.zip` | 解压后运行 `Game AI Foundry.exe` |
| **macOS arm64** | `Game-AI-Foundry-0.0.1-mac-arm64.zip` | 解压后运行 `Game AI Foundry.app` |

> 未签名：Windows 可能 SmartScreen 提示；macOS 首次打开请右键 → 打开。  
> Windows `portable.exe` / `setup.exe` 需构建机可访问 GitHub（NSIS 依赖）；zip 为当前 Windows 推荐分发格式。

## 纯净机使用步骤

1. 解压 zip，双击 **Game AI Foundry**
2. **设置** → 从示例创建 → 填写 **OpenRouter** Key
3. 等待 **FFmpeg / Godot / .NET** 自动安装（顶部芯片变绿）
4. **（推荐）环境 → 执行器** → 配 Hermes / Codex
5. `/brief` → `/plan` → `/run --run-prompts`

**无需**安装 Python、Node 或 npm。

## 包含

- Electron GUI + 内嵌 Python（含 OpenCV、**rembg**）
- gamefactory CLI 与示例 resources
- 环境工具栏、执行器向导、命令指南

> v0.0.2 变更见 [`RELEASE-NOTES-0.0.2.md`](RELEASE-NOTES-0.0.2.md)

## 构建机验证（v0.0.1 Windows zip）

- [x] 内嵌 Python：`doctor --json` 可运行（pipeline executor available）
- [x] `vite build` + `electron-builder --win zip`
- [ ] GUI 双击 E2E（需人工：填 Key → `/brief` → `/run`）
- [ ] 纯净 VM 全链（待 CI / 人工）

## 已知限制

- Windows zip 在 **Windows x64** 本机构建；macOS 包需在 macOS arm64 构建
- Godot、API Key 仍需用户自行配置
- 应用未代码签名
