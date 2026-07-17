# Game AI Foundry

**AI-driven game factory** — describe a game → freeze **brief JSON** → generate assets → Godot project → iterate with AI colleagues.

**Latest:** [**v0.0.5**](https://github.com/ccl6075316-afk/game-ai-foundry/releases/tag/v0.0.5) — 协作稳定性修复（同事隔离 / Hermes Provider / Windows Agent 编码）

**GUI**（`start-gui.bat` / `start-gui.sh`）或 **CLI**（`cd cli && python gamefactory.py`）。七角色 skills + Hermes / Codex / Cursor 执行器。

文档索引 → [`docs/README.md`](docs/README.md)
    10|
## How it works

```
用户（决策人）
  ├─ 策划同事     → brief chat → brief.json（落实才写盘）
  ├─ 项目经理同事 → 分诊 → handoffs / progress / 定点 pipeline
  └─ 程序员同事   → 接 handoff → 改 Godot C# → validate
         │
brief.json → production.json → scaffold
    20|         → pipeline run → assemble → games/
         → validate / test unit / play / regression
```

产品心智 → [`docs/HOST-CHAT-PRODUCT.md`](docs/HOST-CHAT-PRODUCT.md)  
改需求 / Delta → [`docs/ITERATIVE-PRODUCTION.md`](docs/ITERATIVE-PRODUCTION.md)

## Features (v0.0.5)

### GUI — AI 公司前台

| 能力 | 说明 |
|------|------|
| **同事列表** | 策划 / 项目经理 / 程序员；可多实例、改名、解雇、侧栏收起 |
| **策划** | `brief chat`：商量设计，明确「落实」才导出 brief |
| **项目经理** | `agent turn` → 执行器 CLI；分诊写 `plans/handoffs/` + progress |
| **程序员** | 按实例接 handoff；关单写回 progress |
| **一键建议命令** | 白名单执行 `pipeline reset/run`、`godot validate` 等；流式日志 |
| **`/delta`** | Production Delta → 合并蓝图并同步 progress |
| **斜杠命令** | `/plan` `/run` `/board` `/doctor` `/guide` … |
| **Provider / 环境** | 多账号；FFmpeg / Godot / .NET 自动装；执行器向导 |
| **Release** | 内嵌 Python（含 **rembg**），无需用户装 Python/Node |

### CLI / 施工底座

| 能力 | 说明 |
|------|------|
| `brief chat` / `validate` | 策划会话与契约门禁（`brainstorm` 仍兼容） |
| `production derive` / `delta` / `apply-delta` | 工程蓝图与改需求切片 |
| `project progress` / `handoff` | 续作账本与派工文件总线 |
| `pipeline plan` / `run` / `reset` / `suggest-retry` | 资产 DAG 与定点重跑 |
| `godot scaffold` / `assemble` / `validate` | 壳、组装、校验 |
| `test unit` / `play` / `regression` | 验收金字塔 |
| `doctor` / `setup` | API、工具链、执行器 |

### 最低开工 vs 推荐

| 级别 | 配置 | 能做什么 |
|------|------|----------|
| **最低** | LLM Provider Key | 与策划出 brief + `/plan` `/run` 出资产 |
| **推荐** | + Hermes / Codex / Cursor Agent | 项目经理分诊、程序员施工 |
| **写玩法** | + Codex 或 Cursor（程序员岗） | Godot C# Pass 4 |

详见 [`docs/GUI-CONFIG.md`](docs/GUI-CONFIG.md) · 外部 Agent → [`docs/TOOLS.md`](docs/TOOLS.md)

## Quick start

### Release（最终用户）

1. 下载 [**v0.0.5 Release**](https://github.com/ccl6075316-afk/game-ai-foundry/releases/tag/v0.0.5)
2. 解压 / 打开 **Game AI Foundry**
3. **设置** → 填 LLM API Key；等待顶部芯片变绿（FFmpeg / Godot / .NET）
4. **（推荐）环境 → 执行器** → Hermes / Codex / Cursor Agent（Hermes 在角色页可选 Provider 后同步）
5. 与**策划**落实 brief → `/plan` → `/run --run-prompts`
6. 试玩问题找**项目经理**；改需求用 `/delta 00x-name | 描述`

说明 → [`docs/RELEASE-NOTES-0.0.5.md`](docs/RELEASE-NOTES-0.0.5.md) · 打包 → [`docs/RELEASE.md`](docs/RELEASE.md)

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
| **LLM Provider**（如 OpenRouter） | ✅ | Brief、生图（GUI 设置） |
| **Seedance / ARK** | 做视频时 | 生视频 |
| **FFmpeg / Godot / .NET** | ✅ | GUI **启动自动安装** |
| **rembg** | — | **打包版内嵌** |
| **Hermes / Codex / Cursor Agent** | 推荐 | 项目经理 / 程序员；环境面板配置 |

### 开发者

Python 3.11+ · Node 20+ · API keys · 可选 `npm run prepare:python`（含 rembg）

## License

MIT
