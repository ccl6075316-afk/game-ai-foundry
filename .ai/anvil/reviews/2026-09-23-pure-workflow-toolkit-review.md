# Review Report: `pure-workflow-toolkit`

## Metadata

| Field | Value |
|-------|-------|
| Reviewer | anvil-lead |
| MR / Commit | working tree on `codex/pure-workflow-toolkit`；未 commit |
| Baseline | `main=f26aa70caa302a64a8ca58f6ccde5dc340c99451` |
| `origin/main` | `f26aa70caa302a64a8ca58f6ccde5dc340c99451` |
| Review Date | 2026-09-24 |
| Status | `APPROVED`（4 个已复现的既有 baseline errors 获得显式例外） |

---

## 1. Automated Pre-checks

| Check | Command | Result | Notes |
|-------|---------|--------|-------|
| Compile | `python -m compileall -q cli` | PASS | exit 0 |
| Format | `git diff --check` | PASS | exit 0 |
| Lint | 仓库无独立 lint 配置 | N/A | 以 compile、diff check 与 unittest 替代 |
| Type Check | 仓库无独立 type-check 入口 | N/A | 未新增第三套类型检查链 |
| Changed-scope tests | `python -m unittest -q test_workflow_cmds test_pipeline_heal test_host_run_assets test_shell_run test_active_skill_scan` | PASS | 49 tests，0 failures |
| Full unittest | `cd cli && python -m unittest discover -s . -p 'test_*.py'` | PASS_WITH_BASELINE_EXCEPTIONS | 594 tests，0 failures，4 errors，2 skipped |
| Baseline reproduction | 在 `git archive HEAD` 的独立基线目录运行 `test_brief_transitions test_visual_target` | PASS | 同样 4 errors，证明不是本分支新增 |
| CLI surface | 根 `--help` 与六个 `workflow <cmd> --help` | PASS | workflow 可发现；无 `agent/agents/hermes` 或旧根 `context` |
| Read-only behavior | `workflow context/status/validate` 行为测试 | PASS | 临时项目树、mtime、内容与 config 全部不变 |

允许的 4 个既有 errors：

1. `/Users/czl/projects/game-ai-foundry/cli/test_brief_transitions.py:42` — 缺少 `resources/magic-prince-brief.json`。
2. `/Users/czl/projects/game-ai-foundry/cli/test_visual_target.py:320` — CJK guard 拒绝测试 Brief 的中文 prompt。
3. `/Users/czl/projects/game-ai-foundry/cli/test_visual_target.py:290` — 同上。
4. `/Users/czl/projects/game-ai-foundry/cli/test_visual_target.py:475` — 同上。

这些错误在基线 commit 的独立归档中均为相同 4 项；本分支没有新增 failure/error。

---

## 2. Security Scan

| Category | Finding | Severity | Status |
|----------|---------|----------|--------|
| Hardcoded Secrets | 改动源码与运行时文档未发现真实 key/token；测试仅使用明显 fake 值 | — | CLEAN |
| Injection Risks | 未新增 `eval/exec/pickle/yaml.load`；shell 仍要求 `--i-confirm` 且 cwd 受 allowlist 限制 | — | CLEAN |
| XSS Vulnerabilities | GUI/浏览器渲染层已删除，当前输出为 CLI/JSON | — | N/A |
| Dependency CVEs | `requirements.txt` 无变更；Electron/React/Vite lockfile 已删除 | — | CLEAN |
| Sensitive Data in Logs | stdout/stderr、command、cwd、timeout error 均递归脱敏；覆盖 sk、Bearer、`api_key=`、`OPENAI_API_KEY=`、`--token` 等形态 | Medium 已修复 | CLEAN |

安全验证位置：

- `/Users/czl/projects/game-ai-foundry/cli/shell_ops.py:15` — 统一 secret 正则。
- `/Users/czl/projects/game-ai-foundry/cli/shell_ops.py:61` — `redact_text`。
- `/Users/czl/projects/game-ai-foundry/cli/shell_ops.py:65` — 递归 `redact_result`。
- `/Users/czl/projects/game-ai-foundry/cli/shell_cmds.py:35` — 缺少 `--i-confirm` 时拒绝执行。
- `/Users/czl/projects/game-ai-foundry/cli/test_shell_run.py:38` — JSON、文本、timeout 与 CLI/env 参数脱敏测试。

**Security Verdict:** CLEAN

---

## 3. Karpathy Adversarial Principles

