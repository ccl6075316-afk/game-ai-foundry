# GUI 配置说明 — Provider、Agent 与实例

| | |
|--|--|
| **读者** | Release / GUI 用户 |
| **侧重** | Provider 账号 → Agent 工具预设 → 雇人/对话实例配置 |
| **外部 Agent** | 代操 Foundry → [`TOOLS.md`](TOOLS.md) |

---

## 设置全页

顶栏 **设置** 打开完整设置页（非右侧栏），含：

```text
Provider  →  账号库（左列表 / 右详情）+ 生文/生图选用；批量与视频在「高级」
Agent     →  Pi / Hermes / Codex / Cursor（左工具 / 右预设）
本机      →  Godot 路径等
环境      →  本机工具链检测/安装、执行器步进（原「环境」侧栏）
指南      →  对话指令与 CLI 速查（原「指南」侧栏）
```

右侧栏只留给开发期：**文档 | 看板 | 资产**。`/settings` `/env` `/guide` 均进入设置全页对应 Tab。

---

## 最低开工 vs 推荐配置

| 级别 | 需要什么 | 能做什么 |
|------|----------|----------|
| **最低** | OpenRouter（或 LLM Provider）Key | `/brief`、 `/plan`、 `/run` 批量出资产 |
| **推荐** | 上项 + **Hermes 或 Cursor** | 环境排错、改 config、orchestrator 带队 |
| **写玩法** | 上项 + **Codex 或 Cursor**（程序员实例） | Pass 4 Godot C# 开发 |

仅配 API 时，GUI 聊天 **不能** 根据自然语言自由跑终端、改配置；需到 **设置 → 环境** 或斜杠命令。完整 Agent 能力见 [`TOOLS.md`](TOOLS.md) §5。

---

## Provider 页（设置 → Provider）

ChatWise 式：**左侧账号列表**，右侧编辑当前账号（Key / Base / 默认文图模型 / 拉取 models）。页内短选「生文用谁」「生图用谁（可沿用生文）」；代理、批量生图、视频在 **高级** 折叠区。

| 用途 | 说明 | 必填 |
|------|------|------|
| **账号库** | 内置厂商 + 自建 OpenAI 兼容端；`+` 添加 | 生文至少一个 Key |
| **生文选用** | 决定 `host` / 策划对话走哪家 | ✅ |
| **生图选用** | 可沿用生文账号；默认 image model 在账号详情 | ✅ |
| **高级 · 批量** | `bulk_provider` / `bulk_model` | icon_kit 时建议 |
| **高级 · 视频** | Seedance 等 | 做动画时需要 |
| **高级 · 代理** | 顶层 `proxy` | 可选 |

`proxy`：设置 → Provider → **网络**（Clash 示例 `http://127.0.0.1:7897`）。权威字段为配置顶层；保存时会清掉旧的 `host.proxy` / `image.proxy`。域名分流规则在 Clash 客户端配置，不在 Foundry GUI。

`image.provider` + `image.model`：角色/场景等默认生图（**主图 Provider** + **主图 model**）。  
`image.bulk_provider` + `image.bulk_model`：icon_kit 各项与 `generate_tier: "bulk"`（**批量 Provider** + **批量 model**）。缺 `bulk_provider` 时回退 `image.provider`；缺 `bulk_model` 时回退主图 model。两档各从 `provider_accounts` 取对应 Key/Base。icon_kit 按 `items[]` **逐张单物体生成**，不再网格切片。`items` 可为字符串，或 `{id, label?, usage?, usage_description?}`（slug 跟 `id`；玩法绑定见 `production.collectible_items`）。

**API Key 只在此页填写**；雇人弹窗与对话配置仅选择账号库 id，不重复填 Key。

### 自建账号与模型目录

- 除内置厂商外，可 **添加** OpenAI 兼容账号（自定 id / 显示名 / `api_base` / Key）。旧唯一槽 `custom` 仍兼容，可继续再加其它账号。
- 自建账号用于 **Foundry 直连**（生文 `host` / `prompt`、生图含批量）。**不进入** Agent 预设、雇人、对话的 Provider 下拉（Pi / Hermes / Codex / Cursor 未必认自定义 base）。
- 文/图模型可用「刷新」拉 `GET {api_base}/models`（CLI：`setup provider models --provider <id> --json`）。界面默认只展示靠前约 30 条，其余靠搜索或手填；失败时保留当前模型值。

