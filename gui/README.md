# Game AI Foundry — GUI

**Chat-first** 桌面壳（类似 Codex）— 主界面是对话；**看板**为可选侧栏，查看 pipeline 任务状态。

底层仍调用 `cli/gamefactory.py`，不内嵌 Hermes/Codex/Cursor。

## 要求

- Node.js 20+
- Python 3.11+ 与 `cli/requirements.txt` 已安装
- 可选：`GAMEFACTORY_ROOT` 指向仓库根目录（默认自动检测 `gui/../`）

## 首次启动 · 本机工具

GUI 启动时会自动运行 `setup check`（类似 VS Code 缺扩展提示）：

| 组件 | 方式 |
|------|------|
| **FFmpeg** | 缺失时弹窗确认 → 自动下载到 `~/.gamefactory/toolchain/bin` |
| **rembg** | 可选；确认后 `pip install rembg[cpu]` |
| **Godot .NET** | [官方下载页](https://godotengine.org/download) 便携 zip，解压后在 **设置 → 本机工具** 指定可执行文件 |
| **.NET SDK** | [dotnet.microsoft.com](https://dotnet.microsoft.com/download)（C# 玩法开发时需要） |

CLI 手动：`python gamefactory.py setup check` · `python gamefactory.py setup install ffmpeg`

## 开发

```bash
cd gui
npm install
npm run dev
```

会启动 Vite (5173) + Electron 窗口。

## 功能（v0.2）

| 区域 | 能力 |
|------|------|
| **对话（主）** | 自然语言 + 快捷指令 `/brief` `/doctor` `/plan` `/run` `/board` `/godot` |
| **看板（可选）** | 右上角「看板」→ pipeline 任务 DAG、状态、日志 |

LLM 编排：`/brief` 走 brief brainstorm → 导出 `resources/{slug}-brief.json` → `/plan` → `/run --run-prompts`。导出后 **brief JSON 为唯一契约**。

## 架构

```
Electron main (electron/main.mjs)
  └─ spawn python cli/gamefactory.py …
Renderer (React)
  └─ preload bridge → window.gameFactory.*
```

未来：内嵌 Python、打包 release、Kanban 视图 — 见 ROADMAP M3。
