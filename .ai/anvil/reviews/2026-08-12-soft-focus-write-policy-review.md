---
review_date: "2026-08-12"
module: "Host Chat soft-focus write policy"
commit_hash: "WORKTREE"
reviewer: "anvil-lead"
status: "passed"
karpathy_score: 4
---

## 评审摘要

- **范围**：删除 focus 写闸与 related allowlist，使 focus 仅作为上下文提示；核对破坏性写入、路径和 schema 安全边界。
- **变更文件**：`cli/host_chat.py`、`cli/test_host_chat.py`、相关 Anvil plan/spec 与 `resources/skills/orchestrator/host-chat.md`。
- **测试覆盖**：soft-focus / patch safety / shards 相关 171 项通过；全量 CLI 847 项中 1 项因仓库缺少 `resources/magic-prince-brief.json` 报错，另有 2 项跳过。
- **Loaded standards**：`anvil/rules/karpathy.md`、`anvil/skills/review/SKILL.md`。

## 自动化预检

| 检查项 | 状态 | 备注 |
|--------|------|------|
| Lint | ✅ | IDE diagnostics：0 errors |
| 类型检查 | N/A | 本次 Python 变更无独立类型检查命令 |
| 单元测试 | ✅ | 相关 171 项通过；全量唯一错误为既有缺失 fixture `resources/magic-prince-brief.json` |
| 安全扫描 | ✅ | 无新增依赖、密钥、外部输入执行或敏感日志 |

## Karpathy 四原则

| 原则 | 评分 | 发现 |
|------|------|------|
| Think Before Coding | ✅ | patch 先规范化、校验最终候选并快照，再执行事务写入 |
| Simplicity First | ✅ | 删除正则、allowlist 和写闸显著降低复杂度 |
| Surgical Changes | ✅ | 代码和文档主要围绕 soft-focus 政策变更 |
| Goal-Driven Execution | ✅ | canonical identity、并发回滚、结构路径与 inline/catalog 合并均有回归覆盖 |

## 发现项

### 🔴 Critical

无。

### 🟠 High

#### H1（已修复）— 任意 `set` 可执行未经确认的整表删除、稳定 id 重命名和非法 path 写入

- **证据**：`cli/host_chat.py:2468-2475` 把 `id` / `path` 当作普通 index 字段写入；`cli/host_chat.py:2530-2547` 对未匹配的 path 直接调用 `_set_path_value`。
- **复现**：
  - `{"op":"set","path":"project.scenes","value":[]}` 会清空全部场景；
  - `{"op":"set","path":"project.scenes[id=hall].id","value":"dock"}` 会留下 `id=dock` + `path=scenes/hall.json` 冲突；
  - `{"op":"set","path":"project.scenes[id=hall].path","value":"../escape.json"}` 会接受非法 catalog path。
- **影响**：soft-focus 放开后，无 focus 和跨 focus 请求也可触发这些破坏性补丁；这违反确认需求中“非法路径、id/path 冲突、未经确认的删除/重命名仍应阻止”。
- **要求**：在应用任何补丁和写 shard 前统一验证 op/path；默认拒绝集合整体替换、稳定 id/path 修改，除非存在单独的显式确认协议。
- **修复状态**：✅ 已增加统一预检；拒绝受保护 root/集合、空路径段、稳定 `id/path` 修改；按资产名称匹配会解析并保留已有稳定 id。

#### H2（已修复）— typed upsert 信任调用方 `path`，可把 scene 写入 systems

- **证据**：`cli/host_chat.py:2625-2663` 的 `kind_for_path` 来自 `op`，但 `_upsert_list_catalog_ref` / `_upsert_list_item` 使用调用方传入的任意 `path`。
- **复现**：`{"op":"upsert_scene","path":"project.systems","match":{"id":"hall"},"set":{"notes":"x"}}` 会在 `project.systems` 插入 `hall`；catalog 模式还可能把 `scenes/hall.json` 的引用放进 systems 索引。
- **影响**：生成跨类型 catalog 映射，直接破坏稳定 id/path 约束。
- **要求**：shorthand op 必须拒绝非 canonical path；或完全忽略其外部 `path`。
- **修复状态**：✅ typed op 强制 canonical path；generic scene/system `upsert_list` 走 shard 路由并保持薄索引。

