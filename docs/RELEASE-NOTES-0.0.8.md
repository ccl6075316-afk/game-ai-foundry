# Game AI Foundry v0.0.8

**主更新：DeepSeek 模型名修复 + 对话滚动位置** — 旧配置里的 `deepseek-chat` 自动迁到 `deepseek-v4-flash`；打开长对话不再从顶 smooth 滚到底。

相对 [`v0.0.7`](RELEASE-NOTES-0.0.7.md)。

## 下载

| 平台 | 文件 | 说明 |
|------|------|------|
| **Windows x64** | `Game-AI-Foundry-0.0.8-win-x64.zip` | 解压后运行 `Game AI Foundry.exe` |
| **Windows x64** | `Game-AI-Foundry-0.0.8-portable.exe` | 便携版 |
| **Windows x64** | `Game-AI-Foundry-0.0.8-setup.exe` | NSIS 安装包 |

> 未签名：Windows 可能 SmartScreen 提示。macOS 包需在 Apple Silicon 上另打。

## Bug 修复

- **IT / Pi · DeepSeek 400**：官方已下架 `deepseek-chat`，只认 `deepseek-v4-flash` / `deepseek-v4-pro`。加载配置时自动改写并写回；运行时也会映射旧名
- **对话打开狂滚**：取消每次 `smooth` 滚到底；按会话记住 scrollTop，打开瞬间定位

## 纯净机使用

1. 解压并打开 **Game AI Foundry**
2. 若 IT 仍异常：设置 → Provider / IT 实例 model 确认为 `deepseek-v4-flash`（或 `deepseek-v4-pro`）后保存
3. 其余同 v0.0.7

说明 → 本文件 · 打包 → [`RELEASE.md`](RELEASE.md)

## 已知限制

- 同 v0.0.7：layout 启发式、一整局真人验收未作门禁、GUI 不可编辑 content_class、未代码签名
