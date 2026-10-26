# Review Report: `2026-10-26-fish-school-motion`

## Metadata

| Field | Value |
|-------|-------|
| Reviewer | Independent `/root/motion_review_phase4` |
| MR / Commit | Uncommitted isolated prototype; compared against bound `baseline-v1` snapshots |
| Author | `/root/swarm_core`, `/root/swarm_harness`; integrated by `/root` |
| Review Date | 2026-10-26 |
| Status | `APPROVED` for isolated prototype code; user visual acceptance pending |

Scope is the route/body coupling and elapsed-time defect in the experimental fish-school viewer. Runtime freeze: Viewer `ee1e02e8f93c800d31e2ee992b288f97fffdce3b5afa38a90a653be21d3f65c7`, Adapter `3167bf65193b3328f1edf41d16972aa4b9a65e6e705f780d99f8254cb31cc3e1`. Canonical and deployed scripts match. Production controllers, models, materials and profiles are unchanged; the original 754 bound production/simulation files are covered by `production-source-preservation.validation.json`.

## 1. Automated Pre-checks

| Check | Command | Result | Notes |
|-------|---------|--------|-------|
| Lint | N/A | N/A | No configured dedicated GDScript/Python lint gate for this isolated prototype; changed source reviewed directly. |
| Type Check | Godot actual-script loading and execution | PASS | Final real-fish, backlog, adapter and core test reports have no script/parser errors; known macOS CA lookup warning separately classified. |
| Unit Tests | `.venv/bin/python resources/scripts/volume-fish/test_run_fish_school_experiment.py` | PASS | Reviewer independently reran 10 tests; temporary fixtures removed by the test. |
| Launcher syntax | `/bin/sh -n projects/fishing-2d/open-fish-school-review.sh` | PASS | Shell and Windows launchers only move the interactive log folder from historical v1 to current v2; Windows launcher statically reviewed on macOS. |
| Regression tests | External Godot `test_school_motion_v2.gd`, `test_school_clock_backlog_v2.gd`, `test_school_motion_adapter_v2.gd`, `test_fish_school.gd` | PASS | Source-bound final reports: 12, 4, 15 and 25 checks. Baseline and intermediate failures retained as expected negative evidence. |
| Rendered benchmark | Four current 50/200 full/tiered cases, independently revalidated against 756 current source bindings | PASS | Forward+/Metal; 150 ticks, 30 warmup + 120 samples; expected native pose counts 6000/1900/24000/7600; no unexpected engine errors. |

## 2. Security Scan

| Category | Finding | Severity | Status |
|----------|---------|----------|--------|
| Hardcoded Secrets | None in changed runtime, probes or runner | — | CLEAN |
| Injection Risks | Native process arguments remain structured lists; no added shell/network execution; output roots restricted | — | CLEAN |
| XSS Vulnerabilities | No browser/HTML input surface | — | N/A |
| Dependency CVEs | No dependency additions | — | N/A |
| Sensitive Data in Logs | New diagnostics contain fish state, hashes and local evidence paths; no credentials | — | CLEAN |

**Security Verdict:** CLEAN

## 3. Karpathy Adversarial Principles

| Principle | Adversarial Question | Author's Answer (Explicit or Inferred) | Verdict | Severity |
|-----------|---------------------|----------------------------------------|---------|----------|
| Think Before Coding | Which assumptions lack evidence? | Prior phases independently gated; real factory skeletons prove the steering disconnect and clock discard. Native clips are nonzero. Biological tuning and GPU visuals were not inferred from bone statistics. | PASS | — |
| Simplicity First | Can half the implementation disappear? | The small adapter keeps native factory/species behavior intact. Its bounded heading history is required for body delay and reversal; the accumulator is required to retain time while capping work. No unused extensibility layer. | PASS | — |
| Surgical Changes | Does every change follow the task? | Adapter fixes actual-trajectory steering; viewer fixes time flow and presentation default; runner supports distinct current evidence and prevents historical v1 reruns with new sources; probes verify these boundaries. | PASS | — |
| Goal-Driven Execution | Do tests prove behavior? | Opposite inputs fail on frozen v1 and pass after A while B still fails; independent low-FPS/stall tests fail before B. Final tests use real fish plus separately scoped fixture contracts. | PASS | — |

