# Game AI Foundry — AI Agent Handoff

> **读者**：后续接手的 AI Agent / 自动化编排器（中文操作手册）。  
> **侧重**：仓库结构、**brief 字段**、CLI 速查、抠图/动画铁律、配置、**§1.2 资产审查表**。  
> **工具与纠错**：[`TOOLS.md`](TOOLS.md)（本机工具、执行器、外部 Agent 探测命令）。  
> **不写**：设计 vs 施工方法论、六角色边界、里程碑进度 — 分别见 [`ITERATIVE-PRODUCTION.md`](ITERATIVE-PRODUCTION.md)、[`AGENT-ROUTING.md`](AGENT-ROUTING.md)、[`ROADMAP.md`](../ROADMAP.md)。  
> **索引**：[`docs/README.md`](README.md)

---

## 0. 执行摘要

```text
brief chat export（冻结）→ prompt craft → pipeline plan/run → godot assemble → dev-context → C# 玩法
```

- **契约**：export 后只读 `brief.json` + `plans/` + manifest；聊天记忆无效（§1）。
- **批量资产**：用 `pipeline run`，不要逐步 Hermes terminal（[`pipeline-schedule.md`](../resources/skills/orchestrator/pipeline-schedule.md)）。
- **迭代改需求**：流程见 ITERATIVE §3.2；今天 = 改 brief → `plan --merge` → `run`。

---

## 1. 操作流水线（CLI 视角）

| 步 | 执行者 | 命令 / 产物 |
|----|--------|-------------|
| 1 | orchestrator / GUI 策划 | **`brief chat`**（host-chat → 落实）→ `brief chat export` → `brief_meta`；兼容 CLI `brief brainstorm` |
| 1b | orchestrator | **`production derive`** → `plans/production_<brief>.json`（工程蓝图） |
| 1c | orchestrator | **`project progress init`** → `plans/progress_<slug>.json` |
| 2 | prompt-crafter | `prompt craft` → `plans/*.json`（runner 默认跳过，加 `--run-prompts`） |
| 3 | **`pipeline run`** | `pipeline plan` → manifest；`run --jobs N` → `output/` + `assets-manifest.json` |
| 4 | godot-assembler | manifest 内 `godot.assemble` 或 `godot assemble` |
| 4b | orchestrator | **`godot scaffold`**（production → 可编译壳；可在 assemble 前或后） |
| 5 | godot-developer | `production derive` → `godot dev-context` → `plans/dev_*.json` → 写 C# |
| 6 | tester | `test unit` · `test plan` / `test play`（`--task` + `assert_*`；`--progress`）· `test regression` |
| 异常 | orchestrator | `exit 2` → 改 plan/brief → `pipeline reset` → 再 `run` |

角色分工表 → [`AGENT-ROUTING.md`](AGENT-ROUTING.md)。

### 1.1 Brief 门禁

- **GUI 主路径**：策划岗多轮用 `brief chat`（host-chat）；用户明确「落实」才写盘；`brief chat export` 后下游只读文件。
- **CLI 兼容**：`brief brainstorm` 仍可用（问卷式每轮 merge）；**勿**作为 GUI 默认。
- 改素材/玩法 → 改 brief → `pipeline plan`（必要时 `--merge`），不能靠会话记忆。
- 产品心智与工种 → [`HOST-CHAT-PRODUCT.md`](HOST-CHAT-PRODUCT.md)。

**制作完备性审查（makeability）**

```bash
python gamefactory.py brief chat makeability --session-id <id> --json
```

- 独立子 LLM（[`makeability-critic.md`](../resources/skills/orchestrator/makeability-critic.md)）；结果写入 session `makeability_review`（`intent_gaps` / `detail_gaps` / `suggested_defaults`）。
- **Export 门闩（硬）**：结构 / 生图契约校验失败（`gaps` / `_audit_draft_gaps`）→ `brief chat export` 拒绝。
- **制作审查（软 / 建议）**：无审查、草稿指纹过期、或 `intent_gaps` 非空 → **不阻塞** export；GUI 仍可提示再审。`detail_gaps` 同样不阻塞。
- Export 成功时写出 sidecar：`projects/<slug>/makeability.json`（或与 brief 同目录）。
- `production derive` 若发现 sidecar → 合并为 `production_doc.makeability` + 可选 `production_doc.tuning`。

