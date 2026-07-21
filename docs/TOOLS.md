# 工具与外部 Agent 操作手册

| | |
|--|--|
| **读者** | 使用 **其他 AI Agent**（Claude Code、ChatGPT、自建 bot、Hermes/Codex/Cursor 等）代操 Foundry 的人 |
| **侧重** | 本机工具 **配置 / 功能 / 纠错**；Agent 应先跑哪些命令、读哪些路径 |
| **姊妹文档** | GUI 用户 → [`GUI-CONFIG.md`](GUI-CONFIG.md) · 流水线契约 → [`AI-HANDOFF.md`](AI-HANDOFF.md) · Hermes 专篇 → [`HERMES-CODEX.md`](HERMES-CODEX.md) |

---

## 1. 能力三层（Agent 先理解再动手）

```text
① Provider API Key     →  Brief 对话、生图、生视频（LLM / 图像 / 视频接口）
② 本机工具链           →  FFmpeg、Godot .NET、.NET SDK（GUI 启动可自动安装）
③ 执行器 Agent        →  排错、改配置、委派角色、写 Godot C#（Hermes / Codex / Cursor）
```

| 只有 ① | 能 Brief + `pipeline run` 批量出资产；**不能**自由跑终端排错、写玩法代码 |
| ① + ② | 完整 Pass 1–3（策划 → 生图/视频 → Godot 组装） |
| ① + ② + ③ | 完整流程 + 失败 triage + Pass 4 玩法 + 验收 |

**给用户的建议（可写进 onboarding）：**

1. **最低开工**：配置 OpenRouter（或支持的 LLM Provider）→ `/brief` → `/plan` → `/run`
2. **想有人帮你装环境、查日志、改 config、处理 pipeline 失败**：再配 **Hermes** 或 **Cursor**，并安装本项目 Skills
3. **要写 Godot C# 玩法**：程序员角色用 **Codex** 或 **Cursor**

---

## 2. Agent 接入：第一步必跑

在仓库 **`cli/`** 目录执行（`workdir` 设为仓库根或 `cli/`）：

```bash
cd cli
python gamefactory.py doctor --json
python gamefactory.py setup check --json
python gamefactory.py setup executor status --json
python gamefactory.py agents show --discover
python gamefactory.py hermes paths    # 输出 repo_root、cli_dir、config_path
```

| 命令 | 用途 |
|------|------|
| `doctor --json` | API Key 是否 set、Godot 路径、各 executor 是否 available、capabilities |
| `setup check --json` | FFmpeg / Godot / .NET 是否就绪 |
| `setup provider upsert --provider <id> --api-key … --i-confirm --json` | **IT 工具箱**：经用户确认写入 `provider_accounts`（可切当前生文）；输出无完整 Key |
| `setup install <ffmpeg\|godot\|dotnet>` / `setup ensure` | 本机工具链；经 IT 对话须带 `--i-confirm`（CLI 本体可不认该标志，由白名单剥离） |
| `setup executor status --json` | Codex / Hermes / Cursor 分步安装状态（只读） |
| `setup executor step <id> <step>` | 执行器步进；经 IT 须 `--i-confirm` |
| `setup agents executors upsert --executor <pi\|hermes\|codex\|cursor> … --i-confirm --json` | **IT**：经确认写 `agents.executors` 预设（无 Key） |
| `pipeline heal` / `pipeline reset --task-id …` | 流水线修复；经 IT 须 `--i-confirm`（**无** `pipeline run`） |
| `agents show --discover` | 七角色当前配置的 executor 与本机是否可用 |

**关键路径**

| 路径 | 内容 |
|------|------|
| `~/.gamefactory/config.json` | 主配置（Provider、Godot、agents 路由） |
| `~/.gamefactory/toolchain/bin/` | FFmpeg / ffprobe（自动安装） |
| `~/.gamefactory/toolchain/godot/` | Godot .NET 便携版（自动安装） |
| `~/.gamefactory/toolchain/dotnet/` | .NET SDK（自动安装） |
| `~/.hermes/.env` | Hermes OpenRouter Key（GUI 可一键同步） |
| `~/.hermes/config.yaml` | Hermes 模型与 provider |
| `~/.codex/auth.json` | Codex 登录态 |
| `resources/config.example.json` | 配置模板 |
| `resources/skills/<role>/` | 六角色 skill 源文件 |
| `pipeline/` `plans/` `output/` `games/` | 运行产物（通常 gitignored） |

