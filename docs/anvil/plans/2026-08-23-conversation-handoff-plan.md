# 本次对话改动总 Plan — 目标模式、Host 收口、尺寸契约 v2

> **读者**：下一任接手的 AI / 维护者。  
> **来源**：2026-08-20～23 对话（目标模式、GUI/CLI 边界、prompt/validate、sizing、真实比例鱼）。  
> **姊妹**：[`ARCHITECTURE-REFACTOR-HANDOFF.md`](../../ARCHITECTURE-REFACTOR-HANDOFF.md) · [`ARCHITECTURE-LAYER-INVENTORY.md`](../../ARCHITECTURE-LAYER-INVENTORY.md) · [`2026-08-20-host-layer-refactor-plan.md`](2026-08-20-host-layer-refactor-plan.md)

**Goal：** 用户点「运行资产生成」能跑通；契约清晰（brief → plan → 图）；物种/道具按真实比例与任意宽高比生图，不再全员方图 + 手写档位像素。

**Architecture：** CLI 引擎 + 薄 Host 编排 + GUI 展示；尺寸分三层（generation / canonical display / runtime scale）；不削弱 validate、不删 `prompt_craft` 组装层。

---

## 执行元数据

| 字段 | 值 |
|------|----|
| Status | **partial** — §A/B 已落地；§C 核心已落地（2026-08-23）；§E fishing-2d 内容迁移待做 |
| Created | 2026-08-23 |
| Resume Point | **§E** fishing-2d 标尺鱼 + `real_length_cm` + re-plan |
| 验收靶机 | `projects/fishing-2d`（30 鱼 char 方图 / 16:9 描述分裂） |

---

## 一、对话结论速览

| 主题 | 结论 |
|------|------|
| 用户目标 | **跑通** > 报错；中间失败自动修、续跑 |
| validate 太重？ | 门禁合理；痛在 **失败后编排** 与 **sizing 与 brief 脱节** |
| prompt-crafter | **消「角色」不消模块**；对外 `host retry-asset` / `run --run-prompts` |
| 单条重试 | 底层有 reset + suggest-retry；需 **Host + GUI 一键**（Host Plan 已做） |
| 方图强制 | **设计遗留**，非通用真理；枪/鱼应跟 `aspect_ratio` |
| display vs generation | **必须拆开**；可「生大用小」 |
| 同图多处大小 | **placement scale**，不 duplicate 资产 |
| 鱼种大小 | **标尺鱼 + real_length_cm 比例**，非「中鱼=96px」档位 |
| 钓获个体差 | **运行时 scale**，brief 只定物种 canonical |

---

## §A 已完成（本会话早期 + 已 push `e79d7c5`）

- [x] **目标模式 GUI**：`handleRun` 失败 → diagnose/heal → `fix_commands` → PM（必要时）→ 续跑（`GOAL_MODE_MAX_REPAIR_ROUNDS`）
- [x] **`attemptPipelineAutoRepair`**：与「项目经理处理失败」共用
- [x] **`pipeline_heal`**：`build_fix_command_chain`、`fix_commands`、`auto_fix_without_agent`；manifest 注入
- [x] **`handoff`**：dispatch 写回时注入 `--manifest`
- [x] **ACP 全角色**：`prepareRoleAwareAcpPrompt`；`record-turn` + `--brief --progress` + `_apply_assistant_dispatch`
- [x] **`pmOpsContext.ts`** + `product-host.md` 目标模式节
- [x] **`docs/ARCHITECTURE-REFACTOR-HANDOFF.md`** 架构交接
- [x] **fishing-2d** pipeline 状态 sync commit（`6a1c32e`）

**注意：** 改 Electron 须完整重启 GUI。

---

## §B Host 桥接层（`2026-08-20-host-layer-refactor-plan.md` — 已执行）

与本次对话重叠，**已在 main 合入**（见该 Plan §执行元数据 `executed`）：

- [x] T1：CJK/craft 失败归类 `validation`
- [x] T2：`host retry-asset`
- [x] T3：`host run-assets --auto-fix`
- [x] T4：GUI/IPC 接 Host
- [x] T5：VT status CLI 单源
- [x] T6：文档 / prompt-crafter 降级为 pipeline 步骤

**Follow-up（仍 open）：**

- [ ] `host run-assets` **流式日志**（对齐原 pipeline-run 终端体验）
- [ ] `App.tsx` **删 legacy** `attemptPipelineAutoRepair` 重复逻辑（若已全走 Host）
- [ ] `AssetReviewPanel` 全面接 `hostRetryAsset`（看板已部分接）