**Karpathy Score:** 4/4

## 4. Adversarial Dimension Review

### 4.1 Design — "Should this exist at all?"

| Line(s) | Question Asked | Author's Answer | Reviewer Assessment | Severity |
|---------|---------------|-----------------|---------------------|----------|
| `FishSchoolMotionAdapter.gd:21,93`; `FishSchoolReview.gd:259` | Why depend on private controller state? | Avoid modifying shared production controllers or bypassing the factory's species dispatch. | Acceptable prototype boundary: source-bound, isolated, tested with all loaded species in refreshed benchmark; not presented as a stable public API. | — |

**Dimension Verdict:** PASS

### 4.2 Functionality — "What is the author missing?"

| Line(s) | Question Asked | Author's Answer | Reviewer Assessment | Severity |
|---------|---------------|-----------------|---------------------|----------|
| `FishSchoolMotionAdapter.gd:39,54,81,93` | Do heading seams, vertical/stationary motion, reversal and native fins survive? | Unwrapped history, retained direction, orthonormal basis fallback; delayed joint differences; unchanged native local fin poses. | Contract tests cover those cases; actual fish tests independently establish signed steering and preserved clocks. Native rest axes and head-sign conventions match the original equations. | — |
| `FishSchoolReview.gd:335` | Does a long frame lose time or multiply skeleton evaluations? | Up to eight fixed ticks, retained backlog, observation each consumed tick, one due pose per rendered frame. | Correct: zero-delta can drain backlog, pause accepts no input, negative/nonfinite input ignored explicitly; pending tier pose time accumulates. | — |

**Key Edge Cases Probed:** stationary/vertical headings, yaw wrap, turn reversal, invalid observations and delta, held tier poses, 10/15 Hz input, half-second stall, source mismatch, missing factory fish, renderer/import guard rejection. Single-threaded local simulation; no new concurrency path.

**Dimension Verdict:** PASS

### 4.3 Complexity — "Can this be simpler?"

| Line(s) | Question Asked | Author's Answer | Reviewer Assessment | Severity |
|---------|---------------|-----------------|---------------------|----------|
| `FishSchoolMotionAdapter.gd:70,81`; `FishSchoolReview.gd:325` | Are bounded history and metric merging speculative? | Delay needs historical headings; catch-up needs multiple tick counters combined without multiplying native work. | Both have direct callers and observable tests; no generic unused hook. | — |

**Over-engineering Checklist:** no speculative abstractions, unused generic parameters or unnecessary indirection found; removing the history or accumulator would remove required behavior.

**Dimension Verdict:** PASS

### 4.4 Naming — "Does the name lie?"

| Line(s) | Question Asked | Author's Answer | Reviewer Assessment | Severity |
|---------|---------------|-----------------|---------------------|----------|
| `FishSchoolMotionAdapter.gd:54,93,122`; `FishSchoolReview.gd:61` | Are observed and posed time distinguished? | Observation time, pending pose delta, accepted input and accumulator have separate state and reports. | Names and scope notes correctly distinguish simulation, native pose and wall-clock timing. | — |

**Naming Issues:** no blocking vague or misleading new names found.

**Dimension Verdict:** PASS

### 4.5 Comments — "Does this comment add value, or excuse bad code?"

| Line(s) | Question Asked | Author's Answer | Reviewer Assessment | Severity |
|---------|---------------|-----------------|---------------------|----------|
| `FishSchoolMotionAdapter.gd:1,107`; `FishSchoolReview.gd:318,367` | Are limits and unusual ordering explained? | Prototype-only private dependency, authored engineering limit, preserved placement, per-tick observation before once-per-render posing. | Explains reasons and practical limits; no biology claim or unowned TODO. | — |

**Dimension Verdict:** PASS

### 4.6 Style & Consistency

