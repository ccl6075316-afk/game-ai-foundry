# GUI 配置说明 — Provider 与执行器

| | |
|--|--|
| **读者** | Release / GUI 用户 |
| **侧重** | 先配 Provider，再配角色；GUI 对话 vs 外部执行器 |
| **外部 Agent** | 代操 Foundry → [`TOOLS.md`](TOOLS.md) |

---

## 三层配置

```text
Provider（API 账号）  →  GUI /brief、生图、生视频
本机工具链            →  FFmpeg、Godot .NET、.NET SDK（启动可自动安装）
执行器（Executor）    →  排错、委派、写代码：Hermes / Codex / Cursor
```

---

## 最低开工 vs 推荐配置

| 级别 | 需要什么 | 能做什么 |
|------|----------|----------|
| **最低** | OpenRouter（或 LLM Provider）Key | `/brief`、 `/plan`、 `/run` 批量出资产 |
| **推荐** | 上项 + **Hermes 或 Cursor** | 环境排错、改 config、orchestrator 带队 |
| **写玩法** | 上项 + **Codex 或 Cursor**（程序员角色） | Pass 4 Godot C# 开发 |

仅配 API 时，GUI 聊天 **不能** 根据自然语言自由跑终端、改配置；需点环境面板按钮或斜杠命令。完整 Agent 能力见 [`TOOLS.md`](TOOLS.md) §5。

---

## Provider 页（设置 → Provider）

| Provider | 用途 | 必填 |
|----------|------|------|
| **LLM Provider**（如 OpenRouter） | `/brief` 策划对话、文案 LLM | ✅ |
| **生图** | 可勾选「沿用 LLM Provider」 | ✅ |
| **视频 Provider**（Seedance） | 图生视频 | 做动画时需要 |

**GUI 主对话永远走 LLM Provider**，与下方执行器选择无关。

---

## 角色页（设置 → 角色）

| 角色 | 配置什么 | 不配置什么 |
|------|----------|------------|
| 项目经理 | 外部执行器（Cursor/Hermes/Codex） | GUI 聊天不经过 Hermes |
| 文案 | 是否沿用 Provider + 模型名 | 不再重复填 Key |
| 原画 | 只显示 Provider 引用 | Key 在 Provider 页 |
| 程序员 | Codex/Cursor 执行器 | Codex/Cursor **登录式**，不用 OpenRouter Key |

---

## Hermes / Codex / Cursor

| 工具 | 安装（GUI） | API Key |
|------|-------------|---------|
| **Hermes** | 环境 → 执行器：CLI → Skills → **同步 OpenRouter** | 一键写入 `~/.hermes/.env` |
| **Codex CLI** | 环境 → 执行器：安装 → **浏览器登录** | OpenAI OAuth |
| **Cursor** | 下载 IDE → 检测 CLI | Cursor 订阅 |

CLI 等价：`setup executor step <id> <step>` — 见 [`TOOLS.md`](TOOLS.md)。

---

## 本机工具

| 工具 | 方式 |
|------|------|
| **FFmpeg** | 必需；启动缺失时自动安装 |
| **Godot .NET** | 必需；自动下载到 toolchain，写入 `godot.engine_path` |
| **.NET SDK** | 必需；自动安装到 toolchain |
| **rembg** | **打包版内嵌 Python 自带**；不出现在环境安装列表 |

---

## 推荐 Release 用户路径

1. **设置** → 从示例创建 → 填 OpenRouter（+ 可选 Seedance）  
2. 等待启动自动装好 FFmpeg / Godot / .NET（看顶部芯片）  
3. **（推荐）环境 → 执行器** → 配 Hermes（同步 API）或 Cursor  
4. `/brief` → `/plan` → `/run`  
5. 要写 C# 玩法 → 配 Codex，角色页选程序员执行器  

外部 AI（Claude、自建 bot 等）代操：把 [`TOOLS.md`](TOOLS.md) 交给 Agent 阅读。