**Brief 补全 / 议题头脑风暴（可选，不绑导出）**

```bash
python gamefactory.py brief chat enrich --session-id <id> [--hint "只补 HUD"] --json
python gamefactory.py brief chat topic-brainstorm --session-id <id> --topic "张力条怎么呈现" --json
python gamefactory.py brief chat brainstorm-apply --session-id <id> --proposal-id p1 --json
```

- GUI 策划：「补全细节」「议题头脑风暴」→ 方案卡「采用 pN」写回 draft（可含资产候选）。
- 不定死通用 `screens` schema；具体数值可进 production，**需要哪些参数**应在 brief 中声明。
- 写回后 makeability 指纹可能过期；建议再「制作审查」对齐意图，但 **不强制** 才能 export。

**Brief 目录 + 分册（catalog shards）**

- 推荐形态：`brief.json` 为**薄目录**（`scenes` / `systems` / `assets` 仅 `id` + `title`|`name` + `path`）；正文在工程内 `scenes/*.json`、`systems/*.json`、`assets/*.spec.json`。
- 厚 brief 仍可读（validate 告警）；新写入用 `brief shard migrate --brief …` 迁出正文并留 `*.pre-shard.json` 备份。
- **简介预算（软告警）**：`project.description` ≤ **800** 字符、`gameplay_loop` ≤ **1200**；细则进 scene/system 分册，勿堆进 description。
- **结构化搜索**（无向量）：`brief search --brief PATH --q QUERY [--kind scene|system|asset] [--json]`；读单册 `brief shard load --brief PATH --kind scene --id ID [--json]`。
- **host-chat**：主对话轮 payload 为薄索引 + 短简介 + 可选 session `focus` 分册；enrich 等子流程仍可能带整稿 draft。
- **文档 focus / 稳定 id**（定位由宿主钉、模型只改 focus 内正文）：见 [`superpowers/specs/2026-08-10-document-focus-and-stable-ids.md`](superpowers/specs/2026-08-10-document-focus-and-stable-ids.md)。

### 1.2 资产审查表（GUI）

Pipeline 跑完后，GUI 右侧 **看板 | 资产** Tab 打开 **资产审查表**，读当前工程 `assets-manifest.json`：

- **展示**：缩略图 + id/name + type + usage + 交付路径 + `review.status`
- **行粒度**：brief 每项资产一行；`icon_kit` 按 `items[]` **逐项展开**（各行独立 review）
- **三动作**（行内）：
  - **采纳** — 只写 `review.status=accepted`，不改文件
  - **重生成** — `pipeline reset --cascade` + `pipeline run`（需已有 pipeline manifest；无则按钮禁用）
  - **本地替换** — 选图覆盖 canonical 路径（优先 `*_nobg`），`review.source=local_file`
- **软标注**：`review` **不阻塞** `godot.assemble` / 程序员派工；普通资产存 `assets[<name>].review`；kit item 存 `assets[<kit>].item_reviews[<slug>]`

入口：顶栏/侧栏 **「资产」**；聊天快捷 **「打开资产表」** 或 `/assets`。

```bash
python gamefactory.py assets review list --manifest ../output/.../assets-manifest.json --json
python gamefactory.py assets review accept --manifest ... --asset knight
python gamefactory.py assets review replace --manifest ... --asset knight --file /path/to.png
python gamefactory.py assets review regenerate-plan --pipeline-manifest ../pipeline/manifest.json --asset knight
```

设计 → [`superpowers/specs/2026-07-24-asset-review-table-design.md`](superpowers/specs/2026-07-24-asset-review-table-design.md)。

---

## 2. 项目结构

```
game-ai-foundry/
├── cli/                    # gamefactory 入口（在此目录执行命令）
├── resources/
│   ├── asset-brief.example.json   # git 内唯一示例 brief
│   └── skills/                    # 六角色 skill 源（hermes sync 生成包）
├── projects/<slug>/        # 新游戏工程根（隔离；gitignored）
│   ├── brief.json
│   ├── progress.json / production.json
│   ├── pipeline/manifest.json
│   ├── plans/  output/  game/
├── pipeline/ plans/ output/ games/   # 旧扁平产物（兼容；gitignored）
└── docs/                   # 文档索引 → docs/README.md
├── external-projects.json  # 外置工程索引（workspace 根；与 projects/ 同级）
```

