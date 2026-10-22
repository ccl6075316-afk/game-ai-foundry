# Review Report: `2026-10-22-session123`

## Metadata

| Field | Value |
|-------|-------|
| Reviewer | debug_review — independent reviewer |
| MR / Commit | Foundry + nested fishing-2d working trees, pre-commit session123 |
| Author | root agent, user-authorized fish review/repair session |
| Review Date | 2026-10-22 |
| Status | `APPROVED` — code gate; final installed asset gate is separate |

Scope: retained modified/untracked production code, reconstruction/diagnostic tools, species inputs and skill/knowledge changes from113–122/121. This is a large change: review prioritized complete production interfaces and implementations, then diagnostic input/output and failure-path spot checks. Earlier independent negative/positive, numerical mutation and actual visual reviews are retained; this report does not claim every historical diagnostic line was re-executed. No models/configurations were changed and no Godot process was started by this review.

---

## 1. Automated Pre-checks

| Check | Command | Result | Notes |
|-------|---------|--------|-------|
| Lint | `git diff --check`; nested `git -C projects/fishing-2d diff --check` | PASS | No whitespace errors. No additional configured lint gate was introduced. |
| Type Check | Python `ast.parse` over retained changed/untracked Python code | PASS |20 Python files parsed; no Python static type-check configuration applies. GDScript runtime compilation is covered by recorded actual engine gates, not Python parsing. |
| Unit Tests | `python -m unittest discover -s cli -t cli` | PASS | Author log `/private/tmp/foundry123-unit-final.log`:767 tests,2 skips, OK. |
| Focused independent tests | `PYTHONPATH=cli python3 -m unittest test_volume_shape test_game_launch_import` | PASS |19 tests independently rerun; expected negative import messages occur inside passing tests. |
| Runtime mirrors | byte comparisons of BodyChart112, ValidateSurface112, RestSurface114 and LipMaterial115 scripts/includes | PASS | Six Foundry/Fish runtime files exactly equal at review. |
| Great4 evidence | SHA256 child report, model artifact and profile checks | PASS | Details below. |

Full suite logs contain intentional invalid-PNG/HTTP404 fixtures; the unittest summary is OK. No new dependency manifest or lockfile is part of this change.

---

## 2. Security Scan

| Category | Finding | Severity | Status |
|----------|---------|----------|--------|
| Hardcoded Secrets | Restricted pattern scan of72 retained source/config/docs files found no private-key or credential-assignment matches; manual changed-code review found none. | — | CLEAN |
| Injection Risks | Launcher uses argument-list subprocess calls, no shell interpolation; profiles remain parameter data. Reconstruction tools consume explicit local plans. | — | CLEAN |
| XSS Vulnerabilities | Observation overlay escapes user text with `html.escape`; SVG parses before write. No new remote web endpoint. | — | CLEAN |
| Dependency CVEs | No dependency additions or version changes. No online CVE/database audit was performed or implied. | — | N/A |
| Sensitive Data in Logs | New import/capture diagnostics log engine errors and local artifact paths; no new credential logging. | — | CLEAN |

**Security Verdict:** CLEAN for reviewed delta; not a whole-environment security certification.

---

## 3. Karpathy Adversarial Principles

| Principle | Adversarial Question | Author's Answer (Explicit or Inferred) | Verdict | Severity |
|-----------|---------------------|----------------------------------------|---------|----------|
| Think Before Coding | Are flat mouths, material drift and fin failures being conflated? | Separate controlled evidence: cache import, static rest lookup, source-line geometry, anterior crown, planar CDT topology, projected root-band collapse, and posed long-chord penetration. Source/art inference and unknown anatomy remain explicit. | PASS | — |
| Simplicity First | Does the common builder need speculative fish-specific behavior? | Only explicit optional spacing/depth plus boundary-edge subdivision; species coordinates stay in profiles/author helper. Existing internal baselines and absent-depth inset retain their old paths. | PASS | — |
| Surgical Changes | Can each production change be traced to an observed failure? | Import before launch; hide unrelated tanks without stopping clocks; per-surface rest tables; bounded two-fish lip protection; frozen local geometric fields; two new species with complete root/membrane gates. Rejected oral shader was rolled back. | PASS | — |
| Goal-Driven Execution | Would tests fail on the original bug? | Import negative tests, old material drift counterfactual, frozen lip/head/crown negative geometry, source CDT/projection negatives and actual Great3 membrane failure precede positives. | PASS | — |

**Karpathy Score:**4/4

---

## 4. Adversarial Dimension Review

### 4.1 Design — "Should this exist at all?"

> Adversarial stance: Every new abstraction, dependency, and layer is a liability. The author must prove it pays for its cost.

