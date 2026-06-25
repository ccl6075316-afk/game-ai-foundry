# Game AI Foundry — AI Agent Handoff

> **读者**：后续接手的 AI Agent / 自动化编排器。  
> **最后更新**：2026-06-25（Windows 开发机，`E:\game-ai-foundry`）  
> 无需翻阅完整对话历史即可继续工作。

---

## 0. 总目标

**自然语言描述游戏 → AI 生成资产（图、动画、音频、代码）→ 组装 Godot 工程 → 可玩**

编排模式：**Agent + Skill + `gamefactory` CLI**（Hermes / Cursor 调 terminal，**Godot 部分不需要 MCP**）。

---

## 1. 项目结构

```
game-ai-foundry/
├── cli/
│   ├── gamefactory.py          # 主入口
│   ├── asset_pipeline.py       # 资产类型 → pipeline 元数据 + 纯白校验
│   ├── seedance_api.py         # Volcengine Seedance 异步 API
│   ├── video_cmds.py           # video generate / split-frames / matte-frames
│   ├── video_config.py         # 视频生成参数解析（成本可控）
│   ├── video_frames.py         # 拆帧（--frames 均匀采样）
│   ├── video_matting.py        # 视频帧 AI 抠图（rembg）
│   ├── image_cmds.py           # trim / remove-bg / slice / resize / validate-matting
│   ├── godot_cmds.py           # init / inject / validate / open / export
│   ├── matting_config.py
│   ├── plan_io.py              # handoff JSON
│   └── skill_loader.py
├── resources/
│   ├── config.example.json
│   ├── skills/                 # 四 Agent skill 文档
│   ├── godot-templates/default/
│   ├── test-brief-prison*.json # 监狱 demo brief
│   └── asset-brief.example.json
├── plans/                      # 示例 handoff plan
├── docs/AI-HANDOFF.md          # 本文件
└── output/                     # 生成产物（gitignored）
```

**CLI 入口**：在 `cli/` 目录执行 `python gamefactory.py --help`

---

## 2. 四 Agent 架构

| Agent | Role ID | Skills | CLI | 职责 |
|-------|---------|--------|-----|------|
| Orchestrator | `orchestrator` | `pipeline`, `matting`, `matting-video` | 编排后处理 | brief → 委派；trim/remove-bg/video/godot |
| Prompt Crafter | `prompt-crafter` | `asset-planner`, `asset-gen` | `prompt craft` | LLM 写 prompt / video_prompt → plan JSON |
| Image Generator | `image-generator` | `generate` | `image generate` | 只调 OpenRouter 生图 |
| Video Generator | `video-generator` | `generate` | `video generate` | 只调 Seedance 图生/文生视频 |

**Handoff**：`prompt craft -o plans/x.json` → image/video generator 读 `--plan-file`。

---

## 3. 进度总表（2026-06-25）

### ✅ 已完成

| 模块 | 内容 |
|------|------|
| **静图 pipeline** | generate → 纯白 validate → trim → color-key remove-bg → validate-matting |
| **三类资产规则** | character（白底+抠图）/ background（场景不抠）/ icon_kit（网格 slice+抠图） |
| **Seedance 视频** | 正确 API、`video generate`、pro/fast/mini、本地参考图 base64 |
| **视频拆帧** | `video split-frames --frames N`（默认 8，均匀采样） |
| **视频抠图** | `video matte-frames --engine ai`（rembg BiRefNet），与静图色键分开 |
| **成本参数** | brief / config / CLI 三级：`model`, `duration`, `resolution`, `ratio`, `generate_audio`, `sprite_frames` |
| **Godot 基础** | `init` / `inject` / `validate` / `open` / `export` |
| **Skills** | 7 个 skill 文件，pipeline 元数据已更新 |

### 监狱 demo 已跑通（`output/prison-test/`，gitignored）

| 步骤 | 产出 |
|------|------|
| 囚犯角色 v2 | 白底 → trim → 色键 nobg |
| 监狱场景 | background raw |
| 4 件 icon | slice → trim → nobg |
| 走路动画 | 图生视频 mini → 61 帧拆帧 → AI 抠图；8 帧采样已验证 |
| 参考 brief | `resources/test-brief-prison.json`, `-walk.json`, `-scene-icons.json` |

### 🔜 下一步（优先级）

| P | 任务 | 说明 |
|---|------|------|
| **P0** | `godot import-sprites` | 把 `walk_frames_nobg/` → 拷入 `res://` + 生成 `SpriteFrames` |
| **P0** | Godot 场景模板 | 扩展 `godot-templates/`（AnimatedSprite2D + Player） |
| **P0** | `godot-assemble` skill | orchestrator 串 init → import → inject → validate |
| **P1** | 动画 E2E 闭环 | brief → 视频 → 8 帧 → 抠图 → **Godot 可播放 walk** |
| **P1** | 帧 resize 128×128 | 抠图后统一缩放（目前需手动或 loop） |
| **P2** | 文档 | `ROADMAP.md` 仍过时（写 Seedance stub），需同步 |

### ⬜ 未完成

| 模块 | 说明 |
|------|------|
| Godot 全自动组装 | 不能从 brief 一键到可玩场景 |
| 音频 BGM/SFX | 未规划实现 |
| Hermes ↔ gamefactory | 文档有架构，未正式集成 |
| Electron GUI + MCP IPC | 未来 GUI 层，非 Godot 必需 |
| CI / golden 回归测试 | 未做 |
| 一句话端到端 demo | 「做一个 xxx 游戏」→ 可玩工程 |

---

## 4. 两套抠图（必读）

