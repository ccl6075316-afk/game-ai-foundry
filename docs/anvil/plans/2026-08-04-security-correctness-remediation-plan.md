# 修复计划：整仓审查缺陷（按严重程度）

## 执行元数据

- **Status**：confirmed（用户 2026-08-04 拍板开放问题）
- **Workflow Stage**：code（P0）
- **Created**：2026-08-04
- **Updated**：2026-08-04（账本落地：[`docs/solutions/reviews/2026-08-04-whole-project-review-ledger.md`](../../solutions/reviews/2026-08-04-whole-project-review-ledger.md)）
- **Resume Point**：未提交的 F6–F11 与账本一并 commit；P1 仅做 Deferred 表里 High 项（D1/D2），Accepted 勿再改严

## Goal

按严重程度分波次消除审查中的 Critical / Important 缺陷：先收安全与生产正确性，再收稳定性与文档漂移；上帝对象拆分与产品重定位单列、不阻塞 P0。

## Architecture（原则 · 完成优先）

1. **权限放开**：无桥时 mutate/shell 靠白名单 + `--i-confirm` 即可完成需求；有桥时可会话级少打断。
2. **硬闸对准「做错/做不完」**：路径不得逃出 repo；未知 `asset_type` 显式失败；文档勿误导。
3. **出口脱敏**：工具 stdout/stderr redact（次要，不为此加严权限）。
4. **openExternal 白名单**：低成本防乱开协议，不挡正常 https/文档链接。

## Global Constraints

- 不改北极星产品语义（全局 vs 场景效果靶）——那是另一份 Spec；本 Plan 只同步 **docs/skills 与代码已实现的多场景事实**。
- 不在本 Plan 做 `App.tsx` 大拆分（仅列 P2 债）。
- 每个任务：先测后改；波次结束跑相关 unittest。
- Hermes/Codex/Cursor 路径：P0 只动 Pi FOUNDRY_TOOL 与 Electron 路径/`openExternal`；Hermes YOLO 放 P1。

## 波次总览

| 波次 | 严重度 | 主题 | 建议工期 |
|------|--------|------|----------|
| **P0** | Critical | 安全闸 + 资产类型正确性 | 0.5–1 天 |
| **P1** | Important | 稳定性 / agent 默认 / 配置 / 文档漂移 | 1–2 天 |
| **P2** | Minor + 架构债 | 测试补强、ignore、拆上帝对象（可选） | 按需 |

---

## P0 — Critical（必须先做）

### Task P0-1: 权限桥未配置时变更工具 fail-closed

**问题**：`request_mutate_permission` 无 URL 时返回 `"once"` → IT `shell run` 等可变工具自动过。

**Files:**
- Modify: `cli/tool_permission.py`
- Modify: `cli/pi_foundry_tools.py`（若需区分 read-only vs mutate 调用约定）
- Test: `cli/test_tool_permission.py`（及现有 mutate 相关测）

**行为决定（已重钉 · 完成优先）：**
- **无**桥：`shell run` 与其它 mutate 一样，**有 `--i-confirm` 即可执行**（不再无桥必拒）。
- **有**桥：仍可弹批准卡；用户也可选会话信任后少打断（既有 once/turn/session）。
- `request_mutate_permission` 无桥时不再被 `run_allowed_gamefactory` 依赖；helper 无桥返回 `deny` 仅表示「未询问 GUI」，执行路径靠 `--i-confirm`。
- 只读工具不走 mutate 闸。

- [x] 写失败测：无 URL 时 mutate / `shell run` 不得执行
- [x] 写失败测：有 URL + mock approve 仍可执行
- [x] 实现 fail-closed
- [x] 跑 `python -m unittest test_tool_permission test_pi_foundry_tools test_shell_run -q`
- [ ] 更新 `docs/superpowers/plans/2026-07-21-pi-tool-permission-ui.md` 或 AI-HANDOFF 一句：无桥不再 auto-approve（避免与旧 plan「legacy」表述冲突）

### Task P0-2: FOUNDRY_TOOL 子进程输出统一 redact

