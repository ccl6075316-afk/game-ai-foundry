# 工程 Spec：开放 Provider 账号 + 文/图模型目录

## 执行元数据

- **Status**：confirmed
- **Workflow Stage**：executed
- **Created**：2026-07-28
- **Updated**：2026-07-28
- **Source Of Truth Until**：已落地；GUI/CLI 以代码与 [`GUI-CONFIG.md`](../../GUI-CONFIG.md) / [`TOOLS.md`](../../TOOLS.md) 为准
- **Confirmed By**：user「确认」Spec/Plan；user「实现」
- **Requirements Source**：用户 Grill（开放账号 / `/v1/models` / 自建不进 Agent / custom 迁移 / 视频不做）
- **Background Inputs**：聊天 Apilio 配置；[`GUI-CONFIG.md`](../../GUI-CONFIG.md)
- **Compounded Knowledge**：not yet compounded
- **Resume Point**：已合入主线实现；见 RELEASE-NOTES-UNRELEASED

## 背景输入

- 用户已配置 Apilio（OpenAI 兼容），但 GUI 只有一个 `custom` 槽，模型靠手填。
- Chat 类工具常见能力：多套端点账号 + 从 `/v1/models` 选模型 + 刷新。
- 生图同样需要可选目录，而非只认预设 slug。
- 专业视频 AI 少，用户明确本轮不处理视频。

## 工程理解

当前账号库是**封闭枚举**（`API_PROVIDERS` / `KNOWN_PROVIDERS`），未知 `provider_accounts` id 在 GUI 加载时被丢弃；文本/生图模型多为输入框。执行器（Cursor/Codex）已有「实时模型列表」，但**不覆盖** Foundry Provider 账号与生图。

本需求拆成两块，且必须一起交付才有完整体验：

1. **开放账号**：允许用户自建 OpenAI 兼容账号（id + label + base + key + 默认文/图模型）。
2. **模型目录**：对账号调用 `GET {api_base}/models`（或等价），在 Provider 与「绑定该账号的模型字段」提供可刷新下拉；失败可手填。

**硬边界**：自建账号**不进入** Pi / Hermes / Codex / Cursor 的 Agent 预设、雇人、对话 provider 选择——第三方执行器未必认自定义 base。自建账号只服务 **Foundry 直连**（`host` / `prompt` / `image` 含批量档）。

## 目标

1. 用户可在 Provider 页**添加 / 重命名展示名 / 删除**自建账号；可改 `api_base`、Key、默认文本模型、默认生图模型。
2. 内置厂商预设保留；旧唯一 `custom` **自动兼容迁移**为用户账号条目（保留 id `custom` 与已有字段），并可继续新增其它账号。
3. 对任一可用于 Foundry 直连的账号（内置或自建），可**刷新模型目录**；文本默认模型、生图模型（含 `bulk_model`）可从目录选择，亦可手填。
4. Agent 预设 / 雇人 / 对话栏：provider 仍**仅内置厂商**；其模型字段在绑定内置账号时同样可拉目录（能调则调）+ 手填兜底。
5. `host` / `image`（含 `use_text_provider`、批量档）可选自建账号 id 作为活跃账号。
6. Key 仍只存 `provider_accounts`；目录请求不把 Key 写入日志或仓库。

## 非目标

- 视频：`video_accounts` / 视频 Provider UI / 视频模型目录 — **本轮不做**。
- 自建账号接入 Agent 执行器（Pi/Hermes/Codex/Cursor）或 Hermes「同步 API」写入自定义 base — **本轮不做**（可后续单独立项）。
- 为每个厂商维护完美「仅图像模型」分类器；仅做启发式过滤 + 允许选任意 id / 手填。
- 改计费、代理协议、非 OpenAI 兼容协议的专用 SDK。
- 把模型目录持久化进 git 或项目 brief。

## 当前架构约束

- GUI：`gui/src/settings/apiProviders.ts` 封闭 `ApiProviderId`；`providerAccounts.ts` 加载时 `isApiProviderId` 过滤未知 id；`SettingsPanel` / `HireColleagueModal` / `ColleagueConfigBar` / `agentExecutors` 只渲染 `API_PROVIDERS`。
- CLI：`provider_upsert.KNOWN_PROVIDERS` 拒绝未知 id；`agents_executors_upsert` 同样校验。
- 解析：`agent_auth_resolve` 等从 `provider_accounts.<id>` 取 Key；Foundry 生文/生图走 `host` / `image`。
- 已有执行器模型列表：`setup executor models`（CLI 侧），与账号 `/v1/models` 是不同数据源，勿混用。

