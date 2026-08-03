# 评审报告：`2026-08-03-working-tree-gate`

## 元数据

| 字段 | 值 |
|------|----|
| Reviewer | anvil-lead |
| MR / Commit | **整棵未提交工作区**（非单一主题） |
| Author | 本会话多主题累积 |
| Review Date | 2026-08-03 |
| Status | `BLOCKED`（作为**单一合并单元**）/ 分主题见下 |

---

## 0. 范围 triage

工作区同时包含至少 **4 个独立产品主题**。把它们当成一次 commit / 一次「全过」会破坏可回滚性与审查可追溯性。

| 桶 | 主题 | 代表路径 | 既有审查 |
|----|------|----------|----------|
| A | apilio 生图模型名归一化 | `cli/gamefactory.py`（normalize）、`test_image_api_routing.py` | 无独立报告；本闸复审 |
| B | prompt craft 跟 host | `llm_config.py`、ProviderSettings、`GUI-CONFIG`、`test_llm_config` | [prompt-follow-host-review](2026-08-03-prompt-follow-host-review.md) **APPROVED** |
| C | 北极星失败清盘 | `visual_target.py`、`test_visual_target.py` | [visual-target-fail-cleanup-review](2026-08-03-visual-target-fail-cleanup-review.md) **APPROVED** |
| D | IT 只读加宽 + shell + 未完成叙述催办 | `inspect_*` / `conversations_*` / `shell_*` / `pi_*` / diagnose / GUI 文案 | Spec：`it-broad-read` / `it-shell`；**本闸首审** |

`cli/gamefactory.py` **同时**含 A（normalize）与 D（register_*_commands）——提交时必须拆 hunk 或按依赖顺序合入。

---

## 1. 自动化预检（本闸）

| 检查项 | 命令 | 结果 |
|--------|------|------|
| 相关单测 | `python -m unittest test_image_api_routing test_llm_config test_visual_target test_it_broad_read test_shell_run test_pi_unfinished_nudge test_pi_tool_finalize -q` | **PASS**（61） |
| GUI tsc | 未跑 | N/A（GUI 改动极小） |

---

## 2. 安全扫描

| 类别 | 发现 | 严重级别 | 状态 |
|------|------|----------|------|
| Shell `shell=True` | cwd 仅限仓库/`~/.gamefactory`，**命令本身不沙箱**；可读写 cwd 外绝对路径、联网等 | High（产品接受） | **规格已确认**（`it-shell.md`：命令不限制 + 信任本会话） |
| inspect 读 config | 密钥字段 / `sk-` 脱敏 | — | OK（有测） |
| 路径逃逸 | `Path.resolve` + allow_roots | — | OK（设计正确；测覆盖） |
| 硬编码密钥 | 无 | — | OK |

**安全结论：** CLEAN *相对规格*；运维须知：IT +「信任本会话」≈ 本机授权 shell。

---

## 3. 分主题门禁

### A — `normalize_image_model`（apilio 503）

| 项 | 结论 |
|----|------|
| 设计 | OpenRouter 保留 `openai/`；其它网关剥前缀 — 对症 |
| 测 | apilio bare + prefixed 覆盖 |
| 门禁 | **APPROVE**（小） |

### B — prompt 跟 host

| 项 | 结论 |
|----|------|
| 既有审查 | APPROVED |
| 残余 Medium | host 有 key 无 base 时仍可能经 `resolve_host` 继承 **image.api_base**（手改 config）；本闸复现：host 无 key 时 `source=prompt` 仍可吃到 host 解析出来的 image key/base |
| 门禁 | **APPROVE**（残余不阻塞主目标） |

### C — visual-target 失败清盘

| 项 | 结论 |
|----|------|
| 既有审查 | APPROVED（H1 selected.png 已修） |
| 残余 M1 | 先清再生成 → 失败会丢掉上一轮候选 |
| 门禁 | **APPROVE** |

### D — IT broad-read / shell / unfinished nudge

| 项 | 结论 |
|----|------|
| Spec | broad-read + shell 用户已 confirmed |
| 功能 | 白名单、`--i-confirm`、brief 无 shell、输出截断/脱敏、未完成叙述催 1–2 轮 + 轮次上限文案 |
| 对抗 | shell 无命令白名单 = 规格明示，不升格为 BLOCK；建议文档/IT skill 再强调风险 |
| 测 | `test_it_broad_read` / `test_shell_run` / `test_pi_unfinished_nudge` / `test_pi_tool_finalize` 在套件内 |
| 门禁 | **APPROVE**（接受产品风险） |

---

## 4. Karpathy（整树）

| 原则 | 结论 |
|------|------|
| Think Before Coding | 各主题动机清楚；整树混提会掩盖 shell 风险面 |
| Simplicity First | 分模块合理；不宜再揉成更大抽象 |
| Surgical Changes | **FAIL as monolith** — 无法把每行归到单一需求 |
| Goal-Driven Execution | 分主题测在；缺整树「一次提交」验收标准 |

**Karpathy Score（整树）：** 2/4 → **不能作为单 MR 批准**

---

## 5. 发现项摘要

### Critical
无（相对已确认 Spec）

### High
| # | 描述 | 处置 |
|---|------|------|
| H-tree | 工作区不可作为单一合并单元 | **BLOCK 整树**；要求分 commit |
| H-shell | IT shell ≈ 本机任意命令（信任会话自动批准时） | 不阻塞 D（规格接受）；发布说明 / diagnose 需可见 |

### Medium
| # | 桶 | 描述 |
|---|----|------|
| M-B1 | B | host↔image base 继承空洞（既有 review） |
| M-C1 | C | 失败 regenerate 丢掉上一轮候选 |
| M-D1 | D | `gamefactory.py` 底部 register 与 normalize 同文件，提交需拆 |

### Low
| # | 描述 |
|---|------|
| L1 | GUI `App.tsx` / `agentReply` / `roles` 改动未单独 tsc（体量小） |

---

## 6. 门禁结论

| 门禁项 | 状态 |
|--------|------|
| 整树作为一次 commit / 一次「全过」 | **BLOCK** |
| 桶 A / B / C / D 各自 | **APPROVE**（含已记录残余） |
| 安全相对 Spec | CLEAN + 运维须知 |
| 相关单测 61 | PASS |

### 结论

- [x] **BLOCK** — 禁止把整棵脏树当成一个已审查变更合并  
- [x] **分主题 APPROVE** — 可按下列顺序分别提交（你开口后再 commit）

建议提交顺序：

1. **A** image model normalize + 相关测  
2. **B** prompt follow host（含既有 review 文档）  
3. **C** visual-target fail cleanup（含 review）  
4. **D** IT inspect/conversations/shell + pi nudge + diagnose/GUI 文案 + `gamefactory` register 段  

### 评审备注

若你只想「再确认北极星清理」：C 仍为 APPROVED，见既有报告。  
本次 `review` 按**整棵脏树**解释；若只要某一桶，请点名桶号或文件。
