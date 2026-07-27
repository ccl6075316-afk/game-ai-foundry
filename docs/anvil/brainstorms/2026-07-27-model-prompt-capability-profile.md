# 工程 Spec：按生图/视频模型能力自推定组装提示词

## 执行元数据

- **Status**：confirmed
- **Workflow Stage**：req
- **Created**：2026-07-27
- **Updated**：2026-07-27（user「确认」）
- **Confirmed By**：user「确认」
- **Source Of Truth Until**：replaced by confirmed `/anvil:plan`
- **Requirements Source**：用户确认：能力档案驱动组装；Craft 时组装；零人工开关；仅 GPT/Gemini/火山媒体系/Grok；同系差大才拆档；族名用火山系而非 seed* 品牌词
- **Background Inputs**：现有 `assemble_asset_prompt` / class skills；`image_model_route.resolve_image_model_for_tier`；`MODEL_SIZE_MULTIPLES`；公开文档 Seedream=图 / Seedance=视频（火山双引擎）
- **Compounded Knowledge**：not yet compounded

## 背景输入

用户要求：提示词按**模型及其能力**生成/组装，不要整库成品句替换 LLM；不要用户侧开关；prompt 成本可忽略（可重跑 craft）。

公开事实（检索）：火山侧 **Seedream 生图、Seedance 生视频、API 不同**；即梦为产品壳。本仓库今日仅接线 Seedance **视频**；生图主路径为 GPT Image / Gemini 等。用户口头曾称 Seedance 可图可视频——工程上按**火山媒体系两套 API**处理，**族名不用 `seed`**，避免品牌混淆。

## 工程理解

今日 prompt craft：

1. LLM 填结构化字段（`subject` / `style_lock` / …）
2. `assemble_asset_prompt` 合并 art_tokens / view / class 硬锁
3. **不读取**将要调用的 `image.model` / `bulk_model` / `video` 模型

目标：在 craft（及视频 craft）时解析**目标模型 id** → **自动查能力档案** → 按档案组装最终英文 prompt；用户零配置。

## 目标

1. 引入 `resolve_media_prompt_profile(model_id, *, modality) -> PromptCapabilityProfile`（代码内注册表 + 模糊匹配）。
2. 覆盖四系（未命中 → `default`）：
   - **gpt**（生图）
   - **gemini**（生图）
   - **volc**（火山媒体：图 `volc_image` + 视频 `volc_video`；匹配 `seedream*` / `seedance*` / `doubao-seedream*` / `doubao-seedance*` 等）
   - **grok**（生图；按 model id 命中即生效，即使今日接线未全）
3. 同系版本：默认共用一档；**仅当能力差大**时拆子档（例：证实 gpt-image-1 vs 2 文案策略差大再拆；仅尺寸倍数相同不强制拆文案档）。
4. Craft still：用 `resolve_image_model_for_tier` 得模型 → profile → assemble；handoff 可记 `prompt_profile_id` / `image_model`。
5. Craft video：用配置中的 Seedance/视频模型 id → `volc_video`（或匹配结果）→ 视频提示组装规则。
6. **无** GUI/config 人工开关（dialect 等）；档案只在代码维护。
7. LLM 仍填结构化字段；可选向 craft 注入**只读能力摘要**（非让模型猜能力）。

## 非目标

- 市面成品提示词库整句替换
- `models_by_type` 完整产品矩阵
- 运行时向 Provider 拉「提示词方言」元数据
- 用户可配 dialect / negatives 拨杆
- 为省 craft 费用做 generate 前重装（用户明确可不在意 prompt 成本；v1 = craft 时定稿）
- 接入尚未存在的 Volc 生图 API 实现（可先有 profile；无模型 id 则不触发）
- 四系以外的精细优化（一律 default）

## 当前架构约束

- Still：`cli/prompt_craft.py` + `assemble_asset_prompt`；管线 `image_model_route`
- Video：`seedance_api` / video craft skills
- 尺寸：`asset_sizing.MODEL_SIZE_MULTIPLES`（可并存，不合并进本 Spec 必改项）

## 方案选择

**采用：代码内模型族能力注册表 + Craft 时按目标模型自匹配组装。**

### `PromptCapabilityProfile`（内部，非用户配置）

| 字段 | 含义 |
|------|------|
| `profile_id` | 如 `gpt_image` / `gemini_image` / `volc_image` / `volc_video` / `grok_image` / `default` |
| `prompt_dialect` | `natural` \| `tags` |
| `negatives_effective` | false 时 assemble 把 negatives 并进正文/style，不强依赖独立负向通道 |
| `prefer_soft_style_in_prompt` | true 时加强风格软描述（弱 strength API 假设） |
| `modality` | `image` \| `video` |

### 匹配规则（概念）

- 归一化 model 字符串（小写、去空格）
- 按族规则命中；更长/更具体子档优先
- 未命中 → `default`（natural、negatives 并进正文偏保守、soft style true）

### 初始分档（plan 可微调具体布尔值，本 Spec 锁定分档策略）