## 方案选择

**选定：开放 `provider_accounts` 用户条目 + 账号级 `/v1/models` 目录；自建账号仅 Foundry 直连；Agent 侧仅内置厂商；视频不做；旧 `custom` 原地兼容。**

### Config 契约（增量）

`provider_accounts` 值对象扩展（字段均可选，与现网兼容）：

```json
{
  "provider_accounts": {
    "openrouter": { "api_key": "…", "text_model": "…", "image_model": "…" },
    "custom": {
      "api_key": "…",
      "api_base": "https://api.apilio.ai/v1",
      "text_model": "deepseek-v4-flash",
      "image_model": "gemini-3.1-flash-image",
      "label": "Apilio",
      "kind": "user"
    },
    "apilio-backup": {
      "label": "Apilio 备用",
      "kind": "user",
      "api_base": "https://api.apilio.ai/v1",
      "api_key": "…",
      "text_model": "…",
      "image_model": "…"
    }
  }
}
```

| 字段 | 含义 |
|------|------|
| `kind` | `builtin`（可省略，由内置表推断）\| `user`（自建） |
| `label` | UI 展示名；自建建议必填；内置可缺省用预设名 |
| `api_base` | 自建必填；内置可覆盖 |
| `api_key` / `text_model` / `image_model` | 与现网一致 |

规则：

- **保留 id**：`openrouter` | `deepseek` | `kimi` | `glm` | `openai` | `gemini` | `custom` 及既有内置 id 不可被「新建」占用为另一语义；`custom` 视为已迁移的用户槽（`kind=user`）。
- **新建 id**：用户指定 slug，建议 `[a-z][a-z0-9_-]{1,31}`，禁止与保留 id 冲突。
- **删除**：若 `host.provider` / `image.provider` / `image.bulk_provider` 仍引用该 id → 阻止删除并提示先改绑；Agent 侧本轮不会引用自建 id。
- **序列化**：GUI 不得再「只写出 API_PROVIDERS 枚举内的条目」；必须保留全部合法 `provider_accounts` 条目。

### 模型目录

- CLI（或 Electron 经 CLI）提供：`setup provider models --provider <id> --json`（名称可在 plan 定）。
- 行为：读该账号 `api_base` + `api_key`，请求 OpenAI 兼容 models 列表；返回 `{ ok, models:[{id,label?}], error?, source }`。
- GUI：缓存按 `provider id`（可带短 TTL 或会话级）；「刷新」强制重拉。
- 文本选择器：默认展示靠前 N 条；本地搜索过滤（结果仍截断至 N）+ 手填；当前值始终可保留。
- 生图选择器：同上；启发式优先展示疑似图像模型，并提供「显示全部（仍受 N 截断）」与手填。
- 失败：保留手填；展示简短错误（401/网络/非 JSON），不清空已选模型。

### UI 表面

| 表面 | Provider 选择 | 模型目录 |
|------|----------------|----------|
| 设置 → Provider（文/图/批量） | 内置 + 自建 | 是 |
| 设置 → Agent / 雇人 / 对话栏 | **仅内置** | 是（对该内置账号） |
| 视频 | 不变 | 否 |

## 被排除方案

- 固定 `custom_2`… 槽位：扩展性差。
- 并行 `endpoints[]` 与 `provider_accounts` 双源：引用与迁移成本高。
- 自建账号本轮强行进 Hermes/Codex：用户明确第三方未必认。
- 本轮改视频账号库。

## 边界与失败模式

- 端点无 `/v1/models` 或返回非标准 JSON → 目录为空 + 手填。
- 列表极大（如 800+）→ **不全量展示、不做虚拟滚动**；默认只展示靠前 N 条（plan 默认 N=30），其余靠搜索过滤（过滤结果仍截断至 N）与手填；当前已选 id 始终可保留可见（验收：「能搜到或手填选中目标 id」）。
- 误把自建 id 写入 `agents.instances` / `agents.executors`（旧数据或手改 config）→ 解析应安全失败或回退，并在 GUI 加载时回退到合法内置 id（与现「未知 id → fallback」一致），**不**在本轮为执行器打通自建 base。
- 代理：目录请求应走与现网生文/生图相同的 proxy 配置（若已有）。

