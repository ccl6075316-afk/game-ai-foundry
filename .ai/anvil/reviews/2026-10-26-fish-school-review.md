# Review Report: 2026-10-26-fish-school

## Metadata

| Field | Value |
|---|---|
| Reviewer | anvil-lead |
| MR / Commit | Local isolated prototype; no commit requested |
| Author | swarm_core / swarm_harness; lead reviewed and measured |
| Review Date | 2026-10-26 |
| Status | APPROVED for experimental prototype only |

## 1. Automated Pre-checks

| Check | Command / evidence | Result | Notes |
|---|---|---|---|
| Lint / type | Godot check-only and actual execution; Python AST parse | PASS | No standalone GDScript linter configured |
| Behavior | test_fish_school.gd; core-test/test.validation.json | PASS | 25 checks, deterministic 1200-tick trajectories, bounded sampling and motion |
| Runner | test_run_fish_school_experiment.py; unit-test.validation.json | PASS | 7 tests; real Godot metadata, source/settings rejection, error classification |
| GPU cases | run_fish_school_experiment.py; validation-report.json | PASS | 22 cases, 9 matched pairs; source consistency rechecked |
| Interactive | test_fish_school_viewer.gd; viewer-smoke/viewer.validation.json | PASS | 15 checks including actual 25→50 transition and teardown |
| Shutdown | viewer-smoke.stdout.log | PASS | Full stdout contains no engine/script/shader errors or leak diagnostics |
| Deployment | source-consistency.validation.json | PASS | Both canonical GDScript files identical to installed copies |

Evidence root: projects/fishing-2d/plans/reviews/fish-school-v1/.

## 2. Security Scan

| Category | Finding | Severity | Status |
|---|---|---|---|
| Hardcoded secrets | None in new files | — | CLEAN |
| Injection risks | subprocess argv lists; fixed local scene; no shell interpolation | — | CLEAN |
| XSS / SQL | No web/database surface | — | N/A |
| Dependency CVEs | No new packages or downloads | — | N/A |
| Sensitive logs | Metrics, local source hashes and filtered process observations only | — | CLEAN |
| Output boundaries | Absolute designated review root; actual output directories resolved and checked, no symlinks | — | CLEAN for exercised paths |

Security Verdict: CLEAN. No production asset writes, external messages or network requests by the prototype.

## 3. Karpathy Adversarial Principles

| Principle | Author answer / evidence | Verdict | Severity |
|---|---|---|---|
| Think Before Coding | production-delta.json states controlled cohorts, fixed radius, existing rigs and excluded systems | PASS | — |
| Simplicity First | Simulation, renderer and process runner have separate measured responsibilities; no speculative framework | PASS | — |
| Surgical Changes | Only new experimental scene/helpers/tests/launchers and maintained performance reference | PASS | — |
| Goal-Driven Execution | Tests cover behavior and rejection, benchmarks separate simulation/controller/rendering, GUI checks exercise inputs | PASS | — |

Karpathy Score: 4/4.

## 4. Adversarial Dimension Review

### 4.1 Design

FishSchoolSimulation.gd:120,187 separates bounded local decisions from integration and reports approximation limits. FishSchoolReview.gd:216,305 preserves existing assets and puts schooling locomotion outside native rig deformation. No production scene defaults changed. Verdict: PASS for prototype.

### 4.2 Functionality

Probed unknown/duplicate species, missing imports, failed factory append, finite delta, dense neighbors, reversed headings, deterministic initialization, actual coverage and 25→50 rebuild. Source hashes bind all cases. Three hammerheads remain excluded on this host; their guard was not weakened. Verdict: PASS within declared scope.

### 4.3 Complexity

Three focused runtime/measurement responsibilities; no persistent agent database, external service or alternate asset pipeline. Full and tiered modes provide needed controls. Verdict: PASS.

### 4.4 Naming

Reports explicitly distinguish simulation-only agents, actual fish, held poses, controlled cohorts and existing native movement. No realistic hydrodynamic solver or capacity acceptance claimed. Verdict: PASS.

### 4.5 Comments

Comments explain fixed workload cohorts, rotating neighbor selection, emergency projection and native carrier replacement. Limitations are reflected in measured reports rather than hidden in code comments. Verdict: PASS.

### 4.6 Style & Consistency

New GDScript follows the repository's direct SceneTree/Node3D experiment pattern; deployed copies match canonical sources. Python uses stdlib and argv arrays. No unrelated source reformatting. Verdict: PASS.

### 4.7 Context

Existing models, pixel art, materials, skeletons, acceptance guards and production scene defaults remain intact. Godot restored missing imported caches; unrelated concurrent whale work was left untouched. No final fish asset acceptance or SOP gate bypass. Verdict: PASS.

### 4.8 Tests

Behavior tests check observable separation, same-species force, route clearance, timing cohorts, bounds and independent sampling caps. Runner tests reject changed sources/settings and real error signatures. GUI test verifies actual source identities and count, camera, controls and resource release. Verdict: PASS.

## 5. Findings Summary

### Critical / High — resolved

| Finding | Root cause | Fix and verification |
|---|---|---|
| False success and stale species after failed spawn | Factory failure left fish[-1] pointing to prior entry | FishSchoolReview.gd:128,140,216 validates preflight and append/species/model; explicit 28-species request rejects; actual cases confirm exact roster/count |
| False report rejection | Godot JSON rounds 1/60 slightly | run_fish_school_experiment.py:46 tolerates only fixed-step serialization within 1e-14; counts/hashes remain exact; saved-report regressions pass |
| Weak school initialization | Same species members placed at distant route anchors | FishSchoolSimulation.gd:78 phases routes by species; 24 of 25 local pairs in 50-agent fixture; all behavior checks pass |
| GUI smoke resource leak | Immediate quit before detached factory/templates/queued nodes freed | External test releases factory, entries and cache and awaits deletion; clean full stdout on rerun |

### Medium — resolved

Raw monotonic frame intervals replace smoothed engine delta. Controller updates are staggered in benchmark mode. Source hashes and complete engine/stdout diagnostics determine validity. Canonical/deployed source hashes match.

### Low / declared experimental limitations

Fixed cohorts are not distance LOD. Low-frequency skeleton poses are held without interpolation. Point radius0.18m does not represent full species geometry. Density causes neighbor truncation and emergency projections. Native body bends are not driven by the new school trajectory. No water/glass/shadows/full physics/gameplay AI or hydrodynamic swimming was benchmarked. These remain explicit limits, not production acceptance.

## 6. Gate Decision

| Gate | Status |
|---|---|
| All applicable automated checks | PASS |
| Security scan | CLEAN |
| Karpathy score | 4/4 |
| Unresolved Critical / High | None |
| Specific findings and evidence recorded | PASS |

Verdict: APPROVE the isolated experimental prototype. Production-ready fish-school gameplay and visual acceptance remain pending. No commit was performed.
