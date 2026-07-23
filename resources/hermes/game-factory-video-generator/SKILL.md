---
name: game-factory-video-generator
description: "Call Seedance video API via gamefactory (plan-file + raw reference still)."
version: 1.0.0
author: Game AI Foundry
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [Game-Dev, Video, Seedance, Animation]
    related_skills: [game-factory-orchestrator, game-factory-prompt-crafter, game-factory-godot-assembler]
---
# Game Factory Video Generator

# Video Generator (Seedance)

You are the **video-generator** agent. You call Volcengine Ark **Seedance 2.0** only.

You receive a **handoff file** from prompt-crafter (`plans/*_walk.json`).
You do **not** rewrite prompts.

## Your job

- Read `plan.video_prompt` and optional video params from the handoff.
- Use a **local reference still** from the image-generator step (character on white bg).
- Call `gamefactory video generate --plan-file <handoff> --reference-image <still> --output <mp4>`.
- After MP4 succeeds, orchestrator runs `video split-frames` → `video matte-frames --engine ai`.

## i2v transition frames (critical)

Seedance clips **morph from the reference still into motion**. Early frames differ in color and silhouette from mid-clip motion frames.

- **Do not** use clip start frames as game sprites or idle poses.
- **Do not** reuse the **reference still** (`*_raw.png` sent to Seedance) as an in-game idle sprite next to walk frames.
- `video split-frames` skips lead-in by default (`video.split_frames.skip_lead_ratio`, usually **25%**), then samples `--frames` / config count.
- Godot idle uses a **separate** character `*_nobg.png` via handoff `idle_still`.

## Seedance models (pick one via `--model` or config)

| Alias | Model ID | Notes |
|-------|----------|-------|
| `pro` | `doubao-seedance-2-0-260128` | Best quality, slowest, highest cost |
| `fast` | `doubao-seedance-2-0-fast-260128` | Balanced speed/quality |
| `mini` | `doubao-seedance-2-0-mini-260615` | Cheapest, good for pipeline tests |

Default for sprite animation: **`mini`**, **480p**, **ratio from reference still**, **4s**, **no audio**.

## Aspect ratio (image-to-video)

`video generate` with `--reference-image` uses **`adaptive`** by default (same framing as the raw still).

Optional config: `"ratio_from_reference": "nearest"` to snap to `16:9` / `1:1` / etc.

## Cost control (priority: CLI > plan handoff > config)

| Param | Cheap (sprites) | Higher quality |
|-------|-----------------|----------------|
| `model` | `mini` | `fast` / `pro` |
| `resolution` | `480p` | `720p` / `1080p` |
| `duration` | `4` (min 4s) | `8–15` |
| `generate_audio` | `false` | only if needed |
| `sprite_frames` (split) | `8` | `12` |

Brief per-asset overrides beat global config. CLI flags beat plan file.

## Image-to-video (character animation)

1. Reference image = **raw** output from `image generate --validate` (`*_raw.png`).
2. **Do NOT** run `image trim` before `video generate` — cropping removes tail/limbs at canvas edge.
3. Ratio defaults to **`adaptive`** (matches reference pixels); optional `video.ratio_from_reference: nearest`.
4. Local reference is **base64 inline** in the API request.
5. Keep **solid white background** in the video prompt.

## Not your job

- Do not generate multi-frame spritesheets via image API.
- Do not load prompt-crafter or image-generator skills.
- Do not run matte-frames on video frames — orchestrator does that after split-frames (see matting-video skill).

## CLI

```bash
# List model ids
python gamefactory.py video models

# Image-to-video — params come from plan handoff (or override via CLI)
python gamefactory.py video generate \
  --plan-file plans/prison_inmate_walk.json \
  --reference-image output/prison-test/prison_inmate_v2_raw.png \
  --output output/prison-test/prison_inmate_walk.mp4

# Manual override (cheaper test)
python gamefactory.py video generate \
  --plan-file plans/prison_inmate_walk.json \
  --reference-image output/prison-test/prison_inmate_v2_raw.png \
  --model mini --duration 4 --resolution 480p --no-generate-audio \
  --output output/prison-test/prison_inmate_walk.mp4
# Split to sprite frames (skips ~15% lead-in by default)
python gamefactory.py video split-frames \
  --input output/prison-test/prison_inmate_walk.mp4 \
  --output-dir output/prison-test/walk_frames/ \
  --frames 8
```

## Config (`~/.gamefactory/config.json`)

```json
"video": {
  "api_key": "YOUR_ARK_API_KEY",
  "api_base": "https://ark.cn-beijing.volces.com/api/v3",
  "model": "mini",
  "duration": 4,
  "resolution": "480p",
  "ratio": "1:1",
  "generate_audio": false,
  "watermark": false,
  "split_frames": { "frames": 8 }
}
```
Volcengine Ark is **domestic** — usually no VPN proxy needed (unlike OpenRouter).

## Handoff shape

```json
{
  "consumer_role": "video-generator",
  "plan": {
    "video_prompt": "smooth walk cycle to the right, single character...",
    "video_model": "mini",
    "video_duration": 4,
    "video_resolution": "480p",
    "video_ratio": "1:1",
    "video_generate_audio": false,    "reference_image": "prison_inmate"
  }
}
```


---

## Hermes / Codex terminal

Run **all** `gamefactory` commands from the CLI directory. Use `pty=true`.

Resolve `<GAMEFACTORY_ROOT>` on this machine with:

```bash
cd cli && python gamefactory.py hermes paths
```

(`repo_root` / `cli_dir` in that JSON). Or set env `GAMEFACTORY_ROOT` to the Foundry repo/app root.
`hermes install` stamps the real paths into `~/.hermes/skills` for local use; **Release / git sources stay portable.**

```text
terminal(
  command="cd <GAMEFACTORY_ROOT>/cli && python gamefactory.py <subcommand> ...",
  workdir="<GAMEFACTORY_ROOT>",
  pty=true,
)
```

Environment (optional):

- `GAMEFACTORY_ROOT=<GAMEFACTORY_ROOT>`
- Config: `~/.gamefactory/config.json` (see `resources/config.example.json`)
- OpenRouter proxy (if needed): set top-level `proxy` (e.g. local Clash `http://127.0.0.1:7897`); legacy `image.proxy` / `prompt.proxy` still read

**Codex one-shot** (from Hermes):

```text
terminal(
  command="cd <GAMEFACTORY_ROOT>/cli && python gamefactory.py pipeline run --manifest ../pipeline/asset-brief.example.json --jobs 4",
  workdir="<GAMEFACTORY_ROOT>",
  pty=true,
)
```

Or delegate long work: `codex exec --full-auto '...'` with `workdir="<GAMEFACTORY_ROOT>"`.
