# Review Report: `2026-10-14-arapaima-head-face-shell`

## Metadata

| Field | Value |
|---|---|
| Reviewer | anvil-lead / root |
| MR / Commit | Local v16 prototype; no commit |
| Author | anvil doer |
| Review Date | 2026-10-14 |
| Status | BLOCKED |

## 1. Automated Pre-checks

| Check | Result | Notes |
|---|---|---|
| Syntax and diff | PASS | Python compiles; `git diff --check` clean |
| Unit | PASS | 28 targeted tests before reversion |
| Real build | PASS | Foundry plan, build, render and mechanical checks pass |
| Visual | FAIL | Side and oblique head show exposed rectangular cap and dark striping |

## 2. Security Scan

No network, credentials, or new external dependency. Input dimensions were bounded. CLEAN.

## 3. Karpathy Adversarial Principles

| Principle | Verdict | Evidence |
|---|---|---|
| Think Before Coding | FAIL | Rectangular shell boundary cannot blend into a curved, narrowing head. |
| Simplicity First | FAIL | A new generic face-shell contract adds complexity without usable output. |
| Surgical Changes | PASS | Changes were isolated to profile validation, mesh construction, and tests. |
| Goal-Driven Execution | FAIL | Structural tests passed while the visual result regressed. |

## 4. Adversarial Dimension Review

- **Design / functionality, High:** The added front patch is a separate rectangular cap whose edge remains visible in side and oblique views. It does not provide a continuous head surface. [Side render](../evidence/arapaima-head/v16-side.png), [oblique render](../evidence/arapaima-head/v16-oblique.png).
- **Context / complexity, Medium:** The new schema and mesh path would be species-wide maintenance for a failed one-off topology.
- **Tests, High:** Numeric profile validation and manifold checks do not detect exposed seams, texture stripes, or duplicated eyes. Visual review is required.

## 5. Gate Decision

**BLOCKED.** v16 must not be accepted or installed in the game. The v16 code was reverted while preserving the earlier frontal overlay implementation and all diagnostic artifacts. Subsequent edits require a different surface/texture ownership strategy.