Release 打包版：内嵌 Python 在应用 `Resources/python/`，**rembg 已预装**；工作区在 portable `data/` 或用户 AppData。

---

## 3. 配置（`~/.gamefactory/config.json`）

从 `resources/config.example.json` 复制，或 GUI **设置 → 从示例创建**。

### 3.1 Provider（API）

| 段 | 用途 | Agent 检测 |
|----|------|------------|
| `provider_accounts.openrouter` | 多账号库（推荐） | `doctor` → `config.openrouter_key` |
| `host` | 生文 / Brief 默认模型 | `capabilities.image_api` 等 |
| `image` | 生图；可 `use_text_provider: true` | 同上 |
| `video` | Seedance 等视频 API | `config.seedance_key` |

无效 Key 特征：空、`YOUR_*` 占位符 → `doctor` 报 `missing`。

### 3.2 本机工具

| 段 | 说明 |
|----|------|
| `godot.engine_path` | Godot 4 **.NET / Mono** 可执行文件；自动安装后会写入 |
| `toolchain.bin_dir` | FFmpeg 目录（默认 `~/.gamefactory/toolchain/bin`） |
| `toolchain.godot_dir` / `dotnet_dir` | 自动安装目录 |

### 3.3 Agent 路由（`agents`）

| 角色 | 默认 executor | 典型任务 |
|------|---------------|----------|
| `orchestrator` | `hermes` | Brief、派活、失败 triage |
| `prompt-crafter` | `hermes` | `prompt craft` → `plans/*.json` |
| `image-generator` 等 | `pipeline` | **无 LLM**，`pipeline run` 子进程 |
| `godot-developer` | `codex` | Pass 4 写 C# |
| `tester` | `hermes` | `test run` 验收 |

改路由后无需重启 GUI；外部 Agent 用 `agents show --discover` 确认。

### 3.4 Agent 预设与实例（`agents.executors` / `agents.instances`）

| 入口 | 说明 |
|------|------|
| GUI **设置 → Agent** | 按工具（Pi/Hermes/Codex/Cursor）配置全局预设 → `agents.executors` |
| **雇人弹窗** | 创建同事前配置实例字段；预填来自 Agent 预设 → `agents.instances.<id>` |
| **对话内配置** | 各同事可改本实例 Provider / 模型 / 执行器 / Codex 第三方；**只写 instances，不回写 executors** |
| CLI | `agent turn --instance-id <id>` 与 GUI 共用同一解析链 |

- **Key 只在 `provider_accounts`**；executors 与 instances 只引用 provider id，不复制 API Key。
- **解析链**：`agents.instances[id]` 字段 → `agents.executors[<executor>]` → 生文/host 账号回退。
- 兼容旧配置：无 `executors` 时可读工种块（`brief`/`it`→pi 等）再回退 host。
- **Cursor v1 无第三方同步**；仅 IDE 登录/订阅。
- 示例见 `resources/config.example.json` 的 `agents.executors` 与 `agents.instances`。

---

## 4. 本机工具链

### 4.1 FFmpeg（必需）

| | |
|--|--|
| **功能** | 视频拆帧 `video split-frames`、探针 `ffprobe`、剪辑 |
| **检测** | `setup check --json` → `ffmpeg.available` |
| **安装** | `python gamefactory.py setup install ffmpeg` |
| **路径** | `~/.gamefactory/toolchain/bin/ffmpeg` |

**常见错误**

| 现象 | 处理 |
|------|------|
| `ffmpeg not found` | `setup install ffmpeg` 或 GUI 环境栏安装 |
| macOS 无法打开下载的二进制 | 已自动 `xattr -cr`；仍失败则手动允许 |

### 4.2 Godot .NET（必需）

| | |
|--|--|
| **功能** | Pass 3 组装 `godot assemble`、打开工程、C# 构建 |
| **检测** | `setup check` + `doctor` → `tools.godot` / `capabilities.godot_assemble` |
| **安装** | `python gamefactory.py setup install godot`（macOS arm64/x64、Windows） |
| **配置** | 自动写入 `godot.engine_path` |

**常见错误**

| 现象 | 处理 |
|------|------|
| `godot_assemble` false | 跑 `setup install godot` 或设置页指定路径 |
| 用了非 .NET 版 Godot | 必须 **.NET / Mono** 模板 |

### 4.3 .NET SDK（必需）

| | |
|--|--|
| **功能** | Godot C# 项目 `dotnet build` |
| **检测** | `setup check` → `dotnet` |
| **安装** | `python gamefactory.py setup install dotnet` |
| **路径** | `~/.gamefactory/toolchain/dotnet/` |

