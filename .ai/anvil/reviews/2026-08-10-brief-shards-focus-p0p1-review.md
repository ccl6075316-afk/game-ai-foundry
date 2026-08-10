# 评审报告：Brief 分册 + Focus P0/P1（整包）

## 元数据

| 字段 | 值 |
|------|----|
| Reviewer | anvil-lead |
| MR / Commit | 未提交工作区（`main` ahead 1 + 本包未 commit） |
| Author | doers：shards / focus-read / focus-write-p1 |
| Review Date | 2026-08-10 |
| Status | `CHANGES REQUESTED` |
| Spec | `docs/superpowers/specs/2026-08-10-brief-catalog-shards-design.md` · `…/2026-08-10-document-focus-and-stable-ids.md` |
| Plans | shards-search · planner-focus-read-loop · planner-focus-write-p1 |

**Loaded standards:** Anvil review skill。

**变更规模：** Large（~+1000 行；新模块 `brief_shards` + host_chat/GUI/CLI/docs）

---

## 1. 自动化预检

| 检查项 | 命令 | 结果 |
|--------|------|------|
| 单测 | `python -m unittest test_brief_shards test_host_chat test_pi_foundry_tools test_brief_scenes_systems -q` | **PASS** 121 |
| 冒烟 | catalog upsert 写文件；无 focus 拒写；description 截断 | PASS |

---

## 2. 安全扫描

- `resolve_shard_path` 拒 `..` — OK。  
- `brief search` / `shard load` 只读且已进 brief 白名单；`migrate` 未放行 brief — OK。  
- 无新密钥/网络面。

---

## 3. Karpathy / 简化

- 分册 + focus + 子串搜索，无向量 — 符合 Spec。  
- `host_chat` 继续膨胀（focus + patch 分支）— 可接受为阶段债；P2 再拆模块。

---

## 4. 发现

### Critical

无（无崩溃/越权确定性洞）。

### Important（合并前建议修）

1. **`deep_merge_brief` 绕过 focus 拒写**  
   - `_apply_parsed`：有 `brief_patches` 时走 `apply_brief_patches(enforce_focus=True)` — OK。  
   - **否则**若模型交整份 `artifact.draft_brief`，仍 `deep_merge_brief`，可改写 `project.scenes` / `systems` 正文，**不校验 focus**。  
   - 与验收句「无 focus 时无法静默改场景/系统正文」冲突。  
   - **建议（任选）**：  
     - chat 模式对含 scenes/systems 正文的整稿 merge：剥离 body 或拒绝并提示用 patches；或  
     - merge 前对 scenes/systems 条目跑与 patch 相同的 focus 闸。

2. **`pinBriefFocus` 异步竞态**  
   - GUI `void hostChatFocus(...)` 不 await；用户点「钉住」后立刻发聊天，CLI 可能尚未写入 session.focus → 本轮仍无 focus / 拒写或仍灌薄目录无 shard。  
   - **建议**：`pinBriefFocus` 改为 `async` 并在相关路径 `await`；或 turn 前带 focus 参数直传 CLI。

3. **纯 legacy 厚工程（如未 migrate 的 fishing）**  
   - `brief_uses_catalog` 为 false → upsert **不写分册**（符合设计），但 chat 仍 `enforce_focus=True`。  
   - 用户未点看板/VT 时，策划 **无法** 用 upsert 改场景（会报错）— 产品正确，但 UX 需可见「当前 focus」提示，否则像坏了。  
   - **建议**：GUI 顶栏或策划条显示 `focus: scene/spot_select`；无 focus 时发场景补丁前宿主提示点选。

### Suggestions

- `validate_focus_allows_write`：`focus.kind=asset` 且 `id` 为空时放行任意资产 — 应收紧为必须带 id。  
- enrich / makeability 仍灌全稿 — 已知；大工程仍慢。  
- `load_shard` 失败时 `build_focus_context` 仍可能不设 `focus_error`（scene 分支 `except: pass`）— 建议回显错误。  
- Board 钉住依赖 `onPin`；确认空场景（无缩略图）仍可钉 — 需 UI 上 pin 在无图时可用（抽查 VtThumb）。

---

## 5. 已通过的能力（相对上次 BLOCKED）

| 项 | 状态 |
|----|------|
| brief search / shard load 白名单 | 已修 |
| session.focus + CLI/IPC | 已有 |
| GUI/VT/审查钉 focus | 已有 |
| catalog upsert → 分册文件 | 已有（有测） |
| patch 路径 focus 拒写 | 已有（有测） |
| 注入 description/loop 截断 | 已有 |

上次 review 的 P0 读闭环缺口 **已闭合**；本轮阻塞点转到 **整稿 merge 旁路** 与 **focus 异步竞态**。

---

## 6. 裁决

**Status: `CHANGES REQUESTED`**

- 基础设施与 patch 主路径质量够，单测绿。  
- **不建议在未处理 Important-1（deep_merge 旁路）前宣称 focus 写闸完成**；Important-2 强烈建议同批修。  

**最小合并门槛：** 修 Important-1；Important-2 至少 await pin 或 turn 携带 focus。

---

## 7. Resume

- 修 deep_merge 旁路 + pin await → 复测 → 再标 APPROVED → 用户确认后 commit。  
- fishing `brief shard migrate` + description 语义搬家仍属另任务。