---

## §C 尺寸契约 v2 — 生成 / 显示 / 比例（**下一优先级**）

### 问题实锤（fishing-2d）

- spec 写 `aspect_ratio=16:9`、`display_size=1920×1080`、prompt 含 horizontal 16:9
- plan `image_size` 全为 `2048×2048`（character 分支强制方图）
- 背景 plan 为 `1920×1080`（background 分支正常）
- 根因：`cli/asset_sizing.py` `resolve_generation_image_size` character → `gen×gen`，**不读 `aspect_ratio`**

### 设计目标

```text
brief 资产
  real_length_cm?     → 物种间比例（derive display）
  aspect_ratio        → 生图宽高比（非仅文案）
  display_size        → canonical 游戏内像素（derive 或 override）
  generation_size?    → 可选，API 分辨率（否则 f(display, aspect, tier)）

pipeline plan
  image_size          → 只读，真请求尺寸
  display_size        → assemble 缩放目标

production.layout
  placements[].scale? → 同图多处不同屏上大小

Godot 运行时
  instance.scale      → 同种个体差（钓获长度、水族箱随机）
```

### Task C1: `asset_sizing` 按 `aspect_ratio` 生成（取消 character 全局方图）

**Files:** `cli/asset_sizing.py`, `cli/test_display_size.py`, 新增 `cli/test_asset_sizing_aspect.py`

- [x] character / character_pose / weapon(class→still)：**按 `aspect_ratio` 拆 WxH**，不再 `gen×gen`
- [x] 默认比例按 `content_class`（weapon 横长、角色可 1:1 或配置默认）
- [x] 保留 `snap_api_image_size` / `size_multiple_for_model`
- [x] 单测：16:9 + display 1920×1080 → 非方图 `image_size`；background 行为不变

**成功标准：** fishing-2d 任一条 `char_*.json` plan 的 `image_size` 宽高比 ≈ spec `aspect_ratio`（非 1:1 时）。

---

### Task C2: 显式 `generation_size`（可选字段）

**Files:** `cli/brief.py` (`AssetSpec`), `cli/brief_shards.py`, `cli/asset_pipeline.py` (`build_prompt_scaffold`), `docs/AI-HANDOFF.md`

- [x] brief 可选 `generation_size: {width, height}` 或 `generation_tier: standard|high`
- [x] 若存在 → plan `image_size` 优先用它（再 snap）；否则 C1 推导
- [x] `display_size` 仍只驱动 assemble（`godot_import.save_texture_at_display_size`）
- [ ] 文档：生大用小示例（generation 2048×1152，display 128×72）

---

### Task C3: brief 交叉校验（防「写了 16:9 仍是方图」）

**Files:** `cli/brief.py` (`audit_brief_for_export`), `cli/test_brief_contract.py`

- [x] 警告：`aspect_ratio != 1:1` 且 type=character 时，若 derive 后仍为方图 → export 警告（`brief validate`）
- [x] 警告：同场景多鱼 `display_size` 完全相同且均有 `real_length_cm` 差异

---

### Task C4: `project.size_baseline` + `real_length_cm` 比例 derive

**Files:** `cli/brief.py`, `cli/production_cmds.py`（derive）, `resources/skills/orchestrator/brief-enrich.md`

**契约草案：**

```json
"project": {
  "size_baseline": {
    "asset_id": "char_barramundi",
    "real_length_cm": 80,
    "display_size": { "width": 160, "height": 120 }
  }
},
"assets": [{ "id": "char_bluegill", "real_length_cm": 19, "aspect_ratio": "16:9" }]
```

- [x] `real_length_cm`（可选 `real_length_max_cm`、`size_source`）进 AssetSpec + shard 白名单
- [x] `production derive`：`asset_display_sizes` + effective display；`display = baseline × ratio`，再按 aspect 拆宽
- [ ] 允许 `display_size_override` 艺术夸张
- [x] 单测：80cm 标尺 120px 高 → 19cm 鱼 ≈ 28px 高

**非目标：** 本轮不做运行时 Web Search；体长由 enrich/人工填入。

---

### Task C5: enrich 填真实体长（可选子流程）

**Files:** `cli/brief_cmds.py`, `resources/skills/orchestrator/brief-enrich.md`

