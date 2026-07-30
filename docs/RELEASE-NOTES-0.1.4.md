# Game AI Foundry v0.1.4

**主更新：纯净机开箱（可迁移内嵌 Python）+ 制作审查回填主会话 + IT 自然语言配实例**

相对 [`v0.1.3`](RELEASE-NOTES-0.1.3.md)。修复「朋友机没装系统 Python → IT 报 exit 9009」：旧包内嵌的是不可迁移 venv，且找错 `python.exe` 路径。本版改为独立 CPython 拷贝；制作审查结论注入主策划上下文；IT 可通过对话改 Thinking / 模型等。

## 下载

| 平台 | 文件 | 说明 |
|------|------|------|
| **Windows x64（推荐）** | `Game-AI-Foundry-0.1.4-setup.exe` | NSIS：可选安装目录、干净卸载、**应用内自动更新** |
| **Windows x64** | `Game-AI-Foundry-0.1.4-win-x64.zip` | 解压即用；无自动更新 |
| **Windows x64** | `Game-AI-Foundry-0.1.4-portable.exe` | 便携版；无自动更新 |
| **macOS arm64** | 见 [v0.1.1](https://github.com/ccl6075316-afk/game-ai-foundry/releases/tag/v0.1.1) 或本页若已附带 | 手动解压；暂无应用内自动更新 |

> Windows 未签名：可能 SmartScreen 提示。

## 新功能 / 修复

- **可迁移内嵌 Python**：Release 不再依赖打包机 `pyvenv.cfg home=`；路径优先 `resources/python/python.exe`
- **Release 禁止回退系统 `python`**：避免纯净机 exit 9009；缺内嵌时错误更明确
- **制作审查 → 主 agent**：审查结论写入会话 + 每轮注入 `latest_makeability_review`（思考过程不进，回答进）
- **IT 开箱剧本**：`setup agents instances upsert`（模型 / Thinking）；首跑引导装工具链 / Hermes；Provider 激活时同步 Pi 预设与 `image.use_text_provider`
- 继承 v0.1.3：`electron-updater` ESM 修复、Windows `latest.yml` 自动更新

## 纯净机使用（Windows 推荐）

1. 安装 **`Game-AI-Foundry-0.1.4-setup.exe`**（覆盖 0.1.3）
2. **设置** → Provider 填一次文本 API Key；等待顶部芯片变绿（FFmpeg/Godot/.NET 可自动下）
3. **策划 / IT** 开箱可聊；环境/换模型/Thinking/装 Hermes → 跟 **IT** 说自然语言即可
4. 项目经理需 Hermes：对 IT 说「装 Hermes」；生图若文本厂商不支持，再给 IT 一个可出图 Key

说明 → 本文件 · 打包策略 → [`RELEASE.md`](RELEASE.md)

## 已知限制

- 未代码签名 / macOS 未公证；Mac / zip / portable **不做**应用内自动更新
- 视频 Seedance、程序员 Codex（需 npm）仍可能要额外 Key / 本机工具
- IT 不改 Foundry 源码 / 大段玩法 C#
