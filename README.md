# Game AI Foundry

**AI-driven game factory** — describe a game → freeze **brief JSON** → generate assets → Godot project → gameplay C# via agent.

**Electron GUI** (`start-gui.bat`) or **CLI** (`cd cli && python gamefactory.py`). Orchestration: Cursor / Hermes + six role skills.

**Documentation map** → [`docs/README.md`](docs/README.md)

## How it works

```
Brainstorm → brief.json (frozen)
       → pipeline run → output/{slug}/
       → godot assemble → games/{slug}/
       → dev-context → godot-developer (C#)
```

Post-demo changes: [`docs/ITERATIVE-PRODUCTION.md`](docs/ITERATIVE-PRODUCTION.md) (design vs production, Change Request).

## Quick start

### Release（最终用户）

下载 [Release 产物](docs/RELEASE.md) → 双击 **Game AI Foundry** → 设置 API Key → 环境工具栏确认就绪 → `/brief` → `/plan` → `/run --run-prompts`

**无需**安装 Python / Node。

### GUI（开发者）

`start-gui.bat` 或 `cd gui && npm run dev` → 设置 API key → `/brief` → export → `/plan` → `/run --run-prompts`

### CLI

```bash
cd cli && pip install -r requirements.txt
cp ../resources/config.example.json ~/.gamefactory/config.json

python gamefactory.py brief validate --brief ../resources/asset-brief.example.json
python gamefactory.py pipeline plan --brief ../resources/asset-brief.example.json
python gamefactory.py pipeline run --manifest ../pipeline/asset-brief.example.json --run-prompts --jobs 4
python gamefactory.py doctor --json
python gamefactory.py setup check --json
```

Details → [`docs/AI-HANDOFF.md`](docs/AI-HANDOFF.md) · Progress → [`ROADMAP.md`](ROADMAP.md)

## Prerequisites

### Release 用户

- **OpenRouter** + **Volcengine ARK** API keys（设置里填写）
- **Godot 4 .NET** 便携 zip（[下载](https://godotengine.org/download)）— 组装/打开工程时需要
- FFmpeg / rembg：Release 内已含 Python；FFmpeg 可在 GUI 一键安装

详见 [`docs/RELEASE.md`](docs/RELEASE.md)

### 开发者

Python 3.11+ · Node 20+ · OpenRouter + Volcengine ARK keys

## License

MIT
