# Game AI Foundry v0.1.7

**主更新：纯净机 Codex 无需 npm + Release 内嵌 Pi 依赖修复**

相对 [`v0.1.6`](RELEASE-NOTES-0.1.6.md)。解决友人机 / 安装版上「装 Codex 要自备 npm」与「内置 Pi 报缺依赖」两类开箱问题；最终用户仍不必安装 Node / npm。

## 下载

| 平台 | 文件 | 说明 |
|------|------|------|
| **Windows x64（推荐）** | `Game-AI-Foundry-0.1.7-setup.exe` | NSIS：可选安装目录、干净卸载、**应用内自动更新** |
| **Windows x64** | `Game-AI-Foundry-0.1.7-win-x64.zip` | 解压即用；无自动更新 |
| **Windows x64** | `Game-AI-Foundry-0.1.7-portable.exe` | 便携版；无自动更新 |
| **macOS arm64** | `Game-AI-Foundry-0.1.7-mac-arm64.*`（若本页已附带） | 手动解压；暂无应用内自动更新 |

> Windows 未签名：可能 SmartScreen 提示。

## 新功能 / 修复

- **Codex 安装不依赖 npm**：`setup executor step codex install_cli` / GUI「安装 Codex CLI」从 GitHub Releases 下载官方原生二进制到 `~/.gamefactory/toolchain/bin`；CLI / Electron app-server 会优先解析该路径。
- **Release 内嵌 Pi**：`electron-builder` 会剥掉 `extraResources` 里的 `node_modules`；打包后用 `afterPack` 拷回，避免安装版提示「运行 prepare_embedded_pi」。
- **提示文案**：缺 Codex / 坏掉的 npm 包装时，引导走 Foundry 工具链安装，不再要求用户自装 Node。
- 继承 v0.1.6：Critic 缺口卡、多场景北极星、IT 可换执行器、串工程/权限硬化。

## 纯净机使用（Windows 推荐）

1. 安装 **`Game-AI-Foundry-0.1.7-setup.exe`**（覆盖 0.1.6；安装版会走自动更新）
2. **设置** → Provider 填 Key；等待顶部芯片变绿
3. 需要程序员 / Codex 时：**环境 → 执行器 → 安装 Codex CLI**（无需本机 npm）→ 登录或同步第三方 Key

说明 → 本文件 · 工具 → [`TOOLS.md`](TOOLS.md) · 打包 → [`RELEASE.md`](RELEASE.md)

## 已知限制

- 未代码签名 / macOS 未公证；Mac / zip / portable **不做**应用内自动更新
- Codex 安装需能访问 GitHub Releases（或手动把二进制放到 toolchain/bin）
- 视频 Seedance、第三方 LLM 仍可能要额外 Key
