# Game AI Foundry v0.1.3

**主更新：修复 Windows 安装包因 `electron-updater` ESM 导入起不来**

相对 [`v0.1.2`](RELEASE-NOTES-0.1.2.md)。v0.1.2 在打包后主进程以 ESM 加载时，对 CommonJS 的 `electron-updater` 使用命名导入会直接崩溃；本版改为默认导入，GUI 可正常启动，自动更新入口可用。

## 下载

| 平台 | 文件 | 说明 |
|------|------|------|
| **Windows x64（推荐）** | `Game-AI-Foundry-0.1.3-setup.exe` | NSIS：可选安装目录、干净卸载、**应用内自动更新** |
| **Windows x64** | `Game-AI-Foundry-0.1.3-win-x64.zip` | 解压即用；无自动更新 |
| **Windows x64** | `Game-AI-Foundry-0.1.3-portable.exe` | 便携版；无自动更新 |
| **macOS arm64** | 见 [v0.1.1](https://github.com/ccl6075316-afk/game-ai-foundry/releases/tag/v0.1.1) 或本页若已附带 | 手动解压；暂无应用内自动更新 |

> Windows 未签名：可能 SmartScreen 提示。

## 新功能 / 修复

- **启动崩溃修复**：`autoUpdate.mjs` 对 `electron-updater` 改为 default import（CJS ↔ ESM 兼容）
- **应用更新入口不变**：设置 → 本机「检查更新」；顶栏横幅「重启安装」（仅 `*-setup.exe`）
- 继承 v0.1.2：Windows `latest.yml` 自动更新元数据、Brief 定点补丁、上下文预算加大

## 纯净机使用（Windows 推荐）

1. 安装 **`Game-AI-Foundry-0.1.3-setup.exe`**（若已装 0.1.2 但起不来，请直接装本版覆盖）
2. **设置** → Provider 填 LLM API Key；等待顶部芯片变绿
3. 与策划落实 brief → 项目经理 `/plan` `/run`；环境问题找 IT
4. **设置 → 本机** 可手动检查更新；有新版本时顶栏会出现「重启安装」

说明 → 本文件 · 打包策略 → [`RELEASE.md`](RELEASE.md)

## 已知限制

- 同 v0.1.2：未代码签名 / macOS 未公证；Mac / zip / portable **不做**应用内自动更新
- IT 不改 Foundry 源码 / 大段玩法 C#（仍回 Cursor / 程序员）
