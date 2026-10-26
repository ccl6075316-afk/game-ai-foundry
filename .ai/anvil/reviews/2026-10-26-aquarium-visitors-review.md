# Review Report: `2026-10-26-aquarium-visitors`

## Metadata

| Field | Value |
|---|---|
| Reviewer | anvil-lead, with independent visitor_validation review |
| MR / Commit | Working tree; no commit requested |
| Author | visitor_assets, visitor_runtime, visitor_validation |
| Review Date | 2026-10-26 |
| Status | APPROVED for integrated trial; user visual acceptance remains pending |

Scope is the large visitor implementation, reusable asset builder, and review harness. Unrelated fish-school, geometry and species work is excluded.

## 1. Automated Pre-checks

| Check | Command / evidence | Result | Notes |
|---|---|---|---|
| Formatting | game repository `git diff --check` | PASS | Existing hall line endings retained |
| Python syntax | AST parse of both visitor Python tools | PASS | No bytecode cache created |
| Godot parsing | Godot 4.7.1 checks and actual graphical review | PASS | Harness API errors fixed before final run |
| Behavior | `resources/scripts/visitors/test_hall_visitors.gd` | PASS | 51 checks, 133109 segment samples; 22/24 move over 1m in 30s, watch state observed |
| Asset sweep | `output/visitors-v1/review/mesh-sweep-validation.json` | PASS | 720 phases × 9 blends; maximum horizontal radius 0.342672m, navigation uses 0.36m |
| Cold resource read | saved `.res` meshes, actual new Godot process | PASS | No runtime mesh builder; float pivots checked after reload |
| Graphical comparison | `plans/reviews/aquarium-visitors-v1/runtime.validation.json` | PASS | Actual 0/24/100/200/0; 45 warmup + 180 samples per count; camera checked every measured frame |
| Evidence freshness | SHA-256 verification | PASS | 25 runtime bindings and 5 behavior bindings current; four exported mesh hashes current |
| Shell launcher | `bash -n`, `--help`, `--dry-run` | PASS | Windows execution unavailable on this Mac |
| Normal game entry | `output/visitors-v1/review/launcher-entry-validation.json` | PASS | Stale Oct 23 C# assembly rebuilt with `dotnet build --no-restore`: 0 errors, 3 inherited deprecation warnings. Positive scene-tree probe finds 24 visitors, valid resources, coast-return connection and slot save path. |

No dedicated repository GDScript linter was added. Inherited fish PNG export warnings remain; this is an editor/runtime trial, not an exported-package certification.

## 2. Security Scan

| Category | Finding | Severity | Status |
|---|---|---|---|
| Hardcoded secrets | None in visitor code/provenance/logs | — | CLEAN |
| Injection risks | Launcher uses quoted argument arrays; no eval | — | CLEAN |
| XSS / database injection | No browser/database execution | — | N/A |
| Dependencies | No new runtime packages; existing Python/Godot used | — | No new dependency surface |
| Sensitive logs / network | User authorized this round's prompt service and reference upload; no credentials retained | — | CLEAN |

**Security Verdict: CLEAN for the scoped change.** This is not an audit of unrelated dependencies.

## 3. Karpathy Adversarial Principles

| Principle | Question | Answer | Verdict |
|---|---|---|---|
| Think Before Coding | Is visual style or capacity being assumed? | Frozen brief requires existing pixel art; 200 is a bounded stress trial, not a device guarantee. | PASS |
| Simplicity First | Are per-person rigs and physics necessary? | Four shared meshes/material and data-only agents avoid those costs. Navigation grid exists because the hall is editable. | PASS |
| Surgical Changes | Are unrelated fish/save systems changed? | Hall diff is population UI and geometry hooks; save schema and fish logic unchanged. | PASS |
| Goal-Driven Execution | Are tests proving visible behavior? | Movement, watch stops, doorway clearance, rotated obstacles, layout edits, off mode and actual renderer populations checked. | PASS |

**Karpathy Score: 4/4.**

## 4. Adversarial Dimension Review

### 4.1 Design

`HallVisitorCrowd.gd:30` creates only four MultiMesh nodes. `:148` performs bounded route scheduling; no visitor physics body or skeleton. `HallVisitorNavigation.gd:19` rebuilds only on geometry changes. Four whole-hall batches deliberately trade individual frustum culling for simple low-count overhead. PASS within the 200-person trial.

### 4.2 Functionality

