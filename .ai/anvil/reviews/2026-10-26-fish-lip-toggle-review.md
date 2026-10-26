# Review Report: `2026-10-26-fish-lip-toggle`

## Metadata

| Field | Value |
|-------|-------|
| Reviewer | anvil-lead / root |
| MR / Commit | No commit requested; single diagnostic helper |
| Author | swarm_harness |
| Review Date | 2026-10-26 |
| Status | APPROVED for visibility comparison only |

## 1. Automated Pre-checks

| Check | Result | Evidence |
|-------|--------|----------|
| GDScript parse/type check | PASS | Headless load and preflight exit 0 |
| Unit tests | N/A | Reversible visual helper; actual factory invariants used instead |
| Factory preflight | PASS | Identical mesh/skin/material/pose; only lip visibility changes; 3 equal cameras |
| Metal GPU capture | PASS | Fresh process exit 0; 3 actual paired images inspected; engine.log clean |
| Frozen inputs | PASS | 114 SHA bindings unchanged during run and rechecked before delivery |

## 2. Security Scan

| Category | Finding | Severity | Status |
|----------|---------|----------|--------|
| Hardcoded secrets | None | — | CLEAN |
| Injection risks | No command/network evaluation; exact output-directory allowlist | — | CLEAN |
| XSS vulnerabilities | No web surface | — | N/A |
| Dependency CVEs | No dependencies added | — | N/A |
| Sensitive data in logs | Only selected asset paths/hashes and normal factory receipts | — | CLEAN |

**Security Verdict:** CLEAN.

## 3. Karpathy Adversarial Principles

| Principle | Assessment | Verdict |
|-----------|------------|---------|
| Think Before Coding | Explicit current-zander/seek0/visibility-only scope; no whale instantiation | PASS |
| Simplicity First | Existing factory and paired viewport pattern; invariants avoid misleading A/B | PASS |
| Surgical Changes | One external helper; no product or production-asset edits | PASS |
| Goal-Driven Execution | Deliver real GPU images with sole-variable check, not merely successful script exit | PASS |

**Karpathy Score:** 4/4.

## 4. Adversarial Dimension Review

### 4.1 Design

External diagnostic helper is appropriate; current factory resources are reused without loading old reduced candidates. PASS.

### 4.2 Functionality

Reviewed whole script. Output is fixed to an absolute review directory. Missing fish/lip or unequal mesh/material/pose blocks capture. Both worlds use identical cameras/light and fixed native pose. Right node visibility is the sole mutation. Stored triangles remain 212,360; only visible triangles fall to 73,640. Actual PNGs show the expected mouth-local difference. Missing resources rely on native factory errors plus operator log gate; all actual 114 inputs exist. PASS for the present execution.

### 4.3 Complexity

State hashing is justified because independent factory instances can differ; three stills suffice, no movie or model variants added. PASS.

### 4.4 Naming

`visibility_only`, `preflight_only`, stored versus visible counts make the scope explicit. PASS.

### 4.5 Comments

Comments explain why selected-species bindings and the sole visibility toggle exist; no deferred feature TODOs. PASS.

### 4.6 Style & Consistency

Matches neighboring SceneTree capture helpers; no unrelated formatting changes. PASS.

### 4.7 Context

Does not claim formal fin/body/dynamic/export acceptance. Actual visual comparison is retained and production resources remain intact. PASS.

### 4.8 Tests

Real factory assertions plus Metal capture cover the user request. This is not a reduction or runtime-performance test; static images do not establish equivalence through animation. PASS within scope.

## 5. Findings Summary

Critical: none. High: none. Medium: none. Low: none blocking this diagnostic.

## 6. Gate Decision

- [x] Automated checks pass within scope.
- [x] Security scan clean.
- [x] Karpathy score 4/4.
- [x] No unresolved Critical or High findings.
- [x] Actual images reviewed; records and cleanup complete.
- [x] APPROVE — diagnostic still-image comparison only.

User visual preference remains pending. No commit/push, formal asset replacement, SOP acceptance or FPS claim.
