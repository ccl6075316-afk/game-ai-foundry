# Game AI Foundry v0.1.2

**主更新：Windows 自动更新安装包补齐 + Brief 定点补丁（审查回填不瘦身）**

相对 [`v0.1.1`](RELEASE-NOTES-0.1.1.md)。v0.1.1 已发 Mac zip；本版在 Windows 上正式打出带 `latest.yml` 的 NSIS 安装包，并修复策划草稿「改两点却整份变瘦」的更新方式。

## 下载

| 平台 | 文件 | 说明 |
|------|------|------|
| **Windows x64（推荐）** | `Game-AI-Foundry-0.1.2-setup.exe` | NSIS：可选安装目录、干净卸载、**应用内自动更新** |
| **Windows x64** | `Game-AI-Foundry-0.1.2-win-x64.zip` | 解压即用；无自动更新 |
| **Windows x64** | `Game-AI-Foundry-0.1.2-portable.exe` | 便携版；无自动更新 |
| **macOS arm64** | 见 [v0.1.1](https://github.com/ccl6075316-afk/game-ai-foundry/releases/tag/v0.1.1) 或本页若已附带 | 手动解压；暂无应用内自动更新 |

> Windows 未签名：可能 SmartScreen 提示。

## 新功能 / 修复

- **Windows 0.1.2 安装包**：`*-setup.exe` + `latest.yml`（electron-updater）；已装 0.1.1 setup 的用户可走应用内更新到本版
- **Brief 定点补丁**：审查回填 / 小澄清用 `artifact.brief_patches`（`set` / `upsert_asset` / `add_asset`），不再用瘦身整稿覆盖；资产按 id 合并不丢行；长叙事防缩水
- **上下文预算**：策划会话字符预算加大，减少聊一天后细节被摘要冲掉
- 继承 v0.1.1：对话停止、侧栏拖宽、文档面板文案与 focus 修复、NSIS 可选目录与干净卸载

## 纯净机使用（Windows 推荐）

1. 安装 **`Game-AI-Foundry-0.1.2-setup.exe`**（或从已装 0.1.1 点「重启安装」升级）
2. **设置** → Provider 填 LLM API Key；等待顶部芯片变绿
3. 与策划落实 brief → 项目经理 `/plan` `/run`；环境问题找 IT
4. 审查缺口答完后，草稿应定点更新，不应整份变短

说明 → 本文件 · 打包策略 → [`RELEASE.md`](RELEASE.md)

## 已知限制

- 同 v0.1.1：未代码签名 / macOS 未公证；Mac / zip / portable **不做**应用内自动更新
- IT 不改 Foundry 源码 / 大段玩法 C#（仍回 Cursor / 程序员）
