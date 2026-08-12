# Game AI Foundry v0.2.2

**主更新：相关分册提示 + soft-focus 安全写 + related 完整性**

相对 [`v0.2.1`](RELEASE-NOTES-0.2.1.md)。本版给策划焦点注入 `related_shards`（声明引用 + id 提及），帮助发现连锁影响；写入不再靠 focus/related 白名单，而靠 patch 预检与事务（soft-focus）；catalog 分册不可读时明确报 `related_error`，不再静默漏边。

## 下载

| 平台 | 文件 | 说明 |
|------|------|------|
| **Windows x64（推荐）** | `Game-AI-Foundry-0.2.2-setup.exe` | NSIS：可选安装目录、干净卸载、**应用内自动更新** |
| **Windows x64** | `Game-AI-Foundry-0.2.2-win-x64.zip` | 解压即用；无自动更新 |
| **Windows x64** | `Game-AI-Foundry-0.2.2-portable.exe` | 便携版；无自动更新 |
| **macOS arm64** | `Game-AI-Foundry-0.2.2-mac-arm64.*`（若本页已附带） | 手动解压；暂无应用内自动更新 |

> Windows 未签名：可能 SmartScreen 提示。

## 新功能 / 修复

### 相关分册（related_shards）

- **宿主算边**：declared（含反向）∪ mention（词界；短 id 不扫）；结果注入策划 focus payload，不含他册正文。
- **`brief related` CLI**：只读查询，已进 brief 工具白名单。
- **语义**：`related_shards` 是连锁**提示**，不是写权限白名单。

### Soft-focus 写安全

- Focus / related **不限制**跨册 upsert；安全靠规范化、预检、快照事务与项目级锁。
- Brief patch 写路径与 focus 解耦，破坏性 set / 跨 section upsert 有负向回归。

### Related 完整性

- 反向扫描遇到不可读 catalog 分册时抛错 → `related_error`（不再静默残缺列表）。

## 纯净机使用（Windows 推荐）

1. 安装 **`Game-AI-Foundry-0.2.2-setup.exe`**（覆盖 0.2.1；安装版会走自动更新）
2. **设置** → Provider 填 Key；等待顶部芯片变绿
3. 分册工程下策划焦点会看到 `related_shards`；改他册前请自行确认连带影响
4. 国内装工具过慢时：**设置 → 环境** 打开「下载镜像」

说明 → 本文件 · 工具 → [`TOOLS.md`](TOOLS.md) · 打包 → [`RELEASE.md`](RELEASE.md)

## 已知限制

- 未代码签名 / macOS 未公证；Mac / zip / portable **不做**应用内自动更新
- 下载镜像依赖社区反代，不稳定时可关掉；.NET（dot.net）不走该镜像
- 视频 Seedance、第三方 LLM 仍可能要额外 Key
- 大 catalog 每轮 focus 全量读盘算 related，超大工程可能偏慢
