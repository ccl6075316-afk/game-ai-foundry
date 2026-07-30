# Game AI Foundry v0.1.0

**主更新：家庭运维 IT、外置工程、设置全页与 Brief 加厚** — IT 默认可跑流水线；工程可挂独立 Godot 仓；Provider 可自建兼容账号。

相对 [`v0.0.8`](RELEASE-NOTES-0.0.8.md)。

## 下载

| 平台 | 文件 | 说明 |
|------|------|------|
| **Windows x64** | `Game-AI-Foundry-0.1.0-win-x64.zip` | 解压后运行 `Game AI Foundry.exe` |
| **Windows x64** | `Game-AI-Foundry-0.1.0-portable.exe` | 便携版 |
| **Windows x64** | `Game-AI-Foundry-0.1.0-setup.exe` | NSIS 安装包 |

> 未签名：Windows 可能 SmartScreen 提示。macOS 包需在 Apple Silicon 上另打。

## 新功能

- **IT 家庭运维**：加宽 Pi 白名单（草稿 bind / zh-doc / autofix / enrich、看板 plan·run、资产 review 等）；IT 默认「信任本会话」（配置条可关）；信任下可 `pipeline run`；策划 profile 仍不可跑流水线
- **外置工程根**：新建仍默认 `projects/<slug>/`；GUI「打开外置工程…」或 CLI `project external add` 登记独立 Godot 仓；虚拟键 `external:<id>/brief.json`；pipeline / brief 产物写在外置根
- **Brief 补全 + 议题头脑风暴**：策划侧「补全细节」「议题头脑风暴」；CLI `brief chat enrich` / `topic-brainstorm` / `brainstorm-apply`
- **开放 Provider 账号 + 模型目录**：可添加多个 OpenAI 兼容自建账号；`setup provider list|remove|models`；GUI 文/图模型可刷新 `/models`
- **设置全页（ChatWise 式）**：顶栏「设置」（Provider | Agent | 本机 | 环境 | 指南）；右侧栏仅文档 / 看板 / 资产
- **草稿同步与中文说明**：会话草稿落盘 `brief.draft.json`；导出前可生成 `brief.zh.md`

## 纯净机使用

1. 解压并打开 **Game AI Foundry**
2. **设置** → Provider 填 LLM API Key（可自建兼容端）；等待顶部芯片变绿
3. 与**策划**落实 brief → 项目经理 `/plan` `/run`；环境/看板/流水线问题可找 **IT**
4. 外置 Godot 仓用「打开外置工程…」登记，不必塞进 Foundry 仓库

说明 → 本文件 · 打包 → [`RELEASE.md`](RELEASE.md)

## 已知限制

- 同 v0.0.8：layout 启发式、一整局真人验收未作门禁、GUI 不可编辑 content_class、未代码签名
- IT 不改 Foundry 源码 / 大段玩法 C#（仍回 Cursor / 程序员）