**问题**：`run_allowed_gamefactory` 原始 stdout/stderr 回灌模型；inspect/shell 已 redact，此处漏。

**Files:**
- Modify: `cli/pi_foundry_tools.py`
- Reuse: `cli/inspect_ops.py`（或抽出共享 `redact_secrets(text) -> str`）
- Test: `cli/test_pi_foundry_tools.py`（或新建 `test_tool_output_redact.py`）

**行为决定：**
- 所有返回给模型的 tool result 文本（含 error）经同一 redact。
- 至少覆盖：`sk-` / `sk-or-` / 常见 `api_key` JSON 字段；可与 inspect 规则对齐并略加强。

- [x] 抽出或复用 `redact_secrets`
- [x] 测：含假 key 的 stdout 回灌后不可见原文
- [x] `run_allowed_gamefactory` 返回前 redact
- [x] 跑相关 unittest

### Task P0-3: GUI 路径统一严格校验

**问题**：`normalizeRepoRel` / `cliArgForRel` 可被中间 `../` 穿越；pipeline/VT/agent 大量依赖。

**Files:**
- Modify: `gui/electron/externalFs.mjs`（`normalizeRepoRel`）
- Modify: `gui/electron/main.mjs`（`cliArgForRel` / `absForRel` 调用点改走严格 resolve）
- Test: `gui/electron/externalFs.test.mjs`（若无则补）

**行为决定：**
- 与 `resolveRepoRel` 同语义：解析后必须仍在 repo（或已登记的 external root）内；否则抛错/返回失败，**禁止 mkdir 越界路径**。
- `projects/x/../../outside` → reject。

- [x] 写失败测：中间 `../` 越界
- [x] 修 `normalizeRepoRel` + `cliArgForRel` 包装
- [x] 抽查 `pipeline-plan` / `visual-target-*` / `open-godot` 仍用新闸
- [x] 跑 electron 单测（项目既有命令）

### Task P0-4: `openExternal` 协议白名单

**Files:**
- Modify: `gui/electron/main.mjs`（`open-external` handler ~1626–1631）
- Test: 若无现成测，加最小 unit 或文档化手动测清单

**行为决定（已确认）：**
- 允许 `https:`；以及 `http:` 且 host 为 `localhost` / `127.0.0.1`（含可选端口）。
- 拒绝 `file:`、`javascript:`、其它 host 的 `http:`、自定义协议、空/相对串。

- [x] 实现白名单
- [x] 非法 URL → IPC 返回 `{ ok: false, error }`，不调用 `shell.openExternal`

### Task P0-5: 未知 `asset_type` 显式失败

**Files:**
- Modify: `cli/gamefactory.py`（~687–694，勿默认 `AssetType.CHARACTER`）
- Test: 对应 validate / image 路径测（新建或扩 `test_matting_validate.py` / pipeline 相关）

**行为决定：**
- 无法解析的 type → 非 0 退出 + 可读错误；**禁止**静默 CHARACTER。

- [x] 写失败测：未知 type → 错误，非 CHARACTER 启发式
- [x] 改 fallback
- [x] 跑相关 unittest

### P0 出口标准

- [x] 上列 5 任务全绿（P0-1 文档一句遗留可随 P1-5）
- [ ] 无桥环境下手动：IT 尝试 `shell run` → 被拒
- [ ] 用户确认后再 commit（建议 message：`fix: fail-closed tool perms, redact tool I/O, harden paths`）

---

## P1 — Important（P0 后）

### Task P1-1: Pipeline 少用 `shell=True` 拼串

**Files:** `cli/pipeline_manifest.py`, `cli/pipeline_runner.py`  
**做法：** 优先 `subprocess` + argv 列表；若短期难全改，至少对 path 参数做 quote/list 化，并测含空格路径。  
- [ ] 定范围（generate/matte 主路径）  
- [ ] 测空格路径  
- [ ] 改 runner 调用

### Task P1-2: Hermes YOLO — 按「完成优先」再定

