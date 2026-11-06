# Review Report: `2026-11-06-hammer-pair-release`

## Metadata

| Field | Value |
|-------|-------|
| Reviewer | anvil-lead |
| MR / Commit | Current Foundry + fishing-2d release changes |
| Author | Codex, runtime fix dispatched to anvil-doer under review §6 |
| Review Date | 2026-11-06 |
| Status | APPROVED |

Scope: large mixed asset/code/config change. Both accepted R42 models are byte-identical to the user's reviewed files. Full eight-dimension review applies to scripts; artifact review is identity, provenance, scope and actual visual/canonical validation.

## 1. Automated Pre-checks

| Check | Command | Result | Notes |
|-------|---------|--------|-------|
| Lint | AST parse new Python; git diff --check in both repositories | PASS | No dedicated linter configured for these Blender/Godot scripts. |
| Type Check | Actual Godot 4.7.1 parsing/execution of canonical validator and affected runtime | PASS | No standalone static Python type checker for bpy scripts. |
| Unit Tests | PYTHONPATH=cli .venv/bin/python -m unittest cli/test_volume_sop.py | PASS | 29 tests. |
| Asset/runtime integration | verify_hammer_pair_final_entry.gd, current490/072, physical volume, 077, cold source, SOP | PASS | Each fish480 controller comparisons +360 transition steps, maximum pose delta0; complete static arrays and pixels identical across first/cache/raw/fishing entry. Current490 rerun after runtime wiring. |

## 2. Security Scan

| Category | Finding | Severity | Status |
|----------|---------|----------|--------|
| Hardcoded Secrets | No credentials; only asset fingerprints and local paths | None | Clean |
| Injection Risks | Local typed asset paths; no user-generated shell/query string | None | Clean |
| XSS Vulnerabilities | Static local review report, fixed authored labels and relative media paths | None | Clean |
| Dependency CVEs | No dependency/version change | N/A | No introduced dependency |
| Sensitive Data in Logs | Asset hashes/paths/results only; transient logs removed | None | Clean |

**Security Verdict:** CLEAN

## 3. Karpathy Adversarial Principles

| Principle | Adversarial Question | Author's Answer (Explicit or Inferred) | Verdict | Severity |
|-----------|---------------------|----------------------------------------|---------|----------|
| Think Before Coding | Are species/normalization/material assumptions justified? | Exact per-species R42 SHA and accepted 4m/3m canvas. Current material roughness retained, not blindly copied from scalloped. | PASS | None |
| Simplicity First | Can half the implementation be removed? | Small explicit two-fish binder follows existing finished-fish route; no framework or new runtime authoring. | PASS | None |
| Surgical Changes | Is every changed line required? | Tail shading, requested color build, exact final binding, mouth socket, provenance and cleanup only. Other fish unchanged. | PASS | None |
| Goal-Driven Execution | Does verification prove the visible result survives installation? | Canonical/raw first/cache/fishing arrays/materials exact; all action images identical; user R42 acceptance recorded separately from mechanical gates. | PASS | None |

**Karpathy Score:** 4/4

## 4. Adversarial Dimension Review

### 4.1 Design — Should this exist at all?

| Line(s) | Question Asked | Author's Answer | Reviewer Assessment | Severity |
|---------|---------------|-----------------|---------------------|----------|
| FinalizedHammerPair20261106.gd:70–141; FishSurfaceOwnership.gd:91–93 | Could a finished model still enter legacy static patches? | Exact model binding branches before legacy path. | Required High finding fixed and executed through actual entries. | Resolved High |

**Dimension Verdict:** PASS

### 4.2 Functionality — What is missing?

| Line(s) | Question Asked | Author's Answer | Reviewer Assessment | Severity |
|---------|---------------|-----------------|---------------------|----------|
| FishingVolumeFish.gd:26–77; binder:12–65 | Would generic maximum-X mouth choose the hammer tip? | Explicit actual ventral lip vertex/UV/weights guarded by source/model identity. | Actual fishing configure/socket and static equality pass. | Resolved High |
| repair_hammerhead_tail_shading.py:28–59 | Do caps corrupt the outer averaged normal? | Internal transverse caps excluded; both outer skins contribute; finite falloff. | Current shared seam0°/0.0198°; exact geometry/skin/rig preservation. | None |
| bake_hammerhead_multiview_trial.py:91–124 | Can two independent side donors create another tail boundary? | Common full-side donor across both shells; body-only donor resumes upstream. | R41 rejected; R42 matched rendered current asset accepted by user. Native head is resampled, not falsely claimed pixel-exact. | None |

Edge cases: exact species/SHA eligibility, absent/wrong model rejection in binder, finite budget boundaries4m/3m, zero/max motion controls, first/cache/independent load, mouth-socket recipe. Generic future species are outside these explicitly named authoring recipes. No asynchronous external service or concurrent asset mutation in release.