### 4.4 rembg（打包版自带）

| | |
|--|--|
| **功能** | `video matte-frames --engine ai`（BiRefNet 等） |
| **Release** | 内嵌 Python 构建时 `--with-rembg`，**无需** `setup install` |
| **源码开发** | `cd gui && npm run prepare:python`（含 rembg） |
| **回退** | `--engine soft-key` 色键抠图，不依赖 rembg |

---

## 5. 执行器（Hermes / Codex / Cursor）

GUI **环境 → 执行器** 可分步安装；CLI：

```bash
python gamefactory.py setup executor status --json
python gamefactory.py setup executor step hermes install_cli
python gamefactory.py setup executor step hermes install_skills
python gamefactory.py setup executor step hermes configure_api   # 需 Foundry 已配 OpenRouter
python gamefactory.py setup executor step codex install_cli
python gamefactory.py setup executor step codex login
python gamefactory.py setup executor step codex sync_api              # use_third_party=true 时同步到 ~/.codex/
python gamefactory.py setup executor step codex sync_api --instance-id <id>  # 按实例覆盖解析
python gamefactory.py setup executor step cursor verify_cli
```

### 5.1 Hermes

| | |
|--|--|
| **适合** | 独立桌面、多会话 orchestrator / prompt-crafter / tester |
| **安装** | `pip install hermes-agent` + `gamefactory hermes install` |
| **Skills** | `game-factory-orchestrator` 等 → `~/.hermes/skills/` |
| **API** | GUI 可同步 OpenRouter → `~/.hermes/.env` + `model.provider=openrouter` |
| **终端** | 调 `gamefactory` 时 **workdir=repo_root**，`cd cli && python gamefactory.py …` |

详见 [`HERMES-CODEX.md`](HERMES-CODEX.md)。

### 5.2 Codex

| | |
|--|--|
| **适合** | Pass 4 `godot-developer` 写 C# |
| **安装** | `npm install -g @openai/codex` |
| **登录** | `codex login` → `~/.codex/auth.json`（`use_third_party=false` 时走订阅，不覆盖） |
| **第三方** | 实例或 **Agent 预设**（Codex 勾选「用第三方」）→ 保存后 GUI 自动调 `sync_api`，或 CLI `setup executor step codex sync_api`；写入 `~/.codex/config.toml` + `~/.codex/.env` |
| **要求** | git 仓库（本项目满足） |

### 5.3 Cursor

| | |
|--|--|
| **适合** | 在 IDE 内带队 + 改 `games/` 代码 |
| **安装** | 安装 Cursor IDE；命令面板安装 `cursor` shell 命令 |
| **登录** | Cursor 订阅账号 |
| **第三方** | **v1 不支持** Foundry → Cursor 的 API Key 同步；实例 `use_third_party` 对 Cursor 无效 |

### 5.4 执行器 vs GUI 同事对话

| 能力 | GUI ① 策划（薄 Chat） | GUI ②③（executor） | 外置 Agent |
|------|----------------------|---------------------|------------|
| Brief 多轮 / 落实 | ✅ `brief chat` | ❌（找策划岗） | ✅ orchestrator skill / brainstorm 兼容 |
| 分诊派工 / 写 handoff | ❌ | ✅ `agent turn` | ✅ 可读 `plans/handoffs/` |
| 写 Godot C# | ❌ | ✅ 程序员实例 | ✅ Codex/Cursor |
| `/doctor` `/plan` `/run` | ✅ 斜杠命令 | 可经 Agent 调 CLI | ✅ 任意 terminal |
| 读日志改 config 排错 | ❌ | 部分 | ✅ |

---

## 6. 功能速查（Agent 常用命令）

```bash
# 配置
python gamefactory.py doctor --json

# Brief（GUI / 主路径）
python gamefactory.py brief chat start --json
python gamefactory.py brief chat turn --message "..." --json
python gamefactory.py brief chat export -o ../resources/my-game-brief.json

# Brief（CLI 兼容，问卷式）
python gamefactory.py brief brainstorm start --json
python gamefactory.py brief brainstorm turn --message "..." --json
python gamefactory.py brief brainstorm export -o ../resources/my-game-brief.json

# Agent 同事 turn（项目经理 / 程序员）
python gamefactory.py agent turn --role product_host --session-id demo --message "..." --json
python gamefactory.py project handoff list --json

# Pipeline
python gamefactory.py pipeline plan --brief ../resources/my-game-brief.json
python gamefactory.py pipeline run --manifest ../pipeline/my-game-brief.json --run-prompts --jobs 4
python gamefactory.py pipeline status --manifest ../pipeline/my-game-brief.json --json

# Godot
python gamefactory.py godot assemble --assemble-file ../plans/godot_my-game-brief.json
python gamefactory.py godot dev-context --brief ../resources/my-game-brief.json --project ../games/my-game-brief
python gamefactory.py godot validate --project ../games/my-game-brief

# 测试
python gamefactory.py test run --project ../games/my-game-brief --brief ../resources/my-game-brief.json
```

