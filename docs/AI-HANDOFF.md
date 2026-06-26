# Game AI Foundry — AI Agent Handoff

> **读者**：后续接手的 AI Agent / 自动化编排器。  
> **最后更新**：2026-06-25  
> 无需翻阅完整对话历史即可继续工作。

---

## 0. 总目标

**自然语言描述游戏 → AI 生成资产（图、动画、音频、代码）→ 组装 Godot 工程 → 可玩**

编排模式：**brief 定稿 → AI 写 prompt → `pipeline run` 程序执行 CLI**；Hermes/Cursor 仅用于沟通与异常，**不必逐步 terminal 盯流水线**。

### 0.1 开发期 vs 运行期（谁在干活）

| 模式 | 实际执行者 | 说明 |
|------|------------|------|
| **开发期（当前）** | Cursor Agent 单会话 | 编排 + 写 CLI + 跑命令 + 调试（如 Godot Assembler 实现） |
| **运行期（目标）** | 主 Agent 编排 + **`pipeline run`** | 资产/Godot 由 subprocess 自动跑；AI 只管 brief、prompt、失败 |

代码已按五 Agent 拆分；**生产时应收缩 Cursor 职责**，不要长期「一个对话包打天下」。

---

## 1.1 两阶段生产（推荐）

| 阶段 | 谁 | 做什么 |
|------|-----|--------|
| **A 沟通** | 人 + AI | 定 `brief.json`；`prompt craft` → `plans/*.json` |
| **B 执行** | **`pipeline run`（无 LLM）** | 生图 / 生视频 / trim / 拆帧 / matte；`--jobs N` 并行 |
| **C 异常** | AI | `exit 2` 校验失败 → 改 prompt → `pipeline reset` → 再 `run` |

## 1. 项目结构

```
game-ai-foundry/
├── cli/
│   ├── gamefactory.py          # 主入口
│   ├── asset_pipeline.py       # 资产类型 → pipeline 元数据 + 纯白校验
│   ├── seedance_api.py         # Volcengine Seedance 异步 API
│   ├── video_cmds.py           # video generate / split-frames / matte-frames
│   ├── video_config.py         # 视频生成参数解析（成本可控）
│   ├── video_frames.py         # 拆帧（trim 头尾 → 均匀采样）
│   ├── frame_sequence.py       # 共享 trim-then-sample + trim_lead/trim_trail 解析
│   ├── video_matting.py        # 视频帧 AI 抠图（rembg）
│   ├── image_cmds.py           # trim / remove-bg / slice / resize / validate-matting
│   ├── godot_cmds.py           # init / import-sprites / assemble / validate / open
│   ├── godot_assemble.py       # handoff → .NET 工程组装
│   ├── godot_import.py         # PNG → SpriteFrames .tres
│   ├── agent_routing.py        # config.agents 解析
│   ├── agent_cmds.py           # agents show / resolve
│   ├── matting_config.py
│   ├── plan_io.py              # handoff JSON
│   ├── pipeline_manifest.py    # brief → DAG manifest
│   ├── pipeline_runner.py      # pipeline run（subprocess 自动执行）
│   ├── pipeline_cmds.py        # pipeline plan/run/reset/…
│   ├── hermes_pack.py          # Hermes SKILL.md 生成
│   ├── hermes_cmds.py
│   └── skill_loader.py
├── pipeline/                   # manifest JSON（调度状态）
├── resources/
│   ├── config.example.json
│   ├── skills/                 # 五 Agent skill 文档
│   ├── hermes/                 # 生成的 Hermes SKILL 包
│   ├── godot-templates/dotnet/ # Godot 4 .NET 模板（C#）
│   ├── agents.example.json     # 默认 agent 路由
│   ├── test-brief-prison*.json # 监狱 demo brief
│   └── asset-brief.example.json
├── games/                      # Godot 组装产物（gitignored，同 output/）
├── plans/                      # 示例 handoff plan
├── docs/AI-HANDOFF.md          # 本文件
└── output/                     # 生成产物（gitignored）
```

**CLI 入口**：在 `cli/` 目录执行 `python gamefactory.py --help`

---

## 2. 五 Agent 架构

| Agent | Role ID | Skills | CLI | 职责 |
|-------|---------|--------|-----|------|
| Orchestrator | `orchestrator` | `pipeline`, `matting`, `matting-video` | 编排、委派 | brief → 委派；失败 triage |
| Prompt Crafter | `prompt-crafter` | `asset-planner`, `asset-gen` | `prompt craft` | LLM 写 prompt / video_prompt → plan JSON |
| Image Generator | `image-generator` | `generate` | `image generate` | 只调 OpenRouter 生图 |
| Video Generator | `video-generator` | `generate` | `video generate` | 只调 Seedance 图生/文生视频 |
| Godot Assembler | `godot-assembler` | `assemble`, `import-sprites` | `godot assemble` | PNG → Godot 4 .NET 工程（**无 GDScript**） |

