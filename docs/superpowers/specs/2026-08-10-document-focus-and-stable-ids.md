# 设计：文档工作流的稳定标识与 AI Focus

## 状态

- **Status**：confirmed（用户 2026-08-10 口述确认方向：文档缺标识 → 以 id + 宿主 focus 解决）
- **Related**：
  - Brief 分册 Spec：[`2026-08-10-brief-catalog-shards-design.md`](./2026-08-10-brief-catalog-shards-design.md)
  - Plan / Review：[`../../anvil/plans/2026-08-10-foundry-brief-shards-search-plan.md`](../../anvil/plans/2026-08-10-foundry-brief-shards-search-plan.md)、[`.ai/anvil/reviews/2026-08-10-foundry-brief-shards-search-review.md`](../../../.ai/anvil/reviews/2026-08-10-foundry-brief-shards-search-review.md)
  - 多场景北极星：chips 内嵌 `场景｜scene_id`（`gui/src/chat/vtChoiceParse.ts` 等）

## 问题

改代码时，模型和人共享**稳定符号**（文件路径、类名、函数名）。  
改策划文档 / brief / 北极星时，内容多是**散文与图片**，标识很少。结果是：

1. 模型不知道「该改哪一段 / 哪一屏 / 哪张候选图」。
2. 用户口语（「那个」「水族馆那边」「图不行」）无法可靠对齐到磁盘对象。
3. 宿主若仍把整份厚 draft 塞进上下文，模型更容易改错处或把细则堆回 `description`。

典型事故：多场景北极星「选用 / 重做」时，若芯片或路由**没有 scene id**，会落成只改元数据、或改错场景。

## 原则（一句话）

**文档也要有符号表：id 是符号，focus 是当前光标；定位由宿主完成，模型只负责在 focus 内读写内容。**

| 角色 | 负责 |
|------|------|
| **id** | 机器唯一句柄（稳定、可进补丁路径与工具参数） |
| **title / 中文名** | 给人看；可改文案，**不能**当唯一键 |
| **focus** | 本轮正在读/写的对象；由 GUI / 审查卡 / 芯片 / 显式 artifact **写入 session**，不靠模型猜 |
| **目录** | 每轮可给薄列表 `{id, title}`，相当于文件树 |
| **search / load** | 无 focus 或要跳转时，用结构化检索按 id 打开分册（非向量） |

## 标识约定

### 必须有稳定 id 的对象

| 种类 | id 示例 | 人读名 |
|------|---------|--------|
| 场景 | `main_hub`, `spot_select` | 主界面、钓点选择 |
| 系统 | `combat`, `economy` | 钓鱼战斗、经济 |
| 资产 | `eel_01`（与 `name` 可同） | 展示名 |
| 北极星候选 | `a` \| `b` \| `c`（相对**当前场景或全局**） | 图 A/B/C |
| 审查缺口 | `aquarium_unlock_flow` | 卡片标题 |
| 数据表（可选） | `data/spot_pools` 或 `systems/economy.tuning` | 表说明 |

补丁与工具路径一律带 id，例如：

- `project.scenes[id=spot_select].notes`
- `upsert_scene` / `upsert_system` 的 `id` 字段
- `brief shard load --kind scene --id spot_select`
- 北极星芯片：`选用北极星 a（场景：…｜spot_select）`

### Session focus 形状

```json
{
  "kind": "scene | system | asset | visual_target | intent_gap | project | data",
  "id": "spot_select",
  "extra": { "candidate": "a" }
}
```

- `kind=project`：只讨论门面简介（短 `description` / loop），不打开某分册正文。
- `visual_target`：`id` = scene id 或约定的 `global`；`extra.candidate` 可选。
- `intent_gap`：`id` = 审查缺口 id；写回仍走该缺口的 `write_paths`。

## 宿主纪律（强制）

1. **用户点击即钉 focus**  
   看板场景条、审查缺口卡、北极星「重做/选用」芯片、侧栏场景列表等 → 写入 `session.focus`（及 VT 专用 focus 若并存，须同 id）。

