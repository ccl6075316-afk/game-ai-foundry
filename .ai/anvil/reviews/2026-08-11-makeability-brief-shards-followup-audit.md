# 审计：制作审查（Makeability）相对 Brief Catalog/Shards

| 字段 | 内容 |
|------|------|
| Date | 2026-08-11 |
| Scope | Foundry「制作审查」工作流（Critic → 缺口卡 → closer → verifier），对照 catalog/shards |
| Spec 背景 | `docs/anvil/brainstorms/2026-08-10-brief-shards-downstream-audit.md`（曾标 Critic/closer **已跟**） |
| Status | **Important-1 已修**；Suggestions 仍可后置 |

## 结论（一句话）

读侧 Critic / closer / verifier **代码路径已 hydrate**，skills 也写了分册纪律；但 **未绑定工程根时审查仍会跑完，且只看见薄目录**——对已迁 fishing 这类 catalog 工程等于「没审到正文」。

## 已跟上（PASS）

| 环节 | 证据 |
|------|------|
| Critic 读 | `run_makeability_review` → `hydrate_brief_for_review` + `scene_shards` / `system_shards` / `source_of_truth_note` |
| Critic skill | `resources/skills/orchestrator/makeability-critic.md` 明确分册展开、禁止因薄索引开 intent |
| Closer / Verifier 读 | `_hydrate_draft_for_llm`；`test_host_chat…catalog_shard_notes` **PASS** |
| 写回 | `apply_brief_patches` + `intent_gap` focus 放行多 path；catalog upsert 写分册 |
| 指纹 | `draft_fingerprint` 用薄 session draft（不因 hydrate 误脏） |
| fishing 有 bind 时 | 实测：`bound_brief_rel=projects/fishing-2d/brief.json` → hub.notes 可见、9 scene_shards |

## 未跟上 / 缺口

### Important-1 — 无 project root 时「盲审」仍成功（High）

对抗复现：

| 条件 | Critic payload |
|------|----------------|
| session **无** `bound_brief_rel` | `has_notes=False`，`scene_shards=0`，大量 `hydrate_errors`（needs project_root） |
| **有** bind 且 brief 文件存在 | `has_notes=True`，`scene_shards=9` |

根因：`_project_root_for_session` 依赖已绑定且磁盘上存在的 brief；GUI `hostChatMakeability` **不传**当前 `activeBriefRel`、也不在跑审前强制 bind。

影响：顶栏未绑工程 / 会话丢 bind / 仅 CLI 无 bind 时，制作审查对 catalog 工程**看不到 scenes/systems 正文**，却仍返回「审查完成」（仅靠门面 description/loop）。`hydrate_errors` 进了 payload，但 skill 只说「可能仍只有薄映射」，**未要求宿主直接失败**。

**建议修复（择一或组合）：**

1. `brief_uses_catalog(draft)` 且存在 hydrate_errors / 无 root → **`HostChatError` 拒绝审查**（提示先绑定工程）。  
2. GUI `handleBriefMakeability`：有 `activeBriefRel` 时先 `hostChatBind` 再 makeability。  
3. 结果里把 `hydrate_errors` 顶到 `assistant_message` 醒目警告（次优）。

### Suggestion-1 — Closer/Verifier 系统提示未写分册纪律

Payload 已是展开稿，功能可用；建议在 `_MAKEABILITY_ANSWER_SYSTEM` / verifier 提示中加一句：scenes/systems 正文已展开，细则写 upsert 分册字段，勿因索引薄而堆回 description。

### Suggestion-2 — GUI 缺口卡与人侧文档预览未联动

`MakeabilityGapCard` 不展示 `write_paths`，也不按 gap 钉文档栏分册。审查答题后 session 会 `intent_gap` focus，但 Docs 预览按设计不跟随该 kind → 人看文档与审查卡脱节。可后置：点 gap → 文档栏打开 canonical scene/system。

### Suggestion-3 — 文案债（非 shards 主因）

`host-chat.md` 仍写 export「强制」制作审查通过；与软闸门产品不一致。顺手改即可。

### Suggestion-4 — Critic 缺 catalog+bind 回归测

`test_makeability_critic` 多用内联厚 draft；catalog 盲审/有 bind 审到 notes 主要靠 host_chat closer 测。建议补一条：`bound` + mock LLM 断言 user payload 含 notes。

## 相对下游审计表

| 审计表行（2026-08-10） | 本轮复核 |
|------------------------|----------|
| 制作审查 Critic 已跟 | **有条件成立**（须 bind / 有 root） |
| closer / verifier 已跟 | **成立**（同须 root；有单测） |
| GUI 侧栏 / Docs | 人侧预览另包已做；**与审查卡联动仍缺** |

## Resume

1. ~~Important-1：catalog 无 root 拒审 + GUI makeability 前 bind~~ **done**（2026-08-11）  
   - CLI `_hydrate_for_makeability`；answer 同闸  
   - GUI `handleBriefMakeability` / `handleMakeabilityAnswer` 先 `hostChatBind`  
   - closer/verifier 提示补分册纪律  
2. 可选：缺口卡→文档分册、host-chat 软闸文案  
3. Docs 预览包与本修复可一并 commit  