**Handoff**：`prompt craft -o plans/x.json` → image/video generator 读 `--plan-file`；Godot 读 `godot assemble --assemble-file plans/godot_*.json`。

**Agent 路由**：`python gamefactory.py agents show`；详见 `docs/AGENT-ROUTING.md`。

---

## 3. 进度总表（2026-06-25）

> **Git 状态**：`main` 相对 `origin/main` 有大量 **未 commit** 改动（Godot Assembler 全栈）。已推送最新：`33321d2`（pipeline run + wasteland boar idle）。

### ✅ 已完成

| 模块 | 内容 |
|------|------|
| **静图 pipeline** | generate → 纯白 validate → trim → color-key remove-bg → validate-matting |
| **三类资产规则** | character（白底+抠图）/ background（场景不抠）/ icon_kit（网格 slice+抠图） |
| **Seedance 视频** | 正确 API、`video generate`、pro/fast/mini、本地参考图 base64 |
| **视频拆帧** | `video split-frames`：**先裁 i2v 头尾（可配置）→ 再按 `sprite_frames` 采样** |
| **帧序列工具** | `cli/frame_sequence.py`；`trim_lead` / `trim_trail` 开关 + ratio |
| **视频抠图** | `video matte-frames --engine ai`（rembg BiRefNet），与静图色键分开 |
| **成本参数** | brief / config / CLI 三级：`model`, `duration`, `resolution`, `ratio`, `generate_audio`, `sprite_frames` |
| **Godot 组装** | init / import-sprites / assemble / validate；Pass 3；`idle_still` 独立静图 |
| **Godot .NET 模板** | C# Player（WASD+方向键）+ AnimatedSprite2D；静止显 IdleStill |
| **godot-assembler Agent** | 第五 Worker；`agents show`；默认 executor=`pipeline` |
| **Agent 路由文档** | `docs/AGENT-ROUTING.md`、`resources/agents.example.json` |
| **Skills / Hermes** | godot-assembler 包；orchestrator 改为委派 assemble |
| **单元测试** | `test_frame_sequence.py`、`test_video_frames.py` |

### 监狱 demo 已跑通（`output/prison-test/`，gitignored）

| 步骤 | 产出 |
|------|------|
| 囚犯角色 v2 | 白底 → trim → 色键 nobg |
| 监狱场景 | background raw |
| 4 件 icon | slice → trim → nobg |
| 走路动画 | 图生视频 → 抠图 → assemble（61→裁→采 8 帧）→ **Godot 可播 walk** |
| Godot 工程 | `games/prison-demo`（本地 assemble 产出，`games/` 已 gitignore） |
| 参考 brief | `resources/test-brief-prison.json`, `-walk.json`, `-scene-icons.json` |

### 🔜 下一步（优先级）

| P | 任务 | 说明 |
|---|------|------|
| **P0** | Git commit | 合入 Godot Assembler + trim/sample + 文档 |
| **P0** | Pipeline 全链 E2E | brief → `pipeline run` 含 `{brief}.godot.assemble` → 打开可玩 |
| **P1** | 帧 resize 128×128 | 抠图后统一缩放 |
| **P2** | script-crafter（可选） | LLM 写 C#；v1 仍用固定模板 |

### ⬜ 未完成

| 模块 | 说明 |
|------|------|
| 音频 BGM/SFX | 未规划实现 |
| Hermes Kanban 多会话 | ✅ `hermes sync/install`；Kanban 待做 |
| Electron GUI + MCP IPC | 未来 GUI 层 |
| CI / golden 回归测试 | 未做 |
| 一句话端到端 demo | brief → 可玩（资产+Godot 分步已通；编排未自动化） |
| pipeline plan 写 godot handoff | manifest 含 assemble 任务；`plans/godot_*.json` 生成待验证 |

---

## 4. 两套抠图 + 动画帧选取（必读）

| 来源 | 工具 | 技术 |
|------|------|------|
| 静图（character / icon） | `image remove-bg --mode color` | 白底色键，~0.1s，需纯白底 |
| 视频拆帧 | `video matte-frames --engine ai` | rembg BiRefNet，~5–8s/帧，灰底也行 |

**图生视频过渡帧**：Seedance 从参考静图「渐入」动作，片头几帧颜色/形态与正式动作不一致。

- **禁止**把拆帧结果的前几帧当 idle 或 SpriteFrames 首帧
- **禁止**把送给 Seedance 的 `*_raw.png` 当作游戏内站立图（与 walk 帧违和）
- `video split-frames` 默认 **trim_lead/trim_trail=true**，再按 `sprite_frames` 采样；可配置关闭
- Godot 静止态用 **独立** 角色 `*_nobg.png`（handoff `idle_still`），不用动画第 0 帧

**禁止**对视频帧用静图色键（Seedance 背景会从 ~253 漂到 ~225）。

---

## 5. 标准命令速查