**入口**：`cd cli && python gamefactory.py --help`

### 外置工程根

新建游戏仍默认 **`projects/<slug>/`**（隔离、gitignored）。已有独立 Godot 仓（如 fish2d）**不必拷贝进 `projects/`**，可在 GUI 顶栏工程切换器点 **「打开外置工程…」**（目录选择器）登记为当前工程。

| 项 | 说明 |
|----|------|
| **索引** | workspace 根 `external-projects.json`；GUI 与 CLI 共用 |
| **虚拟 brief 键** | `external:<id>/brief.json`（不把绝对路径写入 localStorage 主键） |
| **Godot 布局** | 根目录 `project.godot` → `godot_rel=.`；否则 `game/project.godot` → `godot_rel=game`；皆无则标 `godot_missing`，可绑定但打开 Godot / validate 会报错 |
| **产物路径** | `brief.json`、`pipeline/`、`output/`、`plans/`、`production.json`、`progress.json`、`makeability.json` 均写在 **外置根**（与 brief 同级）；无 brief 时可绑定，export / 保存 Brief 目标为该根 `brief.json` |
| **移除** | 「从列表移除」只删索引条目，**不删**磁盘文件 |
| **CLI** | `project external list|add|remove|detect`（`add --root <abs>` 探测布局并登记；同一归一化路径幂等） |

---

## 3. Brief 契约（export 门禁）

> 设计意图 vs 施工规格的 **概念拆分**见 ITERATIVE §1；下列为 **当前 `brief.json` 校验规则**。

### `project` 必填（P0 玩法）

| 字段 | 说明 |
|------|------|
| `title`, `description`, `art_direction`, `dimension` | 基础。`description` 宜为短产品总览，系统细则放可选 `scenes` / `systems` |
| `genre` | 如 `2d_platformer` |
| `gameplay_loop`, `session_goal` | 英文；godot-developer 完成标准。`gameplay_loop` 写场景串法/主重复活动，**允许短**；系统细则见可选 `scenes` / `systems` |
| `player_asset` | 有 player 向 asset 时必填 |
| `controls` | 动作 → 按键 |
| `viewport` | `{ width, height }` |
| `camera` | 平台类 genre 必填（**运行时**跟随/固定，如 `follow_player`） |
| `view` | 可选；内容视角闭集 `side` \| `top_down` \| `three_quarter`；与 `camera` **正交**；brief LLM 从 genre 推断 |

### `project` 可选（P1）

`visual_reference`（**仅图片路径**，导出时留空，由 `brief visual-target pick` / GUI「北极星图」写入；禁止风格散文；默认 prompt 软对齐 — 作 still `--reference-image` 需从属资产设 `style_anchor_kind: visual_reference`）、`art_tokens`（可选结构化风格硬锁，见下）、`project.visual_target{}`、`hud[]`（有 `ui_element` 素材时必填）、`ui_panels[]`（**可选**：菜单/装备等面板清单 `{id,title,kind?,anchor?,slots?,notes?}`；聊到 UI 时写入；**不**挡导出；与 `hud`/`ui_element` 无强制绑定。字符布局示意见工程内 `ui-wireframe.md`，仅 GUI「生成 UI 示意」或 `brief chat ui-wireframe` / `brief ui-wireframe` 按需生成；程序员上下文在文件存在时软提示路径）、`scenes[]` / `systems[]`（见下）

#### `scenes[]` / `systems[]`（可选）

开发向信息架构：**场景**（有进出的屏）+ **逻辑系统**（跨场景规则）。**不**挡 `brief validate` / 导出；与 `ui_panels` 正交（panel = 屏内块；scene 可通过 `ui_panel_ids` 弱引用）。

| 结构 | 字段 | 说明 |
|------|------|------|
| `scenes[]` | `id`, `title` 必填；`summary?`, `ui_panel_ids?`, `notes?`, **`visual_reference?`（仅图片路径，场景效果靶）** | 如主界面、钓场、商店 |
| `systems[]` | `id`, `title` 必填；`summary?`, `notes?` | 如时间池、经济、图鉴；可无贴图 |