| Line(s) | Question Asked | Author's Answer | Reviewer Assessment | Severity |
|---------|---------------|-----------------|---------------------|----------|
| `build_fish.py:31–60`; `volume_shape.py:63–72` | Does a root fix belong in the common builder? | Actual boundary subdivisions must constrain CDT; a finite median root band needs a depth coordinate only where demonstrated. | Accept. Source geometry, optional explicit field and species data are separated; paired roots reject depth. | — |
| RestSurface114 / BodyChart112 / ValidateSurface112 | Can shared shader state silently mix tables? | Duplicate each material; bind actual imported surface-local arrays; reconstruct exact wrapper and compare table bytes, all arrays, LOD and code hashes. | Accept. SourceJaw inactive false parameters are asserted before duplication and restored after it. | — |

**Dimension Verdict:** PASS

---

### 4.2 Functionality — "What is the author missing?"

> Adversarial stance: The author missed at least one edge case. Find it.

| Line(s) | Question Asked | Author's Answer | Reviewer Assessment | Severity |
|---------|---------------|-----------------|---------------------|----------|
| `godot_cmds.py:583–593`; launch tests | Does skip-build bypass imports, or exit0 hide engine errors? | Import still runs; returncode and stdout/stderr `ERROR:` block launch. | Negative tests cover all three paths; actual missing-ctex fixture gives separate integration evidence. | — |
| `build_fish.py:31–60` | Does midpoint insertion leave the original long boundary constraint? | Matching forward/reverse A/B edge is replaced by ordered boundary points; unmatched internal baselines remain extra points. | Correct. All new species source-plane preflight and actual GLB closure remain mandatory. | — |
| `round_mouth_front122.py:14–24,53–56` / validator | Does the validator check optional transformed tangents? | This retained three-fish batch has no TANGENT attribute. | Nonblocking future-use gap: see L1. | Low |

**Key Edge Cases Probed:**

- [x] Empty/null imported resources fail assertions or import gates.
- [x] Finite/range boundaries: spacing/depth, full support triangles and f32 outputs.
- [x] Invalid negative/NaN/bool/string optional inputs rejected by focused tests.
- [x] External import failure and exit0-with-error block runtime.
- [x] Concurrent GPU/import mutation avoided operationally; captures fingerprint runtime files.
- [x] Runtime visibility transitions/shared tanks retain all controller clocks.

**Dimension Verdict:** PASS, with low future-reuse finding.

---

### 4.3 Complexity — "Can this be simpler?"

> Adversarial stance: If there's a simpler way, the complex way is wrong.

| Line(s) | Question Asked | Author's Answer | Reviewer Assessment | Severity |
|---------|---------------|-----------------|---------------------|----------|
| Reconstruction and capture tools | Why keep separate scripts? | They freeze distinct source-space, imported-space and posed-render contracts and preserve failed experiments. | Reasonable at present. Retained inputs/reports are required to reproduce the particular trial; do not promote diagnostic scripts to universal acceptance APIs. | — |

**Over-engineering Checklist:**

- [x] No new general service/dependency layer.
- [x] Optional fields address demonstrated geometry failures.
- [x] Rejected SourceJaw115 production branch is absent.
- [x] Simplified visibility change retains old animation behavior.

**Dimension Verdict:** PASS

---

### 4.4 Naming — "Does the name lie?"

> Adversarial stance: A misleading name is worse than a bad name. It creates hidden assumptions.

| Line(s) | Question Asked | Author's Answer | Reviewer Assessment | Severity |
|---------|---------------|-----------------|---------------------|----------|
| `root_band_depth`, `baseline_spacing`, RestSurface114 | Do names describe actual effects? | Depth is finite normal inset; spacing creates real source geometry subdivisions; rest tables use imported static arrays. | Accurate. Documentation explicitly denies full-rank/continuous-time guarantees and universal biological targets. | — |

**Naming Issues:**

- [x] Names distinguish source, runtime and posed checks.
- [x] Mutating tools identify reconstruction/restore behavior.
- [x] Native coordinate units and physical scale are documented.
- [x] Historical version numbers identify frozen protocols.

**Dimension Verdict:** PASS

---

### 4.5 Comments — "Does this comment add value, or excuse bad code?"

> Adversarial stance: Comments that explain WHAT the code does are admissions of failure.

| Line(s) | Question Asked | Author's Answer | Reviewer Assessment | Severity |
|---------|---------------|-----------------|---------------------|----------|
| CDT chain / inactive SourceJaw uniform comments | Are comments hiding an unexplained workaround? | They explain float32 near-collinear wedges and Godot duplicate dropping undeclared parameters. | Supported by reproduced failures and strict postconditions. | — |
| Skills and knowledge | Is technical pass being described as visual/anatomical acceptance? | Explicit limits, source-region acceptance, deferred oral effect and rejected attempts recorded. | Accept; final receipts remain authoritative. | — |

