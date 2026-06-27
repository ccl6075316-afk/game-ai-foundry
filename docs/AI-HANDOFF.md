# Game AI Foundry — AI Agent Handoff

> **读者**：后续接手的 AI Agent / 自动化编排器。  
> **最后更新**：2026-06-25  
> 无需翻阅完整对话历史即可继续工作。

---

## 0. 总目标

**自然语言描述游戏 → 冻结 brief JSON → AI 写 prompt → `pipeline run` 程序执行 → Godot 组装 → godot-developer 写玩法 → 可玩**

编排模式：**brief 定稿（唯一契约）→ pipeline plan/run（无 LLM）→ assemble → dev-context**；Hermes/Cursor 用于 brainstorm、prompt craft、玩法代码与异常 triage。

### 0.1 Brief 是唯一标准

- **多轮对话只发生在 brainstorm 阶段**。Host 会话记忆、口头约定 **无效**。
- 用户 `brief export` 后写入 `brief_meta`（`contract_version`, `frozen_at`），下游 **只读 brief 文件**。
- 产物台账：`output/{slug}/assets-manifest.json`（pipeline 阶段 + Godot runtime 绑定）。
- 改玩法或素材 → **改 brief 并重新 plan**，不能靠「我记得聊过」绕过。

### 0.2 开发期 vs 运行期

| 模式 | 实际执行者 | 说明 |
|------|------------|------|
| **开发期（当前）** | Cursor Agent 单会话 | 编排 + 写 CLI + 跑命令 + 调试 |
| **运行期（目标）** | 主 Agent 编排 + **`pipeline run`** | 资产/Godot 由 subprocess 自动跑；AI 只管 brief、prompt、失败、Pass 4 代码 |

---

## 1. 两阶段生产（推荐）

| 阶段 | 谁 | 做什么 |
|------|-----|--------|
| **A 沟通** | 人 + orchestrator | `brief brainstorm` → 校验 → `export` → `brief.json` |
| **B Prompt** | prompt-crafter | `prompt craft` → `plans/*.json`（`pipeline run` 默认跳过，需 `--run-prompts`） |
| **C 执行** | **`pipeline run`（无 LLM）** | 生图 / 生视频 / trim / 拆帧 / matte / assemble；`--jobs N` 并行 |
| **D 玩法** | godot-developer | 读 `godot dev-context` JSON → 写 C# |
| **异常** | AI | `exit 2` 校验失败 → 改 prompt/brief → `pipeline reset` → 再 `run` |

---

## 2. 项目结构

```
game-ai-foundry/
├── cli/
│   ├── gamefactory.py          # 主入口
│   ├── brief.py                # Brief 类型 + export 校验 + animation_graphs
│   ├── brief_cmds.py           # brief validate / export
│   ├── brief_brainstorm.py     # 多轮 brainstorm
│   ├── assets_manifest.py      # assets-manifest.json 构建与更新
│   ├── shared_context.py       # project/asset → JSON（各 role 共用）
│   ├── asset_pipeline.py       # 资产类型 → pipeline 元数据 + 纯白校验
│   ├── pipeline_manifest.py    # brief → DAG manifest
│   ├── pipeline_runner.py      # pipeline run（subprocess）
│   ├── pipeline_cmds.py
│   ├── seedance_api.py         # Volcengine Seedance
│   ├── video_cmds.py / video_frames.py / frame_sequence.py / video_matting.py
│   ├── image_cmds.py
│   ├── godot_cmds.py / godot_assemble.py / godot_import.py / godot_dev.py
│   ├── agent_routing.py / agent_cmds.py
│   └── plan_io.py              # handoff JSON
├── pipeline/                   # manifest JSON（本地，gitignored）
├── resources/
│   ├── asset-brief.example.json   # 仓库内 canonical 示例 brief
│   ├── *-brief.json               # 本地项目 brief（gitignore，如 magic-prince-brief.json）
│   ├── skills/                    # 六 Agent skill 文档
│   ├── hermes/                    # 生成的 Hermes SKILL 包
│   ├── godot-templates/dotnet/
│   └── config.example.json
├── tests/fixtures/             # E2E smoke brief、prison 参考资产
├── games/                      # Godot 组装产物（gitignored）
├── output/                     # 生成产物 + assets-manifest.json（gitignored）
└── docs/AI-HANDOFF.md          # 本文件
```

**CLI 入口**：在 `cli/` 目录执行 `python gamefactory.py --help`

---

## 3. 六 Agent 架构

| Agent | Role ID | 职责 |
|-------|---------|------|
| Orchestrator | `orchestrator` | brief brainstorm、pipeline triage、委派 |
| Prompt Crafter | `prompt-crafter` | `prompt craft` → plan JSON |
| Image Generator | `image-generator` | `image generate` |
| Video Generator | `video-generator` | `video generate` / split / matte |
| Godot Assembler | `godot-assembler` | `godot assemble` — PNG → Godot 4 .NET |
| Godot Developer | `godot-developer` | 读 dev-context，写 C# 玩法 |