`project.description` 应保持**短总览**（约 2–4 句），勿把系统规则/鱼种表堆进去。资产可选 `scene_ids` / `system_ids` 归类（弱引用，不强制校验 id 存在）。程序员/PM 上下文在 brief 含 scenes/systems 时软提示 id 列表。

#### `art_tokens`（可选，Phase 2）

与必填 `art_direction` **并存**；`brief validate` **不要求**本字段。非空时 `build_role_context` / visual-target context 注入整对象，prompt-crafter 优先把 tokens 写成 `style_lock` 硬锁，`art_direction` 仍负责 mood 散文。

| 键 | 类型 | 说明 |
|----|------|------|
| `line` | string | 线宽 / 描边 |
| `palette` | string \| string[] | 主色或 hex 列表 |
| `forbid` | string[] | 禁止风格 / 效果 |
| `silhouette` | string | 剪影 / 头身比 |

旧 brief 无此字段 → 行为与改前相同。示例见 [`resources/style-group-img2img.example.json`](../resources/style-group-img2img.example.json)。

#### 尺寸契约（godogen ASSETS.md Size 列）

**权威字段**：`assets[].display_size: { width, height }` = 在 `project.viewport` 里**看起来多大**（游戏内像素）。

| 层级 | 字段 | 含义 |
|------|------|------|
| 北极星 | `visual_reference` | 整屏参考**图路径**（构图 + 物体屏上比例；风格文案写 `art_direction`） |
| 游戏内 | `display_size` | 玩家眼里多大 → assemble **缩放到此**，Godot scale=1 |
| 生成 | handoff `image_size` | API 出图分辨率（按 display 推导，勿手填） |

兼容旧 brief：`"128x128 px"` 字符串仍可 parse。

**校验**：同 `reference_asset` 家族 / 同 `animation_graphs` 角色 → `display_size` 必须一致。

#### 风格组（`style_group` img2img）

同屏多角色、套图等同族 / 从属关系，用 **风格组** 锁 still 画风（与动作族 `reference_asset` **正交**）：

| 字段 | 说明 |
|------|------|
| `style_group` | 组名；同组 still 共享风格锚 |
| `style_anchor_kind` | `asset`（默认）或 `visual_reference` |
| `style_anchor` | kind=`asset` 时为锚点资产的 `name` / `id`；kind=`visual_reference` 时可省略（读 `project.visual_reference`） |
| `use_style_img2img` | 缺省 **true**；设 `false` 退回纯文生图 |
| `identity_anchor` | 可选；同角色/变体身份锚（`name` / `id`）。从属 + 风格 img2img 时 **优先**于 `style_anchor` 作 `--reference-image`（单槽） |

**默认行为**：资产在组内且为从属（非锚点）→ `pipeline plan` 对该 still 的 `image.generate` **自动**带 `--reference-image`，并 `depends_on` 锚点 raw（或已解析的北极星路径）。handoff 中 `requires_reference_image: true`。

**参考图优先级（单槽）**：需风格 img2img 且 `identity_anchor` 有效 → identity 资产 `*_raw.png`；否则 `style_anchor` / `visual_reference` 既有规则。

**类型配方**：`character` / `texture` / `background` 可从属走风格 img2img；**`icon_kit` 不走跨资产 `style_group`**（类型白名单）。套内另规则：N≥2 且未设 `use_style_img2img: false` 时，**items[0] 为锚**，其余 generate 带 `--reference-image` 指向首项 raw（仍用 `image.bulk_model`）。

**软强度**：prompt-crafter 对从属资产应写「低影响、借风格/身份特征、勿整图复制构图」；Gemini 栈无可靠 API strength。可选 `image.style_img2img_strength`（默认 `0.25`）对支持 `image_config.strength` 的 Provider（如 Recraft）best-effort 透传；不支持则忽略并短日志，**不失败**。

**已做**：Phase 3 GUI DocsPreview 只读标注；看板按资产组头只读 style chips（不写回）。

**例外 / 正交**：