| Principle | Adversarial Question | Reviewer Answer | Verdict | Severity |
|-----------|---------------------|-----------------|---------|----------|
| Think Before Coding | 是否把外部 Agent 判断误塞回项目？ | 没有；Workflow 只组合既有 Brief/Production/Pipeline/Runner，不新增 RPC、队列或第二状态库。 | PASS | — |
| Simplicity First | 新抽象是否只是搬家？ | `workflow` 是薄入口；`contract/state` 只做枚举、失败归类和 manifest 只读分类，调用方仍复用原模块。 | PASS | — |
| Surgical Changes | 删除和改写能否追溯到“去 GUI/去内置 Agent、保留 pipeline 与核心思想”？ | 可以；GUI、Agent/Hermes/Pi/ACP/executor 成组删除，保留能力与新六命令均有对应 Plan 任务。 | PASS | — |
| Goal-Driven Execution | 测试是否证明外部 Agent 能正确接管？ | 覆盖 JSON 合同、真实 root 零写入、init 回滚、Quick Start gate、runner 委托、active Skill、失败分诊和 shell 脱敏。 | PASS | — |

**Karpathy Score:** 4/4

---

## 4. Adversarial Dimension Review

### 4.1 Design — PASS

- `/Users/czl/projects/game-ai-foundry/cli/workflow_cmds.py:505` 的 `run` 直接委托现有 asset runner。
- `/Users/czl/projects/game-ai-foundry/cli/workflow_cmds.py:594` 的 `resume` 直接委托既有 retry runner。
- `/Users/czl/projects/game-ai-foundry/cli/workflow/contract.py:12` 固定状态枚举；`contract.py:45` 固定 failure kind。
- `/Users/czl/projects/game-ai-foundry/cli/workflow/state.py:19` 只读汇总 manifest，不创建第二状态。
- 删除 GUI/内置 Agent 后仍保留唯一确定性执行引擎，没有新增品牌专属适配层。

### 4.2 Functionality — PASS

已验证的边界：

- 缺文件、非法 JSON、非法 manifest 依赖/状态、unsupported stage → `ok=false`、exit 1、合法 failure kind。
- `context/status/validate` → 真实 root 下无磁盘或 config 写入。
- `init` → 先内存构建，随后顺序提交；manifest/progress 写失败会回滚新建文件并保留既有状态。
- `validate` 存在合法 manifest 时透传 manifest 状态；pending manifest 返回 `pending/run`，failed manifest 返回 `failed/resume`，不再误导为 human review。
- runner 返回 paused/blocked/failed/completed → 由既有状态分类映射到稳定 `status/next_action`。
- shell timeout、CLI 参数、环境变量和输出中的凭据均在用户可见字段中脱敏。

### 4.3 Complexity — PASS

- 删除量远大于新增量；没有通用 Agent framework、RPC 或数据库。
- `init` 的内存构建与回滚是多文件一致性的必要复杂度，而不是投机抽象。
- `host` 保留为确定性 repair bridge；内部字段已统一为 `external_agent` / `needs_external_agent` / `triage_*`。

### 4.4 Naming — PASS

- `workflow context/init/run/resume/status/validate` 可从名称预测职责。
- `triage_fit/triage_tip/triage_advice` 明确表示外部 Agent 分诊，不再使用 `pm_*` 或品牌名。
- `stopped_reason=needs_external_agent` 与 JSON 合同一致。

### 4.5 Comments — PASS

- `/Users/czl/projects/game-ai-foundry/cli/host/run_assets.py:31` 已改为 external Agent/CLI 消费者。
- `/Users/czl/projects/game-ai-foundry/cli/pipeline_heal.py:470` 已移除 GUI 路径叙事。
- 当前操作代码与 active Skill 无 stale GUI/Hermes comment；历史文档有明确“已移除/历史”说明。

### 4.6 Style & Consistency — PASS

- 新 Python 沿用 Click、类型标注、`Path` 和 JSON 输出风格。
- 说明文字为中文；命令、路径、JSON 字段和枚举为英文。
- `compileall` 与 `git diff --check` 均为 0。

### 4.7 Context — PASS

- `/Users/czl/projects/game-ai-foundry/gui` 不存在；根启动与 GUI Release 脚本不存在。
- 根 README 明确项目是供外部 Agent 使用的纯 CLI / Workflow 工具箱：`/Users/czl/projects/game-ai-foundry/README.md:3`。
- 当前 runtime、active Skill 与入口文档扫描无旧品牌/GUI 活语义；剩余命中仅为明确标记的历史说明。
- `main`、`origin/main` 均保持 `f26aa70...`；仓库不存在 `master` ref。

### 4.8 Tests — PASS

- `/Users/czl/projects/game-ai-foundry/cli/test_workflow_cmds.py:102` 拒绝非法枚举与缺失 failure kind。
- `/Users/czl/projects/game-ai-foundry/cli/test_workflow_cmds.py:201` 走真实 root 验证只读边界。
- `/Users/czl/projects/game-ai-foundry/cli/test_workflow_cmds.py:339` 与 `:375` 验证 init 中途失败回滚。
- `/Users/czl/projects/game-ai-foundry/cli/test_active_skill_scan.py:13` 阻止 active Skill 再引用删除入口。
- `/Users/czl/projects/game-ai-foundry/cli/test_pipeline_heal.py:281` 验证通用 external-agent 分诊合同。
- `/Users/czl/projects/game-ai-foundry/cli/test_shell_run.py:38` 验证所有用户可见字段脱敏。