**Handoff 链**：
- 生图/视频：`prompt craft -o plans/x.json` → `--plan-file`
- 组装：`godot assemble --assemble-file plans/godot_*.json`
- 写代码：`godot dev-context -o plans/dev_*.json`（含 brief、assets-manifest、animation_graphs、runtime_bindings）

**Agent 路由**：`python gamefactory.py agents show`；详见 `docs/AGENT-ROUTING.md`。

---

## 4. Brief 契约（export 门禁摘要）

### `project` 必填（P0 玩法）

| 字段 | 说明 |
|------|------|
| `title`, `description`, `art_direction`, `dimension` | 基础 |
| `genre` | 如 `2d_platformer` |
| `gameplay_loop`, `session_goal` | 英文；写代码 Agent 的完成标准 |
| `player_asset` | 有 player 向 asset 时必填 |
| `controls` | 动作 → 按键；按 usage 推导 `move_left/right`、`jump`、`attack` |
| `viewport` | `{ width, height }` |
| `camera` | 平台类 genre 必填，如 `{ "mode": "follow_player" }` |

### `project` 可选（P1）

| 字段 | 说明 |
|------|------|
| `visual_reference` | 视觉锚图路径（对标 godogen `reference.png`） |
| `hud[]` | `{ asset, anchor, description }`；有 `ui_element` 素材时必填 |

### `assets[]` 每项

| 字段 | 说明 |
|------|------|
| `name`, `type`, `usage`, `usage_description` | 必填 |
| `display_size` | character / pose / background / icon_kit / ui_element 必填 |
| `generate_method` | `image` / `video` / `procedural` / `file`；音频默认 `procedural` |
| `type: audio` | `usage`: `music` 或 `sfx`；`music` 需 `audio_loop` |
| `usage: parallax_layer` | 需 `parallax_order`, `scroll_factor` |

### `animation_graphs[]`

多 clip 角色必填；`from`/`to`/`then`/`bidirectional`；one-shot 作 `to` 时必须写 `then`。

**校验**：`python gamefactory.py brief validate --brief ../resources/asset-brief.example.json`

---

## 5. 进度总表（2026-06-25）

> **Git 状态**：`main` @ `63b872d` — brief 冻结契约 + assets-manifest + P0/P1 字段 + 73 tests。

### ✅ 已完成

| 模块 | 内容 |
|------|------|
| **Brief 冻结契约** | validate/export、`brief_meta`、`animation_graphs`、P0 玩法、P1 音频/视差/HUD |
| **Assets manifest** | `assets-manifest.json`；pipeline + godot assemble 后更新 runtime |
| **静图 pipeline** | generate → 纯白 validate → trim → color-key remove-bg → validate-matting |
| **资产规则** | character / background / icon_kit / character_pose / audio（schema） |
| **Seedance 视频** | i2v、`video generate`、mini/480p/4s/8 帧 |
| **视频拆帧** | trim 头尾 → 按 `sprite_frames` 采样 |
| **视频抠图** | `video matte-frames --engine ai`（rembg） |
| **Godot 组装** | .NET 模板、SpriteFrames、`idle_still` 独立静图 |
| **Godot dev-context** | Pass 4 handoff（brief + manifest + 契约规则） |
| **Pipeline runner** | plan/run/status/reconcile/reset；E2E smoke 5/5 + validate |
| **Brief brainstorm + GUI** | Electron chat、`/brief` `/plan` `/run` |
| **单元测试** | **73** passed（brief contract、manifest、assemble、smoke） |

### 参考 demo（本地 / gitignored）

| 项目 | Brief | 说明 |
|------|-------|------|
| E2E smoke | `tests/fixtures/briefs/e2e-smoke-brief.json` | 自动化测试 |
| Prison | `tests/fixtures/` 参考资产 | 手动跑通 walk + assemble |
| Magic Prince | `resources/magic-prince-brief.json` | 本地 brief；待 plan merge + 全链重跑 |

### 🔜 下一步（优先级）

| P | 任务 | 说明 |
|---|------|------|
| **P0** | Magic Prince 全链 | validate → plan --merge → run --run-prompts → dev-context |
| **P0** | GUI 一键 E2E | brief 导出后无需手调路径 |
| **P1** | 帧 resize 128×128 | 抠图后统一缩放 |
| **P1** | 视差层素材 + Godot | brief 中 `parallax_layer` 资产 |
| **P2** | 音频生成 CLI | brief 已有 `procedural`/`file` 占位 |
| **P2** | `video_start_from` | 链式 i2v |
| **P2** | CI / golden 回归 | 真实资产 matting |

### ⬜ 未完成

| 模块 | 说明 |
|------|------|
| 音频 BGM/SFX 生成 | brief schema 已有；无 generation CLI |
| Hermes Kanban | `hermes sync/install` 已有；Kanban 待做 |
| 一句话端到端（GUI） | CLI 分步已通；GUI 路径简化待做 |

---

## 6. 两套抠图 + 动画帧选取（必读）