- **视频优先**：`animation_method: video` 仍跟 `reference_asset` 静帧作 i2v 参考；风格组**不**覆盖视频参考图选择。视频所依赖的**初始静帧**本身可先经风格组 img2img 产出。
- **`character_pose`**：仍跟本角色 `reference_asset`（角色本体 still）；风格经本体传递，不走 `style_anchor`。
- **北极星作硬参考**：默认**禁止**把 `project.visual_reference` 当 `--reference-image`；**仅当** brief 对该从属资产设 `style_anchor_kind: visual_reference` 时允许（pipeline 自动传该路径）。
- 无 `style_group` 的旧 brief：行为与改前相同（纯文生图；pose / 视频仍可有各自参考图）。

设计背景 → [`superpowers/specs/2026-07-20-style-group-alignment-design.md`](superpowers/specs/2026-07-20-style-group-alignment-design.md)。

#### `content_class` + `project.view`（Phase 2）

与玩法 **`usage`**、运行时 **`camera`** 均 **正交**；用户自然语言描述，**brief LLM 填写**；旧 brief 无字段仍兼容。

| 层级 | 字段 | 说明 |
|------|------|------|
| `project` | `view` | `side` \| `top_down` \| `three_quarter` — 内容/出图视角；≠ `camera.mode` |
| `assets[]` | `content_class` | 闭集类属（**非** door/cabinet 等特指物名） |
| `assets[]` | `states[]` | 仅 `prop_stateful`；≥2 个 state slug |

**`content_class` 闭集**：`floor_tile`, `wall_tile`, `prop_static`, `prop_interactable`, `prop_stateful`, `weapon`, `tool`, `decor`, `backdrop_sparse`, `backdrop_full`。

**Pipeline 映射（LLM 填 class → 推断 `type`，用户不手填策略）**：

| class 组 | 典型 `type` | 产物 |
|----------|-------------|------|
| `*_tile` | `texture` | 平铺，不去背 |
| `prop_*` / `weapon` / `tool` / `decor` | still 族 | 白底 mattable |
| `backdrop_*` | `background` | 场景背景 |

**场景构图**：默认 `backdrop_sparse` + 独立 props；逻辑布局见 **`production.layout`**（derive 规则生成）；避免单张 busy `backdrop_full` 塞整关。

**`production.layout`（可选）**：`production derive` 写入 `layout.regions`（命名区域）与 `layout.placements`（`asset` + 归一化 `xy_norm`）。**`godot scaffold` / `godot assemble`** 会按 `xy_norm * viewport` 在 `scenes/main.tscn/World` 下写入 Sprite2D；纹理约定路径 `assets/props/{asset}_nobg.png`（assemble 会从 pipeline 产物拷贝；源图缺失时跳过拷贝并记入 `props_skipped`，场景仍引用约定路径）。**注意**：典型流水线里 **assemble 会整文件重写 `main.tscn`**（内联 Player + Background + World），覆盖先前 scaffold 的 PackedScene 结构；施工改动应落在 assemble 之后，或只做纹理绑定。程序员仍可手写覆盖；只引用 brief 已有资产。旧 production 无 `layout` 仍合法。

**`prop_stateful` + `states`**：`pipeline plan` 展开为多 still（如 `{id}__closed` / `{id}__open`）；状态 0 → T2I；状态 k>0 → img2img，`--reference-image` = 状态 0 raw，`depends_on` 状态 0 generate；craft prompt 只写状态差。手写多行 + `identity_anchor` 仍合法。

**Prompt craft（结构化）**：LLM 输出 `subject` / `silhouette` / `style_lock` / `view` / `technical` / `negatives` 等；`assemble_asset_prompt()` 在 Python 合并 `art_tokens`、`project.view`、class 硬锁 → handoff `prompt`（可选保留 `prompt_fields`）。Skills：`resources/skills/prompt-crafter/class-*.md` 按 class 加载；`asset-planner.md` 路由。

**模型能力自推定（assemble）**：craft 时解析目标生图/视频模型 id（still：`image.model` / tier；animation：`video_model` / Seedance 配置）→ `resolve_media_prompt_profile()` → `prompt_profile_id`（`gpt_image` / `gemini_image` / `volc_image` / `volc_video` / `grok_image` / `default`）。火山族用 **`volc_*`** 标识（匹配 `seedream*` / `seedance*` / `doubao-seedream*` 等别名，不用独立 `seed` profile）。Profile 只调组装形态（如 negatives 是否独立成段、soft style 尾句）；结构化硬锁不变。**无 GUI/config 开关**。更换 `image.model` 或 `video_model` 后须 **重跑 `prompt craft`**，旧 handoff 不会自动重装。

