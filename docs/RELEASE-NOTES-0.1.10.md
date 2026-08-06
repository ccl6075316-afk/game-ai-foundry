# Game AI Foundry v0.1.10

**主更新：环境「下载镜像」开关（国内加速 GitHub 工具链）**

相对 [`v0.1.9`](RELEASE-NOTES-0.1.9.md)。国内无代理时装 FFmpeg / Godot / Codex 可走可选 GitHub 反代镜像；默认关闭，不影响直连用户。

## 下载

| 平台 | 文件 | 说明 |
|------|------|------|
| **Windows x64（推荐）** | `Game-AI-Foundry-0.1.10-setup.exe` | NSIS：可选安装目录、干净卸载、**应用内自动更新** |
| **Windows x64** | `Game-AI-Foundry-0.1.10-win-x64.zip` | 解压即用；无自动更新 |
| **Windows x64** | `Game-AI-Foundry-0.1.10-portable.exe` | 便携版；无自动更新 |
| **macOS arm64** | `Game-AI-Foundry-0.1.10-mac-arm64.*`（若本页已附带） | 手动解压；暂无应用内自动更新 |

> Windows 未签名：可能 SmartScreen 提示。

## 新功能 / 修复

- **下载镜像**：设置 → 环境 →「使用 GitHub 下载镜像」（默认关）。开启后 FFmpeg / Godot / Codex 等 GitHub API 与 Release 下载经 `ghproxy.net` 前缀反代（可改 `toolchain.download_mirror_prefix`）。
- 配置字段：`toolchain.download_mirror`（默认 `false`）；文档见 [`TOOLS.md`](TOOLS.md) / [`GUI-CONFIG.md`](GUI-CONFIG.md)。
- 继承 v0.1.9：制作审查去重、顾问同事、聊天回写钉会话。

## 纯净机使用（Windows 推荐）

1. 安装 **`Game-AI-Foundry-0.1.10-setup.exe`**（覆盖 0.1.9；安装版会走自动更新）
2. **设置** → Provider 填 Key；等待顶部芯片变绿
3. 国内装工具过慢时：**设置 → 环境** 打开「下载镜像」，再点安装

说明 → 本文件 · 工具 → [`TOOLS.md`](TOOLS.md) · 打包 → [`RELEASE.md`](RELEASE.md)

## 已知限制

- 未代码签名 / macOS 未公证；Mac / zip / portable **不做**应用内自动更新
- 下载镜像依赖社区反代，不稳定时可关掉；.NET（dot.net）不走该镜像
- 视频 Seedance、第三方 LLM 仍可能要额外 Key