#### H3（已修复）— schema 错误会先写入 shard，未被阻止或回滚

- **证据**：`cli/host_chat.py:2548-2562` 在 schema 校验前调用 `upsert_shard_body`；函数最终只执行 description guard（`cli/host_chat.py:2666`）。
- **复现**：对 catalog 资产执行 `upsert_asset`，把 `type` 设为 `not_a_real_type` 后，`assets/<id>.spec.json` 已持久化该非法值。
- **影响**：后续 readiness/审查即使发现错误也无法保证磁盘原子性，违反“schema 错误仍被拒绝”。
- **要求**：补丁先应用到纯内存完整 draft 并验证，再原子写入分册；失败时不得留下部分写盘。
- **修复状态**：✅ 资产批次按最终候选运行 `AssetSpec` + content-class 校验；写前加载目标 catalog ref；运行时异常按写前快照回滚所有已触及 shard。

#### H4（已修复）— 动态新增资产的实际写入路径未进入快照，失败后遗留 shard

- 同批先 `add_asset(id=a,name=N)`，再按 `name=N` upsert，预检按原 draft 快照 `assets/N.spec.json`；运行时按新条目解析为 id `a` 并写 `assets/a.spec.json`。
- 后续 patch 失败时，事务只删除前者，实际新 shard 残留。
- **要求**：预检、快照和执行必须共享同一批次模拟状态与 canonical target id/path。
- **修复状态**：✅ `add_asset` 先规范化为稳定 id-based upsert；后续校验、快照和执行共同消费 normalized patches。

#### H5（已修复）— 批内 name 冲突使预检目标与执行目标分裂，可绕过最终 schema 校验

- A 在前一补丁改名为 B；后一补丁按 `name=B` 修改时，预检基于原 draft 验证原 B，执行却按当前列表顺序命中 A。
- 结果可能把仅为 B 验证过的字段写入 A，并产生非法 schema 或重复显示名。
- **要求**：禁止有歧义的 name-only match，或在单一模拟状态中解析为唯一稳定 id；同时提供冲突 id/name 时必须拒绝。
- **修复状态**：✅ 批内 identity 按顺序维护；name-only 必须大小写不敏感地唯一命中，id/name 冲突和重名均在写前拒绝。

#### H6（已修复）— Catalog 工程的 `add_asset` 把正文直接追加进薄索引

- `_apply_brief_patches_unchecked` 的 `add_asset` 直接 append `value`，不创建 `assets/<id>.spec.json`。
- 已有 catalog ref 时，新资产的 `type/description/...` 留在索引，违反薄 catalog 不变量。
- **要求**：catalog 模式的新增资产必须创建 shard 并只追加 canonical thin ref。
- **修复状态**：✅ catalog add 经 canonical upsert 创建 `assets/<id>.spec.json`，索引仅保留 `{id,name,path}`。

#### H7（已修复）— Scene/system ID 大小写语义不一致，可迁移或覆盖错误 shard

- `_find_catalog_entry` 精确匹配 id，而执行层 `_match_record` 大小写不敏感。
- 已有 `hall` 时 upsert `HALL` 会被当作新 catalog target，但索引更新又可能命中旧行；在大小写不敏感文件系统上可能覆盖原 shard 并丢失未补字段。
- **要求**：scene/system match.id 必须使用 canonical 小写稳定格式；大小写变体与现有 id 冲突时在写前拒绝。
- **修复状态**：✅ typed/generic upsert 与 set selector 均强制 canonical stable id；shard body id 还会与目标 id 交叉校验。

#### H8（已修复）— 并发事务回滚可擦除另一笔已成功提交的修改

- 两轮同时快照同一 shard；B 成功提交后，A 后续失败仍按旧快照回滚，会把 B 的成功写入恢复成旧值。
- 当前事务没有项目级锁、版本检查或 compare-and-swap。
- **要求**：同一 project root 的 patch 事务串行化，或回滚前验证文件仍等于本事务最后写入版本。
- **修复状态**：✅ 同一 project root 的规范化、预检、快照、写入和回滚由项目级 RLock 完整串行化；磁盘当前 shard 优先于 stale draft。

