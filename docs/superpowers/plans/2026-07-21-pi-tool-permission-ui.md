# Pi Tool Permission GUI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Mutating `FOUNDRY_TOOL` calls from embedded Pi pause for an in-chat Approve/Deny card (once / turn / session) before running with `--i-confirm`.

**Architecture:** Python tool loop POSTs to a loopback HTTP bridge owned by Electron; Electron shows an inline card and answers the HTTP request. Turn-scoped memory lives in the Python process; session-scoped memory lives in Electron across turns.

**Tech Stack:** Python (`pi_foundry_tools`, `tool_permission`), Electron `http` + IPC, React chat messages in `App.tsx`.

## Global Constraints

- Only `_MUTATE_PREFIXES` tools gate; read-only tools unchanged.
- All Pi roles (IT, brief, future Pi roles).
- No permanent allow; session clears on app restart.
- Default timeout 300s → deny.
- Hermes / Codex / Cursor paths unchanged.
- Without `GAMEFACTORY_TOOL_PERMISSION_URL`, keep legacy `--i-confirm`-in-argv behavior (CLI/tests).

## File map

| File | Role |
|------|------|
| `cli/tool_permission.py` | Gate + turn memory + HTTP requester |
| `cli/pi_foundry_tools.py` | Call gate before mutate execute |
| `cli/pi_runtime.py` / `agent_turn.py` | Pass session_id into tool round |
| `cli/test_tool_permission.py` | Unit tests |
| `gui/electron/tool_permission_bridge.mjs` | Loopback server + session memory |
| `gui/electron/main.mjs` | Wire bridge into `runCli` env + IPC |
| `gui/electron/preload.cjs` | `onToolPermission` / `decideToolPermission` |
| `gui/src/vite-env.d.ts` | Types |
| `gui/src/App.tsx` | Inline permission card UI |

---

## Task 1: CLI permission gate + tests

**Files:** `cli/tool_permission.py`, `cli/test_tool_permission.py`, `cli/pi_foundry_tools.py`

- [ ] Write failing tests: turn memory skips second ask; deny returns ok=False; HTTP mock approve; no URL + missing `--i-confirm` still blocked by whitelist; with URL, mutate asks even if `--i-confirm` present
- [ ] Implement `tool_permission.py` (`PermissionTurnState`, `request_mutate_permission`, env URL POST)
- [ ] Hook `run_allowed_gamefactory` / `run_tool_round` to gate mutates
- [ ] Pass `session_id` from `run_pi_agent_turn` into tool round (optional kw)
- [ ] Run `python -m unittest test_tool_permission test_pi_foundry_tools`

## Task 2: Electron permission bridge

**Files:** `gui/electron/tool_permission_bridge.mjs`, `gui/electron/main.mjs`, `preload.cjs`, `vite-env.d.ts`

- [ ] Loopback HTTP server: POST body → emit to renderer; wait for decision; 300s timeout deny
- [ ] Session allow map; turn allow can be honored if `turnId` repeated (optional; Python also tracks turn)
- [ ] Inject `GAMEFACTORY_TOOL_PERMISSION_URL` (+ token) into `runCli` env
- [ ] IPC `agent-tool-permission-decision`
- [ ] preload listeners/API

## Task 3: GUI inline card

**Files:** `gui/src/App.tsx`, light CSS if needed

- [ ] Subscribe to permission events; append inline card message
- [ ] Buttons: once / turn / session / deny → `decideToolPermission`
- [ ] Mark card terminal state; no double-click

## Task 4: Verify + docs touch

- [ ] Re-run CLI unit tests; note manual GUI smoke
- [ ] Update Spec Source Of Truth line to point at this plan (optional)
- [ ] Commit on feature branch

**Done when:** mutate tools cannot run under GUI without bridge approve; unit tests green; Hermes/Codex/Cursor untouched.
