# 工程 Spec：资产审查表 + 任意资产可替换

## 执行元数据

- **Status**：confirmed
- **Workflow Stage**：done（Task 1–5 已实现；见 [`plans/2026-07-24-asset-review-table.md`](../plans/2026-07-24-asset-review-table.md)）
- **Updated**：2026-07-24（Task 5 文档合入）
- **Created**：2026-07-24
- **Confirmed By**：用户「确认」
- **Requirements Source**：部件试生后讨论——量大需审查；任意资产可替换；需要资产展示表看图与映射
- **Background Inputs**：现有 `assets-manifest.json`、Pipeline 看板、`pipeline reset --cascade`、Visual Target pick 模式
- **Deferred**：硬门禁 assemble；多候选影子目录；换 raw 后自动重跑 matting；骨骼专用 UI；批量全部采纳（可选后加）

## 选型账本

| 决策 | 选择 |
|------|------|
| 审查 UI | **A** GUI 新面板「资产」（与看板并列） |
| 审查模型 | **方案 1** 软标注 `review`，不挡 pipeline |
| 行粒度 | brief 资产一行；`icon_kit` **按 item 展开** |
| 三动作 | 采纳 / 重生成 / 本地替换 |
| 替换写盘 | 覆盖 canonical 交付物路径（无影子 candidates/） |

## 目标

1. **资产展示表**：读当前工程 `assets-manifest.json`，展示缩略图 + id/name + type + usage + 路径 + `review` 状态，方便审查与映射。
2. **任意资产可替换**：行内支持采纳、重生成、本地文件覆盖；不限骨骼/部件类型。
3. **与看板分工**：看板 = 任务进度；资产表 = 看图、映射、人审与替换。

## 非目标

- 未 `accepted` 时阻塞 `godot.assemble` / 程序员派工（硬门禁，后续可选配置）
- `candidates/` 多版对比槽
- 本地替换 raw 后自动 trim/remove-bg
- 骨骼装配专用编辑器
- Clash / 生图 Provider 相关改动（已另做）

## 数据契约

### `review`（挂在审查单元上）

```json
"review": {
  "status": "pending",
  "source": "pipeline",
  "updated_at": "2026-07-24T00:00:00+00:00",
  "note": ""
}
```

| 字段 | 含义 |
|------|------|
| `status` | `pending` \| `accepted` \| `replaced` |
| `source` | `pipeline` \| `regenerate` \| `local_file` |
| `updated_at` | ISO8601 |
| `note` | 可选短注 |

- 默认：无字段或 `pending` + `source=pipeline`
- **采纳**：`status=accepted`（可保留原 `source`）
- **重生成成功** / **本地替换**：`status=replaced`，`source` 对应更新
- 用户可对 `replaced` 再点采纳 → `accepted`

### 审查单元（表行）

- **普通资产**：`assets-manifest.assets[<name>]` 一行；展示交付物优先 gameplay-ready / `*_nobg`，否则 `*_raw`（从 `stages` 解析）。
- **icon_kit**：按 item 分行（`kit_item_id` / slug / stage 路径）；每行独立 `review`。
- **映射只读**：`brief.usage`、`usage_description`、`type`、`display_size`、stages 路径列表；**不改 brief id/name**。

`review` 存放建议（实现可选其一，plan 锁定）：

- **A（推荐）**：`assets[<name>].review`；kit item 用 `assets[<kit>].item_reviews[<slug>]`
- **B**：并行 `review_ledger.json` 旁路文件  

v1 推荐 **A**，与单一账本一致。

## CLI / IPC

| 能力 | 行为 |
|------|------|
| 读表 | 已有 manifest 路径；GUI 读 JSON + 解析缩略图 file URL |
| 采纳 | 写回对应 `review` 字段并保存 manifest |
| 本地替换 | `pickFile` → 拷贝覆盖行 canonical 路径 → 更新 `review` |
| 重生成 | 对该行关联 `image.generate`（及必要下游）`pipeline reset --cascade`，再 `pipeline run`；成功后更新 `review` |

无 pipeline manifesto 时：表仍可看 + 本地替换；重生成禁用并提示先 `pipeline plan`。

## GUI

- 右侧 Tab：**看板 | 资产**
- 筛选：`review.status`、type、搜索 name/id
- 列表：缩略图 + 名称 + usage + 状态徽章
- 详情：大图、路径、打开文件夹、三按钮
- 聊天快捷：「打开资产表」（可选，与「打开看板」对称）

## 验收

1. pipeline 跑完后打开资产表可见缩略图与 usage 映射  
2. 采纳只改 `review`，文件不变  
3. 本地替换后缩略图更新，`source=local_file`  
4. 重生成会重置相关看板任务并刷新图，`source=regenerate`  
5. icon_kit 多 item 分行，互不覆盖 review  

## 风险与假设

- 假设 `assets-manifest` 在 pipeline 完成后足够完整（stages 含路径）；缺产物行显示占位。  
- 本地覆盖 nobg 而 raw 仍旧时，下游若再从 raw 重跑可能冲掉替换——详情需提示；v1 不自动联动。  
- 缩略图大量加载：v1 可用原生 `<img>` + 懒加载；过大图可后加降采样。

## Change Log

- 2026-07-24：初稿 — GUI 资产表 + 软 review + 三动作；用户确认三节设计
- 2026-07-24：Workflow Stage → done；AI-HANDOFF / RELEASE-NOTES 文档合入
