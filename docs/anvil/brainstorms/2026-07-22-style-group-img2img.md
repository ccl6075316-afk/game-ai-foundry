# 工程 Spec：风格组默认图生图（style_group img2img）

## 执行元数据

- **Status**：confirmed
- **Workflow Stage**：req
- **Created**：2026-07-22
- **Updated**：2026-07-22（用户「ok」确认账本）
- **Confirmed By**：user「ok」（2026-07-22）
- **Source Of Truth Until**：replaced by confirmed `/anvil:plan` artifact [`docs/anvil/plans/2026-07-22-style-group-img2img-plan.md`](../plans/2026-07-22-style-group-img2img-plan.md) once that plan is user-confirmed for `/anvil:code`
- **Requirements Source**：用户要启用未充分使用的图生图以保障风格；Grill Q1–Q9 + 视频优先澄清
- **Background Inputs**：[`docs/superpowers/specs/2026-07-20-style-group-alignment-design.md`](../../superpowers/specs/2026-07-20-style-group-alignment-design.md)；[`docs/AI-HANDOFF.md`](../../AI-HANDOFF.md)；现有 `image generate --reference-image` / `character_pose` pipeline；OpenRouter `input_references`
- **Compounded Knowledge**：[`docs/solutions/architecture/style-group-img2img-and-art-tokens-20260722.md`](../../solutions/architecture/style-group-img2img-and-art-tokens-20260722.md)；接线坑 [`…/reviews/identity-anchor-resolve-vs-manifest-wire-pipeline-20260722.md`](../../solutions/reviews/identity-anchor-resolve-vs-manifest-wire-pipeline-20260722.md)

## 背景输入

- 今日主路径多为 **文生图**；`--reference-image` 已存在，但 pipeline 几乎只在 `character_pose`（及视频静帧参考）自动接上 → 用户体感「完全没用上图生图」。
- 同屏 / 同族风格靠 `art_direction` + 北极星 **软**对齐，硬锚空缺（见 2026-07-20 草案）。
- 用户目标：有**从属或同级同类关系**时可用图生图锁风格；**不是一律强制**。
- 视频链：涉及生视频时以视频路径为第一；不涉及视频的静帧、或作为视频初始帧的蓝本，可以走风格图生图。

## 工程理解

在 brief 契约中增加 **`style_group` / 锚点**（与动作族 `reference_asset` 正交）。  
Brief **生成阶段**（brainstorm / commit-brief / export）按**保守规则**标定关系；有关系且未关掉时，`pipeline plan` 对相关 **still `image.generate`** 默认带 `--reference-image` 并 `depends_on` 锚点产物。  
资产可用 `use_style_img2img: false` 退回纯文生图。  
北极星可作为组的特殊锚（`style_anchor_kind: visual_reference`），不再禁止「项目氛围图当硬参考」——但仅当 brief 显式如此标定。

## 目标

1. Brief 资产字段：`style_group`、`style_anchor_kind`（`asset` | `visual_reference`）、`style_anchor`（kind=asset 时为资产 name/id）、`use_style_img2img`（缺省视为 true）。  
2. `brief validate` / export：组规则可验（见边界表）；非法关系报错。  
3. Brief 生成技能 / 流程：仅在明确同族、从属、套图时建组；默认锚 = 组内主资产；需钉项目画风时可用 `visual_reference`。  
4. `pipeline plan`：对仍走 still 且应启用风格 img2img 的资产，自动 `--reference-image` + 依赖锚点 raw（或已解析的北极星路径）。  
5. 显式 `use_style_img2img: false` → 不强制参考图（可纯文生图）。  
6. **视频优先**：`animation_method: video` / 视频任务仍按现有 `reference_asset` + Seedance i2v；风格组不覆盖视频参考图选择。视频所依赖的**初始静帧**本身可先经风格组 img2img 产出。  
7. `character_pose` 仍跟 `reference_asset`（角色本体 still）；风格经本体传递。  
8. 文档与 prompt/image-generator skill 更新：何时默认 img2img、如何关、与北极星关系。

## 非目标

