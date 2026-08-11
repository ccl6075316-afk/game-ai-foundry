# 设计：人侧文档预览（总览 + 分册，与对话 focus 解耦）

## 状态

- **Status**：confirmed（用户 2026-08-11：总览默认；预览浏览 ≠ focus；钉住才同步；看板/VT/审查 pin 自动跟上预览）
- **Related**：
  - Brief 分册：[`2026-08-10-brief-catalog-shards-design.md`](./2026-08-10-brief-catalog-shards-design.md)
  - 文档 focus / 稳定 id：[`2026-08-10-document-focus-and-stable-ids.md`](./2026-08-10-document-focus-and-stable-ids.md)
  - 平台包评审 Suggestions：GUI 常驻 focus、侧栏展开分册

## 问题

Catalog 化后，GUI「Brief 工作草稿」仍用 `formatBriefDocument(session draft)` 渲染薄索引。人打开侧栏只见 id/title，正文在 `scenes/`、`systems/`、`assets/*.spec.json`，**像目录被掏空**。

机器侧已按 focus / hydrate 读分册；**人侧预览未跟**，且评审要求的「常驻 focus 指示」未落地。

## 原则（一句话）

**人看文档 = 总览目录 + 可随意打开的分册预览；对话光标 = `session.focus`。二者默认可不同；只有显式「钉住」或看板/审查等已有 pin 才对齐。**

| 角色 | 负责 |
|------|------|
| **总览** | 简介 / loop / art 门面 + 场景·系统·资产 id+title 清单 |
| **预览光标（view）** | 文档栏当前打开的对象：`overview` 或 `{kind,id}`；**不写** session |
| **对话焦点（focus）** | `session.focus`；决定下一轮模型上下文与写闸 |
| **钉住** | 把当前 view 写成 focus（或清空） |
| **外部 pin** | 看板 / VT / 审查已有 `pinBriefFocus` → **同时**把文档 view 切到同 id |

## 产品决策（已钉）

1. 默认第一眼：**总览目录**（不是整本 hydrate）。
2. 点目录项：**只换预览**，不改 `session.focus`（随便看看不误钉）。
3. 显式 **「钉住给对话」** 才 `hostChatFocus`。
4. 看板 / 北极星 / 审查卡 **pin 时，文档预览自动跟上**。
5. 顶栏同时显示 **正在看** 与 **对话焦点**（可不同）。
6. 不一次把全部分册灌进预览；资产默认目录，可点开单册。

## UI 行为

### Brief 工作草稿（主路径）

```
┌─────────────────────────────────────────┐
│ 正在看：总览 / 场景 main_hub            │
│ 对话焦点：未钉住 / scene · main_hub     │
│ [← 总览]  [钉住给对话]                  │
├─────────────────────────────────────────┤
│ 总览时：门面 + 可点目录                 │
│ 分册时：该 shard 可读正文（JSON/格式化）│
└─────────────────────────────────────────┘
```

- **← 总览**：view 回到 overview；不改 focus。
- **钉住给对话**：
  - view 为分册 → `pinBriefFocus(kind, id)`
  - view 为总览 → `clear` focus（或 pin `kind=project`，实现时与现有 API 对齐；优先 clear / project）
- 目录行点击：加载分册 → 更新 view；**禁止**隐式 pin。

### 外部 pin → 预览跟随

`pinBriefFocus` 成功且 kind ∈ `{scene, system, asset}`（及约定的 visual_target→scene id）时：

- 若文档栏当前选中的是 Brief 工作草稿（或可切换到它），将 **view** 设为同 `{kind,id}` 并加载分册。
- 不强制用户离开磁盘 md/json 选中项时：若当前选中非 session-brief，可仅更新「若回到 Brief 时的 view」状态，或轻提示「对话已钉住 xxx」——实现优先：**若在 session-brief 则立即跟；否则记下 pending view，切回 Brief 时应用**。

### 磁盘列表（次要）

现有 `listProjectDocs` / `brief.zh.md` 等保持。不强制把全部 `scenes/*.json` 塞进主列表；主入口是总览内点选。若列表已含分册文件，打开行为与「预览 view」可互通（可选，不挡 MVP）。

## 数据与 API

### 前端状态（session 本地）

```ts
type DocsView =
  | { mode: "overview" }
  | { mode: "shard"; kind: "scene" | "system" | "asset"; id: string };
```

- 与 `status.focus` 独立。
- 外部 pin / 「钉住」只通过现有 `hostChatFocus` 改 focus。

### 读分册

优先复用 CLI：`brief shard load --kind --id`（或 IPC 薄封装返回 JSON）。  
失败时预览区显示错误（对齐后端 `focus_error` 精神），不静默空白。

### 总览渲染

扩展 `formatBriefDocument`（或并列 `formatBriefCatalogOverview`）：

- 场景/系统：可点击的 id + title；无正文则标注「分册」。
- 资产：薄目录；点击加载 `assets/<id>.spec.json`（若工程为 catalog）。

## 非目标

- 不改变模型侧 `build_focus_context` / 写闸语义。
- 不做整本 hydrate 给人看的「迁册前体验」复刻。
- 本轮不拆 `host_chat` 大模块。
- 不强制 ui_wireframe hydrate。

## 验收

| # | 场景 | 期望 |
|---|------|------|
| 1 | 打开 Brief 工作草稿 | 见门面 + 目录，非空心无说明 |
| 2 | 连点多个场景 | 预览切换；`session.focus` 不变；无明显卡顿 |
| 3 | 点「钉住给对话」 | `status.focus` 与顶栏「对话焦点」一致 |
| 4 | 看板钉场景 | 在 Brief 草稿视图下预览自动打开该分册 |
| 5 | 分册缺失 | 可见错误文案，非空白成功态 |
| 6 | 单测 / 组件测 | 总览格式化；view≠focus；钉住调用 focus API（可 mock） |

## 实现提示（供 plan）

| 区域 | 可能触点 |
|------|----------|
| GUI | `DocsPreviewPanel.tsx`、`briefPreviewFormat.ts`、`App.tsx`（pin 后同步 view） |
| IPC | 可选 `briefShardLoad`；或复用现有 CLI invoke |
| 测 | `briefPreviewFormat.test.ts` + Docs 面板轻测 |

## Resume

1. ~~Spec 用户确认~~ **done**  
2. ~~实现计划 + GUI~~ **done**（`DocsPreviewPanel` 总览/分册预览；`status.focus` 跟随；钉住/清空）  
3. 手动验收（文档侧栏连点分册、钉住、看板 pin）→ 可选 commit  
