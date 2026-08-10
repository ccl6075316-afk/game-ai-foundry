# 架构方案：Focus P1（写分册 / 拒写 / 注入截断）

## 执行元数据

- **Status**：executed
- **Workflow Stage**：code
- **Created**：2026-08-10
- **Requirements Source**：[`docs/superpowers/specs/2026-08-10-document-focus-and-stable-ids.md`](../../superpowers/specs/2026-08-10-document-focus-and-stable-ids.md)；用户「继续」
- **Depends on**：P0 planner focus read-loop（已 executed）

## Goal

1. Catalog 工程：`upsert_scene` / `upsert_system` /（可选）资产正文写入 **分册文件**，brief 索引保持薄映射。  
2. 无 focus（或 focus 与目标 id 不符）时，**拒绝**改 scene/system 正文补丁。  
3. 主对话注入：超长 `description` / `gameplay_loop` **截断**到预算，并标注 truncated。

## 非目标

- 自动 migrate fishing 语义搬家  
- 向量搜索  
- 无 focus 时禁止改 `project.description` 短字段（仍允许；description guard 已有）

## Tasks

### T1 — `apply_shard_upsert` + persist 钩子
- `brief_shards.py`：`upsert_shard_body(project_root, brief, kind, id, fields) -> catalog_ref`  
  - 若已有 catalog path：load→merge→save  
  - 若 legacy 厚条目：可写盘为 `scenes/<id>.json` 并返回薄 ref（仅当 brief 已有其它 catalog 条目或 `force_catalog=True`？）— **默认**：仅当该条目已是 catalog ref，或 `project` 下已有任一 catalog scene/system 时，把本条外提为分册。  
  - 纯 legacy 厚工程：upsert 仍只改内存 draft（不强迫 migrate）。
- `apply_brief_patches(..., project_root=None, focus=None, enforce_focus=True)`  
  - upsert_scene/system：若应写分册则调用 upsert_shard_body，列表里只留 ref。  
  - upsert_asset with body + catalog：同类处理 `assets/<id>.spec.json`。

### T2 — 无 focus 拒写
- 对 `upsert_scene` / `upsert_system` 以及 `set` 且 path 匹配 `project.scenes[id=` / `project.systems[id=`：  
  - `enforce_focus` 且（无 focus 或 kind 不兼容或 id 不匹配）→ `HostChatError` 明确文案。  
  - 兼容：`focus.kind=intent_gap` 允许写 paths 内 id；`visual_target` 的 id 等于 scene id 时允许 upsert_scene；`focus.kind=project` **不允许**改 scene/system 正文。  
- `answer_makeability_gaps`：closer 应用补丁时 `enforce_focus=False` **或** 先钉 focus 再 enforce（已钉则 enforce OK）。优先：应用前已 `pin_focus_from_answered_gaps`，`enforce_focus=True`。  
- chat `_apply_parsed`：传入 session focus + project_root。

### T3 — 注入截断
- `build_focus_context`：description > 800 / gameplay_loop > 1200 时截断并设 `project.description_truncated` / `gameplay_loop_truncated`（或顶层 `intro_truncated: true`）。

### T4 — 测与文档
- 单测：catalog upsert 写文件；无 focus 拒写；有 focus 通过；截断。  
- 更新 Spec 清单；skill 一句。

## 验收

1. temp catalog brief：upsert_scene notes → shard 文件更新，brief 条目无 notes。  
2. 无 focus upsert_scene → HostChatError。  
3. focus scene=hall 时 upsert dock → error；upsert hall → ok。  
4. fishing 厚 draft thin context description 被截断至 ≤800。
