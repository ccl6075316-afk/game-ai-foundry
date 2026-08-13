# 工程 Spec：生视频复用 Provider 账号（Veo / Wan / Hailuo / Grok）

## 执行元数据

- **Status**：confirmed
- **Workflow Stage**：plan
- **Created**：2026-08-13
- **Updated**：2026-08-13
- **Confirmed By**：user「1.确认」（2026-08-13）；并行要求：fish 工程两条鱼白底图测各厂最多 3 模型游动动画
- **Source Of Truth Until**：requirements are confirmed and replaced by a `/anvil:plan`, or the request is abandoned
- **Requirements Source**：用户要生视频也支持自定义配置；确认能力接 Google / Alibaba / MiniMax / xAI；联调走 Apilio；Grill Q3=最小图生视频+可扩展私有参数；Grill Q4=方案 1，生视频在已配置 Provider 里可选，选完刷新拉模型
- **Background Inputs**：OpenRouter `/videos` 目录；xAI `/v1/videos/generations`；Apilio 现为 Foundry 自建 OpenAI 兼容账号（`https://api.apilio.ai/v1`）；[`docs/anvil/brainstorms/2026-07-28-open-provider-accounts-model-catalog.md`](2026-07-28-open-provider-accounts-model-catalog.md) 明确「视频本轮不做」；当前 `cli/seedance_api.py` + `video_accounts`
- **Compounded Knowledge**：not yet compounded
- **Resume Point**：Spec 待用户确认 → `/anvil:plan` 拆 GUI 选用、凭证解析、OpenAI 兼容视频 adapter、Seedance 保留、doctor/video_api

## 背景输入

- Foundry 生图已走 `provider_accounts` + `image.provider` / `image.model` + `ModelCatalogPicker` 刷新 `/v1/models`。
- 生视频仍独立：`video_accounts`（Seedance / 自定义）只配 Key/Base，GUI **不写 `video.model`**；运行时只走火山 ARK `seedance_api`。
- 用户目标：图生视频能力覆盖 Google Veo、Alibaba Wan、MiniMax Hailuo、xAI Grok Imagine；入参 + 视频取回；模型联调用 Apilio（已证明支持这些模型的视频通道）。
- 末帧、厂商私有参数本期不做，但架构必须能后续按模型扩展。

## 工程理解

生视频应与生图同一账号层：在**已配置的 `provider_accounts`** 里选一个账号（可选，不做视频可不选），再对该账号刷新模型目录并选定 `video.model`。运行时按账号 `api_base` 分流：

- 火山 ARK（`video.provider=seedance` 或 base 含 `volces.com`）→ 现有 `seedance_api`。
- 其它 OpenAI 兼容中转（Apilio / OpenRouter / 自建）→ 新 **compat video adapter**：提交异步任务 → poll → 下载 MP4。

Foundry 内部只认一套图生视频契约；各网关差异收在 adapter。Apilio 公开文档几乎不写视频 path，实现阶段用现有 Apilio Key **探测** `POST /v1/videos` 与 `POST /v1/videos/generations`，以实际通的为准并固化测试。

## 目标

1. GUI Provider 短选区：生文 / 生图之外增加 **可选「生视频用账号」**，选项 = 全部已出现在账号库的 Provider（与生图同一列表）。
2. 选定账号后，生视频 model 使用与生图相同的 **刷新 / 拉取 `/v1/models` / 手填自定义** 交互（`ModelCatalogPicker` 增加 `role=video` 启发式过滤，可「显示全部」+ 自定义）。
3. 落盘：`video.provider` = 账号 id；`video.model` = 所选或手填 id；Key/Base 从 `provider_accounts.<id>` 解析（与生图同一套优先级），不再要求单独 `video_accounts` 才能生视频。
4. `video.generate` / pipeline 图生视频：统一入参 `prompt` + `model` + `duration` + `resolution` + `ratio` + `generate_audio` + **首帧静图** → 取回 MP4。
5. 保留现有 Seedance ARK 路径（旧 `video.api_key` / `provider=seedance` 仍可用）。
6. `doctor` / `capabilities.video_api`：所选视频账号 Key 可用，或遗留 Seedance Key 可用，即为 true。
7. 预留扩展位 `video.extra`（object，本期忽略不展示），供后续按模型透传私有参数。