**Dimension Verdict:** PASS

### 4.3 Complexity — Can this be simpler?

| Line(s) | Question Asked | Author's Answer | Reviewer Assessment | Severity |
|---------|---------------|-----------------|---------------------|----------|
| binder:70–141; verify_hammer_pair_final_entry.gd | Is a new general asset abstraction needed? | No; fixed pair table and existing native GLB loader. | No speculative hooks. Validator targets actual runtime, not a mock. | None |

No unused runtime generic layer or unrelated style refactor. Historical authoring scripts are bounded tools, not runtime dependencies.

**Dimension Verdict:** PASS

### 4.4 Naming — Does the name lie?

| Line(s) | Question Asked | Author's Answer | Reviewer Assessment | Severity |
|---------|---------------|-----------------|---------------------|----------|
| FinalizedHammerPair20261106.gd; material-continuity.validation.json | Are trial and finished states distinguished? | Historical reports immutable, current final manifest explicitly user-accepted. | Old `trial` builder names describe authoring provenance; current runtime/entry is final. | None |

**Dimension Verdict:** PASS

### 4.5 Comments — Do comments explain the reason?

| Line(s) | Question Asked | Author's Answer | Reviewer Assessment | Severity |
|---------|---------------|-----------------|---------------------|----------|
| binder:90; bake:97–121; repair:28 | Are scale, shared donor and cap-exclusion reasons documented? | Comments explain accepted unit scale, color continuity and closed-shell normal contamination. | Accurate; no TODO or false biological-measurement claim. | None |

**Dimension Verdict:** PASS

### 4.6 Style & Consistency

| Line(s) | Issue | Type (Block / Nit) | Status |
|---------|-------|-------------------|--------|
| Three existing runtime files | Preserve existing line endings and compact style | None | Diff limited to required pair routing and labels |
| New tools | Existing standalone Blender/Godot tool style | None | Parse and execution pass |

**Dimension Verdict:** PASS

### 4.7 Context — Does this improve maintenance?

| Line(s) | Question Asked | Author's Answer | Reviewer Assessment | Severity |
|---------|---------------|-----------------|---------------------|----------|
| release/HANDOFF.md; AGENTS.md; final profiles | Could a future task resume old experiment geometry? | Canonical source/final profile and static freeze are primary; old experiment replaced by retired stubs. | Improves state clarity; exact retirement/relocation map distinguishes historical evidence. | None |
| release/cleanup.validation.json | Is cleanup deleting required authoring inputs? | Verified retained original sources, current assets, R40/tail inputs, native author and needed masks; rest inventoried by SHA/bytes. | No unknown/shared assets removed; no giant archive. | None |

**Dimension Verdict:** PASS

### 4.8 Tests — Do tests prove behavior?

| Line(s) | Question Asked | Author's Answer | Reviewer Assessment | Severity |
|---------|---------------|-----------------|---------------------|----------|
| verify_hammer_pair_final_entry.gd:13 onward | Would changed material/geometry/action be detected? | Exact all-array/material-pixel comparisons, cache/fishing path, controller poses; independent raw load. | Actual Godot integration, not implementation-only assertion. | None |
| roots072 historical rejection and current finals | Would stale runtime evidence be accepted? | Reuse explicitly rejected old Exhibit SHA; full490 rerun under final runtime, then072 passed. | Negative behavior demonstrated; no weakened gate. | Resolved Medium |

**Dimension Verdict:** PASS

## 5. Findings Summary

### Critical (Block Commit)

None.

### High (Block Commit)

1. Legacy runtime could mutate installed R42: dispatched under §6, fixed by exact pair finalizer and all actual entry routes; verified first/cache/raw/fishing equality.
2. Generic fishing mouth socket would select hammer extremity: precise source-bound ventral lip recipe added and executed successfully.

Both resolved; no unresolved High.

### Medium (Strongly Recommend Fix)

Old490 runtime binding invalid after formal-entry edits. Do not rehash old result: final complete490/072 actually rerun and passed. Resolved.

### Low / Nit (Optional)

None requiring additional scope.

## 6. Gate Decision

| Gate | Status |
|------|--------|
| All automated checks pass | [x] |
| Security scan clean | [x] |
| Karpathy score =4/4 | [x] |
| No Critical findings unresolved | [x] |
| No High findings unresolved | [x] |
| Review document complete | [x] |

### Verdict

- [x] **APPROVE** — all gates passed. Methods/parameters/evidence already recorded in existing skill and formal HANDOFF; no extra compound artifact needed.

### Reviewer Notes

User acceptance applies to the exact R42 visual result. No additional shape/color changes were made during final installation. Finite sampled gates are not continuous collision proofs. Historical lip ownership and final resampled atlas are explicitly distinguished. This review authorizes commit; final transport completion still requires both pushes and clean status.
