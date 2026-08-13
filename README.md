# Game AI Foundry

**AI-driven game factory** — describe a game → freeze **brief JSON** → generate assets → Godot project → iterate with AI colleagues.

**Latest:** [**v0.2.2**](https://github.com/ccl6075316-afk/game-ai-foundry/releases/tag/v0.2.2) — 相关分册提示 + soft-focus 安全写 + related 完整性

**GUI**（`start-gui.bat` / `start-gui.sh`）或 **CLI**（`cd cli && python gamefactory.py`）。七角色 skills + Hermes / Codex / Cursor 执行器。

文档索引 → [`docs/README.md`](docs/README.md)

## How it works

```
用户（决策人）
  ├─ 策划同事     → brief chat → projects/<slug>/brief.json + 北极星图
  ├─ 项目经理同事 → 分诊 → handoffs / progress / 定点 pipeline
  └─ 程序员同事   → 接 handoff → 改 Godot C# → validate
         │
brief.json → production.json → scaffold
         → pipeline run → assemble → projects/<slug>/game/
         → validate / test unit / play / regression
```

产品心智 → [`docs/HOST-CHAT-PRODUCT.md`](docs/HOST-CHAT-PRODUCT.md)  
改需求 / Delta → [`docs/ITERATIVE-PRODUCTION.md`](docs/ITERATIVE-PRODUCTION.md)

## Features (v0.2.2)

### GUI — AI 公司前台

| 能力 | 说明 |
|------|------|
| **同事列表** | 策划 / 项目经理 / 程序员 / **IT**；可多实例、改名、解雇、侧栏收起 |
| **策划** | `brief chat`：商量设计；补全细节 / 议题头脑风暴；保存 Brief；**生成/选用北极星图** |
| **项目经理** | 生成流水线 → 运行资产生成；分诊写 handoff + progress |
| **IT** | 家庭运维：环境、草稿同步、中文说明、看板；默认信任本会话，可 `pipeline run` |
| **工程隔离** | 新游戏在 `projects/<slug>/`；也可「打开外置工程」挂独立 Godot 仓 |
| **环境检测** | 失败时对话 + 弹窗写清原因，可复制发给支持 |
| **程序员** | 按实例接 handoff；关单写回 progress |
| **一键建议命令** | 白名单执行 `pipeline reset/run`、`godot validate` 等 |
| **`/delta`** | Production Delta → 合并蓝图并同步 progress |
| **斜杠命令** | `/plan` `/run` `/board` `/assets` `/doctor` `/guide` … |
| **看板 / 资产 / 文档** | 右侧栏可**拖宽**；看板管任务；**资产**表审图；**文档**预览 brief |
| **对话停止** | 生成中可点停止，中断本轮 CLI / ACP |
| **设置（全页）** | Provider 多账号（可自建 OpenAI 兼容）+ 模型目录；Agent 工具预设；本机（含**检查更新**）/ 环境 / 指南 |
| **Release** | 内嵌 Python（含 **rembg**）+ 内嵌 Pi；**Codex 安装无需本机 npm**；Windows **NSIS 安装版自动更新**；无需用户装 Python/Node |

### CLI / 施工底座

| 能力 | 说明 |
|------|------|
| `brief chat` / `validate` | 策划会话与契约门禁（`brainstorm` 仍兼容） |
| `production derive` / `delta` / `apply-delta` | 工程蓝图与改需求切片 |
| `project progress` / `handoff` | 续作账本与派工文件总线 |
| `pipeline plan` / `run` / `reset` / `suggest-retry` | 资产 DAG 与定点重跑 |
| `assets review list` / `accept` / `replace` / … | 资产审查（软 review；GUI 侧栏「资产」） |
| `godot scaffold` / `assemble` / `validate` | 壳、组装、校验 |
| `test unit` / `play` / `regression` | 验收金字塔 |
| `doctor` / `setup` | API、工具链、执行器 |

### 最低开工 vs 推荐

| 级别 | 配置 | 能做什么 |
|------|------|----------|
| **最低** | LLM Provider Key | 与策划出 brief + `/plan` `/run` 出资产 |
| **推荐** | + Hermes / Codex / Cursor Agent | 项目经理分诊、程序员施工 |
| **写玩法** | + Codex 或 Cursor（程序员岗） | Godot C# Pass 4 |

详见 [`docs/GUI-CONFIG.md`](docs/GUI-CONFIG.md) · 外部 Agent → [`docs/TOOLS.md`](docs/TOOLS.md)

## Quick start

### Release（最终用户）

1. 下载 [**v0.2.2 Release**](https://github.com/ccl6075316-afk/game-ai-foundry/releases/tag/v0.2.2)（Windows 推荐 **`*-setup.exe`**）
2. 安装 / 解压并打开 **Game AI Foundry**
3. **设置** → Provider 填 LLM API Key（可自建兼容端）；高级里可配代理；等待顶部芯片变绿（FFmpeg / Godot / .NET）
4. **（推荐）设置 → 环境** → 安装 Hermes / Codex / Cursor Agent；**设置 → Agent** 配默认连法
5. 与**策划**落实 brief → `/plan` → `/run --run-prompts` → 侧栏 **资产** 审图
6. 试玩问题找**项目经理**；环境/看板找 **IT**；改需求用 `/delta 00x-name | 描述`

说明 → [`docs/RELEASE-NOTES-0.2.2.md`](docs/RELEASE-NOTES-0.2.2.md) · 打包 → [`docs/RELEASE.md`](docs/RELEASE.md)

**无需**安装 Python / Node。Windows 安装版支持应用内更新；macOS 请手动换 zip。

### GUI（开发者）

```bash
cd gui && npm install && npm run dev
# 或在仓库根目录：
./start-gui.sh    # macOS/Linux
start-gui.bat     # Windows
```

### CLI

```bash
cd cli && pip install -r requirements.txt
cp ../resources/config.example.json ~/.gamefactory/config.json

python gamefactory.py doctor --json
python gamefactory.py setup check --json
python gamefactory.py brief validate --brief ../resources/asset-brief.example.json
python gamefactory.py pipeline plan --brief ../resources/asset-brief.example.json
python gamefactory.py pipeline run --manifest ../pipeline/asset-brief.example.json --run-prompts --jobs 4
```

Details → [`docs/AI-HANDOFF.md`](docs/AI-HANDOFF.md) · Progress → [`ROADMAP.md`](ROADMAP.md)

## Prerequisites

### Release 用户

| 项 | 必需 | 说明 |
|----|------|------|
| **LLM Provider**（如 OpenRouter） | ✅ | Brief、生图（GUI 设置） |
| **生视频账号** | 做视频时 | Provider 选 Veo/Wan/Hailuo/Grok，或遗留 Seedance/ARK |
| **FFmpeg / Godot / .NET** | ✅ | GUI **启动自动安装** |
| **rembg** | — | **打包版内嵌** |
| **Hermes / Codex / Cursor Agent** | 推荐 | 项目经理 / 程序员；**设置 → 环境** 配置 |

### 开发者

Python 3.11+ · Node 20+ · API keys · 可选 `npm run prepare:python`（含 rembg）

## License

MIT
