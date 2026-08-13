# 中文 Brief + 废弃 brief.zh.md 设计

**状态：** confirmed（用户 2026-08-14 确认方案 A）  
**范围：** Foundry 语言策略、`brief.zh.md` 管线移除、prompt-crafter 二次生成、当前工程一次性英→中迁移

## 问题

拆分册之后，叙事字段强制英文再靠 `brief.zh.md` 做人读镜像，变成持续翻译税。除最终生图 prompt 外，中文叙事没有实质障碍；`id` 英文 slug 已覆盖路径/编码硬约束。

## 目标

1. Brief / 分册**叙事中文优先**（人写人审）。
2. **删除** `brief.zh.md` 生成与产品入口；人读走文档栏分册预览。
3. **prompt-crafter** 对中文 brief 做**二次生成**，输出英文结构化字段再 assemble；brief 原文不是最终 prompt。
4. 对当前工程（至少 fishing-2d）**一次性**把英文叙事翻成中文写回分册。

## 非目标

- 另做新的中文导出 Markdown 替代品。
- validate / export 因「字段仍是英文」失败（不做语言硬校验）。
- 全仓库自动扫所有历史工程。
- 改生图 Provider HTTP API。
- 放宽 `id` 英文 slug 规则。

## 语言边界

| 层 | 语言 | 说明 |
|----|------|------|
| `id`、磁盘路径、pipeline task 前缀 | 英文 slug | 硬约束，不变 |
| `name` / `title`；project / scene / system / asset 叙事（`description`、`art_direction`、`gameplay_loop`、`session_goal`、`summary`、`notes`、`usage_description` 等） | **中文优先** | 新写默认中文；旧英文一次性迁成中文 |
| 对用户对话 | 中文 | 不变 |
| prompt-crafter 输出 / handoff `prompt`（及 structured English fields） | **英文** | 二次生成 |
| `brief.zh.md` | **废弃** | 不再生成；不再作为人读主入口 |

技术枚举（`type`、`content_class`、`view`、`generate_method` 等）保持现有英文取值，不因本设计改为中文。

## 删除 brief.zh.md 管线

### CLI / 宿主

- 移除：`brief zh-doc`、`brief chat zh-doc`、export 默认写 zh、host persist 刷新 zh skeleton。
- 移除 IT / Pi 白名单与剧本中的「生成中文说明」/ `zh-doc` 条目。
- 删除 `cli/brief_zh_doc.py` 及依赖测试；调用点改为无操作或删除。
- export 去掉 `--skip-zh-doc`（无 zh 可 skip）。

### GUI

- Docs 面板「生成中文说明」按钮与 `zh_doc_*` 结果处理去掉。
- IT 快捷「生成中文说明」去掉。
- 人读入口：文档栏预览中文 brief / 分册（已有 shard preview）。

### 文档

- README / AI-HANDOFF / IT / RELEASE 相关表述删除「导出前 brief.zh.md」。
- Skills：`brief-brainstorm`、`commit-brief`、`host-chat`、`brief-enrich` 等去掉「brief 内用英文」；改为叙事中文优先。

### 已有文件

- 迁移完成后删除工程内 `brief.zh.md`（不强制改写 git 历史）。

## 一次性英→中迁移

- **对象：** 当前绑定工程（至少 `projects/fishing-2d` 或外置 fishing 仓）的 brief 叙事 + catalog 分册正文。
- **改：** 上表叙事字段。
- **不改：** 全部 `id` / `path` / 技术枚举。
- **形式：** CLI（如 `brief localize`）或受控脚本 + LLM，写回分册；成功后删该工程 `brief.zh.md`。
- **不做：** 语言硬校验；全仓盲扫。

## prompt-crafter 二次生成

- **输入：** 可为中文的 brief / 分册 / asset spec。
- **输出：** 英文 structured fields → 现有 Python `assemble_*` → handoff `prompt`。
- **纪律（skills + 实现）：** 禁止在 LLM craft 开启时把中文 `description` / `art_direction` **未经英文化改写**直接拼进最终 prompt。
- **北极星 craft：** 同样中文 brief → 英文 visual fields。
- **LLM craft 关闭时的 fallback：** 实现计划选定其一并写死——（推荐）最小英文改写或明确降级警告；本设计要求**有 LLM craft 时字段必须英文化**。

## 验收

1. 新写 / enrich：技能与宿主文案要求叙事中文；`id` 仍英文 slug。
2. 不再出现默认生成的 `brief.zh.md`；GUI/IT 无「生成中文说明」主路径。
3. `prompt craft`（LLM on）对中文 description 的资产产出英文 handoff prompt（抽检或单测夹具）。
4. fishing（或约定工程）叙事字段已中文；`brief.zh.md` 已删或不存在。
5. 相关单测 / IT 白名单测更新并通过。

## 实现分期（供 plan）

| 期 | 内容 |
|----|------|
| P0 | Skills + 文档语言策略；删 zh 写入路径与 GUI/IT 入口 |
| P1 | 删/停 `brief_zh_doc` 模块与 CLI；修测试 |
| P2 | prompt-crafter skills + assemble 守卫（中文不直出） |
| P3 | 一次性 localize 命令/脚本；迁 fishing；删旁路 zh |

## 开放点（实现默认可定）

- localize 命令名与是否进正式 `brief` CLI（默认：`brief localize`，需 `--i-confirm`）。
- LLM-off fallback 的具体行为（默认：组装前若检测到主要字段含 CJK，打警告并尽量不直出；或拒绝 craft——plan 里选一）。