| profile_id | 匹配示例 | 备注 |
|------------|----------|------|
| `gpt_image` | `gpt-image-1`、`gpt-image-2`、`openai/gpt-image-*` | v1 **共用**一档；若日后证实 1/2 文案差大再拆 |
| `gemini_image` | `gemini*image*`、`google/gemini*image*` | |
| `volc_image` | `seedream*`、`doubao-seedream*` | 火山生图 API |
| `volc_video` | `seedance*`、`doubao-seedance*` | 本仓库现网视频 |
| `grok_image` | `grok*` 且像生图型号（plan 定具体子串） | |
| `default` | 其它 | |

**禁止**对外族名使用单独的 `seed` 作为产品族 id（避免与 Seed 品牌纠缠）；实现标识用 **`volc_*`**。

## 被排除方案

| 方案 | 原因 |
|------|------|
| 用户开关 / config 拨杆 | 用户明确不要 |
| 仅把模型名塞进 LLM 让它猜 | 不可测 |
| generate 前重装为主路径 | 用户不在意 craft 成本；保持简单 |
| 族名 `seed` | 用户确认不用；改 `volc` |
| 大提示词语料库替换 craft | 已否 |

## 边界与失败模式

| 模式 | 处理 |
|------|------|
| 未知模型 | `default`，不失败 |
| bulk vs main 不同模型 | 按该资产 tier 解析到的模型选档 |
| 换模型后旧 handoff | 重跑 craft（可接受） |
| 无 `prompt_fields` 旧稿 | 保持原 `prompt` 字符串行为 |
| Volc 生图未接线 | profile 可测；无对应 model 配置则路径不触发 |

## 工程代价

| 模块 | 量级 |
|------|------|
| 新 `image_prompt_profile.py`（或等价） | 小–中 |
| `assemble_asset_prompt` 吃 profile | 中 |
| still craft 接线模型解析 | 小 |
| video craft 接线 | 小–中 |
| 单测按族快照 | 中 |
| skill 一句说明 | 小 |
| GUI | **无** |

## 显式假设

- v1 布尔能力值由实现按公开习性赋初值；验收以「同 fields 不同 profile → 组装结果可区分」为主，不以实网出图质量门禁。
- Grok 生图 id 模式在 plan 用保守子串；误伤文本 grok 时以 modality=image 的调用方为准。
- `tags` 方言 v1 可为轻度逗号压缩，不必上满 SD 加权语法。

## 领域语言

| 术语 | 含义 |
|------|------|
| **PromptCapabilityProfile** | 模型能力档案（内部） |
| **volc_image / volc_video** | 火山图/视频提示档 |
| **自推定** | 由 model id 查表，非用户开关 |
| **dialect** | natural vs tags 组装风格 |

## 功能需求

### FR-1 注册表与解析

- `resolve_media_prompt_profile(model: str, *, modality: Literal["image","video"]) -> profile`
- 单测：四系样例 id → 期望 profile_id；垃圾字符串 → default

### FR-2 Assemble

- `assemble_asset_prompt(..., profile=None)`：按 dialect / negatives_effective / prefer_soft_style 调整输出
- 无 profile → 等价今日行为或显式 default（plan 二选一，建议显式 default 与「未知模型」一致）

### FR-3 Still craft

- craft 路径解析目标 image model（main/bulk tier）→ profile → 组装
- handoff 可选字段：`image_model`、`prompt_profile_id`

### FR-4 Video craft

- 解析 video/Seedance 模型 → `volc_video`（或匹配结果）→ 视频提示组装（至少 negatives/方言策略对齐 profile）

### FR-5 文档

- AI-HANDOFF / prompt-crafter skill 短述：按模型自推定；无用户开关；火山用 volc_* 匹配 seedream/seedance 别名

## 非功能需求

- 解析纯函数、可单测、无网络
- 不增加用户设置项

## 安全关注点

- 无密钥进 prompt；profile 不含凭证

## 成功标准

1. 同一组 `prompt_fields`，`gpt_image` vs `gemini_image` vs `default` 组装字符串有可断言差异（测例固定）。
2. `doubao-seedance-2-0-*` → `volc_video`；`doubao-seedream-*` → `volc_image`。
3. 未知模型 → default，craft 不炸。
4. 无新 GUI/config 键用于 dialect。
5. 现有 structured craft 单测回归绿（或按 profile 默认更新断言）。

## PR Review 关注点

- 是否出现用户可配开关回潮
- 是否误把文本 grok 模型用到生图档
- volc 命名与 seedream/seedance 别名是否写清
- 是否偷偷做了 generate 前重装主路径

## 开放问题

| 项 | 状态 | 说明 |
|----|------|------|
| 各 profile 布尔初值精调 | deferred → plan | 不挡 Spec |
| Grok 生图 id 子串表 | deferred → plan | |
| gpt-image-1/2 是否拆档 | deferred | v1 共用；有证据再拆 |

---

请回复 **确认** 以把本 Spec 标为 `confirmed` 并进入 `/anvil:plan`；或指出要改的点。