Spec → [`docs/anvil/brainstorms/2026-07-24-content-class-structured-craft.md`](anvil/brainstorms/2026-07-24-content-class-structured-craft.md)。

### `assets[]` 每项

`name`, `id`（英文 slug，必填，`^[a-z][a-z0-9_]*$`，用于磁盘路径与 pipeline task 前缀）, `type`, `usage`, `content_class`（可选，见上）, `states`（`prop_stateful` 时）, `usage_description`, `display_size`, `generate_method`；可选 `scene_ids` / `system_ids`（弱引用归类）；音频见 `type: audio`；视差见 `parallax_order` / `scroll_factor`。

**`type: icon_kit`**：`items[]` 必填。每项为字符串，或  
`{id, label?, usage?, usage_description?}`（文件键 slug 跟 `id`；item `usage` 进 `production.collectible_items`）。  
`grid` 可省略（不再驱动切片）。批量模型见 `image.bulk_model` / `generate_tier`。

可选（风格组）：`style_group`, `style_anchor_kind`, `style_anchor`, `identity_anchor`, `use_style_img2img`（见上表）。动作 / 视频族仍用 `reference_asset`。

中文可用在 `name`（对话 / HUD / `reference_asset`）；**产物文件名只用 `id`**（如 `referee_raw.png`）。

### `animation_graphs[]`

多 clip 角色必填；`from`/`to`/`then`/`bidirectional`。

**校验**：`python gamefactory.py brief validate --brief ../resources/asset-brief.example.json`

完整示例 → [`resources/asset-brief.example.json`](../resources/asset-brief.example.json)

---

## 4. 抠图 + 动画帧（必读）

| 来源 | 工具 | 说明 |
|------|------|------|
| 静图 | `image remove-bg --mode color` | 纯白底；~0.1s |
| 视频帧 | `video matte-frames --engine ai` | rembg；**禁止**静图色键 |

- 禁止用拆帧前几帧当 idle；禁止用 `*_raw.png` 当游戏站立图
- `video split-frames` 默认 trim 片头过渡；idle 用独立 `*_nobg.png`

---

## 5. 命令速查

```bash
cd cli

# Brief
python gamefactory.py brief validate --brief ../resources/asset-brief.example.json
python gamefactory.py brief chat export --session-id <SESSION_ID> -o ../projects/my-game/brief.json

# Visual Target（全局或 --scene；另有 status / assign）
python gamefactory.py brief visual-target generate --brief ../projects/my-game/brief.json --candidates 3
python gamefactory.py brief visual-target generate --brief ../projects/my-game/brief.json --scene dock --candidates 3
python gamefactory.py brief visual-target list --brief ../projects/my-game/brief.json --scene dock
python gamefactory.py brief visual-target pick --brief ../projects/my-game/brief.json --id b --scene dock
python gamefactory.py brief visual-target status --brief ../projects/my-game/brief.json
# status：`ready` = brief 已绑定 visual_reference（跑资产闸门）；`disk_marked` = 仅磁盘有 selected.png（进度）
python gamefactory.py brief visual-target assign --brief ../projects/my-game/brief.json --scene harbor --from-scene dock
# 低级可选（无 --scene；场景请用 generate --scene）
python gamefactory.py prompt craft-visual-target --brief ../projects/my-game/brief.json --variant a -o ../plans/visual_target_a.json
# Pipeline（推荐路径）
python gamefactory.py pipeline plan --brief ../resources/asset-brief.example.json
python gamefactory.py pipeline run --manifest ../pipeline/asset-brief.example.json --run-prompts --jobs 4
python gamefactory.py pipeline status --manifest ../pipeline/asset-brief.example.json

# 单资产调试
python gamefactory.py prompt craft --brief ../resources/asset-brief.example.json --asset knight -o ../plans/knight.json
python gamefactory.py image generate --plan-file ../plans/knight.json -o ../output/asset-brief.example/knight_raw.png --validate

# Godot
python gamefactory.py godot assemble --assemble-file ../plans/godot_asset-brief.example.json
python gamefactory.py godot dev-context \
  --brief ../resources/asset-brief.example.json \
  --project ../games/asset-brief.example \
  -o ../plans/dev_asset-brief.example.json
python gamefactory.py godot validate --project ../games/asset-brief.example

# Tester（Pass 5 验收）
python gamefactory.py test plan --brief ../resources/asset-brief.example.json
python gamefactory.py test play \
  --project ../games/asset-brief.example \
  --plan ../plans/playtest_asset-brief.example.json \
  --brief ../resources/asset-brief.example.json

python gamefactory.py doctor --json
python gamefactory.py setup check --json
python gamefactory.py setup executor status --json
python gamefactory.py setup install ffmpeg
python gamefactory.py setup install godot
python gamefactory.py setup install dotnet
```

