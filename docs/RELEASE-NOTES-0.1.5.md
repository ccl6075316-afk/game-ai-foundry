# Game AI Foundry v0.1.5

**主更新：Brief 场景/系统/UI 面板契约 + 文档栏工程恢复 + Pi 优先系统 Node（无 Dock 闪）**

相对 [`v0.1.4`](RELEASE-NOTES-0.1.4.md)。策划 brief 可结构化描述场景 / 逻辑系统 / UI 面板；GUI 冷启动可靠恢复工程并显示文档列表；本机有 Node 时 Pi 不再每次拉起 Electron（macOS Dock 不再闪「Electron」图标）。

## 下载

| 平台 | 文件 | 说明 |
|------|------|------|
| **Windows x64（推荐）** | `Game-AI-Foundry-0.1.5-setup.exe` | NSIS：可选安装目录、干净卸载、**应用内自动更新** |
| **Windows x64** | `Game-AI-Foundry-0.1.5-win-x64.zip` | 解压即用；无自动更新 |
| **Windows x64** | `Game-AI-Foundry-0.1.5-portable.exe` | 便携版；无自动更新 |
| **macOS arm64** | `Game-AI-Foundry-0.1.5-mac-arm64.*`（若本页已附带） | 手动解压；暂无应用内自动更新 |

> Windows 未签名：可能 SmartScreen 提示。

## 新功能 / 修复

- **`project.scenes[]` / `project.systems[]`（可选）**：场景 + 跨场景逻辑系统；资产可挂 `scene_ids` / `system_ids`；不挡导出。下游 makeability / enrich / 预览 / Hermes skills 已对齐。
- **`project.ui_panels[]` + `ui-wireframe.md`**：可选 UI 面板清单；按需生成字符线稿（不挡导出）。
- **文档栏工程恢复**：冷启动用 `lastBrief` 软恢复；「新对话」不再误清工程绑定；打开文档时若未绑定会再尝试恢复。
- **文档列表布局**：列表 `flex-shrink: 0`（不再被预览区挤没）；列表约 1.5 card 高可滚，内容预览区为主。
- **Pi Node 候选顺序**：PATH / nvm / brew 优先于 `ELECTRON_RUN_AS_NODE`（有够新系统 Node 时无 macOS Dock 闪图标；Release 无 Node 仍回退 Electron）。
- 继承 v0.1.4：可迁移内嵌 Python、制作审查回填、IT 开箱剧本、Windows `latest.yml` 自动更新。

## 纯净机使用（Windows 推荐）

1. 安装 **`Game-AI-Foundry-0.1.5-setup.exe`**（覆盖 0.1.4）
2. **设置** → Provider 填 Key；等待顶部芯片变绿
3. 顶栏确认工程；右侧 **文档** 应列出本工程文件并可预览

说明 → 本文件 · GUI 工程/文档 → [`GUI-CONFIG.md`](GUI-CONFIG.md) · Brief 字段 → [`AI-HANDOFF.md`](AI-HANDOFF.md) · 打包 → [`RELEASE.md`](RELEASE.md)

## 已知限制

- 未代码签名 / macOS 未公证；Mac / zip / portable **不做**应用内自动更新
- 无系统 Node 的 macOS 正式包仍可能偶发 Dock 闪一下（Electron-as-Node 兜底）
- 视频 Seedance、程序员 Codex 仍可能要额外 Key / 本机工具
