# Game AI Foundry v0.0.1

首个可分发 Release（macOS Apple Silicon）。

## 下载

- **macOS arm64**：`Game-AI-Foundry-0.0.1-mac-arm64.zip`（解压后运行 `Game AI Foundry.app`）

> 未签名：首次打开请右键 → 打开。Windows 安装包将在后续 CI 中提供。

## 纯净机使用步骤

1. 解压 zip，双击 **Game AI Foundry**
2. **设置** → 从示例创建 → 填写 OpenRouter / 视频 API Key
3. 顶部**环境工具栏** → 重新检测 → 一键安装 FFmpeg（如缺）
4. （可选）[下载 Godot .NET 便携版](https://godotengine.org/download) → 设置里指定路径
5. `/brief` → `/plan` → `/run --run-prompts`

**无需**安装 Python、Node 或 npm。

## 包含

- Electron GUI + 内嵌 Python（含 OpenCV、rembg）
- gamefactory CLI 与示例 resources
- 环境工具栏、命令指南侧栏

## 已知限制

- 本包仅在 **macOS arm64** 构建；Windows 需在 Windows 上执行 `scripts\build-release.bat`
- Godot、API Key 仍需用户自行配置
- 应用未 Apple 公证，Gatekeeper 可能拦截
