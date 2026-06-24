# Game AI Foundry

AI-powered game asset pipeline — generate images, videos, and Godot projects from the command line.

## Architecture

```
game-ai-foundry/
├── cli/                    # Python CLI tools (zero LLM dependency)
│   ├── gamefactory.py      # Main entry point + image generation
│   ├── image_cmds.py       # Sprite slicing, background removal, resize
│   ├── video_cmds.py       # Video generation (Seedance) + frame splitting
│   └── godot_cmds.py       # Godot project init, script injection, export
├── resources/
│   └── godot-templates/    # Empty Godot project templates
└── output/                 # Generated assets (gitignored)
```

**CLI tools are pure Python** — image processing uses OpenCV/rembg, video uses ffmpeg, Godot uses headless CLI. No LLM in the tools themselves.

**Hermes Agent** orchestrates everything — user describes what they want, Hermes calls `gamefactory` via terminal, results land in `output/`.

## Setup

### Prerequisites
- Python 3.11+
- ffmpeg (for video frame splitting)
- Godot 4.x (for project management, optional)

### Install
```bash
cd cli
pip install -r requirements.txt
```

### Configure
Create `~/.gamefactory/config.json`:

```json
{
  "image": {
    "model": "google/gemini-3.1-flash-image",
    "api_key": "sk-or-...",
    "size": "1024x1024",
    "api_base": "https://openrouter.ai/api/v1",
    "proxy": "http://127.0.0.1:7897"
  }
}
```

Environment variables also work: `OPENROUTER_API_KEY`, `GAMEFACTORY_API_KEY`, `GAMEFACTORY_PROXY`.

## Usage

### Image Generation
```bash
# Generate via OpenRouter (Nano Banana / GPT-5-Image)
python gamefactory.py image generate \
  --prompt "A pixel art slime monster, RPG enemy" \
  --output ./output/slime.png

# Options: --model, --size, --api-key, --proxy
```

### Image Processing
```bash
# Auto-slice sprite sheet into individual sprites
python gamefactory.py image slice --input spritesheet.png --mode auto

# Grid slice (4x4)
python gamefactory.py image slice --input sheet.png --mode grid --rows 4 --cols 4

# Remove background
python gamefactory.py image remove-bg --input photo.png --output cutout.png

# Batch resize
python gamefactory.py image resize --input ./sprites/ --width 64 --height 64
```

### Video Generation
```bash
# Generate via Volcengine Seedance
python gamefactory.py video generate \
  --prompt "A dragon flying over mountains" \
  --output ./output/dragon.mp4

# Split video into frames
python gamefactory.py video split-frames \
  --input video.mp4 --output-dir ./frames/
```

### Godot Project
```bash
# Initialize a new Godot project
python gamefactory.py godot init --path ./my-game --name "My Game"

# Inject a GDScript into the project
python gamefactory.py godot inject --project ./my-game --script player.gd

# Validate project structure
python gamefactory.py godot validate --path ./my-game
```

## Supported AI Providers

| Provider | Model | Type | Auth |
|----------|-------|------|------|
| OpenRouter | `google/gemini-3.1-flash-image` | Image (Nano Banana) | API Key |
| OpenRouter | `openai/gpt-5-image` | Image (GPT-5) | API Key |
| Volcengine ARK | `doubao-seedance-*` | Video (Seedance) | API Key |

## License

MIT
