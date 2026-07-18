# Game AI Foundry v0.0.6

**主更新：工程隔离 + 北极星视觉定稿 + 环境错误可读** — 每个游戏进 `projects/<slug>/`；策划侧生成/选用北极星；检测失败会写清原因方便转发支持。

相对 [`v0.0.5`](RELEASE-NOTES-0.0.5.md)。

## 下载

| 平台 | 文件 | 说明 |
|------|------|------|
| **Windows x64** | `Game-AI-Foundry-0.0.6-win-x64.zip` | 解压后运行 `Game AI Foundry.exe` |
| **Windows x64** | `Game-AI-Foundry-0.0.6-portable.exe` | 便携版 |
| **Windows x64** | `Game-AI-Foundry-0.0.6-setup.exe` | NSIS 安装包 |

> 未签名：Windows 可能 SmartScreen 提示。macOS 包需在 Apple Silicon 上另打。

## 新功能 / 体验

- **工程目录隔离**：新 Brief 导出到 `projects/<slug>/`（brief、pipeline、plans、output、game 同目录）；旧扁平布局仍兼容
- **北极星图（Visual Target）**：保存 Brief 后在**策划**侧生成候选 → 选用写入 `visual_reference`；都不满意可「换风格」改 `art_direction` 再生成
- **项目经理流程**：① 生成流水线 → ② 运行资产生成（北极星归策划定稿）
- **环境检测可读**：启动 /「重新检测」在对话里列出缺 API Key、缺 FFmpeg 等；顶部「检测异常」；弹窗含配置类错误，方便复制发给支持
- **策划选项可点**：气泡内 `choices` 可点；正文 `1. / 2.` 列表也会推断成按钮
- **legacy 迁移**：`project migrate-layout` 可将旧 brief/manifest 迁入 `projects/<slug>/`

## Bug 修复

- **缩略图只显示「图片」**：候选图路径误裁成 `output/...` 丢掉 `projects/<slug>/`；预览与「点击查看」现已解析正确
- **`visual_reference` 误写风格散文**：校验 + autofix 清掉，风格只进 `art_direction`
- Brief / CLI 路径：`resources/` ↔ `cli/resources/` ↔ `projects/` 别名解析

## 纯净机使用

1. 解压并打开 **Game AI Foundry**
2. **设置**填图像 API Key → 顶部「重新检测」（有红字先修）
3. **策划**商量 → 保存 Brief → **生成北极星图**并选用
4. **项目经理** → 生成流水线 → 运行资产生成

说明 → 本文件 · 打包 → [`RELEASE.md`](RELEASE.md)

## 已知限制

- 执行器 CLI（Hermes / Codex / Cursor）仍需本机安装
- 已跑过的 `prompt.craft` 在选定新北极星后需 reset 再含文案重跑
- macOS 本版若未附包，请自行 `scripts/build-release.sh`
