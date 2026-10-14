# Review Report: `2026-10-14-arapaima-head-ownership`

## Metadata

| Field | Value |
|---|---|
| Reviewer | anvil-lead / root |
| MR / Commit | Local v15 prototype; no commit |
| Author | anvil doer |
| Review Date | 2026-10-14 |
| Status | BLOCKED |

## 1. Automated Pre-checks

| Check | Command | Result | Notes |
|---|---|---|---|
| Syntax | `py_compile` | PASS | CLI and Blender builder source |
| Diff | `git diff --check` | PASS | No whitespace errors |
| Unit | `cd cli && python3 -m unittest test_volume_fish` | PASS | 28 tests; profile validation only |
| Real build | `volume plan → build → render` | PASS | 64 underlay donor faces; all mechanical checks pass |

## 2. Security Scan

No new network calls, credentials, dynamic code execution, or dependency. Donor coordinates validated as finite and in bounds. **CLEAN** for the tested scope.

## 3. Karpathy Adversarial Principles

| Principle | Verdict | Evidence |
|---|---|---|
| Think Before Coding | PASS | v14 pixel-owner ray cast located duplicate eye on front-oblique `Closed_body` faces. |
| Simplicity First | FAIL | New generic donor API adds code but does not solve the visual defect. |
| Surgical Changes | PASS | Changes limited to profile contract, builder, and targeted tests. |
| Goal-Driven Execution | FAIL | Unit tests validate fields, while actual rendered head is worse. |

**Karpathy Score:** 2/4.

## 4. Adversarial Dimension Review

### 4.1 Design

Face-level donor shift treats the front-facing duplicate eye as an isolated UV issue. The same faces remain visible from the side, so moving their UV also erases the eye needed in that view. **FINDING (High).**

### 4.2 Functionality

The [v15 front render](../evidence/arapaima-head/v15-front.png) has weak, dirty eyes and an unchanged circular head; the [side render](../evidence/arapaima-head/v15-side.png) loses the compact eye from the accepted side source. The oblique view also lacks a credible eye. **FINDING (High).**

### 4.3–4.7 Complexity, naming, comments, style, context

Names and validation are understandable, but a generic contract with no passing art result adds maintenance cost. Revert the v15 implementation while retaining the diagnostic artifacts. **FINDING (Medium).**

### 4.8 Tests

The 28 unit tests demonstrate safe parsing, not visual ownership. They would pass with the observed eye loss. Blender/Godot visual gates remain mandatory. **FINDING (High).**

## 5. Gate Decision

**BLOCKED.** Do not `volume accept`, copy v15 into the game, or commit this implementation. Revert the new donor code and redesign head geometry/texture ownership as a coherent surface instead of masking selected eye pixels.
