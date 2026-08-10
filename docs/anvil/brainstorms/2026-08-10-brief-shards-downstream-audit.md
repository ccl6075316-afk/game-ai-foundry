# Brief 分册重构 — 下游功能跟改审计

> **Created**：2026-08-10  
> **Context**：catalog + shards + focus 已落地；用户确认：**制作审查不怕慢，但必须审到拆分后的分册正文**；并要求盘点其它功能是否跟改。  
> **Related**：[`2026-08-10-brief-catalog-shards-design.md`](../superpowers/specs/2026-08-10-brief-catalog-shards-design.md)、[`2026-08-10-document-focus-and-stable-ids.md`](../superpowers/specs/2026-08-10-document-focus-and-stable-ids.md)

## 原则

| 场景 | 读策略 |
|------|--------|
| 主对话（策划聊天） | 薄目录 + focus 单册（快） |
| **制作审查** | **展开全部 scene/system 分册正文**（可慢；资产可仍只给目录） |
| 补全细节 enrich | hydrate + patches / canonicalize（已接） |
| 审查答题 closer | hydrate 读 + patches 写（已接） |
| Pipeline / Godot / assets | `load_brief_full` resolve 资产 + hydrate 场景（已接） |

---

## 跟改状态总表（2026-08-10 再扫）

| 功能 | 读 brief 方式 | Catalog 后风险 | 状态 | 建议 |
|------|---------------|----------------|------|------|
| **Pipeline plan/run** | `load_brief_full` → `resolve_asset_specs` | 资产缺 type | **已跟** | 保持 |
| **assets_manifest / 审查表** | 同上 | 同上 | **已跟** | 保持 |
| **prompt craft** | `load_brief` | 同 resolve | **已跟** | 保持 |
| **主对话 host-chat** | `build_focus_context` | 无 focus 不见正文 | **已跟（P0/P1）** | 保持 |
| **brief search / shard load** | 分册 | — | **已跟** | 保持 |
| **制作审查 Critic** | `hydrate_brief_for_review` | 须见 notes | **已跟** | 保持；资产仅 index |
| **补全细节 enrich** | hydrate + patches / canonicalize | 整稿旁路 | **已跟** | 保持 |
| **北极星 visual_target** | `_load_project` hydrate + shard VR 写回 | 索引无正文 | **已跟** | 保持 |
| **brief.zh.md** | hydrate 后渲染 | 只有薄目录 | **已跟** | 保持 |
| **deep_merge / focus 闸** | strip 正文 + patches upsert | 整稿改正文 | **已跟** | 保持 |
| **审查答题 closer / verifier** | hydrate 后喂 LLM；写侧 patches+focus；指纹仍用薄 draft | 读侧曾盲 | **已跟** | 保持 |
| **topic brainstorm** | hydrate 读；apply `canonicalize_structure_to_shards` | 正文回索引 | **已跟** | 保持 |
| **godot_dev / playtest_plan / production 验收句 / shared_context** | `load_brief_full` hydrate scenes/systems | 缺 summary | **已跟** | 保持 |
| **validate / `audit_visual_reference`** | 经 `load_brief` hydrate 后见分册 VR | 曾漏分册 VR | **已跟**（随 load_brief_full） | 保持 |
| **agent_turn 场景提示** | 直接读 brief JSON id 列表 | 仅 id，故意薄 | **可接受** | 文案可改「细节在分册」 |
| **ui_wireframe** | `ui_panels` | 不依赖 scene notes | **低风险 / 可后置** | 需要再 hydrate |
| **autofix** | 图/clip/hud 确定性修补 | 基本不读 scene notes | **可接受** | — |
| **GUI 侧栏草稿 / Docs 预览** | session 薄 draft | 只见索引 | **可接受** | 可选展开 |
| **Board `onFocusScene`** | await `pinBriefFocus` | pin 竞态 | **已跟** | 保持 |
| **fishing 工程数据** | 已 migrate：薄目录 + `scenes/` `systems/` `assets/*.spec.json`；简介已瘦身；backup `*.pre-shard.json` | **数据已迁** | 可选：在 fishing 仓 commit |

---

## 根因备忘（为何下游曾「丢正文」）

1. Catalog 索引键仅为 `id/title/path`；`summary`/`notes`/`visual_reference` 在分册文件。  
2. `ProjectContext.normalize_scenes`：有 `path` 时**只保留**三键 → 直接 `from_dict` **不带** scene 正文。  
3. **已修**：`load_brief_full` hydrate 后回填 `project.scenes/systems`；closer/verifier/brainstorm/VT/Critic/enrich/zh-doc 显式 hydrate。

---

## 制作审查 Critic（已完成）

`hydrate_brief_for_review` + `run_makeability_review` 注入展开后的 `draft_brief` / `scene_shards` / `system_shards`。  
closer / verifier 同样 hydrate 读侧；写侧 patches + focus；ledger 指纹仍用薄 session draft。

---

## 建议下一刀

1. （可选）fishing 仓 commit 迁移结果。  
2. （可选）ui_wireframe / GUI 展开分册；agent_turn 文案；Suggestions（focus 指示等）。

---

## 明确可后置

- 资产 138 条全文进审查。  
- GUI Brief 大编辑器 / 侧栏展开分册。  
- ui_wireframe hydrate（当前只靠 ui_panels）。  
- 向量检索。

---

## Resume

1. ~~`hydrate_brief_for_review` + Critic~~ **done**  
2. ~~deep_merge / VT / enrich / zh-doc~~ **done**  
3. ~~closer/verifier；load_brief_full；topic brainstorm；Board pin~~ **done**  
4. ~~fishing migrate + 瘦 description~~ **done**（2026-08-10）
