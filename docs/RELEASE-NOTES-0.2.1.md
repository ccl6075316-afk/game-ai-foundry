# Game AI Foundry v0.2.1

**主更新：Brief 目录分册 + 文档焦点预览 + 应用内媒体灯箱**

相对 [`v0.2.0`](RELEASE-NOTES-0.2.0.md)。本版把厚 brief 拆成「目录索引 + 分册正文」，策划对话按焦点只加载当前分册；文档栏可读分册与中文标题；看板/资产缩略图在应用内灯箱查看，不再跳系统相册。

## 下载

| 平台 | 文件 | 说明 |
|------|------|------|
| **Windows x64（推荐）** | `Game-AI-Foundry-0.2.1-setup.exe` | NSIS：可选安装目录、干净卸载、**应用内自动更新** |
| **Windows x64** | `Game-AI-Foundry-0.2.1-win-x64.zip` | 解压即用；无自动更新 |
| **Windows x64** | `Game-AI-Foundry-0.2.1-portable.exe` | 便携版；无自动更新 |
| **macOS arm64** | `Game-AI-Foundry-0.2.1-mac-arm64.*`（若本页已附带） | 手动解压；暂无应用内自动更新 |

> Windows 未签名：可能 SmartScreen 提示。

## 新功能 / 修复

### Brief 目录 + 分册

- **`brief.json` 作目录**：scenes / systems / assets 以 `id` + `path` 索引；正文落在分册文件（sole source of truth）。
- **migrate / validate**：支持旧厚 brief 迁移与 path/id 校验；下游 pipeline / 北极星按 path hydrate。
- **策划焦点**：host-chat 按 focus 只注入当前分册，减轻上下文膨胀；`focus_error` / catalog audit 失败会明确报出。

### 文档与可制作性

- **文档栏**：分册预览、中文标题；人类可读文档与 shards 对齐。
- **makeability 绑定闸门**：审查与 brief 分册绑定更严，避免未绑定就放行。

### GUI

- **MediaLightbox**：看板北极星 / 资产审查缩略图在应用内全屏查看，可返回列表（不再被系统「照片」占死）。

## 纯净机使用（Windows 推荐）

1. 安装 **`Game-AI-Foundry-0.2.1-setup.exe`**（覆盖 0.2.0；安装版会走自动更新）
2. **设置** → Provider 填 Key；等待顶部芯片变绿
3. 大 brief 工程可用分册模式；旧工程可 migrate 后再继续策划
4. 国内装工具过慢时：**设置 → 环境** 打开「下载镜像」

说明 → 本文件 · 工具 → [`TOOLS.md`](TOOLS.md) · 打包 → [`RELEASE.md`](RELEASE.md)

## 已知限制

- 未代码签名 / macOS 未公证；Mac / zip / portable **不做**应用内自动更新
- 下载镜像依赖社区反代，不稳定时可关掉；.NET（dot.net）不走该镜像
- 视频 Seedance、第三方 LLM 仍可能要额外 Key
- 并行生图在网关限流时仍可能变慢；重试无法取消已发出的 HTTP 请求