2. **本轮上下文按 focus 组装**  
   - 常驻：薄目录（scenes/systems/assets 的 id+title）+ 短项目简介。  
   - 附加：当前 `focus` 对应分册 / 缺口 / 北极星状态。  
   - **禁止**无 focus 时注入全部场景/系统正文。

3. **无 focus 禁止瞎改**  
   用户说「改一下」「图不行」且宿主无法从 UI/芯片/指称解析出 id → **先澄清或弹出选择**，本轮 `brief_patches` 应为空（或仅允许改 focus 本身）。

4. **写出必须回写同一 id**  
   - Catalog 工程：upsert 某 scene → 写 `scenes/<id>.json`，索引只留映射。  
   - 补丁 path 与 focus.id 不一致 → 宿主拒绝或要求确认。

5. **模型不得「发明定位」**  
   Skill 写明：定位以 payload 里的 `focus` / 工具返回的 `{kind,id}` 为准；禁止凭记忆改未加载分册。

## 与现有子系统的关系

### Brief 分册 + 结构化搜索

- 分册把正文拆开；**focus + id** 决定打开哪一册。  
- `brief search` 返回命中的 `{kind,id,path,snippet}`，供跳转 focus，**不是**替代 id。  
- 详见 catalog/shards Spec。

### 多场景北极星

- 已部分落地：选择/重做芯片携带 `｜scene_id`；restyle 路由钉住场景。  
- 仍须保证：相关聊天轮的 host payload / sticky 与 `session.focus`（或 VT focus）**同一 scene id**，避免「口头全局、实际某屏」。

### 制作审查

- 缺口自带 id + `write_paths`（可含多处 scenes/systems）。  
- 答题卡应设置 `focus.kind=intent_gap`（并可选同时 focus 主 canonical scene/system）。  
- **禁止**为过审把系统细则抄回 `description`。

## 反模式

| ❌ | ✅ |
|----|----|
| 只靠中文标题当键 | 标题可变；键用 id |
| 整份 draft 每轮灌给模型「让它自己找」 | 目录 + focus 分册 |
| 「都不满意」不带场景 | 芯片/宿主钉 `scene_id` |
| 模型空口说「已写入某某场景」 | 必须有同 id 的 patches / 工具写盘 |
| 把表级数值写进项目 description | 写入 `systems/<id>` / `data/<id>` |

## 实现清单（对照进度）

| 项 | 状态（2026-08-10） |
|----|-------------------|
| 场景/系统/资产 id 与 upsert-by-id | 已有 |
| 审查 `target_paths` / gap id | 已有 |
| VT 芯片嵌入 scene id | 已有 |
| Brief catalog + shard 文件 + search CLI | 已有（平台） |
| `session.focus` 注入主对话 payload | 已有；**生产路径已接 GUI / 审查钉 focus** |
| brief Pi 白名单 `brief search` / `shard load` | **已放行（P0）** |
| Catalog 下 upsert 写分册文件 | **已做（P1）** |
| 宿主 related_shards 注入 + `brief related` CLI | **已做**；用户确认「一并改」时 related 可写 |
| 无 focus 拒写 | **已做（P1）** |
| GUI 点选场景 → 写 focus | **已做（看板场景条 + VT restyle/pick）** |

**P0（策划读闭环）**：白名单放行只读 search/load；GUI/审查/芯片写入 `session.focus`；skill 与真实工具一致。  
**P1**：catalog upsert 写分册；无 focus 拒写；超长 description / gameplay_loop 注入截断（已做）。

## 验收句

1. 用户只点 UI、不打字 id 时，本轮 payload 仍带正确 `focus.id`。  
2. 无 focus 时模型无法静默改某一 scene/system 正文（宿主拦或先追问）。  
3. 北极星选用/重做在嵌套中文标题下仍解析到正确 `scene_id`。  
4. 补丁 path / upsert id 与 focus 不一致时有明确失败或确认，不Silent 写错册。

## 非目标

- 不用向量库做「语义猜你想改哪」。  
- 不强制用户记忆 id（UI 展示 title，内部传 id）。  
- 不在本文展开 GUI 线框；实现跟 Anvil plan / review 走。
