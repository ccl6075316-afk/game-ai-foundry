# 评审报告：`2026-08-10-foundry-brief-shards-search`

## 元数据

| 字段 | 值 |
|------|----|
| Reviewer | anvil-lead |
| MR / Commit | 未提交工作区（相对 `main` ahead 1 + 未跟踪 brief_shards） |
| Author | `/anvil:code` doers T1–T8 |
| Review Date | 2026-08-10 |
| Status | `CHANGES REQUESTED` |
| Spec | `docs/superpowers/specs/2026-08-10-brief-catalog-shards-design.md` |
| Plan | `docs/anvil/plans/2026-08-10-foundry-brief-shards-search-plan.md`（executed） |

**Loaded standards:** Anvil review skill；无 domain vendor skills 适用。

**变更规模：** Large（新模块 `brief_shards` + brief/host_chat/CLI/docs）

---

## 1. 自动化预检

| 检查项 | 命令 | 结果 | 备注 |
|--------|------|------|------|
| 单元测试 | `python -m unittest test_brief_shards test_host_chat test_brief_scenes_systems test_brief_contract -q` | PASS | 104 tests |
| CLI 冒烟 | `brief search --help` / `brief shard --help` | PASS | |
| fishing 瘦身体积 | `build_focus_context(fishing, None)` | 90k→26k | 仍含 ~6.9k description + 138 资产薄目录 |

---

## 2. 安全扫描

- 分册 path 有 `..` 拒绝（`resolve_shard_path`）— OK。
- `brief search` / `shard load` 只读 — OK。
- migrate 写盘 + backup — OK；勿对用户工程静默 migrate（当前需显式命令）— OK。
- 无新增网络/密钥路径。

---

## 3. Karpathy / 简化

- 无向量库 — 符合 Spec。
- `build_focus_context` + CLI search 职责清晰。
- **问题**：payload note 要求策划用 `brief search`，但 **brief Pi 白名单未放行**（见 Important-1）— 文档与能力不一致。

---

## 4. 发现

### Critical

无（不导致崩溃/越权的确定性缺陷）。

### Important

1. **策划读路径未闭环**  
   - 主对话已用 `build_focus_context`：无 `focus` 时只给场景/系统 **id+title 目录**。  
   - `session.focus` **仅测试写入**，GUI/CLI/`run_turn` **从未设置** → 生产几乎永远没有 `focus_shard`。  
   - skill/payload 写「用 `brief search` / `brief shard load`」，但 `_BRIEF_ALLOWED_PREFIXES` **不含** `("brief","search")` / `("brief","shard","load")`。  
   - **结果**：fishing 类工程策划每轮看不到场景正文，也调不到搜索工具 → 只能瞎猜或把细节写回 description（与目标相反）。

2. **写路径仍是整份 `draft_brief`**  
   - `upsert_scene` / `brief_patches` 仍改内存/磁盘厚 draft。  
   - **无**「按 id 写分册」；migrate 后若再 upsert 带 body，会破坏「索引无正文」纪律。  
   - `persist` 仍整文件写 `brief.draft.json`。

3. **简介预算未真正压住门面**  
   - `audit_intro_budgets` 只 warning；`apply_description_write_guard` 只挡「继续变长」。  
   - fishing 现有 6899 字 description **仍整段注入** thin context（实测 project 段 ~16k）。  
   - `gameplay_loop` 无对等守卫。

### Suggestions

- thin 资产目录 138 条仍占 ~6k；可按 focus.scene 的 `asset_ids` 过滤，或只给 id 列表摘要。  
- enrich / makeability 仍灌全稿 — 可接受为 follow-up，但应在 skill 标明。  
- `load_shard` 失败时 `build_focus_context` 静默 `pass` — 建议留下 `focus_error` 字符串，避免 AI 以为已加载。

---

## 5. 对策划能力 / 其它读 brief 路径的结论

### 现有能力盘点

| 路径 | 现状 | 分册后是否够用 |
|------|------|----------------|
| host-chat 主轮 `current_draft_brief` | 薄目录 + 可选 focus_shard | **缺 focus 设置 + 缺读工具白名单** |
| enrich / makeability / autofix | 仍全稿 | 暂时可用；大工程会继续慢 |
| `brief validate` / export | 走 audit + catalog | OK；catalog 资产靠 resolve |
| pipeline `load_brief_full` | `resolve_asset_specs` | OK |
| Pi FOUNDRY_TOOL（brief） | 无 search/load | **要加** |
| IT `inspect read` | 可读文件 | 可绕路读分册，但策划不该依赖 IT |

### 要不要给 AI id？

**要，而且已经在用，应升成一等公民。**

现网已有：
- `upsert_scene` / `upsert_system` 按 **id**
- 审查 `target_paths`：`project.scenes[id=hall].notes`、`project.systems[id=combat].notes`
- `closed_intent_gap_ids`

分册时代建议钉死：

| 操作 | 标识 | 说明 |
|------|------|------|
| 列目录 | 每轮给 `scenes[]`/`systems[]` 的 `{id,title[,path]}` | 已有 |
| 读一册 | `focus={kind,id}` 或工具 `brief shard load --kind --id` | **需接线** |
| 搜 | `brief search --q` → 返回 `{kind,id,path,snippet}` | **需白名单** |
| 写一册 | `upsert_scene`/`upsert_system` 仍带 **id**；落盘改写 `scenes/<id>.json` | **需写分册** |
| 表/tuning | `systems[id].tuning` 或 `data/<name>.json`，用 **id/name** | 规划中 |

标题可给人看；**机器读写必须以 id 为准**（中文 title 会变、会重）。

### 建议的策划能力改造（下一波，非本 diff 必须一次做完）

1. **读**  
   - 白名单加：`brief search`、`brief shard load`（只读）。  
   - GUI/宿主：用户提到某屏或审查卡带 `scenes[id=…]` 时自动 `session.focus`。  
   - 可选：LLM 输出 `artifact.focus` 本轮切换焦点。

2. **写**  
   - `upsert_scene`/`upsert_system`：若工程已是 catalog，**写 shard 文件**，brief 只保留/更新映射。  
   - 禁止补丁往 catalog 条目塞 `summary`/`notes` 正文（或自动外提）。

3. **表**  
   - v1 继续 `systems/<id>.json` 的 `tuning`；跨系统再 `data/<id>.json`，search 一并扫。

4. **skill**  
   - 明确：「先看目录 id → search/load → upsert 同 id」；禁止把系统细则写进 `description`。

---

## 6. 裁决

**Status: `CHANGES REQUESTED`**

- **基础设施（migrate / search CLI / resolve / 单测）可留**，质量够。  
- **不能宣称「策划已按分册工作」**：focus 未接线、读工具未放行、写仍厚稿、超长 description 仍灌上下文。  

**合并前最低补丁（建议 P0）：**  
1. brief 白名单加入 search + shard load；  
2. 宿主设置 `session.focus`（审查路径 / `artifact.focus` / CLI）；  
3. skill 与 payload note 与真实工具一致。  

**可随后 P1：** catalog 模式下 upsert 写分册；description/loop 注入截断或强制迁出。

---

## 7. Resume

- 用户确认是否先做「P0 策划读闭环」再 commit，或先 commit 基础设施再开 follow-up plan。
