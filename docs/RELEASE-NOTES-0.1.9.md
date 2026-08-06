# Game AI Foundry v0.1.9

**主更新：制作审查去重 + 顾问同事 + 聊天回写钉会话**

相对 [`v0.1.8`](RELEASE-NOTES-0.1.8.md)。策划侧避免制作审查反复追问同一缺口；新增只提问的顾问同事；对话回写钉到当前忙碌同事会话，避免串聊。

## 下载

| 平台 | 文件 | 说明 |
|------|------|------|
| **Windows x64（推荐）** | `Game-AI-Foundry-0.1.9-setup.exe` | NSIS：可选安装目录、干净卸载、**应用内自动更新** |
| **Windows x64** | `Game-AI-Foundry-0.1.9-win-x64.zip` | 解压即用；无自动更新 |
| **Windows x64** | `Game-AI-Foundry-0.1.9-portable.exe` | 便携版；无自动更新 |
| **macOS arm64** | `Game-AI-Foundry-0.1.9-mac-arm64.*`（若本页已附带） | 手动解压；暂无应用内自动更新 |

> Windows 未签名：可能 SmartScreen 提示。

## 新功能 / 修复

- **制作审查去重**：已答复 / 已落盘的缺口不再反复追问；导出与 ledger / draft CAS 门闩加硬，冲突时不误报成功。
- **顾问同事**：新增 ask-only **顾问**角色；消息走 `agent turn`（非 brief chat）；角色门闩与软导出文档加固。
- **聊天回写钉会话**：`append` 钉到忙碌中的同事会话，避免并行时消息落到错误对话。
- **Brief 导出**：Pi brief 导出受结构就绪门闩约束；制作审查结论在导出路径保持 advisory。
- 继承 v0.1.8：对话内 Codex/Cursor 批准卡、Windows spawn / `GAMEFACTORY_PYTHON`、IT Python 误诊修复。

## 纯净机使用（Windows 推荐）

1. 安装 **`Game-AI-Foundry-0.1.9-setup.exe`**（覆盖 0.1.8；安装版会走自动更新）
2. **设置** → Provider 填 Key；等待顶部芯片变绿
3. 策划导出 Brief 前按制作审查补齐缺口；需要旁路问询可雇 **顾问**

说明 → 本文件 · 工具 → [`TOOLS.md`](TOOLS.md) · 打包 → [`RELEASE.md`](RELEASE.md)

## 已知限制

- 未代码签名 / macOS 未公证；Mac / zip / portable **不做**应用内自动更新
- Codex 安装需能访问 GitHub Releases（或手动把二进制放到 toolchain/bin）
- 视频 Seedance、第三方 LLM 仍可能要额外 Key