**原审查建议**：默认 off。  
**产品重钉后**：若默认 off 导致非开发用户 Hermes **需求卡住**，则保持默认开或 GUI「信任本机执行器」一键；安全文案用白话说明会改文件。  
- [ ] 与用户确认最终默认（建议：**维持较开**，与权限哲学一致）
- [ ] 若改默认，补测 + GUI 一句说明

### Task P1-3: 收敛双白名单

**Files:** `cli/safe_cli.py`, `cli/pi_foundry_tools.py`  
**做法：** 单一模块导出允许前缀（或生成对照测：两边 mutate/read 集合断言无意外漂移）。  
- [ ] 抽共享常量或双向 diff 测试  
- [ ] 修已知漂移

### Task P1-4: `load_config` 迁移失败不静默写盘

**Files:** `cli/gamefactory.py`（~109–119）  
**做法：** 迁移异常记录日志；失败时不 rewrite；或写 `.bak` 后明确报错。  
- [ ] 测坏配置不丢原文件  
- [ ] 实现

### Task P1-5: 文档/skills 对齐「已实现的多场景北极星」

**非目标：** 不落地「取消全局伪概念」产品改版（见 brainstorm）。  
**目标：** 停止误导 agent。

**Files（至少）：**
- `docs/AI-HANDOFF.md`（scenes 表补 `visual_reference`；VT CLI 补 `--scene`/`assign`/`status`；删或改 `brief export`）
- `resources/skills/**/visual-target.md`、`commit-brief.md`、`image-generator/generate.md`、`product-host.md` 等仍写全局-only 的
- `AGENTS.md` 一行指向隔离 `projects/<slug>/` + 多场景 VT

- [ ] 对照 `cli/visual_target.py` / `brief.py` 改文档  
- [ ] 注明：style img2img 场景资产优先场景 ref，不默认可回落错场景

### Task P1-6: 工程绑定「勿静默 briefs[0]」（小修）

**Files:** `gui/src/App.tsx`（`resolveBriefForPlan` / `loadInitial`）  
**做法：** 无 lastBrief / 无绑定 → 保持未选择，不绑第一个工程。  
- [ ] 复现路径测或注释+手动清单  
- [ ] 改逻辑

### P1 出口标准

- [ ] P1-1…P1-6 完成或明确 defer 项写回本文件  
- [ ] 用户确认后 commit

---

## P2 — Minor / 架构债（可记债）

| ID | 项 | 说明 |
|----|-----|------|
| P2-1 | redact 扩展非 `sk-` token | 与 P0-2 同函数迭代 |
| P2-2 | `external-projects.json` gitignore | 防本机路径误提交 |
| P2-3 | 示例 brief 坏 png 路径 | 改占位或去掉 |
| P2-4 | 安全回归测 | `normalizeRepoRel` 越界、`openExternal`、tool 回灌 redact 的 e2e 级 |
| P2-5 | 拆 `App.tsx` / `main.mjs` | ChatCommands / ProjectBinding / VisualTargetFacade；**单独 Spec** |
| P2-6 | 北极星产品重定位 | 按 brainstorm 升 Spec；**不在本 Plan** |

---

## 明确不做（本 Plan）

- 取消 `project.visual_reference` 或强制「仅场景靶」产品流  
- 重写全部 ACP 执行器权限模型  
- 大范围 GUI 设置 schema 校验（可另立）

## 开放问题 → 已确认

| 项 | 决定 |
|----|------|
| P0-1 无桥 | **放宽**：shell 与其它 mutate 均只需 `--i-confirm`（完成需求优先） |
| P0-4 openExternal | `https` + `http://localhost`/`127.0.0.1`（防做错打开，成本低） |
| P1-2 Hermes YOLO | 默认 off **改评估**：若挡需求可维持默认开或 GUI 一键信任（P1 再定） |
| 产品权重 | **需求无法完成 > 信息危险**；权限剧场不作为主防线 |

## 建议执行顺序（单线程）

```text
P0-1 → P0-2 → P0-5 → P0-3 → P0-4 →（commit）
→ P1-5（文档可与代码并行）→ P1-2 → P1-1 → P1-3 → P1-4 → P1-6 →（commit）
→ P2 按需
```
