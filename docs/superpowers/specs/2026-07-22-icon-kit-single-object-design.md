# 工程 Spec：icon_kit 单物体展开 + 生图双档模型

## 执行元数据

- **Status**：confirmed
- **Workflow Stage**：plan
- **Created**：2026-07-22
- **Updated**：2026-07-23（用户 Spec「确认」后开工）
- **Source Of Truth Until**：实现以 [`docs/superpowers/plans/2026-07-22-icon-kit-single-object.md`](../plans/2026-07-22-icon-kit-single-object.md) 为准
- **Workflow Stage**：implement
- **Confirmed By**：用户「确认」（2026-07-22）
- **Change Log**：初稿 — 方案 A（pipeline 展开 kit；废弃网格切片；`image.model` + `image.bulk_model`）
- **Requirements Source**：用户发现 sheet 切片无法绑定「是哪个 / 用在哪」；要求每张图强制单物体，icon 等批量走便宜模型；选型：保留 kit 壳 / 废切片 / 配置两档 / kit+`generate_tier:bulk`
- **Background Inputs**：现有 `icon_kit` + `items` + `grid` + `image slice`；全局 `image.model`；风格组与 icon_kit 正交（icon 不走 style img2img 的既有约束可复查）
- **Deferred**：按类型完整 models 表；sheet 逃生舱；视觉自动认格；~~items 对象级 `usage`~~ → [`2026-07-23-icon-kit-item-objects-design.md`](2026-07-23-icon-kit-item-objects-design.md)

## 背景

今日 `icon_kit`：一张网格图 → 几何切片 → `*_0.png`…。身份依赖模型按 `items` 顺序摆格，**无硬绑定**；kit 级 `usage` 也无法表达「这张药水用在哪」。用户要：

1. **每张生成图只含一个物体**（不再靠切片认人）  
2. **动态选模型**：主图用 `image.model`；批量单物体用便宜的 `image.bulk_model`  
3. Brief 仍可用 **一个 `icon_kit` + `items[]`** 描述一套图标（语法糖），pipeline **内部**拆成 N 次单图生成  

## 目标

1. `icon_kit` 在 `pipeline plan/run` 中展开为 **每 item 一次** `image.generate`（及后续 trim / remove-bg / validate），**不再**调用 `image slice`。  
2. 产物文件名（或稳定相对路径）与 **item 身份**一一对应（slug），不再使用格子序号 `_0/_1` 作为权威身份。  
3. Config 支持双档：`image.model`（默认）与 `image.bulk_model`（批量单物体）。  
4. 显式 `generate_tier: "bulk"` 的 still 资产也走 `bulk_model`；缺省策略见下。  
5. Prompt / skill：单物体、禁止网格/多物同框。  
6. Brief 校验：废弃对「grid≥items 才能切」的硬依赖；`grid` 若仍存在则 **警告或忽略**（不驱动切片）。

## 非目标

- 恢复或保留网格 sheet 作为默认/逃生路径（本 Spec **废止**切片路径）。  
- `image.models_by_type` 完整类型表（二期）。  
- 视觉模型自动识别「图里是剑还是盾」。  
- 首期强制把 `items` 升级为带 `usage` 的对象（可兼容字符串；对象形态二期）。  
- 改变视频 / character_pose 的 reference 语义。

## 架构（方案 A）

```text
brief: icon_kit { id, items: ["sword","potion",…] }
        ↓ pipeline plan
tasks:  generate(sword, bulk_model) → validate → trim → remove-bg
        generate(potion, bulk_model) → …
        ↓
artifacts: …/item_icons_sword_nobg.png 等（示例命名，实现可微调但必须稳定可引用）
```

- **不**在 plan 前改写用户 brief 为 N 条 asset（避免与策划编辑冲突）。  
- 失败可按 **单 item 任务** 重试（优于单任务 for 循环）。

## Brief 契约

| 字段 | 行为 |
|------|------|
| `type: icon_kit` | 保留；必填非空 `items` |
| `items` | 首期：`string[]`；每项 slug 化后作文件/任务键；空串非法 |
| `grid` | **废弃驱动**；校验可 warning「ignored」；不再 `resolve_icon_grid` 升级切格 |
| `generate_tier` | 可选：`"default"` \| `"bulk"`；缺省：kit 展开项视为 `bulk`；其它类型缺省 `default` |
| kit 级 `usage` / `usage_description` | 仍描述整套用途；单 item 用途二期再加 |

Slug 规则：小写、非 `[a-z0-9_]` 转 `_`、去重冲突时加短后缀（实现写死并单测）。

## Config

```json
"image": {
  "provider": "…",
  "model": "<主图/默认>",
  "bulk_model": "<批量单物体，便宜>",
  …
}
```

| 键 | 语义 |
|----|------|
| `image.model` | 默认生图模型（角色、场景、未标 bulk 的 still） |
| `image.bulk_model` | 批量单物体；**未配置时回退 `image.model` 并打日志**（不硬失败） |

Provider / Key 仍走现有 `image` + `provider_accounts`；双档可同 provider 不同 model id。

路由：

- `icon_kit` 展开项 → `bulk_model`  
- `generate_tier: "bulk"` → `bulk_model`  
- 其余 → `image.model`  

`image.generate` CLI / runner 需能接受 **每任务覆盖 model**（或等价 env/flag），避免只能读全局一次。

## Prompt / Skills

- icon / bulk 单物体：明确「single item only, centered, solid white bg, no grid, no other objects」。  
- 删除或改写 prompt-crafter / image-generator 中「NxM grid then slice」为默认路径的表述。  
- Orchestrator matting：icon_kit 后处理改为 **per-item** trim/remove-bg，去掉「grid slice」步骤说明。

## 风格对齐

- 既有「icon_kit 不挂 style_group 做 style img2img」可保持，或改为：**展开后的单 item 仍不自动 style img2img**（与切片正交的结论不变，除非另开 Spec）。  
- 若需套内风格一致：二期可用「kit 内第一张作锚 + bulk img2img」；**首期不做**。

## 成功标准

1. 新 plan 的 icon_kit **无** `image.slice` 任务。  
2. N 个 items → N 条 generate（及对应后处理）；产物路径含 item slug。  
3. 配置了 `bulk_model` 时，这些 generate 实际请求该模型（测例或日志可证）。  
4. 旧 brief 带 `grid` 仍能 plan/run（忽略 grid，不切片）。  
5. 角色/背景等未标 bulk 的资产仍走 `image.model`。  
6. 相关单元测试与示例 brief / skill 文档已更新。

## 测试要点

- Slug 与重名。  
- Manifest：kit → N generate，无 slice。  
- Model 路由：bulk vs default；`bulk_model` 缺失时回退。  
- `generate_tier: "bulk"` 非 kit 资产。  
- Brief validate：无 items 仍报错；有 grid 不因格数失败。

## 迁移

- 文档与示例 brief 去掉「靠 grid 切片」叙述。  
- 已生成的 `*_tiles/*_0.png` 不自动迁移；用户需重跑 kit 任务。  
- Release note 写明 breaking：icon_kit 产物布局变化。

## 与相关 Spec

- 风格组：[`2026-07-20-style-group-alignment-design.md`](./2026-07-20-style-group-alignment-design.md)（切片问题边界：本 Spec 直接废切片）。  
- 资产英文 id：[`2026-07-19-asset-english-id-design.md`](./2026-07-19-asset-english-id-design.md)（kit `id` + item slug 组合需一致）。