| Line(s) | Issue | Type (Block / Nit) | Status |
|---------|-------|-------------------|--------|
| Changed scripts | Existing GDScript/Python conventions retained; no unrelated formatting churn | — | PASS |

**Style Checklist:** surrounding style followed, functional changes kept scoped, deployment copies identical.

**Dimension Verdict:** PASS

### 4.7 Context — "Does this make the system healthier?"

| Line(s) | Question Asked | Author's Answer | Reviewer Assessment | Severity |
|---------|---------------|-----------------|---------------------|----------|
| `run_fish_school_experiment.py:24,32,39,139`; `open-fish-school-review.sh:8`, `.cmd:5` | Can new adapter code or measurements silently reuse old source evidence? | Include every school script in simulation binding; require exact canonical review root; reject changed-source v1 run before schedule mutation. Interactive logs also move to v2. | New runner tests exercise inclusion, source rejection and historical preservation. Current paths resolve to intended repository roots. Existing source/import guards retained; launcher adjustment does not alter the bound runtime hashes. | — |
| `FishSchoolReview.gd:490`; debug session | Does the report imply fish acceptance or a new swim solver? | Explicitly scopes current steering, fixed point agents, held poses, benchmark cadence and pending human review. | Correct. Images corroborate mesh response, not fin-root/body/anatomy acceptance or full-body avoidance. | — |

**System Health Checklist:** complete adapter and viewer flow read; full runner read; native posing equations and complete black/red species-controller diffs checked; prior evidence preserved.

**Dimension Verdict:** PASS

### 4.8 Tests — "Do the tests prove it works, or do they just run?"

| Line(s) | Question Asked | Author's Answer | Reviewer Assessment | Severity |
|---------|---------------|-----------------|---------------------|----------|
| `test_school_motion_v2.gd:75,100`; `test_school_clock_backlog_v2.gd:20`; adapter contract | Would the old bug still pass? | Frozen v1 produces zero turn residuals and lost input time; post-A still fails B; pre-B stall fails. | Negative evidence proves test sensitivity. Actual-fish skeleton/clock tests avoid relying solely on the tiny native fixture. Native fin/wave contract is separately labelled and GPU captures independently viewed. | — |

**Test Quality Checklist:** regression sensitivity established before fixes; edge cases tested; actual factory contexts used; fixture limitations stated; reports bind implementation hashes.

**Dimension Verdict:** PASS

## 5. Findings Summary

### Critical (Block Commit)

None.

### High (Block Commit)

None.

### Medium (Strongly Recommend Fix)

None.

### Low / Nit (Optional)

None.

## 6. Gate Decision

| Gate | Status |
|------|--------|
| All automated checks pass | PASS |
| Security scan clean | PASS |
| Karpathy score = 4/4 | PASS |
| No Critical findings unresolved | PASS |
| No High findings unresolved | PASS |
| Review document complete | PASS |

### Verdict

- [ ] **BLOCK** — findings must be resolved before commit
- [x] **APPROVE** — all gates passed; compound the verified debugging lesson

### Reviewer Notes

Reviewer independently viewed frozen-v1 2-second image and current 2/6-second images: actual rendered sailfish and whale-shark posterior bodies bend in opposite directions after reversed trajectory input. Captures use identical source fish, phases and controlled input; they do not establish realtime performance. Explicit tiered mode still holds skeleton poses without interpolation. Full-frequency is now the interactive default. This is prototype review only; user visual acceptance and production fish gates remain pending.

Final independent source rehash and case validation: all four current reports match all 756 current bound files and exact requested settings; frozen Viewer and Adapter hashes unchanged. All cases consume 150 fixed ticks / 2.5 simulated seconds including warmup, with 120 measured frames / 2.0 simulated sample seconds and zero pending time. Measured native pose calls match cadence exactly. Frame median/P95 milliseconds: 50 full 17.247/18.960; 50 tiered 8.266/8.653; 200 full 55.959/60.170; 200 tiered 33.127/35.357. These measurements include the adapter cost and remain fixed-tick benchmark observations, not a realtime capacity claim. Reports and logs have no unclassified runtime errors. No unresolved findings.
