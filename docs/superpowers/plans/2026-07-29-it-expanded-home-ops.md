# IT Expanded Home Ops Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Widen IT Pi tool whitelist (including `pipeline run`), default session-trust for IT so permission cards rarely interrupt, and update IT skill/GUI copy so home ops stay in Foundry instead of Cursor.

**Architecture:** Extend `pi_foundry_tools` allow/mutate lists for IT profile only; Electron session-allow map pre-seeded for IT instances when trust is on; skill + roles text teach the new ops playbooks. Brief profile stays narrow (no pipeline run).

**Tech Stack:** Python (`pi_foundry_tools`, `tool_permission`, `agent_turn`/`pi_runtime`), Electron `tool_permission_bridge.mjs`, React config bar / hire defaults, Markdown skill.

**Spec:** [`docs/superpowers/specs/2026-07-29-it-expanded-home-ops-design.md`](../specs/2026-07-29-it-expanded-home-ops-design.md)

## Global Constraints

- IT profile: wide whitelist; brief profile: unchanged narrow set (status / validate / gated export only).
- IT default **session trust ON**; user can turn OFF �?restore per-tool cards.
- `pipeline run` allowed for IT when trusted (or after card if trust off); never on brief profile.
- Hard deny: shell metacharacters; Foundry/Electron/Pi source edits; arbitrary paths outside projects/external/output/plans.
- IT must not silent-export brief.json; export stays user-intent + brief gates.
- No Hermes/Codex/Cursor permission redesign.
- Prefer TDD on allowlist + trust skip; GUI smoke manual.

## File map

| Path | Responsibility |
|------|----------------|
| `cli/pi_foundry_tools.py` | IT allow/mutate prefixes; profile split; instructions text; `pipeline run` |
| `cli/test_pi_foundry_tools.py` | Allowlist / profile / mutate tests |
| `cli/tool_permission.py` | Optional env/flag to skip HTTP when session pre-trusted (if needed) |
| `gui/electron/tool_permission_bridge.mjs` | Pre-seed session allow for IT; honor trust flag from env |
| `gui/electron/main.mjs` | Pass trust + role into agent-turn / runCli env |
| `gui/src/settings/agentInstances.ts` (or hire) | Default `pi_session_trust: true` for IT |
| `gui/src/components/ColleagueConfigBar.tsx` | Toggle「信任本会话」for IT |
| `gui/src/chat/roles.ts` | IT subtitle / quick prompts |
| `resources/skills/it/diagnose.md` | Home-ops playbooks |
| `docs/superpowers/specs/2026-07-29-it-expanded-home-ops-design.md` | Point Source Of Truth to this plan |

---

### Task 1: Expand IT whitelist (+ pipeline run) with tests

**Files:**
- Modify: `cli/pi_foundry_tools.py`
- Modify: `cli/test_pi_foundry_tools.py`

**Steps:**

- [x] Add failing tests:
  - IT allows: `brief chat zh-doc`, `brief chat autofix`, `brief chat makeability`, `brief chat bind`, `brief chat enrich`, `project external list`, `assets review list`, `pipeline plan`, `pipeline run`
  - Brief profile still rejects `pipeline run` and `setup install`
  - Mutate set includes new write ops (`zh-doc`, `autofix`, `enrich`, `pipeline plan`, `pipeline run`, bind if mutating)
- [x] Extend `_ALLOWED_PREFIXES` (shared or IT-only list). Prefer `_IT_ALLOWED_PREFIXES` + keep `_BRIEF_ALLOWED_PREFIXES` as today; `is_allowed_argv(profile="it"|"brief")` selects set.
- [x] Extend `_MUTATE_PREFIXES` for new writers; keep `--i-confirm` injection behavior.
- [x] Update `tool_protocol_instructions(profile="it")` to list new tools and state pipeline run is allowed under session trust; remove “never pipeline run�?
- [x] Cap documented default: skill says `--jobs` �?4 (enforce soft in skill; optional argv clamp later).
- [x] Run: `cd cli && python -m unittest test_pi_foundry_tools -v`