## 非目标

- 末帧 / 多参考图 / reference-to-video。
- 实现并暴露厂商私有字段（Veo `personGeneration`、Kling 专有项等）；只留 `video.extra` 扩展位。
- 为 Google / Alibaba / MiniMax / xAI 各写一套官方原生 SDK。
- 把生视频账号强制绑定生图账号（不提供「生视频沿用生图」开关，除非后续单独立项）。
- 改 brief 玩法字段、prompt-crafter 文案策略、拆帧/matting。
- Agent 执行器（Pi/Hermes/Codex/Cursor）下拉出现自建账号。
- 把 Apilio 做成内置厂商预设；继续作为用户自建 `provider_accounts` 条目。

## 当前架构约束

- GUI 短选：`ProviderSettingsView` 生文账号 + 「生图沿用生文」+ 生图账号；高级区才有 Seedance/自定义视频槽。
- 模型目录：`ModelCatalogPicker` + `window.gameFactory.providerModels` → `cli/provider_models.py` `GET {api_base}/models`；`role` 仅 `text|image`。
- 凭证：`image_model_route.resolve_image_credentials` 从 `provider_accounts` / legacy `image.*` / `host.*` 解析；视频 `_video_settings` 只读 `video.api_key` / `video.api_base`。
- 生成：`cli/seedance_api.generate_video` 固定 ARK `/contents/generations/tasks`；`video_config.resolve_video_generate_settings` 已有 duration/resolution/ratio/audio。
- 能力探测：`discover_capabilities.video_api` 仅看 `video.api_key`（seedance_key）。
- 旧 spec 将视频标为非目标，本 Spec 取代该非目标中的「视频模型目录 / video 选用」部分；不推翻账号库本身。

## 方案选择

**选定：生视频选用 = 可选的 `provider_accounts` 账号 + 同款模型目录；运行时 Seedance ARK 与 OpenAI 兼容视频 adapter 双后端；内部统一最小图生视频契约；`video.extra` 预留。**

### Config（增量，兼容旧文件）

```json
{
  "video": {
    "provider": "apilio",
    "model": "veo-3.1",
    "duration": 5,
    "resolution": "720p",
    "ratio": "adaptive",
    "generate_audio": false,
    "extra": {}
  }
}
```

- `video.provider`：`provider_accounts` 的 id，或遗留 `"seedance"`。空 / 未选 = 不启用生视频。
- `video.model`：目录所选或手填；Seedance 仍可用 `mini` / `fast` / `pro` 别名。
- Key/Base：优先 `provider_accounts[provider]`；若 `provider=seedance` 或账号无 Key，回退现有 `video.api_key` / `video.api_base`。
- `video.extra`：本期读写忽略；禁止因未知键失败。
- `video_accounts`：可继续读以兼容旧 GUI 数据；新保存不再作为生视频主路径。新 GUI 保存必须写出 `video.provider` + `video.model`，且不得抹掉未在表单编辑的 `duration` / `resolution` / `ratio` / `generate_audio` / `watermark` / `split_frames`。

### GUI

- Provider 页短选区增加「生视频用账号」：首项 **未启用**，其余 = 与生文/生图相同的账号列表（已配置标 ✓）。
- 仅当已选账号时显示「生视频 model」：`ModelCatalogPicker(providerId, role="video")`，刷新行为与生图相同。
- 视频启发式过滤（可显示全部）：`veo|wan|hailuo|grok-imagine|seedance|kling|sora|runway|happyhorse|flux.*video` 等；过滤失败或目录空 → 手填。
- 高级区旧「视频平台 Seedance/自定义」可降级为遗留说明或移除重复 Key 表单；不得再作为唯一配置入口。

