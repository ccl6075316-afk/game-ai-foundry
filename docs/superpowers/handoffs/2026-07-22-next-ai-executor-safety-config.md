# 交接：下一台电脑 AI 要做的事（2026-07-22）

> **状态：B v2 选项 1 及后续 ACP / app-server 已合入 main（勿再按本文实现）。**  
> 保留本文作历史上下文；新任务见文末「下一步」。

---

## 0. 一句话（原任务，已完成）

**原目标**：Feature B v2「配置层安全旋钮」—— Codex / Cursor / Hermes 沙箱与放行策略可 GUI 配置并写入 config，`agent turn` argv 真正吃到配置。

**已交付（main，约 `92f88f6` 起）**：

| 项 | 提交线索 |
|----|----------|
| 执行器 safety 配置 | `92f88f6` feat: executor safety config… |
| 同事级覆盖 | `fd7e870` |
| Cursor ACP mid-turn | `882969f` |
| Hermes ACP mid-turn | `139fe7a` / `6e9ef5d` |
| Codex app-server 审批 | `c4c6da4` |

原 Spike 的选项 1 / 2 / 3 **均已落地**；不要再按「明天只做选项 1」开工。

---

## 1. 已经做完（勿重复）— 更新至 2026-07-23

| 项 | 状态 |
|----|------|
| Electron 39 + Pi Node 22.19+ | ✅ |
| 执行器模型档位 A | ✅ |
| Feature B v1 Pi 权限卡 | ✅ |
| B v2 配置层 + ACP / app-server | ✅ |
| style_group / art_tokens / identity_anchor | ✅ |
| DocsPreview 风格只读（Phase 3） | ✅ `9c27486` |
| icon_kit 单物体展开 + `image.bulk_model` | ✅ `8efae99` / GUI `5868092` |
| icon_kit items 对象 + `production.collectible_items` | ✅（见 Spec `2026-07-23-icon-kit-item-objects-design.md`） |

---

## 2. 原「明天要实现」正文

~~见历史修订；已完成，以下章节作废：~~

<details>
<summary>折叠：原 §2–§7 实现说明（已完成）</summary>

原文档要求实现 Codex `sandbox` / Cursor `permission_mode` / Hermes `yolo`，并禁止「关 yolo 仍 capture_output」。  
实现与验证已合入；细节以代码与 `docs/GUI-CONFIG.md` 为准。

</details>

---

## 3. 下一步（给新会话）

按用户优先级 **135** 剩余卫生与可选增强：

1. ~~icon_kit items 对象~~ — 已做  
2. ~~风格 Phase 3 GUI~~ — 已做  
3. 文档：本文已标 DONE；见 [`docs/RELEASE-NOTES-UNRELEASED.md`](../../RELEASE-NOTES-UNRELEASED.md) 的 icon_kit breaking  
4. 仍可选：`live-executor-model-list`、完整 E2E smoke、`models_by_type`、kit 内 style 锚 + bulk img2img  

开工前：`git pull origin main`，勿重复 B v2 / ACP。

---

## 8. 变更日志

| 日期 | 说明 |
|------|------|
| 2026-07-22 | 初稿：交接 B v2 选项 1 |
| 2026-07-23 | 标 DONE；指向 icon_kit / 风格后续与 UNRELEASED notes |