`HallVisitorNavigation.gd:84` expands each local obstacle before transforming its raster bounds, including rotated tanks. `HallVisitorCrowd.gd:80` clears old routes immediately on geometry edits; a 0.12s settle delay avoids repeated rebuilds while dragging. `:53` rejects missing mesh/material/atlas resources and reports zero active people. Empty, disconnected, fully blocked, concave and doorway layouts, negative/excess count, pause and re-enable behavior are covered. PASS.

### 4.3 Complexity

The grid/component map, spatial buckets and GPU pose data each serve a present requirement. No economy, visitor needs, individual facial rig, animation graph or speculative asset registry was added. Four base resources plus one material/atlas remain reviewable. PASS.

### 4.4 Naming

`set_layout`, `set_paused`, `set_visitor_count`, `point_clear` and `get_review_snapshot` describe their effects. Requested and actual populations are reported separately. “Stress trial” is not labeled supported capacity. PASS.

### 4.5 Comments

Comments explain the opposite 3D/2D rotation sign, conservative clearance, float pivot encoding and spawn spacing. No unowned TODO is used to excuse an incomplete path. PASS.

### 4.6 Style & Consistency

Existing hall formatting/line endings are preserved. New functionality is in visitor files and narrowly scoped hall hooks. Source art and reusable tooling live in their established project/resources locations. PASS.

### 4.7 Context

Source brief, corrected generation prompt, original style reference, source image and hashes are retained. The female donor is slightly three-quarter; it is not claimed to be calibrated orthographic art. Actual front/back/oblique/animated showroom images and hall views were inspected. Faces/clothes retain painted pixel clusters; the existing dark blue hall lighting reduces their color visibility. Trial accepted by agent only. PASS for trial, visual acceptance pending user.

### 4.8 Tests

Tests use actual resource loads and movement, rather than mocks. Segment checks compare against footprint/obstacle geometry. Sweep sampling is discrete and does not prove all continuous times. The final graphical run locks GUI/camera input, asserts camera stability and source freshness, and records failed attempts separately. PASS with documented measurement limits.

## 5. Findings Summary

| Severity | Location | Finding | Resolution |
|---|---|---|---|
| High | `build_visitors.py:122` | Opposite triangle winding displayed inner/back faces | Clockwise Godot winding; actual multi-view check |
| High | `save_visitor_meshes.gd:34`, `VisitorMaterial.gdshader:25` | COLOR encoding changed joint pivots and disconnected limbs | Float CUSTOM0; cold reload error below 1µm; walking screenshots checked |
| Medium | `build_visitors.py` trouser donor map | Side donor included hand pixels/contour stripes | Unobscured cloth donor; actual oblique check |
| High | `HallVisitorNavigation.gd:6`, `:84` | Animated body needed larger clearance; rotated inflation needed correct raster bounds | 0.36m body radius and transformed inflated rectangle; route/sweep checks |
| Medium | `HallVisitorCrowd.gd:53` | Missing resources could leave invisible simulated visitors | Explicit validation, fail-closed groups, tested failure/recovery |
| High | `HallVisitorReview.gd` benchmark | Wrong get_render_info arity invalidated initial run | Two-argument API, fail-fast missing-trial checks; failed attempt preserved |
| High | `HallVisitorReview.gd:114`, `:178` | GUI signal allowed camera drift during first Metal run | Disconnect canvas input, recursively disable GUI input, assert camera every frame; rerun passed |

No unresolved Critical or High findings in the visitor trial. Mac Compatibility cannot link an inherited fish shader using 18 texture samplers against a 16-sampler limit; scoped Mac launcher selects Metal. This is not reported as a visitor regression or a Compatibility pass.

## 6. Gate Decision

| Gate | Status |
|---|---|
| Scoped automated checks | PASS |
| Security review | CLEAN |
| Karpathy score | 4/4 |
| Unresolved Critical / High | None |
| Review document | Complete |
| User visual acceptance | Pending; independent of technical review |

**APPROVE the integrated trial.** No commit/push performed.

Final fixed-camera M4/Metal medians: whole hall 7.869ms at zero, 8.303ms at 24, 8.2305ms at 100, 8.598ms at 200; visitor update CPU 0.106/0.351/0.7135ms. Repeat-zero median is 7.9865ms (0.1175ms drift). GPU cost is not isolated, and the single ordered run is not a hardware capacity guarantee. The renderer reported 362 draw calls across counts; primitive growth matches 1344 average triangles/person, so no unmeasured “four additional draw calls” claim is made.