### 运行时分流

`resolve_video_credentials(config)` → `{provider, api_key, api_base, model, backend}`：

| backend | 条件 | 客户端 |
|---------|------|--------|
| `seedance` | provider=`seedance` 或 api_base 含 `volces.com` / `ark.` | 现有 `seedance_api` |
| `openai_compat` | 其它 | 新 adapter |

Compat adapter 职责：

1. 把首帧本地图编成 data URL 或网关接受的 image 字段。
2. 提交异步任务（探测顺序：`POST {base}/videos` → `POST {base}/videos/generations`）。
3. Poll 直到完成 / 失败 / 超时（默认与 Seedance 同级 timeout）。
4. 从响应或 `{id}/content` 下载 MP4 到 `--output`。
5. 统一错误为 `HostChatError`/`RuntimeError` 风格短文案（HTTP + 上游 message），不含 Key。

映射内部字段（最小集）：

| Foundry | 优先发给网关的名字 |
|---------|-------------------|
| prompt | `prompt` |
| model | `model`（Apilio 用其目录裸 id，不要强加 `google/` 前缀；OpenRouter base 才用 `google/veo-3.1` 这类 slug） |
| duration | `duration` 或 OpenAI Videos 的 `seconds`（adapter 内转换） |
| resolution | `resolution` |
| ratio | `ratio` / `aspect_ratio`（`adaptive` 时按参考图推断，与现 `video_config` 一致） |
| generate_audio | `generate_audio` / `audio`（网关不认则省略，不失败） |
| first_frame | `frame_images[first_frame]` 或 `input_reference` / `image` / `image_urls[0]`（按探测到的协议） |

模型 id 规范化：复用生图经验——非 OpenRouter base 时去掉 `google/`、`openai/`、`x-ai/`、`alibaba/`、`minimax/` 等 vendor 前缀，避免中转 503。

### 扩展位（本期不实现行为）

- `video.extra: dict` 存盘允许。
- 后续 adapter 可 `deep_merge` 进请求；未知键不得让当前版本崩。
- GUI 本期不展示 extra。

## 被排除方案

- 按厂商各接原生 Veo/Wan/Hailuo/Grok SDK。
- 生视频强制与生图同一账号。
- 只加 Seedance 自定义 model、不接大厂中转。
- 本期做末帧或私有参数表单。

## 边界与失败模式

- 未选生视频账号：pipeline `video.generate` / `video generate` 明确报「未配置生视频 Provider」，doctor `video_api=false`。
- 已选账号但无 model：拒绝生成，提示刷新目录或手填。
- 目录刷新失败：允许手填 model，与生图一致。
- 网关两种 videos path 皆失败：报探测结果（status + snippet），不静默回退 Seedance。
- 模型不支持音频 / 某档分辨率：省略或按网关错误提示，不把 Seedance 4–15s 硬限制套到 Veo（Veo 仅 4/6/8）；**硬限制按 backend/model family 放宽或取消全局 4–15**，改为提交前 best-effort，失败用上游错误。
- 超时 / 任务 failed：与现 Seedance 相同，不留下半截 MP4。
- 旧配置只有 `video.api_key` 无 `video.provider`：视为 Seedance，行为不变。

## 工程代价

- GUI：`ProviderSettingsView`、`providerAccounts` serialize、`ModelCatalogPicker` video role、`sections` 文案；`GUI-CONFIG.md` / `TOOLS.md` 短更新。
- CLI：`resolve_video_credentials`；compat video adapter + 单测（协议探测、字段映射、前缀剥离、失败不落盘）；`video_cmds` / pipeline 接线；`env_discover.video_api`；`video_config` 时长校验按 backend。
- 联调：用本机 Apilio 账号对 Veo / Wan / Hailuo / Grok 各至少一次图生视频（可人工，不把 Key 写入仓库）。
- 不改 brief schema、不改拆帧。