#### H9（已修复）— `title.*` 等结构非法路径会破坏 shard，且漏入回滚快照

- `project.scenes[id=hall].title.text` 未被当作稳定/index 字段拒绝，会把标量 title 写成对象或字符串化对象。
- `_touched_shard_paths` 又排除首段为 `title` 的所有子路径，因此后续失败时该写入不在快照中。
- **要求**：`id/title/path` 仅允许完整字段写入；任何子路径必须拒绝，快照排除规则也只能匹配完整字段。
- **修复状态**：✅ `title.*` 与稳定字段子路径写入在预检拒绝；精确 title 写入同步更新索引和 shard。

### 🟡 Medium

#### M1（已修复）— 两份当前 spec 对安全边界自相矛盾，且 Code Status 过早标记 done

- `docs/superpowers/specs/2026-08-10-document-focus-and-stable-ids.md:83,140` 和 blast-radius spec 第 42 行声称路径、id/path、schema 安全仍由宿主阻止。
- blast-radius spec 第 50 行又把删除/重命名确认策略列为“另行设计”，而当前代码实测未满足前述验收。
- **要求**：先确定最小安全策略并写入同一事实源；代码和负向测试满足后再标记 done。
- **修复状态**：✅ 两份 spec 已统一为“focus 只提示，patch 安全预检独立强制”。

#### M2（已修复）— 合法 `add_asset` + 增量 upsert 批次被误拒

- upsert 候选只从原 draft 构造，没有吸收同批 `add_asset` 的 `type/name`。
- 先新增合法资产、再只补 `usage` 会错误报缺少 `type`。
- **修复状态**：✅ add 与后续 upsert 合并到同一最终候选后校验。

#### M3（已修复）— generic scene/system upsert 允许 name-only match 形成重复稳定 id

- `upsert_list(project.scenes, match={"name":"hall"})` 可创建第二个 `id=hall` ref，并混入不属于 scene identity 的 `name`。
- scene/system generic upsert 应强制唯一 `match.id`。
- **修复状态**：✅ scene/system typed 与 generic upsert 均强制 `match.id`。

#### M4（已修复）— 非法新 id/path 可在事务快照阶段以裸 `ValueError` 逃逸

- `_catalog_shard_path_for_patch` 在事务 `try` 外解析默认路径；例如新 scene id=`../escape` 会抛 `ValueError`。
- 主聊天只按协议捕获 `HostChatError`，因此可能中断整轮而不是返回“补丁未应用”。
- **修复状态**：✅ 规范化、预检、路径解析和快照阶段的结构异常统一转换为 `HostChatError`。

#### M5（已修复）— 资产 id/name 跨字段冲突未被拒绝

- 当前仅检查 id-id 与 name-name 冲突；已有 `{id:"rod",name:"bait"}` 时仍可新增 `{id:"bait",name:"hook"}`。
- 下游按 `"bait"` 查找时可能命中旧资产 name，而不是新资产 id，导致目标错误。
- **要求**：identity 命名空间应统一执行大小写不敏感的 `new.id ↔ existing.id/name`、`new.name ↔ existing.id/name` 冲突检查。
- **修复状态**：✅ id/name 使用统一 casefold identity 命名空间；新增、匹配与重命名均拒绝跨字段冲突和歧义。

#### M6（已修复）— 新资产 id 缺少稳定格式校验

- `AssetSpec.from_dict` 不校验 id；`a/b`、`A`、`two words` 等值可进入 catalog，并生成嵌套或非 canonical shard path。
- **要求**：新增资产和新目标 upsert 必须满足稳定 id 规则（如 `^[a-z][a-z0-9_]*$`），失败时不得创建 shard 或修改索引。
- **修复状态**：✅ 新 add/upsert 目标强制 `^[a-z][a-z0-9_]*$`，非法 id 在路径解析和写盘前拒绝。

#### M7（已修复）— inline 资产使用浅合并，与预检和 catalog 深合并语义不一致