- [ ] enrich 提示：对鱼类资产建议填 `real_length_cm`（成年常见体长，附 `size_source: web|manual`）
- [ ] 不自动覆盖已有 display；derive 在 export/derive 阶段算 display
- [ ] GUI「补全细节」可选展示比例预览表

---

### Task C6: placement 级 `scale`（一图多处）

**Files:** `cli/production.py` / layout schema, `cli/godot_layout.py`, `docs/AI-HANDOFF.md` §production.layout

- [x] `layout.placements[]` 增加可选 `scale`
- [x] assemble/scaffold 读 placement scale → Godot `Sprite2D.scale`
- [x] 单测：placement `scale` → scene fragment 含 `scale = Vector2(...)`
- [ ] 文档：AI-HANDOFF §production.layout

---

### Task C7: 文档

**Files:** `docs/ARCHITECTURE-REFACTOR-HANDOFF.md`, `docs/AI-HANDOFF.md`, `docs/RELEASE-NOTES-UNRELEASED.md`

- [ ] 新增 §「尺寸契约 v2」：三层 + 标尺鱼 + 个体 runtime scale
- [ ] 更新尺寸表：取消「character 必方图」叙述
- [ ] fishing-2d 迁移说明：先填 `real_length_cm` + baseline，再 re-plan / recraft

---

## §D Agent / 权限（对话中确认、部分已做）

| 项 | 状态 | 说明 |
|----|------|------|
| ACP 全角色完整 prompt | ✅ §A | |
| record-turn 应用 dispatch | ✅ §A | |
| PM 自动串跑 `cli_hints` | ✅ §A + §B Host | |
| `safe_cli` 放行 `prompt craft --asset` | 可选 | Host 内 craft 优先；若开放须限单资产 |
| 六角色文档降级 | ✅ §B T6 | prompt-crafter = pipeline 步骤 |
| 目标模式：禁止只报 errno | ✅ skill + GUI | |

---

## §E fishing-2d 内容迁移（依赖 §C，非 Foundry 内核）

- [x] 定 **标尺鱼**（维多利亚尖吻鲈 `char_330d60e64c` ~80cm → display 213×120）
- [x] 30 鱼 spec 填 `real_length_cm`（`scripts/migrate_sizing_v2.py`）
- [x] 去掉「全员 1920×1080 display」；`generation_size` 1920×1080 + derive display
- [ ] validation 失败鱼：`host retry-asset --recraft-prompt`（按需人工续跑）
- [ ] 钓获大小 / 水族箱：**Godot C#** `scale`，不写 brief 个体

---

## §F 架构瘦身（P3，可 §C 后并行）

- [ ] `cli/host/` 与 `App.tsx` 去重（Host Plan follow-up）
- [ ] Electron `main.mjs` 仅 ACP 传输，prompt 全 CLI
- [ ] 物理目录 `cli/core` vs `cli/host` 渐进迁移（不大爆炸）
- [ ] `docs/ARCHITECTURE-LAYER-INVENTORY.md` 更新归属表

---

## 推荐执行顺序

```text
§C1 asset_sizing aspect     ← 立刻解除 16:9→方图
§C2 generation_size         ← 生大用小
§C4 size_baseline + real_length_cm
§C3 / C5 / C6               ← 契约与 enrich、placement
§C7 文档
§E fishing-2d 迁移
§B follow-up（流式日志、App 瘦身）
§F 可选
```

---

## 验收总表

| # | 场景 | 期望 |
|---|------|------|
| 1 | 鱼 spec 16:9 | plan `image_size` 非 1:1 |
| 2 | 蓝鳃 19cm / 标尺 80cm | derive display 高度 ≈ 标尺×0.24 |
| 3 | generation 2K + display 128px | assemble 输出 128px 级纹理 |
| 4 | `host run-assets --auto-fix` | validation 无人点 PM 可续跑 |
| 5 | `host retry-asset --recraft-prompt` | 单鱼离开 failed |
| 6 | 同鱼两 placement 不同 scale | 屏上大小不同，同 source 图 |
| 7 | pytest | `test_display_size test_asset_sizing* test_host_* test_pipeline_heal` 绿 |

---

## 关键约束（全 Plan 遵守）

- **禁止**为过关削弱 image/matting validate
- **禁止**删除 `prompt_craft` Python assemble / CJK 守卫
- **禁止**运行时 LLM 决定物种屏上大小（brief + derive + 代码 scale）
- character **不是**默认方图；方图仅是部分 class 的默认值

---

*Plan 版本：2026-08-23 · 覆盖本次对话全部改动项与 Host Plan 衔接。*
