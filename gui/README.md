# Game AI Foundry — GUI

**Chat-first** 桌面壳 — 主界面是对话；**看板**为可选侧栏。

底层调用内嵌或本机 `gamefactory` CLI。Hermes/Codex/Cursor **不内嵌**，通过环境面板向导安装。

## Release（最终用户）

下载 **Game AI Foundry.exe**（或 macOS `.dmg`）→ 双击运行。

1. **设置** → 从示例创建 → **OpenRouter Key**
2. 等 **FFmpeg / Godot / .NET** 自动装好
3. **（推荐）环境 → 执行器**
4. `/brief` → `/plan` → `/run`

外部 AI 代操：[`docs/TOOLS.md`](../docs/TOOLS.md) · 配置说明：[`docs/GUI-CONFIG.md`](../docs/GUI-CONFIG.md)

打包：[`docs/RELEASE.md`](../docs/RELEASE.md) · 变更：[`docs/RELEASE-NOTES-0.0.2.md`](../docs/RELEASE-NOTES-0.0.2.md)

## 开发

```bash
cd gui && npm install && npm run dev
```

- Node.js 20+
- Python 3.11+ + `cli/requirements.txt`
- 可选：`npm run prepare:python`（内嵌 venv + rembg，模拟 Release）

## 功能一览

### 对话（主界面）

| 指令 | 作用 |
|------|------|
| `/brief` | 多轮策划 → 导出 brief |
| `/plan` | 生成 pipeline manifest |
| `/run` | 执行管线（可加 `--run-prompts`） |
| `/doctor` | 环境探测 |
| `/env` | 环境侧栏 |
| `/settings` | 设置侧栏 |
| `/guide` | 命令指南（含 Agent 推荐） |
| `/board` | 看板 |
| `/godot` | 打开 Godot 工程 |

自然语言输入（无 `/`）→ 等同开始 Brief。

### 设置

| 页签 | 内容 |
|------|------|
| **Provider** | 生文 / 生图 / 生视频；多账号库；DeepSeek/Kimi/GLM 预设 |
| **角色** | 项目经理 / 程序员执行器；Codex/Cursor 显示登录说明（无 API 项） |
| **本机** | Godot 路径（自动安装后通常已填） |

### 环境

| 区域 | 内容 |
|------|------|
| **本机工具** | FFmpeg、Godot、.NET — 缺失时启动自动装 |
| **执行器** | Hermes / Codex / Cursor 分步按钮 + 日志 |
| **能力探测** | doctor capabilities、配置状态 |

### 工具栏

顶栏下方芯片：FFmpeg · Godot · .NET · Hermes · Codex · Cursor · API · 配置

## 本机工具

| 组件 | Release | 开发 `npm run dev` |
|------|---------|-------------------|
| FFmpeg | 启动自动装 | 同左 |
| Godot .NET | 启动自动装 | 同左 |
| .NET SDK | 启动自动装 | 同左 |
| rembg | 内嵌 Python | `prepare:python` 可选 |

## 架构

```
Electron main (electron/main.mjs)
  ├─ IPC: doctor, toolchain-install, executor-step, pipeline-*, config …
  └─ spawn python cli/gamefactory.py
Renderer (React)
  └─ window.gameFactory.* (preload)
```

## 相关文档

| 文档 | 用途 |
|------|------|
| [`docs/GUI-CONFIG.md`](../docs/GUI-CONFIG.md) | Provider vs 执行器 |
| [`docs/TOOLS.md`](../docs/TOOLS.md) | 工具、纠错、外部 Agent |
| [`ROADMAP.md`](../ROADMAP.md) | 进度与 Backlog |