**本机工具**：FFmpeg / Godot .NET / .NET SDK 为必需项；`setup install` 或 GUI 启动自动装。Godot 自动安装后写入 `godot.engine_path`。**rembg**：Release 内嵌 Python 自带；开发机可 `npm run prepare:python`（gui）。详见 [`TOOLS.md`](TOOLS.md)。

本地 demo brief（`test-brief-*`、`magic-prince-brief.json`、`tests/fixtures/`）均为 **gitignored**；clone 后用 `asset-brief.example.json`。

---

## 6. 配置

模板：`resources/config.example.json` → `~/.gamefactory/config.json`

| 项 | 说明 |
|----|------|
| `provider_accounts` | 多 Provider 账号库（内置厂商 + 自建 OpenAI 兼容；可 `label`/`kind`/`api_base`） |
| `host` / `image` / `video` | 活跃 Provider 与 API key；生图可 `use_text_provider`；批量见 `bulk_provider`/`bulk_model` |
| `image.style_img2img_strength` | 可选，默认 `0.25`；风格 img2img 时 best-effort 透传 `image_config.strength`（Recraft 等）；Gemini 可忽略 |
| `godot.engine_path` | Godot 4 **.NET / Mono**；`setup install godot` 可自动写入 |
| `toolchain.bin_dir` | FFmpeg 目录（默认 `~/.gamefactory/toolchain/bin`） |
| `toolchain.godot_dir` / `dotnet_dir` | 自动安装目录 |
| `agents` | 七角色 executor 路由（见 AGENT-ROUTING） |
| rembg | **Release 内嵌**；开发 venv 用 `prepare:python --with-rembg` |

**执行器配置**（Hermes / Codex / Cursor）：GUI **设置 → 环境** 或 `setup executor step` — 见 [`TOOLS.md`](TOOLS.md) §5。账号与模型见 **设置 → Provider / Agent**（[`GUI-CONFIG.md`](GUI-CONFIG.md)）。

启动检测：`setup check --json` + `doctor --json` + `setup executor status --json`。

---

## 7. 操作原则

1. 只读 brief — 不补猜未写入 JSON 的内容  
2. 生图 `exit 2` → prompt-crafter，不要 trim/remove-bg  
3. 视频帧只用 `video matte-frames`  
4. Pass 3 = assemble；Pass 4 = dev-context 再写 C#  
5. 省钱默认：mini + 480p + 4s + 8 帧 + no audio  
6. godot-developer 不扩 scope（ITERATIVE §8）

---

## 8. 代码索引

| 用途 | 路径 |
|------|------|
| Brief 校验 | `cli/brief.py` |
| Pipeline DAG / runner | `cli/pipeline_manifest.py`, `cli/pipeline_runner.py` |
| Godot handoff | `cli/godot_dev.py`, `cli/godot_assemble.py` |
| Tester / screenshot | `cli/test_analysis.py`, `cli/godot_screenshot.py` |
| 本机工具检测 / 安装 | `cli/toolchain_setup.py`, `cli/setup_cmds.py` |
| 执行器向导 | `cli/executor_setup.py`, `setup executor` |
| Runner 阶段说明 | `resources/skills/orchestrator/pipeline-schedule.md` |
| 资产审查表 / review | `cli/asset_review.py`, `cli/assets_cmds.py` |
| 工具与外部 Agent 手册 | `docs/TOOLS.md` |

---

*文档版本：2026-07-24*
