# Review Report: `2026-10-26-whale-shark-closeout`

## Metadata

| Field | Value |
|---|---|
| Reviewer | Codex / anvil-lead |
| Scope | Whale tools, profiles, SOP/knowledge and candidate checkpoint only |
| Review Date | 2026-10-26 |
| Status | APPROVED — scoped code and checkpoint |

## 1. Automated Pre-checks

| Check | Command / evidence | Result | Notes |
|---|---|---|---|
| Whitespace | scoped `git diff --check` | PASS | Original SOP CRLF retained; no whole-file normalization |
| Python | `unittest discover -s cli -p test_reviewed_side_field.py` | PASS: 5 | Irregular/invalid sections, mouth constraints, recipe-relative paths |
| Existing volume tests | `unittest discover -s cli -p 'test_volume*.py'` | PASS: 143 | Existing workflow/shape/mouth/motion/SOP/archive behavior |
| Godot parser | four promoted `.gd` scripts, `--check-only` | PASS | Native dorsal, seams, taper, metric binding |
| Independent numerical test | 1643 actual triangle probes | PASS | Current metric max .21622%; old metric fails at 22.53% as expected |
| Current body output | both body surfaces recomputed | PASS | Position float bytes unchanged by section-entry fix |
| Candidate SOP | current `volume sop-check` | EXPECTED BLOCK | Asset acceptance is out of scope; pending items retained honestly |
| Archive | per-member hash roundtrip | PASS: 806 files | 766,482,394-byte package verified |

No standalone linter/type checker is configured for these Python/Godot tools; actual parser and scoped whitespace checks used.

## 2. Security Scan

| Category | Finding | Severity | Status |
|---|---|---|---|
| Hardcoded secrets / sensitive logs | Reviewed text and credential-pattern matches; matches were permission/provenance prose | None | Clean |
| Injection | No new shell interpolation, SQL or executable remote content | None | Clean |
| XSS | Static local review page, no untrusted dynamic input | None | Clean |
| Dependency CVEs | No dependency added or version changed | N/A | Not a general dependency audit |
| Destructive cleanup | Exact owned archive, frozen input hashes, representative extrema and receipts before deletion | None | Verified scope excludes other tasks |

**Security Verdict:** CLEAN for scoped changes.

## 3. Karpathy Adversarial Principles

| Principle | Question / resolution | Verdict |
|---|---|---|
| Think Before Coding | Numeric head width remains unknown; generated frames are qualitative. Real sections no longer depend on regular rings. | PASS |
| Simplicity First | Small optional fin transport controls and one explicit section branch; unused imports removed. No new generic workflow engine. | PASS |
| Surgical Changes | Only whale changes staged; active zander/fish-school/performance work excluded. | PASS |
| Goal-Driven Execution | Negative metric example and broken-section tests detect the actual failure, not just execution. | PASS |

**Karpathy Score:** 4/4.

## 4. Adversarial Dimension Review

### 4.1 Design

`retarget_reviewed_side.py:17-45`: measured sections must replace ring inference. The previous ordering rejected valid irregular inputs; fixed with explicit finite/ordered/nondegenerate validation. Path base resolves from recipe rather than process cwd. PASS.

### 4.2 Functionality

`retarget_reviewed_side.py:53-88`: mouth mapping keeps top/bottom and transverse coordinates; whole width is not inferred from generated frontal perspective. Empty, one-row, unordered, NaN, zero-height and negative-width sections reject. Nonpositive Jacobian produces nonzero exit. PASS.

### 4.3 Complexity

`build_source_fins141.py:82-132,174`: foil, basal-depth and outward-collar controls are opt-in, default transport remains unchanged. Every new option has a whale caller. PASS.

### 4.4 Naming

`resolve_paths` returns a copy; cleanup/archive scripts explicitly name mutations and refuse overwrite. Reports distinguish candidate, timeout and formal acceptance. PASS.

### 4.5 Comments

Comments explain irregular-head extrapolation, projection-edge discontinuity and belly-midline crossing. Knowledge records unknowns and rejected approaches rather than claiming universal fish parameters. PASS.

### 4.6 Style & Consistency

Retained source byte conventions and existing CLI/report style. Full SOP line-ending churn removed. No unrelated cleanup staged. PASS.

### 4.7 Context

Generic builders/profile declarations stay in Foundry; source/model/evidence checkpoint stays in fishing-2d. Existing accepted game asset is unchanged. Historical absolute paths remain documented; current promoted recipes use explicit relative base. PASS.

### 4.8 Tests

Removing the section-first fix breaks the no-regular-rings test; mapping the mouth line without preserving envelope/Z breaks the numerical expectation. The old field fails independent surface probes. Parser-only checks do not imply full visual or runtime validation; that scope remains explicit. PASS.

## 5. Findings Summary

| Severity | Finding | Resolution |
|---|---|---|
| High | Real sections incorrectly required more than100 regular rings first | Fixed; regression test passes |
| Medium | Promoted recipes contained one machine's absolute input paths | Explicit path-base resolution added; original recipes archived byte-exact |
| Medium | Invalid-Jacobian report could still return process success | Nonzero exit added |
| High | Candidate could be mistaken for finished asset | Checkpoint, README, SOP and handoff all preserve unfinished status; game asset unchanged |

No unresolved code blockers. Asset lip contact/full membrane/LOD/game-scene limitations remain documented and are not waived by this review.

## 6. Gate Decision

Code checks and security pass. Checkpoint archive verification passed. Commit uses explicit whale-only paths; no unrelated staged changes are included. This review approves retention/tool changes, not model acceptance.
