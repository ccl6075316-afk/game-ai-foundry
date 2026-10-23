# Review Report: 2026-10-23-bluegill-gait

## Metadata

| Field | Value |
|---|---|
| Reviewer | anvil-lead / root |
| MR / Commit | Working tree; no commit or push requested |
| Author | bluegill_gait_trial implementation agent |
| Review Date | 2026-10-23 Asia/Shanghai |
| Status | APPROVED for isolated experiment; production adoption and user visual acceptance remain pending |

## 1. Automated Pre-checks

| Check | Command / evidence | Result | Notes |
|---|---|---|---|
| Whitespace | Both repositories: git diff --check | PASS | Existing unrelated mouth experiments preserved |
| GDScript parse/runtime | trial_swim_gait132.py qa with Godot4.7.1 | PASS | Actual imported bluegill skeleton, four actions and transitions |
| Unit tests | test_runtime_pose_coverage.py | PASS | Three methods; valid206/490, seven negative faults, canonical177 and missing-sample rejection |
| Fresh receipt | stale-receipt.validation.json | PASS | Seeded success plus fake Godot exit0 rejected in qa/capture/body |
| Candidate fin roots | validate_fin_completion.py with export_swim_gait132.gd | PASS | Seven complete basal bands,206 actual poses |
| Whole fins | validate_fin_membrane_clearance.py with candidate exporter | PASS | Seven fins,490 poses incl native25 and dense integrated candidate sequence; original tolerances |
| Baseline regression | validate_fin_completion.py standard exporter | PASS | Original177 contract retained |
| Body shell/material/GPU | validate_body_integrity.py baseline | PASS |25 installed species; bluegill16 views zero missing pixels |
| Candidate GPU coverage | trial_swim_gait132.py body | PASS | Eight candidate poses × eight views; all64 comparisons zero missing pixels |
| Rendered demonstration | capture.launcher.validation.json and bluegill-gait-ab.mp4 | PASS |240 GPU frames,30fps,8s; no interactive-button automation claim |

## 2. Security Scan

| Category | Finding | Severity | Status |
|---|---|---|---|
| Secrets/logs | No credentials or external services in new implementation | — | CLEAN |
| Injection | subprocess uses argv list, no shell; local explicit executable and paths | — | CLEAN |
| XSS | No web content or script injection added | — | N/A |
| Dependencies | No dependency installation or version changes | — | N/A |
| Stale success | Old receipt could survive early clean engine exit | High | FIXED: launcher23–26 removes exact previous mode receipts; fresh-receipt negative tests pass |

**Security Verdict:** CLEAN within this local experiment scope.

## 3. Karpathy Adversarial Principles

| Principle | Question | Answer / evidence | Verdict |
|---|---|---|---|
| Think Before Coding | Is this measured bluegill biomechanics? | No. Literature supports qualitative intermittentBCF; numeric gains and timing explicitly engineering hypotheses. Lab/field differences recorded. | PASS |
| Simplicity First | Why an adapter? | Existing asset/controller pipeline unchanged; one opt-in species config and wrapper are sufficient for an A/B. Private-interface coupling is explicit and hash-bound. | PASS |
| Surgical Changes | Any unrelated geometry/material changes? | None. Shared checker only extracts original coverage contract and adds a distinct candidate contract. Mouth126–132 work retained. | PASS |
| Goal-Driven | Could speed variation pass with gait disabled? | Initial test could, due ellipse speed variation. Fixed by spatial speed normalized against native instantaneous path speed and actual-bone wave checks. | PASS |

**Karpathy Score:**4/4.

## 4. Adversarial Dimension Review

### 4.1 Design

IntermittentFishGait.gd19–42 validates oscillator/controller bounds,67–101 integrates bounded fixed steps,103–112 preserves delayed steering independently of active wave amplitude. This is an experiment adapter, not a replacement rendering pipeline. Production files and all GLB/source assets remain unchanged. PASS.

### 4.2 Functionality

