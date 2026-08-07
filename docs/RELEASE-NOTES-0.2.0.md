# Game AI Foundry v0.2.0

**主更新：多场景北极星体验加固 + 退出杀进程 / 生图重试 / 并行生成可靠性**

相对 [`v0.1.10`](RELEASE-NOTES-0.1.10.md)。本版把北极星「进度」与「资产生成闸门」拆开，修掉 restyle / 选用 / 全局重做若干会卡住流程的问题；退出升级时尽量清掉子进程树；生图与并行候选更耐瞬断。

## 下载

| 平台 | 文件 | 说明 |
|------|------|------|
| **Windows x64（推荐）** | `Game-AI-Foundry-0.2.0-setup.exe` | NSIS：可选安装目录、干净卸载、**应用内自动更新** |
| **Windows x64** | `Game-AI-Foundry-0.2.0-win-x64.zip` | 解压即用；无自动更新 |
| **Windows x64** | `Game-AI-Foundry-0.2.0-portable.exe` | 便携版；无自动更新 |
| **macOS arm64** | `Game-AI-Foundry-0.2.0-mac-arm64.*`（若本页已附带） | 手动解压；暂无应用内自动更新 |

> Windows 未签名：可能 SmartScreen 提示。

## 新功能 / 修复

### 北极星（多场景）

- **进度看板 / 缩略图 / restyle 流程**：场景级进度、看板预览、「都不满意 → 写反馈 → 重新生成」链路（含 v0.1.10 之后合入的主路径）。
- **闸门拆分**：跑资产生成要求 brief 里已绑定 `visual_reference`；磁盘上仅有 `selected.png` 只算进度标记，不再误开闸门。
- **选用 / 重做**：选用成功后不再长期污染后续策划对话；裸「选用北极星 a」= 全局；「重新生成全局」不再误落到当前场景；澄清启发式改为「多句放行、单句硬追问才挡」，避免卡住重生成 chip。

### 可靠性

- **退出杀进程树**：Windows 退出 / 升级前对 CLI 子进程做 `taskkill /T`，并检查退出码，减轻「Foundry 仍在运行」挡安装。
- **北极星并行生成**：候选并行；失败时 abort + 等在途任务结束再 rollback，避免孤儿 `candidate_*.png`。
- **生图 API 重试**：非 JSON / 429 / urllib3 连接池 / Windows 连接被重置等瞬断可重试（不再误匹配「connection string」类文案）。

### 继承

- v0.1.10：环境「下载镜像」开关（国内加速 GitHub 工具链）。

## 纯净机使用（Windows 推荐）

1. 安装 **`Game-AI-Foundry-0.2.0-setup.exe`**（覆盖 0.1.x；安装版会走自动更新）
2. **设置** → Provider 填 Key；等待顶部芯片变绿
3. 策划侧生成并**选用**北极星（全局或按场景）后再跑资产生成
4. 国内装工具过慢时：**设置 → 环境** 打开「下载镜像」

说明 → 本文件 · 工具 → [`TOOLS.md`](TOOLS.md) · 打包 → [`RELEASE.md`](RELEASE.md)

## 已知限制

- 未代码签名 / macOS 未公证；Mac / zip / portable **不做**应用内自动更新
- 下载镜像依赖社区反代，不稳定时可关掉；.NET（dot.net）不走该镜像
- 视频 Seedance、第三方 LLM 仍可能要额外 Key
- 并行生图在网关限流时仍可能变慢；重试无法取消已发出的 HTTP 请求