**Done when:** tests green; brief cannot run pipeline; IT can.

---

### Task 2: Default session trust for IT

**Files:**
- Modify: `gui/electron/tool_permission_bridge.mjs`
- Modify: `gui/electron/main.mjs` (agent-turn / runCli env)
- Modify: `cli/pi_runtime.py` or `cli/agent_turn.py` (pass trust into env if bridge reads it)
- Modify: `gui/src/settings/agentInstances.ts` + hire defaults
- Modify: `gui/src/components/ColleagueConfigBar.tsx` (or HireColleagueModal)
- Test: `cli/test_tool_permission.py` and/or bridge unit if present

**Steps:**

- [x] Config field: `agents.instances[<id>].pi_session_trust` (bool, default **true** when `role_kind === "it"`; brief default false / ignore).
- [x] When launching IT Pi turn, set env e.g. `GAMEFACTORY_TOOL_SESSION_TRUST=1` and stable `session_id`.
- [x] Bridge: if trust env set for this session_id, treat as session-allow already (auto `session` without card); still log argv_summary.
- [x] Config bar toggle「信任本会话」for IT; OFF clears session allow map entry and stops pre-seed.
- [x] Unit/integration: with trust, `request_mutate_permission` path does not block (mock bridge returns session immediately or Python skips POST when `GAMEFACTORY_TOOL_SESSION_TRUST=1` **and** profile=it �?pick one place, prefer bridge so CLI without Electron unchanged).

**Recommended implement detail (B1):** Electron bridge checks `sessionTrustIds` set; agent-turn registers IT session id into that set when trust on; `request_mutate_permission` still POSTs but bridge answers `session` synchronously without renderer card.

**Done when:** IT mutate tools under GUI with trust ON never show a card; OFF shows cards again.

---

### Task 3: IT skill + roles copy

**Files:**
- Modify: `resources/skills/it/diagnose.md`
- Modify: `gui/src/chat/roles.ts`

**Steps:**

- [x] Rewrite diagnose.md playbooks: 环境 / 草稿同步与中文说�?/ 导出�?autofix·makeability / 看板 heal·reset / 跑资产（pipeline run�?
- [x] Explicit: do not export brief unless user clearly asks 导出; prefer zh-doc + autofix.
- [x] roles.ts: IT subtitle + suggested chips matching playbooks.
- [x] No code commit required beyond docs/strings; spot-check Chinese.

**Done when:** IT system prompt/skill matches new whitelist language.

---

### Task 4: Optional GUI shortcuts (same PR if cheap)

**Files:**
- Modify: `gui/src/App.tsx` and/or IT action chips in ChatInput / ColleagueConfigBar

**Steps:**

- [x] If timeboxed: chips that send user messages IT already understands (“生成中文说明”“检测环境”“运行资产生成”“看板诊断�? rather than new IPC.
- [x] Skip dedicated IPC for v1 unless chip→agent turn already exists for IT.

**Done when:** at least chip text updated; full buttons optional.

---

### Task 5: Spec pointer + verify

**Files:**
- Modify: `docs/superpowers/specs/2026-07-29-it-expanded-home-ops-design.md` (Source Of Truth �?this plan)
- Modify: `docs/RELEASE-NOTES-UNRELEASED.md` one bullet

**Steps:**

- [x] Update spec metadata Status / Source Of Truth.
- [x] UNRELEASED: IT 家庭运维白名�?+ 默认信任本会�?+ �?pipeline run.
- [x] Run full related tests: `python -m unittest test_pi_foundry_tools test_tool_permission -q`
- [x] Manual smoke: hire IT �?trust on �?ask install/diagnose/zh-doc �?no cards; toggle trust off �?card appears; ask 跑资�?�?pipeline run starts or clear error.
- [x] Commit (user-requested) on main or feature branch.

**Done when:** tests green; UNRELEASED updated; smoke notes in commit body if useful.

---

## Out of scope (do not implement in this plan)

- IT editing `games/**/*.cs` or Foundry source
- Permanent global allow across app restarts
- Brief profile inheriting IT tools
- Auto-export brief from IT
