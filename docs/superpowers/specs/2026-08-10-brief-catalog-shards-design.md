# Brief 目录化 + 场景 / 系统 / 资产分册

## 状态

- **Status**：confirmed（用户 2026-08-10 确认 spec）
- **Related**：[`docs/ITERATIVE-PRODUCTION.md`](../../ITERATIVE-PRODUCTION.md) Design vs Production；brief 场景/系统清单可进一步拆盘（见本 Spec）

## 背景

- Brief 同时承担「游戏意图」与「场景/系统/资产正文」，体积膨胀；host-chat 每轮灌整稿，策划一轮可达数分钟。
- 生图需要图级契约（空/满底图、画幅、动静母版），不宜堆进 `project.description`。
- 若 brief 与分册**两边都写正文**，补丁冲突概率高；用户要求索引**只保留映射**。

## 目标

1. `brief.json` / `brief.draft.json` 退化为：**短产品描述 + 目录映射**（id、显示名、path）。
2. 场景 / 系统 / 资产**正文唯一**落在工程内分册文件。
3. 读内容只信分册；索引与分册不一致时 **validate 失败或明确要求修复索引**，不静默双源合并。
4. host-chat / 生图 / 写码按 **focus 只加载相关分册**，缩短回合耗时。
5. 提供迁移：把现有内嵌 scenes/systems/assets 正文搬出，brief 收成映射。

## 非目标（v1）

- 不重做大型 GUI Brief 编辑器（CLI + host-chat 纪律即可；GUI 最小展示索引）。
- 不强制第三层独立全局数值库（数值表先放在 `systems/<id>.json`）。
- 不一次改完所有 Godot 手写路径；pipeline / resolve 改为「读映射 → 打开分册」。
- 不要求旧工程自动在打开时迁移（显式 migrate 命令 / 导出前检查）。

## 原则

| 规则 | 说明 |
|------|------|
| 单源正文 | 按钮、跳转、tuning、生图 Spec 等**只**在分册 |
| Brief = 目录 | `scenes` / `systems` / `assets` 条目仅含映射字段 |
| 冲突 | 分册为权威；索引 path 缺失或 id 不一致 → 错误，不猜 |
| 兼容读 | 无分册、仍为旧内嵌厚 brief 时：v1 **可读旧格式**并告警；**新写入**只写分册+映射 |

## 目录布局

```text
projects/<slug>/
  brief.json                 # 或 brief.draft.json — 薄目录
  scenes/<id>.json           # 场景正文
  systems/<id>.json          # 系统正文 + tuning
  assets/<id>.spec.json      # 资产 / 生图 Spec
```

外置工程：同样相对 `project_root`。

### Brief 索引条目（唯一允许字段）

**Scene ref**

```json
{ "id": "aquarium_hall", "title": "Aquarium hall", "path": "scenes/aquarium_hall.json" }
```

**System ref**

```json
{ "id": "economy", "title": "Economy", "path": "systems/economy.json" }
```

**Asset ref**（顶层 `assets[]`）

```json
{ "id": "eel_01", "name": "eel_01", "path": "assets/eel_01.spec.json" }
```

- `id` 必填；scene/system 用 `title`，asset 用 `name`（与现网 AssetSpec.name 对齐，可与 id 相同）。
- `path` 必填，相对工程根，POSIX `/`。
- **禁止**在索引上再挂：`summary`、`notes`、`ui_panel_ids`、`visual_reference`、`display_size`、`type`、`usage` 等正文/施工字段（全部进分册）。
- `project.description` / `gameplay_loop` / `session_goal` / viewport 等**项目级**短字段仍留 brief。
- **简介纪律（用户 2026-08-10 确认）**：玩法细则、屏级交互、数值表、鱼种/钓点名单、UI 实现方案**不得**堆进 `description` / 长 `gameplay_loop`；应落在 **scenes / systems / 数据表（tuning 或独立 data 分册）**。`description` 只保留类型、一句话循环、画风一句、无终局目标等门面信息（建议硬预算，见 Plan）。

### 分册最小形状（v1）

**`scenes/<id>.json`**

- `id`, `title`（与索引一致）
- `summary?`, `notes?`
- `ui_panels?` 或按钮/跳转列表（具体键名实现时对齐现有 ui_panels 习惯）
- `asset_ids?`：本屏引用的资产 id
- `plate_fill?`：`empty` | `sparse` | `dense`（屏级默认，可被资产 Spec 覆盖）
- `visual_reference?`：北极星路径（从现 scene 内嵌迁出）

