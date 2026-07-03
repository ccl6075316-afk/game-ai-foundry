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

### GUI

`start-gui.bat` → 设置 API key → `/brief` → export → `/plan` → `/run --run-prompts`

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

Python 3.11+ · OpenRouter + Volcengine ARK keys

**本机工具**（GUI 启动时会检测；FFmpeg 可一键自动安装）：

- **FFmpeg** — 视频拆帧；`python gamefactory.py setup install ffmpeg` 或 GUI 弹窗确认
- **Godot 4 .NET** — [下载便携 zip](https://godotengine.org/download)（无需安装），在 `~/.gamefactory/config.json` 设置 `godot.engine_path`
- **.NET SDK** — C# 玩法开发；[官方下载](https://dotnet.microsoft.com/download)

## License

MIT
