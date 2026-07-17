# Game AI Foundry v0.0.4

**主更新：AI 公司对话前台** — 策划 / 项目经理 / 程序员可多实例协作；分诊派工 + 一键定点重跑 + Production Delta。

相对 [`v0.0.3`](RELEASE-NOTES-0.0.3.md)。完整进度见 [`ROADMAP.md`](../ROADMAP.md) · 产品心智见 [`HOST-CHAT-PRODUCT.md`](HOST-CHAT-PRODUCT.md)。

## 下载

| 平台 | 文件 | 说明 |
|------|------|------|
| **macOS arm64** | `Game-AI-Foundry-0.0.4-mac-arm64.zip` | 解压后运行 **Game AI Foundry.app** |
| **Windows x64** | （需在 Windows 构建机跑 `scripts\build-release.bat` 后补传） | 解压后运行 `Game AI Foundry.exe` |

> 未签名：macOS 可能需右键打开 / 系统设置放行；Windows 可能 SmartScreen 提示。

## 主功能 — AI 公司前台

用户是**决策人**；左侧同事列表，右侧与选中同事聊天：

| 工种 | 能力 |
|------|------|
| **策划** | `brief chat`：商量设计，明确「落实」才写 `brief.json` |
| **项目经理** | `agent turn` → 执行器 CLI；分诊 → `plans/handoffs/` + progress |
| **程序员** | 接 handoff（按实例路由）；关单写回 progress |

- 多实例雇佣 / 改名 / 解雇；同事栏可收起
- 分诊建议命令可一键执行（白名单：`pipeline reset/run`、`godot validate` 等）
- Agent / 一键命令**流式日志**刷进聊天
- `/delta change-id \| 意图` → Production Delta → 合并 production + 同步 progress

## 亦含于本包（自 v0.0.3）

- Construction harness：`production` / `godot scaffold` / `project progress` / 验收金字塔
- Provider 多账号、执行器向导、工具链自动安装（FFmpeg / Godot .NET / .NET SDK）
- 内嵌 Python（含 rembg）

## 纯净机使用

1. 安装 / 打开 **Game AI Foundry**
2. **设置** → 填 LLM API Key；顶部环境芯片等工具链变绿
3. **（推荐）环境 → 执行器** → Hermes / Codex / Cursor Agent（项目经理 / 程序员依赖）
4. 与**策划**落实 brief → `/plan` → `/run --run-prompts`
5. 试玩反馈找**项目经理** → 点「执行 · …」或切换**程序员**施工
6. 改需求：`/delta 00x-name | 描述`

## 已知限制

- 执行器需本机安装对应 CLI（不随包内嵌 Hermes/Codex/Cursor）
- 一键命令为白名单，非全自动验收闭环
- 视觉 QA 非硬门禁；首次启动完整引导待 0.0.5+
- Windows 干净机全链 E2E 仍待验证

## 构建机验证（本包）

- [x] macOS arm64（本机构建）
- [ ] Windows zip（需 Windows 构建机）
- [ ] GUI 双击全链（人工）
- [ ] 干净 VM E2E