**`systems/<id>.json`**

- `id`, `title`
- `summary?`, `notes?`（规则说明）
- `tuning?`：数值表 / 日衰减等对象或数组（**不**再拆第三层，除非多系统共享再引入 `_shared_tuning.json`）

**`assets/<id>.spec.json`**

- 现有 AssetSpec 权威字段：`id`/`name`, `type`, `usage`, `display_size`, `generate_method`, `scene_ids?`, `system_ids?`, …
- 新增图级契约（可渐进）：`motion_intent`, `frame_aspect`, `plate_fill`, `depth_role`, `compose_mode`, `overlay_policy`, `negative_hard`

## 运行时解析

```text
load_brief_catalog(brief)
  → refs only
load_scene(project_root, ref) → read JSON at ref.path
load_asset_spec(...) → read spec; used by pipeline plan / prompt craft
```

- `brief validate`：每个 ref 的 path 存在；分册内 `id` 与索引 `id` 一致；旧厚 brief 无 path 时走 legacy 路径并 warning。
- Pipeline / visual-target：需要资产正文时 **打开 spec**，不从 brief.assets 读 type。

## Host-chat / 性能

1. 会话携带 `focus`：`{ kind: scene|system|asset|project, id }`。
2. 每轮 user payload：**薄 brief 索引** + **短 description/loop** + **当前 focus 分册全文**（非 focus 不注入正文）。
3. 写入：默认只 patch 当前分册；新建则写分册 + append 索引映射；**拒绝**把场景/系统/表级细节写回 `description`。
4. **禁止**再输出整份厚 `draft_brief` 内嵌 assets/scenes/systems 正文（迁移完成后）；过渡期宿主拒绝写入索引上的禁止字段。

## 结构化搜索（v1，非向量）

- CLI / host-chat 工具：`brief search --q …`（及等价内部 API）。
- 在工程根下检索：薄目录标题/id + 各 scene/system shard 正文 + 可选 `data/` 表文件；按命中返回 `{kind,id,path,snippet}`，**不**把全部分册灌进模型。
- 模型工作流：看目录 → search → `load_shard(kind,id)`；不用 embedding / 向量库（v1 明确非目标）。

## 迁移

命令（名称实现定）：`brief shard migrate --brief …` 或 `project migrate-shards`：

1. 读现 brief/draft。
2. 对每个内嵌 scene/system/asset：写出分册文件。
3. 将 brief 对应数组替换为 `{id,title|name,path}`。
4. 保留 backup（如 `brief.pre-shard.json`）。

不自动在每次打开时迁移。

## 验收

1. 新工程：brief 仅映射；分册可独立编辑；validate 检查 path/id。
2. 迁移 fishing（或合成样例）：正文不在 brief；pipeline 仍能 resolve 至少一个 asset spec。
3. host-chat 单测或夹具：focus=scene 时 payload **不含**其他 scene 正文。
4. 旧厚 brief：仍能 validate（warning），文档说明需 migrate。
5. AI-HANDOFF / ITERATIVE 短注：Brief=目录；分册=正文。

## 实现分期（供 plan）

可执行任务清单（取代旧 shards-only plan）：[`docs/anvil/plans/2026-08-10-foundry-brief-shards-search-plan.md`](../../anvil/plans/2026-08-10-foundry-brief-shards-search-plan.md)

| 期 | 内容 |
|----|------|
| P0 | 分册 IO + normalize + validate；legacy 读 |
| P1 | migrate + description/loop 瘦身规则与告警 |
| P2 | 结构化 search + load_shard |
| P3 | host-chat focus 注入/写入；禁双写 description |
| P4 | pipeline / prompt craft；文档与 skills |

## 开放点（实现时可定默认）

- Asset 索引是否同时保留 `name` 与 `id`（默认两者都有，可相同）。
- `ui_panels` 全局列表：v1 建议挂在**主场景分册**或 `scenes/_ui.json`，不回灌 brief。
- 外置工程 path 与 `external:` brief key 的拼接规则（跟现 `project_paths`）。
- `description` 硬预算默认：**800 字符**；`gameplay_loop` 默认：**1200 字符**（超限 = validate warning，export 不硬拦；enrich/host 写入时拒扩）。
- `data/` 目录：v1 可选；名单/倍率可先放 `systems/*/tuning`，多表共享时再引入 `data/<name>.json`。
