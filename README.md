# Game AI Foundry

**AI-driven game factory** — describe a game → freeze **brief JSON** → generate assets → Godot project → gameplay C# via agent.

**Electron GUI** (`start-gui.bat` / `start-gui.sh`) or **CLI** (`cd cli && python gamefactory.py`). Orchestration: Cursor / Hermes / Codex + seven role skills.

**Documentation map** → [`docs/README.md`](docs/README.md)

## How it works

```
Brainstorm → brief.json (frozen)
       → pipeline run → output/{slug}/
       → godot assemble → games/{slug}/
       → dev-context → godot-developer (C#)
```

Post-demo changes: [`docs/ITERATIVE-PRODUCTION.md`](docs/ITERATIVE-PRODUCTION.md) (design vs production, Change Request).

## Features (v0.2)

### GUI

| 能力 | 说明 |
|------|------|
| **Chat-first** | `/brief` 多轮策划、`/plan` `/run`、看板、设置、环境、指南 |
| **Provider 设置** | 生文 / 生图 / 生视频分块；**多 Provider 账号库**（OpenRouter、DeepSeek、Kimi、GLM、自定义） |
| **工具链自动装** | 启动缺失时自动安装 **FFmpeg、Godot .NET、.NET SDK** |
| **执行器向导** | 环境面板分步安装 **Hermes / Codex / Cursor**；Hermes 一键同步 OpenRouter |
| **环境工具栏** | 本机工具 + 执行器 + API 状态芯片 |
| **命令指南** | 推荐配 Agent；链到 [`docs/TOOLS.md`](docs/TOOLS.md) 供外部 AI 代操 |
| **Release** | 内嵌 Python（含 **rembg**），无需用户装 Python/Node |

### CLI

| 能力 | 说明 |
|------|------|
| `setup check` / `install` | FFmpeg、Godot、.NET 检测与自动安装 |
| `setup executor` | Codex/Hermes/Cursor 分步安装、登录、配 API |
| `doctor --json` | API Key、工具链、执行器、capabilities |
| `pipeline run` | 并行资产生成 DAG |
| `hermes install` | 安装 game-factory skills 到 `~/.hermes/skills` |

### 最低开工 vs 推荐

| 级别 | 配置 | 能做什么 |
|------|------|----------|
| **最低** | OpenRouter（或 LLM Provider）Key | Brief + pipeline 出资产 |
| **推荐** | + Hermes 或 Cursor | 排错、改 config、orchestrator 带队 |
| **写玩法** | + Codex 或 Cursor（程序员角色） | Godot C# Pass 4 |

详见 [`docs/GUI-CONFIG.md`](docs/GUI-CONFIG.md) · 外部 Agent → [`docs/TOOLS.md`](docs/TOOLS.md)

## Quick start

### Release（最终用户）

1. 下载 [Release 产物](docs/RELEASE.md) → 双击 **Game AI Foundry**
2. **设置** → 从示例创建 → 填 **OpenRouter** Key（做视频再填 Seedance）
3. 等待顶部芯片变绿（FFmpeg / Godot / .NET 自动安装）
4. **（推荐）环境 → 执行器** → 配 Hermes 或 Codex/Cursor
5. `/brief` → `/plan` → `/run --run-prompts`

**无需**安装 Python / Node。

### GUI（开发者）

```bash
cd gui && npm install && npm run dev
# 或在仓库根目录：
./start-gui.sh    # macOS/Linux
start-gui.bat     # Windows
```

### CLI

```bash
cd cli && pip install -r requirements.txt
cp ../resources/config.example.json ~/.gamefactory/config.json

python gamefactory.py doctor --json
python gamefactory.py setup check --json
python gamefactory.py brief validate --brief ../resources/asset-brief.example.json
python gamefactory.py pipeline plan --brief ../resources/asset-brief.example.json
python gamefactory.py pipeline run --manifest ../pipeline/asset-brief.example.json --run-prompts --jobs 4
```

Details → [`docs/AI-HANDOFF.md`](docs/AI-HANDOFF.md) · Progress → [`ROADMAP.md`](ROADMAP.md)

## Prerequisites

### Release 用户

| 项 | 必需 | 说明 |
|----|------|------|
| **OpenRouter**（或支持的 LLM Provider） | ✅ | Brief、生图（GUI 设置页） |
| **Seedance / ARK** | 做视频时 | 生视频 Provider |
| **FFmpeg / Godot / .NET** | ✅ | GUI **启动自动安装** |
| **rembg** | — | **打包版内嵌**，无需单独装 |
| **Hermes / Codex / Cursor** | 推荐 | 排错、带队、写 C#；GUI 环境面板分步配置 |

详见 [`docs/RELEASE.md`](docs/RELEASE.md) · [`docs/TOOLS.md`](docs/TOOLS.md)

### 开发者

Python 3.11+ · Node 20+ · API keys · 可选 `npm run prepare:python`（含 rembg）

## License

MIT
