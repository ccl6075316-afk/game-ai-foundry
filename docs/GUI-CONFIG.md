# GUI 配置说明 — Provider 与执行器

| | |
|--|--|
| **读者** | Release / GUI 用户 |
| **侧重** | 先配 Provider，再配角色；GUI 对话 vs 外部执行器 |

---

## 三层配置

```text
Provider（API 账号）  →  GUI /brief、生图、生视频
执行器（Executor）     →  外部派活：Hermes / Codex / Cursor
本机工具              →  FFmpeg、Godot
```

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

| 工具 | 安装 | API Key |
|------|------|---------|
| **Hermes** | 用户安装 + `gamefactory hermes install`（GUI 可装 skills） | Hermes **自有**配置，**不会**自动读 `~/.gamefactory/config.json` |
| **Codex CLI** | `npm i -g @openai/codex` + `codex login` | OpenAI 登录 |
| **Cursor** | 安装 Cursor IDE | Cursor 订阅 |

环境工具栏可检测并给出安装命令；**不能**在 GUI 内统一切换 Codex/Cursor 模型（非同一 Chat 引擎）。

---

## 本机工具

- **FFmpeg**：环境栏一键安装（多源 fallback；失败见手动指引）
- **Godot**：官方 zip 下载 + 设置路径

---

## 推荐 Release 用户路径

1. Provider 页填 OpenRouter + Seedance  
2. 环境栏装 FFmpeg、配 Godot  
3. `/brief` → `/plan` → `/run`  
4. 要写 C# 玩法时再装 Codex/Cursor，在角色页选执行器
