# Game AI Foundry v0.1.6

**主更新：制作审查缺口卡落盘 + 多场景北极星 + IT 可换执行器 + 工程串扰/权限硬化**

相对 [`v0.1.5`](RELEASE-NOTES-0.1.5.md)。策划侧制作审查改为对话流内 Critic 缺口卡点选写入草稿（不经主 LLM 猜意图）；北极星支持按场景绑定；IT 可离开内嵌 Pi 选用 Codex 等；并修复视觉定稿跨工程误匹配与若干权限/路径门闩。

## 下载

| 平台 | 文件 | 说明 |
|------|------|------|
| **Windows x64（推荐）** | `Game-AI-Foundry-0.1.6-setup.exe` | NSIS：可选安装目录、干净卸载、**应用内自动更新** |
| **Windows x64** | `Game-AI-Foundry-0.1.6-win-x64.zip` | 解压即用；无自动更新 |
| **Windows x64** | `Game-AI-Foundry-0.1.6-portable.exe` | 便携版；无自动更新 |
| **macOS arm64** | `Game-AI-Foundry-0.1.6-mac-arm64.*`（若本页已附带） | 手动解压；暂无应用内自动更新 |

> Windows 未签名：可能 SmartScreen 提示。

## 新功能 / 修复

- **制作审查 · Critic 缺口卡**：审查结果以对话流卡片呈现；点选/手写后经 `brief chat makeability-answer` 专用 closer 写入 `brief_patches`；输入框下小钮「审/补/议/UI/修/存」与主对话选项拆开。
- **草稿优先**：绑定/同步优先 `brief.draft.json`，避免旧导出 `brief.json` 盖回已拍板决定；过期审查不再把旧 `intent_gaps` 塞回主 LLM。
- **多场景北极星**：`project.scenes[].visual_reference`；生图按资产 `scene_ids` 选型；CLI `--scene` / assign / status。
- **视觉定稿 status 防串工程**：匹配范围收紧到本工程树，避免 basename `brief.json` 误绑。
- **IT 可换执行器**：雇佣/配置栏可离开内嵌 Pi，选用 Codex 等；相关提示与解析修复。
- **完成优先的工具权限**：桥不可用时回退 `--i-confirm`；路径逃逸与缺省 `asset_type` 硬化；外置工程 media 路径统一。
- **只说不写拦截**：策划口头声称已写入但无 `brief_patches` 时宿主警告并下一轮催落盘。
- **审查账本**：[`solutions/reviews/2026-08-04-whole-project-review-ledger.md`](solutions/reviews/2026-08-04-whole-project-review-ledger.md) 记录 Fixed / Accepted / Deferred，避免重复报 Accepted 项。
- 继承 v0.1.5：scenes/systems/ui_panels、文档栏工程恢复、Pi 优先系统 Node。

## 纯净机使用（Windows 推荐）

1. 安装 **`Game-AI-Foundry-0.1.6-setup.exe`**（覆盖 0.1.5；安装版会走自动更新）
2. **设置** → Provider 填 Key；等待顶部芯片变绿
3. 策划：聊草稿 → 点「审」→ Critic 卡片关意图缺口 → 再审 →「存」→ 北极星 → 交给项目经理

说明 → 本文件 · GUI → [`GUI-CONFIG.md`](GUI-CONFIG.md) · Brief → [`AI-HANDOFF.md`](AI-HANDOFF.md) · 打包 → [`RELEASE.md`](RELEASE.md)

## 已知限制

- 未代码签名 / macOS 未公证；Mac / zip / portable **不做**应用内自动更新
- Critic 缺口写入仍依赖 Host LLM API；关闭后需再跑一次「审」才能导出
- 视频 Seedance、程序员 Codex 仍可能要额外 Key / 本机工具