**Comment Quality Checklist:**

- [x] Non-obvious workarounds explain why.
- [x] Unknown source/anatomy remains unknown.
- [x] No new non-actionable TODO used to bypass a gate.
- [x] Earlier mistaken hypotheses are corrected in records.

**Dimension Verdict:** PASS

---

### 4.6 Style & Consistency

> Adversarial stance: Style violations mixed with functional changes are noise. Separate them.

| Line(s) | Issue | Type (Block / Nit) | Status |
|---------|-------|-------------------|--------|
| Existing compact Python/GDScript style | Follows surrounding reconstruction-tool conventions. | — | No blocking style issue. |
| `.gitattributes` | Explicit byte preservation for hashed tools/profiles; avoids platform EOL rewrite changing receipts. | — | Intentional functional provenance change. |

**Style Checklist:**

- [x] Existing file conventions retained.
- [x] No unrelated formatting sweep in production code.
- [x] Both working tree whitespace gates pass.

**Dimension Verdict:** PASS

---

### 4.7 Context — "Does this make the system healthier?"

> Adversarial stance: "Doesn't make it worse" is not enough. It must improve or maintain health.

| Line(s) | Question Asked | Author's Answer | Reviewer Assessment | Severity |
|---------|---------------|-----------------|---------------------|----------|
| Skill references + docs/anvil knowledge | Can the next agent repeat the corrected method without repeating rejected experiments? | Common methods remain in Foundry; species data and exact failure/positive evidence are separate. | Accept. Internal baselines, source alpha/free arc, REST pose and full-membrane distinctions are documented. | — |
| Body integrity capture diagnostics | Was a truncated capture assumed to prove a model or time-budget defect? | Added process returncode/receipt/error diagnostics only; original1200/180s and tests unchanged. Same-budget retry passed, first cause stays unknown. | Correct failure reporting and no gate relaxation. | — |

**System Health Checklist:**

- [x] Production files reviewed in whole-file context; large historical diagnostic scope sampled explicitly.
- [x] No new dependency/cross-service coupling.
- [x] Foundry runtime/Fish mirrors match.
- [x] Rejected oral implementation removed; its failure evidence remains labeled.

**Dimension Verdict:** PASS

---

### 4.8 Tests — "Do the tests prove it works, or do they just run?"

> Adversarial stance: Tests that pass when the implementation is wrong are worse than no tests.

| Line(s) | Question Asked | Author's Answer | Reviewer Assessment | Severity |
|---------|---------------|-----------------|---------------------|----------|
| Import/shape tests | Do mocks alone establish the visual bug? | Tests only prove launcher order/failure behavior and finite optional fields; actual missing-import fixture and renderer evidence are separate. | Good separation.19 focused tests independently pass. | — |
|122 crown validator | Does calling builder.field self-prove the geometry? | Independent frozen42-point analytic crown expectations, old flat-cap negatives, numerical Jacobian differences and mutation tests supplement field equality. | Accept current tested no-tangent batch; L1 limits future tangent reuse. | Low |
| Great4 roots/membranes | Did density change the checker or hide part of the root? | Only Pectoral root_attachment.baseline_spacing added; complete.025 root band, poses/controller/thresholds unchanged. | Verified profile diff and artifact/report SHA; actual membrane positive closes the previously reproduced chord failure. | — |

**Test Quality Checklist:**

- [x] Retained negative evidence fails on original behavior.
- [x] Geometry, imported arrays and actual posed rendering have distinct gates.
- [x] Actual nonempty coverage is required where diagnostic zero-change could be vacuous.
- [x] Fin/opacity tests retain physical thresholds and complete selection.
- [x] Mock tests are not used as visual acceptance.

**Dimension Verdict:** PASS with L1.

---

## 5. Findings Summary

### Critical (Block Commit)

| # | Dimension | Line(s) | Description | Required Action |
|---|-----------|---------|-------------|-----------------|
| — | — | — | None found. | — |

### High (Block Commit)

| # | Dimension | Line(s) | Description | Required Action |
|---|-----------|---------|-------------|-----------------|
| — | — | — | None found. | — |

### Medium (Strongly Recommend Fix)

| # | Dimension | Line(s) | Description | Required Action |
|---|-----------|---------|-------------|-----------------|
| — | — | — | None found in current retained scope. | — |

### Low / Nit (Optional)