GUI 主对话（① 策划薄 Chat）走 LLM Provider，与下方 Agent 执行器选择无关。

---

## Agent 页（设置 → Agent）

左列选工具，右侧编辑该工具全局预设，写入 `agents.executors`：

| 工具 | 预设字段 |
|------|----------|
| **Pi** | 默认 Provider、模型 |
| **Hermes** | 默认 Provider；**YOLO**（默认开；关则走 GUI ACP 审批，见下） |
| **Codex** | 用第三方开关；**沙箱** `sandbox`（默认 `workspace-write` → GUI app-server 审批，见下）；开启第三方时选 Provider + 模型 |
| **Cursor** | **权限模式** `permission_mode`（默认 `force`）；本机登录/订阅 |

安全字段写入 `agents.executors.<工具>`，下一轮组装 CLI argv / 分流。详见 Feature B v2 Spec。

**Cursor ACP mid-turn（GUI）**：当生效 `permission_mode` 为 `auto_review` / `plan` / `ask`（实例或全局）时，聊天走常驻 `agent acp`，并会 `session/set_mode`（plan/ask）+ 声明 clientCapabilities。仅当 Cursor **真正发起工具调用**时才会弹与 Pi 同款卡片（纯闲聊、不调工具不会出卡）。「本会话」仅在该同事实例 ACP 进程存活期内有效，**不**永久落盘。`force` 仍为一键 one-shot（`--force`）。**CLI** `agent turn` 在 Cursor 非 force 时会拒跑，并提示改用 GUI 或改回 force。

**Hermes ACP mid-turn（GUI）**：当生效 `yolo=false`（实例或全局）时，聊天走常驻 `hermes acp --accept-hooks` + 与 Pi/Cursor 同款批准卡。`--accept-hooks` 仅静默 shell hooks；**工具** permission 仍走 GUI 卡。Hermes 仅对判定为危险的终端命令发起 `session/request_permission`（普通 `echo` 等不会弹卡）。「本会话」仅在该同事实例 ACP 进程存活期内有效，**不**永久落盘。`yolo=true` 仍为一键 one-shot（`--yolo`）。**CLI** `agent turn` 在 Hermes `yolo=false` 时会拒跑，并提示改用 GUI 或开回 YOLO。Foundry 启动 Hermes ACP 时会注入运行时补丁，修复上游 0.13.x 审批回调签名/`ToolCallUpdate` 问题，否则危险命令会静默拒绝且不出卡。

**Codex app-server mid-turn（GUI）**：当生效 `sandbox ≠ danger-full-access`（默认 `workspace-write`）时，聊天走常驻 `codex app-server --listen stdio://` + 与 Pi 同款批准卡（command / file / patch 等审批请求统一进卡，文案可区分类型）。`danger-full-access` 仍为一键 one-shot（`codex exec`）。「本会话」仅在该同事实例 app-server 进程存活期内有效，**不**永久落盘；**不用** app-server daemon。这是有意「默认更安全」跳变（相对 Cursor 默认 `force`、Hermes 默认 yolo）。**CLI** `agent turn` 在 Codex 非 `danger-full-access` 时会拒跑，并提示改用 GUI 或改 sandbox 为 `danger-full-access`。

**同事实例可覆盖**（雇人弹窗 + 对话顶栏）：可选写入 `agents.instances.<id>` 的 `sandbox` / `permission_mode` / `yolo`（仅当前执行器相关键生效）。下拉首项「继承全局」= **不写/删除**该键，继续跟 Agent 预设；换执行器后历史键可留在盘上但不串用。实例可比全局更松或更紧。Hermes 生效 `yolo=false` 时 **GUI** 走 ACP 审批（见上）；Codex 生效 `sandbox ≠ danger-full-access` 时 **GUI** 走 app-server 审批（见上）；**CLI** 仍拒跑。

