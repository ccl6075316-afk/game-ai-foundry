# 架构方案：策划 AI Focus 读闭环（P0）

## 执行元数据

- **Status**：executed
- **Workflow Stage**：code
- **Created**：2026-08-10
- **Updated**：2026-08-10
- **Requirements Source**：[`docs/superpowers/specs/2026-08-10-document-focus-and-stable-ids.md`](../../superpowers/specs/2026-08-10-document-focus-and-stable-ids.md)（用户「准备改造」）
- **Resume Point**：执行 P0
- **Scope**：仅 P0（白名单 + 写入 session.focus + skill）；不含 catalog upsert 写分册、无 focus 硬拒写（P1）

## Goal

让策划主对话真正按 **id + focus** 读分册：工具可调、宿主会钉 focus、skill 与能力一致。

## Tasks

### T1：brief Pi 白名单放行只读 search / shard load
- `cli/pi_foundry_tools.py`：`_ALLOWED_PREFIXES` + `_BRIEF_ALLOWED_PREFIXES` 增加 `("brief","search")`、`("brief","shard","load")`
- 更新 brief 工具说明文案
- 测：白名单允许 / 仍禁止 shard migrate（mutate）

### T2：session focus API
- `host_chat.set_session_focus` / `clear`；校验 kind+id
- CLI：`brief chat focus --session-id … --kind scene --id X [--json]`；`--clear` 清空
- Electron + `vite-env`：`hostChatFocus`
- 单测

### T3：自动钉 focus 的生产路径
- `makeability-answer`：从缺口 `write_paths` / `target_paths` 解析首个 `scenes[id=…]` 或 `systems[id=…]` → 设 focus
- 主对话 `artifact.focus`：若模型返回则写入 session（可选）
- GUI：VT restyle/pick 已知 `sceneId` 时调用 `hostChatFocus`；看板北极星条点击场景缩略图设 focus（可先只设 focus，不必改图）

### T4：skill / payload 对齐
- `resources/skills/orchestrator/host-chat.md`：focus 纪律 + 真实 FOUNDRY_TOOL 命令
- payload note 指向 focus 与 search/load
- 更新 focus Spec 实现清单状态

## 验收

1. brief profile 可跑 `brief search` / `brief shard load`，不可 migrate 无 confirm 随意写（migrate 本就不在 brief 白名单）
2. `brief chat focus` 后 `run_turn` chat payload 含对应 `focus_shard`（legacy 或 catalog）
3. makeability-answer 后 session.focus 指向解析到的 scene/system id
4. 单测绿

## 非目标

- upsert 写分册文件、无 focus 拒写、description 注入截断（P1）
