# Game AI Foundry v0.1.8

**主更新：Codex/Cursor 对话内批准卡可靠 + Windows 执行器 spawn / IT 误诊修复**

相对 [`v0.1.7`](RELEASE-NOTES-0.1.7.md)。解决 Foundry 内 Codex「只有计时、看不见批准卡」、Windows `spawn … ENOENT`，以及 IT 把缺 PATH `python` 误判成须重装安装包等问题。

## 下载

| 平台 | 文件 | 说明 |
|------|------|------|
| **Windows x64（推荐）** | `Game-AI-Foundry-0.1.8-setup.exe` | NSIS：可选安装目录、干净卸载、**应用内自动更新** |
| **Windows x64** | `Game-AI-Foundry-0.1.8-win-x64.zip` | 解压即用；无自动更新 |
| **Windows x64** | `Game-AI-Foundry-0.1.8-portable.exe` | 便携版；无自动更新 |
| **macOS arm64** | `Game-AI-Foundry-0.1.8-mac-arm64.*`（若本页已附带） | 手动解压；暂无应用内自动更新 |

> Windows 未签名：可能 SmartScreen 提示。

## 新功能 / 修复

- **对话内批准卡**：Codex / Cursor / Hermes 工具批准只出现在聊天流（允许一次 / 本回合 / 本会话 / 拒绝）；修复 HMR/依赖变更后 IPC 监听丢失导致「永远看不见卡、300s 超时」。
- **执行器子进程环境**：Codex/Cursor/Hermes spawn 注入 `GAMEFACTORY_PYTHON`，与 FOUNDRY_TOOL / shell 一致。
- **Windows spawn**：Codex / Cursor / Hermes 优先 toolchain `.exe`；`.cmd` 开 shell，避免 `ENOENT`。
- **Codex 安装**：下载全失败时回退 PATH/npm 已有二进制（带 warning）；单测隔离 BIN_DIR。
- **IT / Python 误诊**：FOUNDRY_TOOL 已通即证明内嵌 Python 可用；skill 与提示词不再因 9009/`where python` 教用户重装；补 `instances list` / `executors show`、`--executor` 参数纠错。
- 批准超时（含 Pi bridge）会回写 UI，避免假挂起。

## 纯净机使用（Windows 推荐）

1. 安装 **`Game-AI-Foundry-0.1.8-setup.exe`**（覆盖 0.1.7；安装版会走自动更新）
2. **设置** → Provider 填 Key；等待顶部芯片变绿
3. IT / Codex：**环境 → 执行器 → 安装 Codex CLI**（无需本机 npm）→ 第三方 Key 时 upsert → `sync_api`
4. Codex 要跑命令时：在**对话里的批准卡**点允许（不是系统弹窗）

说明 → 本文件 · 工具 → [`TOOLS.md`](TOOLS.md) · 打包 → [`RELEASE.md`](RELEASE.md)

## 已知限制

- 未代码签名 / macOS 未公证；Mac / zip / portable **不做**应用内自动更新
- Codex 安装需能访问 GitHub Releases（或手动把二进制放到 toolchain/bin）
- 视频 Seedance、第三方 LLM 仍可能要额外 Key