## 显式假设

1. Apilio 对上述四家视频走 OpenAI 兼容异步 videos API（path 以实现探测为准）。
2. 用户 Apilio `/v1/models` 会列出可用视频模型 id；过滤启发式不保证完美，手填兜底。
3. Foundry 动画主路径仍是 **静图首帧 → MP4**；纯文生视频可走同一 adapter（无 reference 时不传 image 字段），但 GUI/验收以 i2v 为准。
4. OpenRouter 若被选为视频账号，使用其 `/v1/videos` + `vendor/model` slug；与 Apilio 裸 id 规则相反，由 api_base 判断。
5. Seedance 用户不迁移也能继续生成。

## 领域语言

| 词 | 含义 |
|----|------|
| 生视频账号 | `video.provider` 指向的 `provider_accounts` 条目 |
| 生视频 model | `video.model`，目录或手填 |
| compat video adapter | OpenAI 兼容中转的提交/poll/下载层 |
| Seedance backend | 火山 ARK 现有客户端 |
| 首帧 | 图生视频的 reference still |
| `video.extra` | 预留的模型私有参数袋，本期忽略 |

## 功能需求

1. Provider 短选：可选生视频账号（未启用 + 全部账号库 id）。
2. 选定后可刷新模型目录并选择/手填 `video.model`；保存写入 `video.provider` + `video.model`，不破坏其它 `video.*`。
3. `video generate` 与 pipeline `video.generate` 使用 `resolve_video_credentials` + 对应 backend；支持 `--reference-image` 首帧。
4. Compat adapter 完成提交、poll、MP4 取回；单测覆盖映射与失败路径。
5. Seedance 旧配置回归通过。
6. doctor `video_api` 认新账号 Key。
7. `video.extra` 出现在 example/config 注释或类型中，运行时忽略。

## 非功能需求

- 不把 API Key 写入日志、测试夹具或 git。
- 视频任务 timeout 默认 ≥ 600s，可 CLI 覆盖。
- 目录请求失败不得清空已选手填 model。

## 安全关注点

- 仅使用用户已配置的 Provider Key；中转把静图以 data URL 或临时 URL 交给上游，注意日志不要 dump base64。
- 无新权限模型；无 PII 新字段。

## 成功标准

1. GUI：选 Apilio 为生视频账号 → 刷新目录 → 能选或手填 Veo/Wan/Hailuo/Grok 之一 → 保存后 `config.video.provider/model` 正确。
2. 用 Apilio 对四家各跑通一次图生视频（有首帧）并得到可播放 MP4（人工或带 Key 的本机验证）。
3. 未选生视频账号时 doctor `video_api=false`，生成命令失败信息可读。
4. 仅有旧 Seedance Key 的配置仍能生成，相关单测通过。
5. 单元测试：compat 字段映射、vendor 前缀剥离、双 path 探测、失败不写输出文件、保存 patch 不丢 `split_frames`。
6. 末帧与 `video.extra` 行为均不在本期 GUI/请求中出现。

## PR Review 关注点

- 保存 Provider 时是否误清空 `video` 其它键。
- Seedance 与 compat 分流是否误判 api_base。
- Apilio 裸 id vs OpenRouter slug 是否按 base 处理。
- `video_api` doctor 是否仍只看 seedance_key。
- 是否偷偷实现了末帧或 extra 透传。

## 开放问题

- Apilio 最终 videos path / 取回字段：实现探测后写入 plan 附录；**不阻塞确认本 Spec**（已授权用 Apilio 联调）。
- 是否在短选提供「生视频沿用生图」：本期不做，标为后续 UX。
- 高级区旧 `video_accounts` UI 删除还是隐藏：plan 默认 **隐藏重复 Key 表单，读旧数据一次迁移进 `video.provider=seedance` 若仅有 ARK Key**。
