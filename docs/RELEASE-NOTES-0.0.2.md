# Game AI Foundry v0.0.2（开发中）

相对 v0.0.1 的主要变更。完整进度见 [`ROADMAP.md`](../ROADMAP.md)。

## 新功能

### GUI

- **Provider 设置重构**：生文 / 生图 / 生视频分块；`provider_accounts` 多账号库
- 预设 **DeepSeek、Kimi、GLM**；切换 Provider 不互相清空 Key
- **环境 → 执行器向导**：Hermes / Codex / Cursor 分步安装
- Hermes **一键同步 OpenRouter** → `~/.hermes/.env`
- Codex **浏览器登录**（后台 `codex login`）
- 环境工具栏：**执行器状态芯片**
- 命令指南：**推荐配置 Agent**；链到 `docs/TOOLS.md`

### 工具链

- **FFmpeg、Godot .NET、.NET SDK** 均为必需项；**启动时自动安装**
- Godot：GitHub API 拉 mono zip；解压后自动 chmod
- FFmpeg：多源 fallback 下载
- **rembg** 从 `setup check` 移除（Release 内嵌 Python 自带）

### CLI

- `setup executor status` / `setup executor step` — 执行器分步配置
- `executor_setup.py` — Hermes API 同步、Codex 登录探测

### 文档

- 新增 [`TOOLS.md`](TOOLS.md) — 工具配置、纠错、外部 Agent 操作手册
- 更新 `GUI-CONFIG`、`README`、`ROADMAP`、`RELEASE`、`AI-HANDOFF`

## 用户升级注意

1. 仅需 API Key 仍可 `/brief` + `/run`（与 v0.0.1 相同最低门槛）
2. 推荐在 **环境 → 执行器** 配置 Hermes，便于排错与带队
3. 不再需在环境列表手动安装 rembg
4. Godot / .NET 首次启动会自动下载（需网络，体积较大）

## 已知限制

- GUI 主聊天**尚未**路由到设置的 host executor（Brief 仍直连 LLM API）
- 无首次启动串联引导条
- Windows 纯净机全链 E2E 待验证

## 构建

与 v0.0.1 相同：`scripts/build-release.sh` / `.bat`（含 `--with-rembg`）