雇人弹窗打开时会 **预填** 对应工具的 Agent 预设（Provider/模型等）；安全旋钮默认「继承全局」，不把全局安全值拷进实例。

---

## 雇人与对话配置（`agents.instances`）

| 入口 | 说明 |
|------|------|
| **雇人弹窗** | 创建同事前配置执行器、Provider、模型、Codex 第三方、以及（非 Pi）安全旋钮；确认后写入 `agents.instances.<id>` |
| **对话内配置** | 各同事可打开配置（策划/IT 含 Provider + 模型；项目经理/程序员含执行器与安全旋钮等）；变更立即持久化到该实例 |

- **对话内修改只更新该实例**，**不回写** Agent 页全局预设。
- 删除同事时清理对应 `agents.instances.<id>`。
- **Pi Thinking**：Pi 实例可设 `thinking_level`（关/低/中/高 → `off|low|medium|high`），对话顶栏与雇人弹窗可改；运行时传给嵌入式 Pi 的 `--thinking`。Host 直连 `chat/completions` **不读**该字段。Codex/Cursor 仍只用模型高/中/低档，无独立 Thinking 控件。

**项目经理 / 程序员（Codex 登录态、Cursor）**：聊天顶栏从本机 CLI **实时读取**模型列表（`agent --list-models` / `codex debug models`），经 `setup executor models --json`。列表为空时不展示假选项；Cursor 会结合 `agent status` 区分「未登录」与「已登录但目录仍空（多半需重登刷新会话）」；可用「刷新」重拉。高/中/低档仅当偏好 id 出现在实时列表中时可点。仍写入 `agents.instances.<id>.model`。Codex 勾「第三方」时走 **内置** Provider + 账号模型目录（`setup provider models`，可搜索/手填）。Pi / Hermes 同。GUI 拉执行器列表时 PATH 会补上 `~/.local/bin`（Cursor `agent` 常见安装位置）。

---

## Hermes / Codex / Cursor

| 工具 | 安装（GUI） | API Key |
|------|-------------|---------|
| **Hermes** | 环境 → 执行器：CLI → Skills → **同步 OpenRouter** | 一键写入 `~/.hermes/.env` |
| **Codex CLI** | 环境 → 执行器：安装 → **浏览器登录** | 订阅 OAuth；或 Agent/实例开「用第三方」后 sync |
| **Cursor** | 下载 IDE → 检测 CLI | Cursor 订阅 |

CLI 等价：`setup executor step <id> <step>` — 见 [`TOOLS.md`](TOOLS.md)。

---

## 本机工具

| 工具 | 方式 |
|------|------|
| **FFmpeg** | 必需；启动缺失时自动安装 |
| **Godot .NET** | 必需；自动下载到 toolchain，写入 `godot.engine_path` |
| **.NET SDK** | 必需；自动安装到 toolchain |
| **rembg** | **打包版内嵌 Python 自带**；不出现在环境安装列表 |

---

## 工程切换

新建游戏默认 **`projects/<slug>/`**。已有独立 Godot 仓可在顶栏工程切换器点 **「打开外置工程…」**（目录选择器，不拷贝进 `projects/`）；产物与 brief 写在外置根，详见 [`AI-HANDOFF.md`](AI-HANDOFF.md) §外置工程根。

---

## 推荐 Release 用户路径

1. **设置** → 从示例创建 → 填 OpenRouter（+ 可选 Seedance）  
2. 等待启动自动装好 FFmpeg / Godot / .NET（看顶部芯片）  
3. **（推荐）环境 → 执行器** → 配 Hermes（同步 API）或 Cursor  
4. **设置 → Agent** → 配各工具默认 Provider（可选；雇人时会预填）  
5. `/brief` → `/plan` → `/run`  
6. 要写 C# 玩法 → 雇程序员实例时在弹窗选 Codex 执行器（或对话内改配置）  

外部 AI（Claude、自建 bot 等）代操：把 [`TOOLS.md`](TOOLS.md) 交给 Agent 阅读。