---

## 5. Findings Summary

### Critical (Block Commit)

| # | Dimension | Line(s) | Description | Required Action |
|---|-----------|---------|-------------|-----------------|
| — | — | — | 无 | — |

### High (Block Commit)

| # | Dimension | Line(s) | Description | Required Action |
|---|-----------|---------|-------------|-----------------|
| — | — | — | 无 | — |

### Medium (Strongly Recommend Fix)

| # | Dimension | Line(s) | Description | Required Action |
|---|-----------|---------|-------------|-----------------|
| — | — | — | 无未解决项 | — |

### Low / Nit (Optional)

| # | Dimension | Line(s) | Description | Required Action |
|---|-----------|---------|-------------|-----------------|
| 1 | Context | 历史 Anvil/Release/Superpowers 文档 | 仍描述已删除的 GUI/Agent 运行时，但均位于历史区且入口有“已移除/历史”说明。 | 保持历史原文；不得恢复为操作入口。 |
| 2 | Reliability | `/Users/czl/projects/game-ai-foundry/cli/workflow_cmds.py:433` | 顺序写 + 异常回滚不等价于进程崩溃时的跨文件原子事务。 | 当前已覆盖可捕获异常；若未来要求断电级原子性，再引入 journal/两阶段提交。 |

---

## 6. Fix History

| Round | Fix Description | Verification |
|-------|-----------------|--------------|
| A | 统一 Workflow status/stage/next_action/failure kind；补真实 root 只读、init 回滚和 Quick Start gate 行为测试。 | 合同与 workflow 定向测试通过；只读树/config 快照不变。 |
| B | shell JSON/text/timeout 全字段脱敏并让 JSON 失败返回非零；active Skill 删除旧入口并增加扫描测试。 | `test_shell_run`、`test_active_skill_scan` 通过。 |
| C | 当前操作文档、Plan、Skill 与命令合同同步；删除旧根 `context` 与 GUI Release helper。 | 六命令 help、根 help、删除扫描通过。 |
| D | `pipeline_heal` / `host.run_assets` 去品牌化：`hermes/needs_hermes/pm_*` → `external_agent/needs_external_agent/triage_*`。 | `test_pipeline_heal`、`test_host_run_assets` 通过；当前 runtime 扫描为 0。 |
| E | Handoff、路径、CLI help、注释与操作文档清除 GUI/看板/项目经理按钮语义。 | 相关 52 项定向测试仅保留 3 个既有 CJK baseline errors；入口扫描为 0。 |
| F | 复审补强 shell 对 `OPENAI_API_KEY=`、`--token value` 等常见凭据形态的脱敏。 | `test_shell_run` 9/9 通过。 |
| G | `workflow validate` 在合法 manifest 存在时透传 manifest 状态，pending 不再错误指向 human review。 | workflow 定向测试 49/49 通过；全量无新增失败。 |

原始 6 个 High 与 3 个 Medium 均已关闭：

- Workflow 枚举 / failure kind → `/Users/czl/projects/game-ai-foundry/cli/workflow/contract.py:12`
- 只读 config migration → `/Users/czl/projects/game-ai-foundry/cli/gamefactory.py:95`
- init 部分写入 → `/Users/czl/projects/game-ai-foundry/cli/workflow_cmds.py:433`
- shell command 泄露 → `/Users/czl/projects/game-ai-foundry/cli/shell_ops.py:15`
- active Skill 删除引用 → `/Users/czl/projects/game-ai-foundry/cli/test_active_skill_scan.py:13`
- 测试绕过真实 root/失败路径 → `/Users/czl/projects/game-ai-foundry/cli/test_workflow_cmds.py:201`
- Quick Start 校验门禁 → `/Users/czl/projects/game-ai-foundry/README.md:26`
- GUI Release helper → 已删除
- 旧根 `context` 双入口 → 根 help 扫描为 0

---

## 7. Gate Decision

| Gate | Status |
|------|--------|
| All automated checks pass | [x]（变更范围全绿；全量 4 errors 已在基线独立复现并显式豁免） |
| Security scan clean | [x] |
| Karpathy score = 4/4 | [x] |
| No Critical findings unresolved | [x] |
| No High findings unresolved | [x] |
| Review document complete | [x] |
| `main` / `origin/main` 未改动 | [x] |
| 未执行 commit | [x] |

### Verdict

- [ ] **BLOCK** — findings must be resolved before commit
- [x] **APPROVE** — all gates passed, suggest `/anvil:compound`

### Reviewer Notes

- 当前工作树未 commit；用户未授权提交。
- 4 个测试 errors 是基线 fixture/CJK 既有问题，不是本 MR 回归。
- 历史文档保留用于审计，但不能作为当前操作入口。
- 下一步可执行 `/anvil:compound`，随后由用户决定是否 commit。
