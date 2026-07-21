# GUI 配置说明 — Provider、Agent 与实例

| | |
|--|--|
| **读者** | Release / GUI 用户 |
| **侧重** | Provider 账号 → Agent 工具预设 → 雇人/对话实例配置 |
| **外部 Agent** | 代操 Foundry → [`TOOLS.md`](TOOLS.md) |

---

## 设置三栏

```text
Provider（API 账号）  →  各厂商 Key、生图、生视频
Agent（工具预设）     →  Pi / Hermes / Codex / Cursor 默认连法
本机                  →  Godot 路径等本地项
```

环境面板（非设置 Tab）负责 **安装/登录** 执行器 CLI，不配业务 Provider 字段。

---

## 最低开工 vs 推荐配置

| 级别 | 需要什么 | 能做什么 |
|------|----------|----------|
| **最低** | OpenRouter（或 LLM Provider）Key | `/brief`、 `/plan`、 `/run` 批量出资产 |
| **推荐** | 上项 + **Hermes 或 Cursor** | 环境排错、改 config、orchestrator 带队 |
| **写玩法** | 上项 + **Codex 或 Cursor**（程序员实例） | Pass 4 Godot C# 开发 |

仅配 API 时，GUI 聊天 **不能** 根据自然语言自由跑终端、改配置；需点环境面板按钮或斜杠命令。完整 Agent 能力见 [`TOOLS.md`](TOOLS.md) §5。

---

## Provider 页（设置 → Provider）

| Provider | 用途 | 必填 |
|----------|------|------|
| **LLM Provider**（如 OpenRouter） | `/brief` 策划对话、文案 LLM | ✅ |
| **生图** | 可勾选「沿用 LLM Provider」 | ✅ |
| **视频 Provider**（Seedance） | 图生视频 | 做动画时需要 |

**API Key 只在此页填写**；雇人弹窗与对话配置仅选择账号库 id，不重复填 Key。

GUI 主对话（① 策划薄 Chat）走 LLM Provider，与下方 Agent 执行器选择无关。

---

## Agent 页（设置 → Agent）

按 **执行器工具** 配置全局预设，写入 `agents.executors`：

| 工具 | 预设字段 |
|------|----------|
| **Pi** | 默认 Provider、模型 |
| **Hermes** | 默认 Provider（保存后可提示去环境同步 OpenRouter） |
| **Codex** | 用第三方开关；开启时选 Provider + 模型；关闭时走订阅登录 |
| **Cursor** | 只读说明：本机 IDE 登录/订阅 |

雇人弹窗打开时会 **预填** 对应工具的 Agent 预设；用户可改后再写入实例。

---

## 雇人与对话配置（`agents.instances`）

| 入口 | 说明 |
|------|------|
| **雇人弹窗** | 创建同事前配置执行器、Provider、模型、Codex 第三方等；确认后写入 `agents.instances.<id>` |
| **对话内配置** | 各同事可打开配置（策划/IT 含 Provider + 模型；项目经理/程序员含执行器等）；变更立即持久化到该实例 |

- **对话内修改只更新该实例**，**不回写** Agent 页全局预设。
- 删除同事时清理对应 `agents.instances.<id>`。

---

## Hermes / Codex / Cursor

| 工具 | 安装（GUI） | API Key |
|------|-------------|---------|
| **Hermes** | 环境 → 执行器：CLI → Skills → **同步 OpenRouter** | 一键写入 `~/.hermes/.env` |
| **Codex CLI** | 环境 → 执行器：安装 → **浏览器登录** | 订阅 OAuth；或 Agent/实例开「用第三方」后 sync |
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
4. **设置 → Agent** → 配各工具默认 Provider（可选；雇人时会预填）  
5. `/brief` → `/plan` → `/run`  
6. 要写 C# 玩法 → 雇程序员实例时在弹窗选 Codex 执行器（或对话内改配置）  

外部 AI（Claude、自建 bot 等）代操：把 [`TOOLS.md`](TOOLS.md) 交给 Agent 阅读。