```bash
cd cli

# ── 静图 ──
python gamefactory.py prompt craft --brief ../resources/test-brief-prison.json --asset prison_inmate -o ../plans/prison_inmate.json
python gamefactory.py image generate --plan-file ../plans/prison_inmate.json -o ../output/prison-test/prison_inmate_raw.png --validate
python gamefactory.py image trim --input ../output/prison-test/prison_inmate_raw.png --output ../output/prison-test/prison_inmate_trimmed.png
python gamefactory.py image remove-bg --input ../output/prison-test/prison_inmate_trimmed.png --output ../output/prison-test/prison_inmate_nobg.png

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

# ── Godot（godot-assembler agent）──
python gamefactory.py godot assemble --assemble-file ../plans/godot_prison_demo.json
python gamefactory.py godot validate --project ../games/prison-demo
python gamefactory.py godot open --project ../games/prison-demo

# ── Agent 路由 ──
python gamefactory.py agents show
python gamefactory.py agents resolve --role godot-assembler

# ── Pipeline（brief 定稿后程序 runner）──
python gamefactory.py pipeline plan \
  --brief ../resources/test-brief-wasteland-boar-idle.json \
  -o ../pipeline/wasteland-boar-idle.json \
  --output-dir ../output/wasteland5-boar-idle
python gamefactory.py prompt craft --brief ../resources/test-brief-wasteland-boar-idle.json --asset mutant_boar -o ../plans/mutant_boar.json
python gamefactory.py prompt craft --brief ../resources/test-brief-wasteland-boar-idle.json --asset mutant_boar_idle --animation -o ../plans/mutant_boar_idle.json
python gamefactory.py pipeline run --manifest ../pipeline/wasteland-boar-idle.json --jobs 4
python gamefactory.py pipeline status --manifest ../pipeline/wasteland-boar-idle.json
python gamefactory.py pipeline reset --manifest ../pipeline/wasteland-boar-idle.json --task-id mutant_boar.image.generate

# ── Hermes / Codex ──
python gamefactory.py hermes sync      # 从 resources/skills/ 生成 SKILL.md
python gamefactory.py hermes install   # 安装到 ~/.hermes/skills
python gamefactory.py hermes paths     # 输出 repo_root / cli_dir（Hermes terminal workdir）
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
    "split_frames": {
      "frames": 8,
      "trim_lead": true,
      "trim_trail": true,
      "skip_lead_ratio": 0.25,
      "skip_trail_ratio": 0.05
    }
  },
  "godot": {
    "engine_path": "E:\\Godot_v4.6.1-stable_mono_win64\\Godot_v4.6.1-stable_mono_win64_console.exe",
    "import_trim_lead": true,
    "import_trim_trail": true
  },
  "agents": {
    "orchestrator": { "executor": "hermes", "skill": "game-factory-orchestrator" },
    "godot-assembler": { "executor": "pipeline", "skill": "game-factory-godot-assembler" }
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
5. **Godot** → 委派 **godot-assembler**：`godot assemble --assemble-file`；pipeline Pass 3 可自动跑  
6. **Agent 路由** → `docs/AGENT-ROUTING.md` + `agents show`  
7. **省钱默认值**：mini + 480p + 4s + 8 帧 + no audio  

---

## 8. 关键文件索引

| 用途 | 路径 |
|------|------|
| 动画 pipeline 元数据 | `cli/asset_pipeline.py` → `build_animation_pipeline()` |
| Seedance API | `cli/seedance_api.py` |
| 视频参数解析 | `cli/video_config.py` |
| 拆帧 + trim/sample | `cli/video_frames.py`, `cli/frame_sequence.py` |
| 视频抠图 | `cli/video_matting.py` |
| 静图抠图 | `cli/image_cmds.py` |
| Orchestrator skills | `resources/skills/orchestrator/` |
| Video generator skill | `resources/skills/video-generator/generate.md` |
| 监狱 walk brief | `resources/test-brief-prison-walk.json` |
| Godot assemble | `cli/godot_assemble.py`, `cli/godot_import.py` |
| Godot handoff | `plans/godot_prison_demo.json` |
| Agent routing | `cli/agent_routing.py`, `docs/AGENT-ROUTING.md` |
| Godot assembler skill | `resources/skills/godot-assembler/` |

---

## 9. Git / 里程碑

| Commit | 内容 |
|--------|------|
| `33321d2` | pipeline run 程序执行器 + wasteland boar idle demo |
| `a1a2ee4` | Hermes 集成 + pipeline DAG |
| `c1ac879` | Seedance 视频 + 视频帧 AI 抠图 |
| `a0fe3b4` | 三 Agent + proxy |

**Commit `1a34bd7+`**：godot-assembler 全栈（`games/` 不纳入版本库，与 `output/` 同级忽略）。

**里程碑进度**：
- M1 视频 + Godot 组装 ~100%
- M2 Hermes + pipeline ~90%
- M3 GUI 0%
- M4 完整可玩 demo ~50%（缺 pipeline 一键 Godot + 一句话编排）

---

*文档版本：2026-06-25 · 工作区含未推送 Godot Assembler 变更*