- 预检候选和 catalog shard 使用递归深合并；inline 执行仍使用 `dict.update`。
- 连续修改 `display_size.width` / `height` 时，预检通过但 inline 最终可能只保留后一半字段，静默丢数据。
- **要求**：inline `upsert_asset` 应复用 `_deep_merge_patch_fields`，并增加 inline/catalog 等价性测试。
- **修复状态**：✅ inline 资产复用深合并；嵌套字段多补丁测试通过。

#### M8（已修复）— Inline scene/system generic upsert 仍使用浅合并

- 相同 `camera/tuning` 嵌套补丁在 inline 模式丢失未触及键，catalog shard 则深合并保留。
- **要求**：`_upsert_list_item` 对 scene/system fields 复用递归深合并，并加入 inline/catalog 等价测试。
- **修复状态**：✅ inline scene/system 与资产统一使用递归深合并。

#### M9（已修复）— Catalog 新资产 upsert 缺少 project_root 时退化为 fat inline

- `add_asset` 已拒绝 catalog 无 root，但同义的新目标 `upsert_asset` 仍会直接追加正文到 assets 索引。
- **要求**：normalized batch 识别新 asset target；catalog 且无 `project_root` 时统一拒绝。
- **修复状态**：✅ catalog 下所有 scene/system/asset 分册写入缺少 `project_root` 时统一拒绝。

### 🟢 Low

#### L1（已修复）— `apply_brief_patches(..., focus=...)` 参数已无行为

- `cli/host_chat.py:2500-2519` 仍接收 `focus`，仅通过 `_ = focus` 消除未使用警告；“context only”注释也不准确，因为该函数不构建上下文。
- **建议**：删除参数及内部调用方传参，避免后续维护者误以为 patch 层仍处理 focus。
- **修复状态**：✅ 参数及调用方传参已删除。

## 修改建议

1. 先补负向测试：整表删除、id/path 改写、op/path 冲突、非法 schema、失败不落盘。
2. 增加单一的 patch 安全预检层；focus 不参与该层。
3. 将 shard 写入改为验证后提交，至少保证单轮补丁失败不留下部分写盘。
4. 对齐两份 spec 的安全边界和状态，再重跑相关测试与全量测试。

## 修复记录

| 轮次 | 修复说明 | 验证 |
|------|----------|------|
| 1 | 增加 destructive/path/schema 预检，删除无效 focus 参数，对齐 spec | 专项与 host-chat 测试通过 |
| 2 | 封堵空路径段与 content-class 绕过 | 新增负向测试通过 |
| 3 | 保留 name-match 稳定 id、generic upsert shard 路由、最终候选校验、事务回滚 | 相关 139 项通过；独立终审无 High/Critical |
| 4 | 全新独立终审发现动态 identity/path 模拟与 catalog add 仍有绕过 | 相关 139 项通过，但 H4–H6 / M2–M4 未修复 |
| 5 | 引入统一批次规范化，修复动态目标、薄索引、name 歧义和异常协议 | 原 3 High / 3 Medium 复现关闭 |
| 6 | identity 比较改为 casefold；新 id+name upsert 固化 display name | 相关 147 项通过；独立终审通过 |
| 7 | 全新独立终审发现跨字段 identity、id 格式与 inline 深合并问题 | 相关 147 项通过，但 M5–M7 未覆盖 |
| 8 | 修复跨字段 identity、stable id 与 inline 深合并 | 原 M5–M7 反例关闭 |
| 9 | 连续 review 修复新建/重命名名称的非空、trim 与 canonical set 一致性 | 相关 154 项通过；终审 PASS |
| 10 | 整体并行审查覆盖核心事务、测试与文档 | 文档 PASS；核心发现 H7–H9 / M8–M9，整体 BLOCK |
| 11 | 修复 canonical 结构 id、项目事务锁、结构路径、scene/system 深合并与 catalog root | 原 H7–H9 / M8–M9 反例关闭 |
| 12 | 连续对抗复审修复 stale draft、mixed/orphan shard、通用 set 类型穿透与 shard 身份错配 | 相关 171 项通过；最终独立验收 PASS |

## 最终结论

- [x] **PASSED** — 允许提交
- [ ] **FAILED** — 提交前必须修复

Focus 现仅作为上下文提示；patch 安全、identity、schema、inline/catalog 一致性与项目级事务边界均已覆盖，当前无阻塞项。