Reviewed finite rates, clip length, slow action clips, zero-delta action selection, restart, frame stalls, independent clocks, actual skeleton and body coverage. Queue-until-step at58–60 avoids exposing a native intermediate pose during action switches. Maximum actual adjacent bone step0.02547rad at60Hz;30/60Hz end poses identical. PASS.

### 4.3 Complexity

No species dispatch or speculative world simulation. Fixed120Hz plus a second steering pose pass is deliberately costly; microbenchmark0.469ms versus baseline0.223ms per presented update on one host. Not approved as a fish-school performance budget. This limit is material and documented. PASS for isolated trial.

### 4.4 Naming

travel_rate is a multiplier of the existing path clock, not metres/second or hydrodynamic thrust. Config and README explicitly describe this. body_hz and fin_hz are independent wall-time oscillator targets. PASS.

### 4.5 Comments

Comments explain phase compensation, stall limits and retained curvature. Research distinguishes evidence, engineering choices and unknowns; no cross-species calibration claim. PASS.

### 4.6 Style & Consistency

New helpers remain in Foundry resources; game research/card and local trial evidence remain in the independent game repository. Existing shared checker geometric computations and tolerances are unchanged. No unrelated formatting rewrite. PASS.

### 4.7 Context

Actual pixel textures and same installed model are reused. A/B at equal wall-time has different positions/headings because candidate travel is retimed; it is a behavior comparison, not an anatomical same-pose overlay. Separate GPU same-pose coverage handles material integrity. PASS.

### 4.8 Tests

Root requested stronger tests after identifying the ellipse confound and stale-output path. Normalized Swim speed means1.443 propel versus0.796 coast. Actual active-wave angle sum0.21455 versus0.02592rad; reconstruction error3.59e-8rad. Field/lab observations do not establish these gains. Baseline177 and candidate206/490 contracts are distinct; missing samples/actions/phases, invalid timestamps/revision and empty inventory are rejected. PASS.

## 5. Findings Summary

| Severity | Finding | Resolution |
|---|---|---|
| High | Native amplitude reduction also reduced turn/pitch steering | FIXED: retain yaw and pitch curvature; reduce only active base/wave contribution |
| High | Native action change could expose intermediate pose | FIXED: queued action resolved inside fixed tick; action boundary pose difference0 |
| High | Speed test could pass on ellipse geometry alone | FIXED: normalized spatial speed and actual skeleton wave checks |
| High | Candidate could be mislabeled as old standard coverage | FIXED: separate strict revision132 contract, untouched legacy contract |
| High | Prior successful receipt could mask early exit0 | FIXED: invalidate exact prior receipts and reject missing new receipt; three negative modes pass |
| Medium | Private controller API and120Hz overhead | ACCEPTED only for opt-in trial; hash-bound evidence and measured2.10× update cost, no production rollout |

## 6. Gate Decision

| Gate | Status |
|---|---|
| Automated checks | PASS |
| Security scan | CLEAN |
| Four principles |4/4 |
| Unresolved Critical/High findings | NONE |
| Code review document | COMPLETE |
| User visual acceptance | PENDING |
| Cross-species and production performance | NOT CLAIMED |

**APPROVE** the isolated bluegill trial. No commit/push performed. Numerical and sampled collision checks do not prove continuous-time contact or scientific fidelity. Root inspected rendered whole-fish frames0030/0060; opaque coverage is an independent technical check. Native window inspection returned the Godot project manager instead of the trial, so interactive UI automation is not claimed. Review the rendered video and rerunnable preview before deciding whether to integrate an optimized version.

## Submission follow-up

The user subsequently authorized committing and pushing this chat's changes in both repositories and removing this chat's disposable experiment output. Submission preserves original reports/hashes, the A/B video, two complete-fish stills and bluegill same-pose body PNGs. Raw per-pose mesh JSON, intermediate video frames and other-species baseline PNGs are removed with a checksum/size inventory in `cleanup.validation.json`; README states that those historical raw paths no longer exist and provides regeneration commands. No runtime implementation or scientific parameters changed during this packaging step. Unrelated active mouth experiments are excluded from staging and cleanup.
