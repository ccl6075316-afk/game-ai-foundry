# 工程 Spec：content_class + view + 分类型结构化 prompt craft

## 执行元数据

- **Status**：confirmed
- **Workflow Stage**：req
- **Created**：2026-07-24
- **Updated**：2026-07-24（用户确认 Spec）
- **Confirmed By**：user「确认」
- **Source Of Truth Until**：replaced by confirmed `/anvil:plan`
- **Requirements Source**：用户增强 prompt 四项讨论；布局 A；content_class B；词表 B（类属不特指）；view A；范围 B；多状态 C + 图生图；user「确认」
- **Background Inputs**：现有 `usage` / `AssetType` / style_group / identity_anchor / visual-target 结构化组装；[`asset-gen.md`](../../../resources/skills/prompt-crafter/asset-gen.md)
- **Compounded Knowledge**：[`style-group-img2img-and-art-tokens`](../../solutions/architecture/style-group-img2img-and-art-tokens-20260722.md)；resolve≠wire

## 工程理解

为 prompt-crafter 建立 **内容类属 × 项目视角 × 结构化出词** 三件套：

1. Brief 增加 **`content_class`**（与玩法 **`usage` 正交**）与项目级 **`project.view`**（与运行时 **`project.camera` 正交**）。  
2. 按 class 加载分 skill；槽位固定；**强制吃 `art_tokens`**。  
3. Craft 输出结构化字段，Python 组装最终 `prompt`（对齐 visual-target）。  
4. **`prop_stateful`**：`states[]` 可展开；状态 0 文生图，其后 **img2img** 锁身份；也允许手写多行 + identity。  
5. 场景搭建默认 **逻辑布局**（不依赖 vision 分析生成背景）；布局 JSON **本期不做**，仅策略入账。

用户仍只说自然语言；class/view/states 由 brief LLM 填写。

## 目标

### Brief 契约

1. `project.view`：枚举闭集，至少含 `side` | `top_down` | `three_quarter`（可再加 `isometric` 若 plan 需要）；缺省时 genre 启发式 + craft 可标注所用默认。  
2. `assets[].content_class`：中闭集（类属，**禁止** door/cabinet 等特指物名）：  
   - `floor_tile` / `wall_tile`  
   - `prop_static` / `prop_interactable` / `prop_stateful`  
   - `weapon` / `tool`  
   - `decor`  
   - `backdrop_sparse` / `backdrop_full`  
3. `usage` 仍表玩法（`player_idle` / `ui_element` / `tile_texture` 等）；与 `content_class` 可同时存在；校验给映射警告（如 `tile_texture` 应对 `floor_tile`/`wall_tile`）。  
4. UI 继续走现有 `ui_element` / `icon_kit`；可不强制 `content_class`，或 plan 定可选 `ui_*`——**建议 v1：UI 不进上表，单独 ui skill**。  
5. `prop_stateful` + 可选 `states: string[]`（≥2）：export/plan **展开**为多 still；文件键如 `{id}__{state}`；状态 0 无参考，状态 k>0 自动 `--reference-image` ← 状态 0 raw，prompt 只写状态差。手写多行 + `identity_anchor` 仍合法。

### Pipeline 映射（少 kind）

| content_class | pipeline 行为（概念） |
|---------------|----------------------|
| `*_tile` | 近 `texture` + 可平铺；不去背 |
| `prop_*` / `weapon` / `tool` / `decor` | 近白底 mattable still |
| `backdrop_*` | 近 `background`；`sparse` skill 强调留白 |

不新增大量 `AssetType`；`type` 仍由映射/LLM 填现有枚举。

### Skills

- 按 class（或 class 组）拆文件；统一槽位：subject → silhouette → palette/line → view → technical → forbid。  
- `art_tokens` 优先硬锁；`art_direction` 仅 mood。  
- `project.view` 驱动视角句；禁止写死「仅横版侧视」。  
- `backdrop_sparse`：少焦点、留给积木；满幅氛围用 `backdrop_full`。  
- UI：独立 skill（可读性、正交、禁透视拟真等）— 属本期 skill 增强，字段可不改。  
- 角色/mattable：按 view 表；小 display_size → flat + thick outline。

### 结构化 craft

- LLM JSON 字段（名称 plan 可微调）：`subject`, `silhouette`, `style_lock`, `view`, `technical`, `negatives`（动画另议）。  
- Python `assemble_*` 合并 tokens/forbid/类型硬锁后写入 handoff `prompt`；可选保留 `prompt_fields`。  
- 旧整段 `prompt` 路径：兼容读取；新 craft 走结构化。

## 非目标（本期）

- Vision 分析生成背景再摆积木（策略上不作为默认；实现不做）  
- Production 逻辑布局 JSON 落地（策略已确认，实现另开）  
- LoRA / 新图像后端  
- 把 `door` 等特指物升为 class  
- 大量扩展 `AssetType` 枚举  
- Pipeline 看板/GUI 大改（DocsPreview 只读可顺带展示 class/view，非必须）

## 方案选择（决策账本）

| 状态 | 决策 |
|------|------|
| 已确认 | 场景默认逻辑布局，不依赖看背景图 |
| 已确认 | 字段 `content_class`，与 `usage` 正交 |
| 已确认 | 中闭集类属词表；不特指具体物件 |
| 已确认 | `project.view` 与 `camera` 正交 |
| 已确认 | 本期范围 = 契约 + 分 skill + 结构化 craft |
| 已确认 | 多状态：C（`states[]` 展开为主 + 手写多行）；出图首态 T2I、其后 img2img |
| 已排除/延后 | 布局 JSON 实现；背景 vision placement |

## 成功标准

1. 带 `content_class`/`view` 的 brief 能 validate；旧 brief 无字段仍可用。  
2. 不同 class craft 结果含对应 technical/view 锁；有 `art_tokens` 时 hex/forbid 出现在组装 prompt。  
3. `states: ["closed","open"]` 的 stateful：plan 含两 generate，第二个带参考第一态 raw。  
4. 结构化 craft 单测：字段缺失时代码仍注入白底/forbid 等硬锁（按类型）。  
5. commit-brief / brainstorm skill 说明：用户自然语言 → LLM 填 class/view/states。

## 工程代价（量级）

- `cli/brief.py`、context、validate、可能 manifest 展开  
- `cli/prompt_craft.py` + skill_loader  
- `resources/skills/prompt-crafter/*`、commit-brief  
- 单测；文档 AI-HANDOFF 短更  
- **预估**：中

## Resume

实现完成（pause，未 commit）。验证：相关单测 53 OK。下一步：`/anvil:review` + commit。