| 来源 | 工具 | 技术 |
|------|------|------|
| 静图（character / icon） | `image remove-bg --mode color` | 白底色键，~0.1s，需纯白底 |
| 视频拆帧 | `video matte-frames --engine ai` | rembg BiRefNet，~5–8s/帧，灰底也行 |

**禁止**对视频帧用静图色键（Seedance 背景会从 ~253 漂到 ~225）。

---

## 5. 标准命令速查

```bash
cd cli

# ── 静图 ──
python gamefactory.py prompt craft --brief ../resources/test-brief-prison.json --asset prison_inmate -o ../plans/prison_inmate.json
python gamefactory.py image generate --plan-file ../plans/prison_inmate.json -o ../output/prison-test/prison_inmate_raw.png --validate
python gamefactory.py image trim -i ../output/prison-test/prison_inmate_raw.png -o ../output/prison-test/prison_inmate_trimmed.png
python gamefactory.py image remove-bg -i ../output/prison-test/prison_inmate_trimmed.png -o ../output/prison-test/prison_inmate_nobg.png

# ── 动画（视频路径）──
python gamefactory.py prompt craft --brief ../resources/test-brief-prison-walk.json --asset prison_inmate_walk -o ../plans/prison_inmate_walk.json
python gamefactory.py video generate \
  --plan-file ../plans/prison_inmate_walk.json \
  --reference-image ../output/prison-test/prison_inmate_v2_raw.png \
  --output ../output/prison-test/prison_inmate_walk_mini.mp4
python gamefactory.py video split-frames \
  --input ../output/prison-test/prison_inmate_walk_mini.mp4 \
  --output-dir ../output/prison-test/walk_frames_8 \
  --frames 8
python gamefactory.py video matte-frames \
  --input-dir ../output/prison-test/walk_frames_8 \
  --output-dir ../output/prison-test/walk_frames_nobg \
  --engine ai

# ── Godot（当前仅脚手架）──
python gamefactory.py godot init --path ../games/prison-demo --name "Prison Demo"
python gamefactory.py godot inject --project ../games/prison-demo --file scripts/player.gd --content "extends Node2D"
python gamefactory.py godot validate --project ../games/prison-demo
```

---

## 6. 配置（`~/.gamefactory/config.json`）

模板：`resources/config.example.json`

```json
{
  "image": {
    "model": "google/gemini-3.1-flash-image",
    "api_key": "YOUR_OPENROUTER_KEY",
    "api_base": "https://openrouter.ai/api/v1",
    "proxy": "http://127.0.0.1:7897"
  },
  "prompt": {
    "model": "deepseek/deepseek-chat",
    "api_key": "YOUR_OPENROUTER_KEY",
    "proxy": "http://127.0.0.1:7897"
  },
  "video": {
    "api_key": "YOUR_ARK_API_KEY",
    "api_base": "https://ark.cn-beijing.volces.com/api/v3",
    "model": "mini",
    "duration": 4,
    "resolution": "480p",
    "ratio": "1:1",
    "generate_audio": false,
    "split_frames": { "frames": 8 }
  },
  "godot": {
    "engine_path": "E:\\Godot_v4.6.1-stable_mono_win64\\Godot_v4.6.1-stable_mono_win64_console.exe"
  },
  "matting": {
    "trim": { "threshold": 240, "padding": 2 },
    "color_key": { "threshold": 235, "fuzz": 24, "key_scope": "exterior" },
    "video_frames": { "engine": "ai", "model": "birefnet-general" }
  }
}
```

**Brief 动画字段**：`duration_seconds`, `sprite_frames`, `video_model`, `video_resolution`, `video_ratio`, `generate_audio`

**代理**：OpenRouter 需 Clash；规则模式加 `DOMAIN-SUFFIX,openrouter.ai,PROXY`。Seedance 国内一般直连。

**视频 AI 抠图依赖**：`pip install "rembg[cpu]"`（首次下载 BiRefNet ~973MB）

---

## 7. 给后续 AI 的操作原则

1. **生图 validate 失败**（非纯白）→ 回 prompt-crafter 重生成，**不要** trim/remove-bg  
2. **静图白边** → 调色键参数（erode/fuzz），不要重生成图  
3. **视频帧** → 只用 `video matte-frames`，不用 `image remove-bg`  
4. **切图** = `trim`；**拆 kit** = `slice --mode grid`  
5. **Godot** → 走 CLI，不需要配 MCP；下一步做 import-sprites  
6. **省钱默认值**：mini + 480p + 4s + 8 帧 + no audio  

---

## 8. 关键文件索引

| 用途 | 路径 |
|------|------|
| 动画 pipeline 元数据 | `cli/asset_pipeline.py` → `build_animation_pipeline()` |
| Seedance API | `cli/seedance_api.py` |
| 视频参数解析 | `cli/video_config.py` |
| 拆帧逻辑 | `cli/video_frames.py` |
| 视频抠图 | `cli/video_matting.py` |
| 静图抠图 | `cli/image_cmds.py` |
| Orchestrator skills | `resources/skills/orchestrator/` |
| Video generator skill | `resources/skills/video-generator/generate.md` |
| 监狱 walk brief | `resources/test-brief-prison-walk.json` |
| 示例 plan | `plans/prison_inmate_walk.json` |

---

## 9. Git / 里程碑

| Commit | 内容 |
|--------|------|
| `a0fe3b4` | 三 Agent + proxy |
| `ef77f0b` | 静图 matting 色键 + 边缘校验 |
| `c1ac879` | Seedance 视频 + 视频帧 AI 抠图 + 拆帧/成本参数 |

**里程碑进度**：
- M1 视频流水线 ~95%（缺 Godot 闭环）
- M2 Hermes 0%
- M3 GUI 0%
- M4 完整可玩 demo ~20%

---

*文档版本：2026-06-25 · 与 `main` 同步*