完整字段契约与铁律 → [`AI-HANDOFF.md`](AI-HANDOFF.md)。

---

## 7. 纠错手册

### 7.1 环境与配置

| 症状 | 诊断 | 修复 |
|------|------|------|
| Brief 启动失败 / 无 API | `doctor --json` → `openrouter_key: missing` | 创建 config，填 `provider_accounts.openrouter.api_key` |
| `image_api` false | 同上或 image 段无 Key | 设置 image provider 或 `use_text_provider` |
| `video_api` false | `seedance_key: missing` | 填 `video.api_key`（做视频时需要） |
| `godot_assemble` false | `setup check` godot 缺失 | `setup install godot` |
| pipeline 报 ffmpeg | `setup check` ffmpeg 缺失 | `setup install ffmpeg` |
| C# 构建失败 | dotnet 缺失 | `setup install dotnet` |
| Hermes 无响应 | `setup executor status` | 装 CLI + skills + configure_api |
| Codex 不可用 | `~/.codex/auth.json` | `codex login` |
| orchestrator 配置了 hermes 但 unavailable | `doctor` executors.hermes | 完成 Hermes 三步安装 |

### 7.2 Pipeline 运行

| 症状 | 处理 |
|------|------|
| 任务 `failed` | `pipeline status --json` 看 `failed_ids`；读日志；`pipeline reset <task_id>` 后重跑 |
| 生图 `exit 2` | **不要** trim/remove-bg；交 prompt-crafter 改 plan |
| 视频帧抠图失败 | 确认 rembg（打包版自带）；或 manifest 改 `engine: soft-key` |
| manifest 过期 | brief 变更后 **必须** `pipeline plan`（必要时 `--merge`） |

### 7.3 给外部 Agent 的操作原则

1. **先 `doctor --json`，再动手** — 不要猜 Key 或 Godot 路径  
2. **export 后的 brief 只读文件** — 不依赖聊天记忆（见 AI-HANDOFF §1.1）  
3. **批量资产用 `pipeline run`** — 不要逐步开 Hermes 会话生每张图  
4. **改需求 = 改 brief + re-plan** — 不是口头补丁  
5. **所有探测命令优先加 `--json`** — 便于程序化解析  

---

## 8. 外部 Agent 最小接入清单

```text
□ 克隆或定位 game-ai-foundry 仓库，记录 repo_root / cli_dir（hermes paths）
□ 创建 ~/.gamefactory/config.json，填入 OpenRouter Key
□ 运行 doctor + setup check，修复 missing_required
□ （推荐）安装 Hermes + gamefactory hermes install，configure_api
□ （可选）安装 Codex + login，用于 godot-developer
□ 加载 resources/skills/orchestrator/ 或 Hermes skill game-factory-orchestrator
□ 从 brief chat export（或兼容 brainstorm export）开始，禁止跳过 frozen brief 门禁
□ GUI 修改场景：找项目经理同事 → 分诊落盘 handoff → 程序员接单（见 HOST-CHAT-PRODUCT）
```

---

## 9. 相关文档

| 文档 | 何时读 |
|------|--------|
| [`HOST-CHAT-PRODUCT.md`](HOST-CHAT-PRODUCT.md) | GUI AI 公司前台、工种与文件总线 |
| [`GUI-CONFIG.md`](GUI-CONFIG.md) | GUI 用户配 Provider / 执行器 |
| [`AI-HANDOFF.md`](AI-HANDOFF.md) | brief 字段、pipeline 铁律 |
| [`AGENT-ROUTING.md`](AGENT-ROUTING.md) | 七角色与 executor 表 |
| [`HERMES-CODEX.md`](HERMES-CODEX.md) | Hermes terminal、pty、多会话 |
| [`../AGENTS.md`](../AGENTS.md) | Codex 单文件最短入口 |
