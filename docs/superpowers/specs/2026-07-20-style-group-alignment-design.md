# 同族 / 从属资产的风格对齐

**日期：** 2026-07-20  
**状态：** 设计草案（未实现硬约束）  
**背景问题：** black-whistle 裁判与球员各自 text-to-image，同屏风格不一致；北极星无法单独解决。

## 问题本质

**相同或从属关系**的资产，需要比「全项目艺术方向」更强的对齐：

| 关系 | 例子 | 今日约束 |
|------|------|----------|
| 项目氛围 | 全体资产 ↔ 北极星 | 软：prompt 读 `visual_reference` 文案，**不** img2img |
| 同角色动作族 | `player_run` → `player` | 硬：`reference_asset` + 视频/pose 带 `--reference-image` |
| 同屏多角色 | 裁判 ↔ 球员 | **空缺**：各自独立生图 |
| 图标套图格子 | icon_kit items ↔ grid | 几何切片；格子不够会切坏物体（另见下方「已修」） |

显示尺寸已在同 `reference_asset` / 同 `animation_graphs` 上校验；**风格锚尚未成为 brief 契约**。

## 行业常见做法

1. **Master still → 变体**：先定一张锚点静帧，动作 / 变体只允许 img2img 或 i2v（你们视频链已接近）。
2. **Character sheet / turnaround**：一张多视角定稿，再生产衍生。
3. **Style / character reference API**：IP-Adapter、Midjourney `--cref` / `--sref` 等。
4. **锁定共用 prompt 块 + seed**：批处理常用，仍可能漂。
5. **Art bible + 人工审**：大厂流程，工具难自动化。

共性：**先定锚点图，同族只从锚点衍生，禁止各自重新纯文生图。**

## 约束应落在哪一层

| 层 | 职责 | 强度建议 |
|----|------|----------|
| **Brief 契约** | 声明 `style_group` / `style_anchor`（或扩展 `reference_asset`） | **必须** — 可 validate |
| **Pipeline 门禁** | 从属资产 generate **必须** `--reference-image`（锚点 raw）；锚点变更 cascade 失效同组 | **必须** |
| **Prompt-crafter** | 写清线宽 / 头身 / 描边对齐锚点 | 辅助，不可单独依赖 |
| **Tester** | 同组并排相似度警告 | 可选晚闸，不作唯一手段 |

**不要**只写在 skill 文档里指望模型自觉——难验收、易回归。

## 建议数据模型（草案）

```json
{
  "id": "player",
  "name": "球员_普通",
  "type": "character",
  "style_group": "cast_main",
  "style_anchor": "referee"
}
```

规则草案：

1. 同一 `style_group` 内恰好一个资产作为锚点（`style_anchor` 为空或自指），其余必须指向该锚点的 `name` 或 `id`。
2. 锚点未 `image.generate` done → 从属资产不得进入 generate（或 plan 时 depends_on 锚点）。
3. 锚点 raw 变更 / 删除 → `invalidate` 同组下游（与缺产物失效同一套）。
4. 与现有 `reference_asset`（动作家族）正交：动作仍跟本角色 still；跨角色风格跟 `style_anchor`。

也可第一期**复用** `reference_asset` 表示「风格从属」（语义会混），不如显式字段清晰。

## 非目标（本草案）

- 不要求北极星裁角色区域当默认 cref（可后续增强）
- 不强制全项目单一角色锚（允许多 `style_group`：主角组 / UI 组）
- 不在本草案实现 API 侧 IP-Adapter；先契约 + pipeline 强制 `--reference-image`

## 实施顺序（建议）

1. Brief 字段 + `brief validate` 报错规则 + 示例 brief  
2. `pipeline plan`：从属 `image.generate` depends_on 锚点 generate；命令带 `--reference-image`  
3. 锚点变更 cascade（manifest reconcile）  
4. Prompt skill 补充「同组对齐锚点」  
5. （可选）tester 同组视觉警告  

## 与 icon_kit 切分问题的边界

icon 切坏是 **grid 格数 < items** 导致几何硬切，不是风格对齐。  
已在代码侧：`resolve_icon_grid` / brief 校验 / prompt skill 要求 grid≥items。  
风格对齐问题**不要**和切片问题混在一个字段里解决。

## 相关文件

- 现有硬家族：`assets[].reference_asset`、`animation_graphs`（`cli/brief.py`、`cli/pipeline_manifest.py`）
- 项目软对齐：`project.visual_reference`（`cli/visual_target.py`、`cli/shared_context.py`）
- 显示尺寸家族校验：`cli/asset_sizing.py` / `docs/AI-HANDOFF.md`