| 来源 | 工具 | 技术 |
|------|------|------|
| 静图（character / icon） | `image remove-bg --mode color` | 白底色键，~0.1s，需纯白底 |
| 视频拆帧 | `video matte-frames --engine ai` | rembg BiRefNet，~5–8s/帧，灰底也行 |

**图生视频过渡帧**：Seedance 从参考静图「渐入」动作，片头几帧与正式动作不一致。

- **禁止**把拆帧前几帧当 idle 或 SpriteFrames 首帧
- **禁止**把 `*_raw.png` 当游戏内站立图
- `video split-frames` 默认 trim 头尾，再按 `sprite_frames` 采样
- Godot 静止态用 **独立** `*_nobg.png`（handoff `idle_still`）

**禁止**对视频帧用静图色键。

---

## 7. 标准命令速查

```bash
cd cli

# ── Brief ──
python gamefactory.py brief validate --brief ../resources/asset-brief.example.json
python gamefactory.py brief brainstorm start --topic "2D platformer with a knight"
python gamefactory.py brief export --brief ../resources/my-game-brief.json

# ── Pipeline ──
python gamefactory.py pipeline plan --brief ../resources/asset-brief.example.json
python gamefactory.py pipeline run --manifest ../pipeline/asset-brief.example.json --run-prompts --jobs 4
python gamefactory.py pipeline status --manifest ../pipeline/asset-brief.example.json

# ── 静图（单资产）──
python gamefactory.py prompt craft --brief ../resources/asset-brief.example.json --asset knight -o ../plans/knight.json
python gamefactory.py image generate --plan-file ../plans/knight.json -o ../output/example/knight_raw.png --validate

# ── 动画（视频）──
python gamefactory.py prompt craft --animation --brief ../resources/asset-brief.example.json --asset knight_walk -o ../plans/knight_walk.json
python gamefactory.py video generate --plan-file ../plans/knight_walk.json --reference-image ../output/example/knight_raw.png -o ../output/example/knight_walk.mp4
python gamefactory.py video split-frames --input ../output/example/knight_walk.mp4 --output-dir ../output/example/knight_walk_frames --frames 8
python gamefactory.py video matte-frames --input-dir ../output/example/knight_walk_frames --output-dir ../output/example/knight_walk_nobg --engine ai

# ── Godot ──
python gamefactory.py godot assemble --assemble-file ../plans/godot_asset-brief.example.json
python gamefactory.py godot validate --project ../games/asset-brief.example
python gamefactory.py godot dev-context \
  --brief ../resources/asset-brief.example.json \
  --project ../games/asset-brief.example \
  --assemble-file ../plans/godot_asset-brief.example.json \
  -o ../plans/dev_asset-brief.example.json

# ── Agent / Doctor ──
python gamefactory.py agents show
python gamefactory.py doctor --json
python gamefactory.py hermes sync
```

---

## 8. 配置（`~/.gamefactory/config.json`）

模板：`resources/config.example.json`

Brief 动画字段：`duration_seconds`, `sprite_frames`, `video_model`, `video_resolution`, `video_ratio`, `generate_audio`

**代理**：OpenRouter 需 Clash。Seedance 国内一般直连。

**视频 AI 抠图**：`pip install "rembg[cpu]"`

---

## 9. 给后续 AI 的操作原则

1. **只读 brief** — 不要补猜 brainstorm 会话里说过但未写入 JSON 的内容  
2. **生图 validate 失败** → 回 prompt-crafter，**不要** trim/remove-bg  
3. **静图白边** → 调色键参数，不要重生成图  
4. **视频帧** → 只用 `video matte-frames`  
5. **Godot Pass 3** → `godot assemble`；**Pass 4** → `godot dev-context` 再写 C#  
6. **改 brief** → 必须 `pipeline plan`（必要时 `--merge`）再 run  
7. **省钱默认**：mini + 480p + 4s + 8 帧 + no audio  

---

## 10. 关键文件索引

| 用途 | 路径 |
|------|------|
| Brief 类型与校验 | `cli/brief.py` |
| Assets manifest | `cli/assets_manifest.py` |
| Pipeline DAG | `cli/pipeline_manifest.py` |
| Godot dev handoff | `cli/godot_dev.py` |
| Brief brainstorm skill | `resources/skills/orchestrator/brief-brainstorm.md` |
| Godot developer skill | `resources/skills/godot-developer/implement.md` |
| 示例 brief（git） | `resources/asset-brief.example.json` |
| E2E smoke brief | `tests/fixtures/briefs/e2e-smoke-brief.json` |
| Agent routing | `docs/AGENT-ROUTING.md` |

---

## 11. Git / 里程碑

| Commit | 内容 |
|--------|------|
| `63b872d` | Brief 冻结契约、assets-manifest、P0/P1 字段、animation_graphs、测试 |
| `17b98ee` | E2E smoke Godot assemble |
| `0259ad9` | Matting validate 修复 |

**里程碑**：
- M1 视频 + Godot 组装 ~100%
- M2 Hermes + pipeline ~90%
- M3 GUI ~75%
- M4 Brief → 可玩 ~65%
- M5 Pass 4 玩法 ~70%

---

*文档版本：2026-06-25 · main @ 63b872d*