- 全项目所有 still 强制进同一组 / 一律图生图  
- Pipeline 事后自动把无关资产捆进组（推断只在 brief 生成时）  
- 新图像 Provider / Seedream / 真 OpenAI `/images/edits` 端点（沿用现有 OpenRouter `input_references` 路径）  
- API 侧 IP-Adapter / Midjourney cref  
- Tester 视觉相似度硬门禁（可后置）  
- 改变视频生成主链路（Seedance）或假安全式跳过参考图  
- Windows mid-turn / executor 审批（无关）  
- 抽统一「所有参考图」基类超抽象

## 当前架构约束

| 证据 | 含义 |
|------|------|
| `cli/gamefactory.py` `image generate --reference-image` | 执行层已支持 img2img |
| `cli/pipeline_manifest.py` 仅 pose 自动拼参考图 | 需扩展到 style 组 still |
| `cli/brief.py` `AssetSpec.reference_asset` | 动作/视频族；风格须新字段正交 |
| `project.visual_reference` + skills「勿作角色 img2img」 | 本期允许 **显式** kind=visual_reference；默认仍不自动当锚 |
| 2026-07-20 style-group 草案 | 字段与 cascade 思路可继承，门禁改为「默认开可关」而非绝对强制 |
| OpenRouter `input_references` | 非 OR provider 的参考图能力可能弱；失败应硬失败可读 |

## 方案选择

| 决策 | 选择 |
|------|------|
| 用途 | 有关系时可用图生图锁风格，非一律强制 |
| 默认松紧 | 声明关系后默认 img2img，资产 `use_style_img2img: false` 可关 |
| 字段 | `style_group` + `style_anchor_kind` + `style_anchor`；与 `reference_asset` 正交 |
| 范围 | 凡能走 `image.generate` 的 still（含 icon 等）**可**入组 |
| 北极星 | 允许作特殊锚（kind=`visual_reference`） |
| 标定时机 | Brief 生成时保守推断并写入 |
| 与视频 | 视频链第一；静帧蓝本可风格 img2img |
| 与 pose | pose/video 参考仍 `reference_asset` |

## 被排除方案

- 仅靠 skill 文案、无 brief/pipeline 契约  
- 复用 `reference_asset` 兼作风格锚（语义混）  
- 激进：所有 still 默认一组、锚一律北极星  
- 风格优先覆盖视频/pose 参考图  
- 双参考一次 API（v1）

## 边界与失败模式

| 场景 | 期望 |
|------|------|
| 无 `style_group` | 行为同今日（文生图；pose 仍可有参考图） |
| 有组 + 缺省开关 | still generate 带 `--reference-image`，depends_on 锚点 |
| `use_style_img2img: false` | 该资产不强制风格参考图 |
| kind=`asset`，锚点未生成 | 从属不得跑 generate（plan 依赖或 validate） |
| kind=`visual_reference`，路径缺失 | validate/plan 失败，可读错误 |
| 锚点 raw 变更 | 同组下游 invalidate（与现有缺产物失效对齐；plan 定细节） |
| 视频动画任务 | 参考图规则不变（跟 `reference_asset` 静帧）；不改用 style 锚替代 |
| 视频初始静帧在组内 | 该 still 可先风格 img2img，再被视频引用 |
| Provider 不支持参考图 | 硬失败，不静默去掉 `--reference-image` |
| 旧 brief 无新字段 | 完全兼容 |

## 工程代价

- `cli/brief.py`：字段解析 + validate 组规则  
- `cli/pipeline_manifest.py` / `asset_pipeline.py`：still 任务拼参考图与依赖  
- Brief 生成 skills（brainstorm / commit-brief 等）：保守标定说明 + 示例  
- `resources/skills/prompt-crafter` / `image-generator`：更新契约  
- `docs/AI-HANDOFF.md` / 示例 brief  
- 单测：validate、plan argv、开关关闭、视频/pose 不被风格覆盖  
- GUI：v1 **不强制**新面板（brief JSON 即可）；若雇人/预览需展示可 plan 可选  
- **预估**：中型

## 显式假设

1. OpenRouter（或当前 image provider）对 `--reference-image` / `input_references` 足够支撑风格锁定；强度因模型而异。  
2. Brief 作者（含 AI 生成）能在对话线索下正确「保守」建组；误组可用关开关或改 brief 纠正。  
3. `visual_reference` 指向的文件在 plan/run 时可解析（含 VT pick 后路径）。  
4. v1 GUI 不阻塞；CLI/pipeline 为事实源。

