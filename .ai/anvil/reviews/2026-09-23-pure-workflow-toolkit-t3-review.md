---
review_date: "2026-09-23"
module: "T3 — remove built-in Agent runtime"
commit_hash: "uncommitted workspace diff on codex/pure-workflow-toolkit"
reviewer: "anvil-lead"
status: "passed"
karpathy_score: 4
---

## Review Summary

- **Scope**: Remove Agent/ACP/Pi/Hermes/Cursor/Codex executor runtime and registration while preserving Brief, Production, Pipeline, Prompt craft, media validation, Godot, Progress, Handoff, Asset Review, Test, Provider/API Key, and FFmpeg/Godot/.NET toolchain behavior.
- **Files Changed**: Runtime registration and config/discovery modules in `cli/`; direct runtime tests and resources; minimal LLM model migration helpers moved to `cli/llm_config.py:12`. T4-owned `cli/host_chat.py:1` and Brief chat commands remain intact.
- **Test Coverage**: 119 targeted tests pass. Full discovery runs 819 tests with 2 skips and only the four documented baseline errors: `test_brief_transitions.test_magic_prince_requires_graph` plus three `test_visual_target` CJK guard errors.

## Automated Pre-checks

| Check | Status | Notes |
|-------|--------|-------|
| Lint | N/A | No repository lint command is configured. |
| Type Check | N/A | No repository type checker is configured. |
| Unit Tests | PASS_WITH_BASELINE_EXCEPTIONS | Targeted suite: 119/119 pass. Full suite: 819 tests, 2 skipped, 4 known errors, no new failures. |
| Security Scan | PASS | No added secret/token patterns; doctor reports key status only; shell execution remains gated by `--i-confirm` at `cli/shell_cmds.py:34`. |

## Karpathy Four Principles

| Principle | Score | Finding |
|-----------|-------|---------|
| Think Before Coding | ✅ | T3/T4 boundary is explicit: `cli/host_chat.py:4073` and Brief chat behavior are deferred, while runtime registration is removed now. |
| Simplicity First | ✅ | The change removes executor, roster, session, permission bridge, and packaging helpers without adding a replacement runtime. |
| Surgical Changes | ✅ | Registration removal at `cli/gamefactory.py:932`, provider cleanup at `cli/provider_upsert.py:253`, and discovery cleanup at `cli/env_discover.py:71` map directly to T3. |
| Goal-Driven Execution | ✅ | CLI contract, provider/toolchain discovery, shell confirmation, pipeline healing, and retained Brief/Production/Godot behavior are covered by targeted tests. |

## Findings

### 🔴 Critical

None.

### 🟠 High

None.

### 🟡 Medium

None.

### 🟢 Low

1. `cli/host_chat.py:4073` still contains the intentionally deferred lazy `pi_runtime` import. Remove it with Brief chat cleanup in T4.
2. Retained Brief-chat skills still link the deleted `host-chat.md`, for example `resources/skills/orchestrator/commit-brief.md:6`. Reconcile those links with T4/T6 documentation work.
3. `cli/pipeline_heal.py:600` retains the legacy `needs_hermes` JSON contract and `owner: "hermes"` values. This is intentional compatibility debt; do not rename it inside T3.

## Recommended Changes

- T4: remove `brief chat` session/turn/export registration and the remaining `host_chat.py` runtime references without touching deterministic Brief validation/shard commands.
- T4/T6: update retained skill links and operational documentation after the final external-Agent command surface is fixed.
- Keep `needs_hermes` unchanged unless a versioned Pipeline JSON migration is explicitly scheduled.

## Fix History

| Round | Fix Description | Verification |
|-------|-----------------|------------|
| 1 | Removed runtime modules/registrations and moved model migration helpers to `llm_config.py`. | Compile, import smoke, targeted tests passed. |
| 2 | Cleaned all 145 Click help surfaces and removed Codex download runtime. | Recursive help scan: 0 banned runtime terms. |
| 3 | Reverted accidental T4 changes to Brief chat, UI wireframe tests, and IT skill content. | `brief freeze` absent; Brief chat tests restored; targeted/full tests rerun. |
| 4 | Final adversarial review and baseline comparison. | `git diff --check` passed; no new full-suite failures. |

## Final Decision

- [x] **PASSED** — Code may be committed
- [ ] **FAILED** — Fixes required before commit

Commit remains blocked by the user instruction for this task: do not commit.
