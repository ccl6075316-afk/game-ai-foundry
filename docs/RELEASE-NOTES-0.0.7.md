# Game AI Foundry v0.0.7

**主更新：类型化出图 + 审图 + layout 进 Godot** — `content_class` / `view` 驱动结构化出图；侧栏可审图；`production.layout` 由 scaffold/assemble 写入场景 World 节点。

相对 [`v0.0.6`](RELEASE-NOTES-0.0.6.md)。

## 下载

| 平台 | 文件 | 说明 |
|------|------|------|
| **Windows x64** | `Game-AI-Foundry-0.0.7-win-x64.zip` | 解压后运行 `Game AI Foundry.exe` |
| **Windows x64** | `Game-AI-Foundry-0.0.7-portable.exe` | 便携版 |
| **Windows x64** | `Game-AI-Foundry-0.0.7-setup.exe` | NSIS 安装包 |

> 未签名：Windows 可能 SmartScreen 提示。macOS 包需在 Apple Silicon 上另打。

## 新功能 / 体验

- **content_class / project.view**：brief 声明内容类与视角；prompt craft 按类型结构化组装；`prop_stateful` 多状态 img2img
- **production.layout**：derive 写出 regions + placements；**scaffold / assemble** 按 `xy_norm * viewport` 在 `World` 下放置 Sprite2D（纹理 `assets/props/{asset}_nobg.png`）
- **资产审查表**：侧栏「资产」采纳 / 重生成 / 本地替换；软 review 不阻塞管线
- **双图 Provider + 顶层 proxy**：主图与 bulk 可分 Provider；GUI Provider 页「网络」
- **icon_kit**：逐项出图（非网格切图）；套内 img2img；条目可为带 `usage` 的对象；`collectible_items` 绑定
- **DocsPreview / 看板**：只读展示 `art_tokens`、`style_group`、`view`、`content_class`
- **示例 brief**：`view: side` + sparse 背景 + 可摆放 prop，derive 即有非空 placements

## Breaking

- **`icon_kit` 产物布局**：不再 sheet + `image slice`；改为 `{kit_id}__{item_slug}_raw.png` / `_nobg.png`。旧工程需改路径。

## 纯净机使用

1. 解压并打开 **Game AI Foundry**
2. **设置**填图像 API Key（可选顶层 proxy / 批量 Provider）→ 顶部「重新检测」
3. **策划**商量 → 保存 Brief（尽量带 `view` / `content_class`）→ 北极星定稿
4. **项目经理** → 生成流水线 → 运行资产生成 → 需要时打开侧栏审图
5. `production derive` → `godot scaffold` / 管线 assemble 后检查 `scenes/main.tscn/World` 是否有 prop

说明 → 本文件 · 打包 → [`RELEASE.md`](RELEASE.md)

## 已知限制

- 执行器 CLI（Hermes / Codex / Cursor）仍需本机安装
- layout 坐标为规则启发式，可手写覆盖；不做背景 vision 摆放 / LLM 精修
- **一整局**「聊天→可玩且看见摆好道具」的真人验收未作为本版门禁；单测已覆盖放置逻辑
- GUI 仍不可编辑 `content_class` / `view` 写回 brief（只读预览）
- macOS 本版若未附包，请自行 `scripts/build-release.sh`
- 未代码签名