| # | Dimension | Line(s) | Description | Required Action |
|---|-----------|---------|-------------|-----------------|
| L1 | Tests | `validate_round_mouth122.py:28–38`; builder:53–56 | Optional TANGENT is exempted from preservation comparison but its transported value is not independently checked. All current three source GLBs lack TANGENT, so this does not invalidate122 evidence. | Before using on a tangent-bearing model, add expected tangent transport/handedness and mutation checks, or reject unsupported tangent inputs. Not required to change current verified assets. |

---

## 6. Gate Decision

| Gate | Status |
|------|--------|
| All automated checks pass | [x] Reviewed code gate; final installed asset receipts pending separately |
| Security scan clean | [x] Scoped to changed source/config/docs; no dependency changes |
| Karpathy score =4/4 | [x] |
| No Critical findings unresolved | [x] |
| No High findings unresolved | [x] |
| Review document complete | [x] |

### Verdict

- [ ] **BLOCK** — findings must be resolved before commit
- [x] **APPROVE** — code review gate passed; preserve knowledge via `/anvil:compound`

### Reviewer Notes

Great4 independent receipt checks: completion and both child SHA256 values match files; model artifact is `fd75b27ce3634cdf5fc1241369ba5ca0176fb868333608fecb1ad7350e175d52`, matching handoff4 GLB. Handoff profile SHA is `b403cda6bc6245ebfdc47508d5c77ea37c5c1a95d5393dbf552a70ffcb4e40a0`, matching actual profile. Diff against archived failed Great3 profile contains exactly `/fins/3/root_attachment/baseline_spacing: absent →0.0005`; no body/head-cap proposal was mixed in. Both actual reports contain490 samples; all8 fins have zero failed root contact and zero failed membrane poses. Controller remains `d93e40b4…bac1`, motion config `e26d3e7f…4a45`; membrane thresholds remain root collar0.5mm and free penetration0.02mm. Root checker retains its pre-existing separate0.1cm gap/0.6cm penetration settings; the stricter membrane collar gate is not replaced by those looser root limits.

The root cause is actual posed chord penetration, not a checker sample deficit: prior independent samples located15.12–15.37mm root edges with interior penetration0.520/0.606mm while endpoints were shallower. The new builder adds/reprojects real basal boundary vertices; it does not merely increase validator samples. Smooth3 is deliberately unchanged by this fix.

Prior independent reviews remain applicable only to their frozen inputs:113 cache/visibility,114 rest anchoring,115 bounded partial external lip fit,117 catfish corner,119 local width and122 anterior crown.115 oral color/UV work remains explicitly deferred;122 zander cap material border and hammerhead small body-terminal-cap appearance remain known visual limitations, not claimed fixes. Current rounded/head trials may be retained without overwriting the user's preferred formal baseline unless explicitly installed by the main task.

This code approval does not claim formal25-fish final installed acceptance, full continuous collision proof, complete anatomy accuracy, or user visual acceptance. Parent must bind final actual installed25-fish GPU body,177 root, applicable490 membrane, selection/load and visual receipts before final delivery, and separately verify both repository commit/push/clean-status requirements. No new engine jobs were started by this reviewer.

### Follow-up: historical candidate restore

The subsequent `restore_review_candidate.py` correction is also APPROVED. It verifies every archive file hash before copy, recursively restores the frozen aquarium script tree, and removes only temporary-copy GLBs absent from that archive's frozen motion species inventory. The formal game is never the copy destination. This prevents a historical23-fish119/122 runtime/config snapshot from being mixed with the newly installed25-fish model inventory.

Independent read-only checks verified exact archive-file inventory coverage and every file SHA:119 has96 archived files and122 has96; each frozen motion inventory contains23 species, while the actual formal game contains25 model files. Parent's `plans/reviews/123-session-candidate-restore.validation.json` separately records actual restore/copy/byte verification and temporary-directory removal; that is not a new rendered acceptance. No code approval change or new blocker.

### Final installed asset gate — reviewed after code approval

**APPROVED — finite final delivery.** `projects/hammer-pair-121/review/independent-final-review.md` and its `.validation.json` now record independent formal-artifact convergence.25 current GLBs match the installed receipt (old23 preserved;119/122 remain isolated); both new fish pass177 full-root and490 full-membrane samples; gallery1528 passes;400 body views have no missing pixels, and800 underlying PNG hashes were checked. The64 quarter-cycle/transition/native PNG hashes and75 captured runtime dependencies match current formal files. All report child hashes, actual model/profile/controller/motion identities and original physical thresholds were checked. Four final static/motion contact sheets were actually viewed. No new blocker found.

Known head/body terminal-cap and donor-tone boundaries remain visible optional art work; oral115 remains deferred. This supersedes earlier final-asset-pending notes for the listed receipts only. Operator accept/archive remapping, commit/push, cleanup and clean status remain the parent's separate final transaction checks; this approval does not pretend those are already completed.
