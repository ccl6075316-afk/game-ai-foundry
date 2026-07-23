# Game AI Foundry — GUI

**Chat-first** 桌面壳 — 主界面是对话；**看板** / **资产** 为可选侧栏。

底层调用内嵌或本机 `gamefactory` CLI。Hermes/Codex/Cursor **不内嵌**，通过环境面板向导安装。

## Release（最终用户）

下载 **Game AI Foundry.exe**（或 macOS `.dmg`）→ 双击运行。

1. **设置** → 从示例创建 → **OpenRouter Key**；需要时填 Provider 页 **网络** 代理
2. 等 **FFmpeg / Godot / .NET** 自动装好
3. **（推荐）环境 → 执行器**
4. `/brief` → `/plan` → `/run` → 侧栏 **资产** 审图（或 `/assets`）

外部 AI 代操：[`docs/TOOLS.md`](../docs/TOOLS.md) · 配置说明：[`docs/GUI-CONFIG.md`](../docs/GUI-CONFIG.md)

打包：[`docs/RELEASE.md`](../docs/RELEASE.md) · 变更：[`docs/RELEASE-NOTES-UNRELEASED.md`](../docs/RELEASE-NOTES-UNRELEASED.md)

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
| `/board` | 看板（任务进度） |
| `/assets` | 资产审查表（缩略图 + 采纳/重生成/本地替换） |
| `/godot` | 打开 Godot 工程 |

自然语言输入（无 `/`）→ 等同开始 Brief。

### 设置

| 页签 | 内容 |
|------|------|
| **Provider** | **网络**（顶层 `proxy`）；生文 / 生图（主图 + 批量可分 Provider）/ 生视频；多账号库 |
| **Agent** | Pi / Hermes / Codex / Cursor 工具预设与安全旋钮 |
| **本机** | Godot 路径（自动安装后通常已填） |

### 侧栏

| 面板 | 内容 |
|------|------|
| **看板** | pipeline 任务状态、失败、续跑 |
| **资产** | `assets-manifest` 缩略图与 usage 映射；行内审图与替换 |

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
  ├─ IPC: doctor, toolchain-install, executor-step, pipeline-*, assets-review-*, config …
  └─ spawn python cli/gamefactory.py
Renderer (React)
  └─ window.gameFactory.* (preload)
```

## 相关文档

- [`docs/GUI-CONFIG.md`](../docs/GUI-CONFIG.md) — Provider / 代理 / 生图双档
- [`docs/AI-HANDOFF.md`](../docs/AI-HANDOFF.md) §1.2 — 资产审查表契约
- [`docs/README.md`](../docs/README.md) — 文档索引