## 工程代价

- **模块**：`cli`（provider upsert/list/delete、models fetch）、`gui` settings（账号 CRUD、选择器数据源）、可能 `electron` IPC、少量 docs（`GUI-CONFIG.md` / `TOOLS.md`）。
- **测试**：账号序列化不再丢用户条目；迁移/删除守卫；models 命令对 mock HTTP；GUI 类型与关键路径。
- **迁移**：读路径兼容无 `kind`/`label` 的旧 `custom`。
- **回滚**：仅配置与 UI；用户可删自建账号回到内置。

## 显式假设

1. 目标端点为 OpenAI 兼容（`Authorization: Bearer` + `/models`）。
2. Apilio 类聚合站的 models 列表可用于选模型；不保证每个 id 对 chat/images 都可用（选错由调用方报错）。
3. 内置厂商多数也可用同一 models API；个别失败则手填，不阻塞保存。
4. 本机已有 `custom`→Apilio 配置在升级后仍可用，无需用户重填 Key。

## 领域语言

| 术语 | 含义 |
|------|------|
| 内置厂商 | 预设表中的 openrouter/deepseek/… |
| 自建账号 / 用户账号 | `kind=user` 的 `provider_accounts` 条目 |
| 账号库 | `provider_accounts` |
| 模型目录 | 对该账号 `/models` 的可刷新列表 |
| Foundry 直连 | 不经 Pi/Hermes/Codex/Cursor，由 Foundry 用 host/prompt/image 调 API |
| 执行器账号面 | Agent 预设/雇人/对话的 provider，本轮仅内置 |

## 功能需求

1. Provider 页可列出内置 + 自建；可「添加账号」（id、label、api_base、key）；可编辑 label/base/key/默认模型；可删除（引用守卫）。
2. 活跃文本账号、活跃生图账号、批量生图账号可选自建 id。
3. 文本/生图/批量模型字段：下拉（目录）+ 刷新 + 手填。
4. CLI：支持对任意已存在账号 upsert（含用户 id）、列出、删除（带确认）、拉取 models。
5. Agent/雇人/对话：provider 下拉不含自建；模型选择器对当前内置 provider 拉目录。
6. 文档：说明自建账号用途边界（直连 vs 执行器）与 models 刷新。

## 非功能需求

- 目录请求超时可控（建议 ≤30s）；失败不卡死设置页。
- 不在日志打印完整 API Key。
- 大列表下可通过「搜索或手填」选中已知 id（如 `deepseek-v4-flash`）；默认可见选项不超过 N 条。

## 安全关注点

- Key 仅本地 config；models 请求经本机发出。
- IPC/CLI 传 Key 的既有路径保持；新增命令勿把 Key 回显到 `--json` 成功载荷（最多 `has_api_key: true`）。
- 用户粘贴 Key 进聊天的风险不在本功能范围，文档可一句提醒轮换。

## 成功标准

1. 可新增第二个自建账号并保存；重启 GUI 后仍在。
2. 旧 `custom`（Apilio）升级后仍为活跃可选，无需重填 Key。
3. 对 Apilio 类 base，刷新后能看到并选中 chat 与 image 相关模型 id，写入 config 后 Foundry 直连调用使用新模型。
4. Agent/雇人/对话 provider 列表无自建账号；误引用自建 id 的旧实例不导致崩溃。
5. 视频相关配置与 UI 无行为变更。
6. 相关 CLI 单测 + GUI typecheck 通过。

## PR Review 关注点

- GUI 序列化是否仍只遍历封闭枚举导致丢账号。
- 自建 id 是否泄漏进执行器同步路径。
- 删除守卫与 `host`/`image`/`bulk` 引用。
- models 错误处理与 Key 泄露。

## 开放问题

- （已由 plan 关闭）大列表 = 前 N + 搜索 + 手填；不做虚拟滚动/全量展示。
- （非阻塞 / 交 plan）CLI 子命令精确命名与是否复用 `httpx`/`urllib`。
- （延期）自建账号进 Hermes/Codex OpenAI 兼容档 — 触发条件：用户验证目标执行器认自定义 base 后再开。
- （延期）视频开放账号 — 用户确认暂缓。