## 领域语言

| 术语 | 含义 |
|------|------|
| 风格组 | 共享 `style_group` 的 still 集合 |
| 风格锚 | 组内参考图来源：资产 raw 或北极星 |
| 风格 img2img | still `image.generate` 带 `--reference-image` |
| 动作族参考 | 现有 `reference_asset`（pose / video） |
| 视频优先 | 视频任务参考图规则不被风格组覆盖 |

## 功能需求

1. Brief 读写与校验上述字段。  
2. Brief 生成流程写入保守编组。  
3. Pipeline 对启用风格 img2img 的 still 自动参考图 + 依赖。  
4. 可关开关；无组不改变旧行为。  
5. 视频 / pose 规则按「视频优先 + 正交」表执行。  
6. 文档与 skill 与行为一致。

## 非功能需求

- 旧 brief 零改动可跑。  
- 错误信息含资产名、组名、缺哪张锚点图。  
- 不泄漏 API key。  
- 相关 unittest 绿。

## 安全关注点

- 禁止「需要参考图却静默改文生图」假成功。  
- 参考图路径限制在项目/约定产出树（沿用现有解析，防任意读盘若已有则保持）。

## 成功标准

1. 示例 brief：两角色同 `style_group`，锚为角色 A → `pipeline plan` 中 B 的 `image.generate` 含 `--reference-image` 且依赖 A。  
2. B 设 `use_style_img2img: false` → 无风格参考图强制。  
3. 组 `style_anchor_kind: visual_reference` 且北极星存在 → 从属带该路径参考图。  
4. 视频任务 argv/依赖与改前一致（跟 `reference_asset`）。  
5. 无 `style_*` 的旧 brief plan 行为不变。  
6. validate：坏锚 / 未知 `style_anchor` / 缺北极星文件 → 非 0 或明确 errors。  
7. Docs/skills 不再写「绝对禁止北极星作参考」而不提 kind 例外。

## PR Review 关注点

- 是否误改视频参考图逻辑  
- 无组时是否回归  
- 关开关是否生效  
- 是否静默丢弃 `--reference-image`  
- Brief 生成是否激进乱建组  

## 开放问题

（无阻塞。）

非阻塞（plan/code）：

| 项 | owner | 触发 |
|----|--------|------|
| 锚点 cascade invalidate 精确触发点 | implementer | 对照现有 manifest reconcile |
| 组内多锚 / 环检测报错文案 | implementer | validate |
| GUI 是否展示组关系 | plan 可选 | 用户要可视化时 |
| 非 OpenRouter 参考图能力探测 | implementer | doctor 或 generate 错误 |

## 决策账本

| 状态 | 决策 |
|------|------|
| 已确认 | 有关系才用图生图，非一律强制 |
| 已确认 | 声明后默认开，`use_style_img2img: false` 可关 |
| 已确认 | `style_group` + `style_anchor_kind` + `style_anchor` |
| 已确认 | still 凡 `image.generate` 可入组 |
| 已确认 | 允许北极星作特殊锚 |
| 已确认 | Brief 生成时保守标定 |
| 已确认 | 视频优先；静帧蓝本可风格 img2img；pose 跟 `reference_asset` |
| 已确认 | 非目标：新 provider、激进全组、双参考 API |

## Resume

- **示例 brief**：[`resources/style-group-img2img.example.json`](../../resources/style-group-img2img.example.json)（`cast_demo` 组：锚 `hero_a`、默认 img2img 从属 `hero_b`、`use_style_img2img: false` 的 `hero_c`、视频 `hero_a_walk` 仍跟 `reference_asset`）。
- **验收**：`cd cli && python -m unittest test_style_group test_pipeline_manifest test_brief_contract -q`；`test_style_group.StyleGroupPipelineTests.test_example_brief_manifest_reference_image` 断言 follower 含 `--reference-image`、opt-out 不含、视频仍依赖 `hero_a`。
- **下一步**：`/anvil:plan` 拆任务 DAG → 用户确认 plan → `/anvil:code`。  
