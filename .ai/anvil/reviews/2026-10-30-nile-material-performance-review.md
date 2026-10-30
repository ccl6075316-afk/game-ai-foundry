# Review Report: `2026-10-30-nile-material-performance`

## Metadata

| Field | Value |
|---|---|
| Reviewer | Independent `/root/nile_material_review` |
| MR / Commit | Uncommitted R10 isolated material/performance experiment |
| Author | `nile_material_atlas`, `nile_material_benchmark` |
| Review Date | 2026-10-30 Asia/Shanghai |
| Status | APPROVED — isolated controlled experiment, code and evidence; no production asset/FPS acceptance |

## 1. Automated Pre-checks

| Check | Command | Result | Notes |
|---|---|---|---|
| Python syntax | `ast.parse` on packer, behavior tests, case runner | PASS | No writes or package additions |
| Unit tests | `.venv/bin/python resources/scripts/volume-fish/test_pack_fish_material_atlas.py` | PASS | Three tests, actual synthetic GLB; opacity/wrap/linear mouth, alias/overwrite, incompatible materials |
| Independent GLB comparison | Decode original and candidate accessors, compare each of nine recorded part ranges | PASS | POSITION/NORMAL/JOINTS/WEIGHTS and directed triangle indices exact; IBMs and animation channels/times/values exact |
| Alpha control | Compare the MASK/OPAQUE binary streams | PASS | BIN byte exact; intended material alpha setting change only |
| GDScript runtime | Actual GPU case receipts, independently audited | PASS |36 adopted controlled cases; invalid/window-rejected experiments excluded |
| Controlled aggregate tests | `.venv/bin/python resources/scripts/volume-fish/test_summarize_fish_material_matrix.py` | PASS |6 meaningful negative/positive protocol controls; independently rerun after rendering ended |
| Lint / static type checker | Dedicated infrastructure for these scripts | N/A | No new dependencies; project style matches existing tools |

Baseline SHA: `2e947fb4116f3dbdfc9128080efec0907c5cb87a7f4795e0a6f8bb87c8cf859a`.
Initial merged MASK SHA: `912a2f3d336e0ebf92b30fd457131fc845518922a2712726f9bfa9e1905152b9`.

## 2. Security Scan

| Category | Finding | Severity | Status |
|---|---|---|---|
| Hardcoded secrets / logged credentials | None | — | CLEAN |
| Injection | Child process uses argv arrays, no shell interpolation | — | CLEAN |
| XSS | No web/UI text execution | — | N/A |
| Dependency CVEs | No newly installed dependencies; no claim of repository-wide CVE scan | — | N/A |
| Evidence/path ownership | Packer accepts any path with a component named work/output/experiments | Medium | Requested narrow repository-root guard |

**Security verdict:** CLEAN within changed code; path guard recommendation fixed. No new dependency installation or whole-repository CVE claim.

## 3. Karpathy Adversarial Principles

| Principle | Question / assessment | Verdict |
|---|---|---|
| Think Before Coding | Same skin, common parent, identity mesh transforms, no morphs, exact supported vertex semantics are checked before joining. Source tiling is explicitly extended into atlas rather than clamped. | PASS |
| Simplicity First | One atlas packer and one bounded single-case runner; no new workflow backend, AI or production runtime layer. | PASS |
| Surgical Changes | New experiment-only files. Original R9 source/export and accepted mouth untouched. | PASS |
| Goal-Driven Execution | Three actual variants distinguish old split surfaces, packed MASK, and packed OPAQUE; GPU visual equivalence remains separate from throughput. | PASS |

**Karpathy score:**4/4 within the isolated experiment and qualified result scope below.

## 4. Adversarial Dimension Review

### 4.1 Design

`pack_fish_material_atlas.py:125–147` rejects unlike parents/skins/transforms and animated mesh nodes. It concatenates disconnected vertices and index ranges without welding or changing skin coordinates. `:178–182` preserves node indices/names while removing unused mesh bindings, retaining clip targets and skeleton names. Appropriate narrow production candidate rather than runtime reconstruction. PASS for actual Nile input.

### 4.2 Functionality

`pack_fish_material_atlas.py:78–100,151–172` preserves native texel scale and original repeat/clamp modes over each actual affine UV domain, including body UV outside 0–1. Bodies formerly OPAQUE receive atlas alpha255; fin MASK retains alpha. Source linear baseColorFactor becomes linear COLOR_0 with a white texel, avoiding mouth-color quantization/gamma baking. Actual GPU parity is required to verify importer/material behavior.

`material_settings:63–69` retains arbitrary material extensions while replacing texture tables. Current Nile only has numeric KHR_materials_specular.specularFactor0, so its output is valid; a future extension texture reference could silently point at the new atlas. Requested explicit supported numeric-extension restriction instead of broad compatibility claim.

`benchmark_fish_materials.gd:107–125,146–182` shares prototype resources and creates independent skeleton/controller instances; real controller step followed by carrier reset preserves the fixed visible layout. Pose-change assertion checks requested animation/static branch. Frame interval and direct controller call are separated, GPU0 is flagged unavailable, not interpreted as zero cost. Capture and runtime raw counters still need final artifact review.

Boundary checks reviewed: input aliases, existing evidence, unsupported PBR maps/material settings, UV wrapping, missing headless GPU, bounded samples/count/timeouts and Godot errors even when process exit is zero. No GPU test launched by this reviewer.

### 4.3 Complexity

No speculative model reduction, multimesh, alternate renderer or new rig. Two output alpha variants share exact geometry/BIN. Renderer timing can be unavailable without widening scope. PASS.

### 4.4 Naming

Original module description “Lossless” was overly broad: native image pixels are unresampled, but nearest sampling can differ at FLOAT32 texel boundaries. Actual probe reports 4 RGBA mismatches out of210688 sampled points and maximum address difference0.000060918 original px. Wording is now “Native-pixel-preserving”; report discloses the limitation. No zero-pixel-difference claim approved.

### 4.5 Comments

Comments explain transform, crop, opacity and timing constraints. Scope correctly distinguishes experiment from editable-source delivery/user asset acceptance. PASS subject final document stating visual differences and sample limitations.

### 4.6 Style & Consistency

New tools follow existing compact Python/GDScript utility style; no unrelated formatting edits found. PASS.

### 4.7 Context

R9 remains frozen; no full490 re-run or ledger retargeting is required for these isolated non-delivery candidates. A future adopted source/GLB must be authored/frozen and revalidated separately. Material merge does not prove a thousand-fish gameplay budget. PASS.

### 4.8 Tests

Behavior tests check real synthetic GLBs and output opacity/color values, not mocks. Independent reviewer additionally decoded the current source/candidate data and verified nine ranges, skin and clips, avoiding sole reliance on builder boolean fields. Six aggregation tests reject missing or extra actual draws, incomplete geometry work, missing motion/image change, incomplete samples, invented GPU timer and inconsistent step components. Fresh actual capture and complete controlled matrix evidence independently audited below. PASS for declared experiment scope.

## 5. Findings Summary

| Severity | Location | Finding | Required action/status |
|---|---|---|---|
| High | Original packer COLOR_0 / actual Godot material path | Actual same-camera head-front capture brightens oral cavity (~948 pixels, max channel difference132). This is materially larger than the four near-boundary UV probe differences. | RESOLVED in candidates-v2 after offline sRGB patch correction and actual captures-v3 review; v1 remains rejected and distinct. |
| Medium | Original Packer:53–60 | Output containment checked component names rather than allowed repository roots | FIXED: resolved path must lie in current Foundry work/output or projects/project/experiments. New external-work negative passed. |
| Medium | Original Packer:63–69 | Retained extension texture references would be invalid after texture-table replacement | FIXED: only empty extensions or known scalar specularFactor0 allowed. Texture-extension negative passed. |
| Low | Packer:1 | “Lossless” could be read as zero nearest-sample differences | FIXED wording; quantified probe/GPU parity still required. |

Fix verification: independently reran all five behavioral tests, PASS. Current builder SHA `a591da545b38d852ebd0969eb0fa8d90a23c18848aeeb98ad69105fc8a53c0a4`. Candidate GLB bytes remain unchanged. Packing report preserves original generation-tool hash, with a separate post-generation guard-review receipt; it does not pretend the candidate was regenerated. All node hierarchy/rest transforms/names/extras independently compared unchanged except intended mesh/skin assignment removal. The supplementary `analyze_fish_alpha_dependence.py` is a source-bound, no-asset-write rest-triangle diagnostic; its fractions explicitly exclude visible-screen/occlusion/action-time interpretation.

### Actual mouth-color regression: root cause and v2 fix review

Independent reviewer viewed both actual `captures/baseline9/rest-head-front.png` and failed `captures/merged-mask/rest-head-front.png`; the mouth upper interior became visibly white. `actual-material-colors.validation.json` proves merged ARRAY_COLOR contains1465 values including the dark oral factor, yet the imported material has `vertex_color_use_as_albedo=false`, a white albedo and a white constant texel. This explains the region and is unrelated to the four UV-boundary samples. Actual COLOR values also show byte quantization, so merely switching a runtime color flag would not establish exact equivalence.

Debug Phase1/2/3 review APPROVED: reproducer and working baseline texture/factor path support a single offline correction. Phase4 code review APPROVED: encode textureless linear factors with the standard piecewise sRGB function to a dedicated rounded RGBA8 atlas patch, omit COLOR_0, and reject nonwhite textured factors instead of inventing an untested bake. The report records source linear value, sRGB target, byte values, decoded linear errors and explicitly does not equate half-byte encoding error with screen-pixel error.

Independently reran six behavioral tests, PASS, including the prior-white-texel failure witness. Independently decoded new v2 GLB ranges: all9part POSITION/NORMAL/JOINTS/WEIGHTS/directed indices unchanged, no COLOR_0, MASK/OPAQUE BIN exact. New builder SHA `9b518e82712c06e3614e344a4d05f1c4aa8dcd3821a5a7902c17389b9f05fb85`; v2 MASK `b8a7794a87803aa0e01fa56a071a6166f9699f5f9bd2199acefb2d60dee16cec`. Failed v1 artifacts remain distinct and are not overwritten.

### Actual v3 captures and bounded capture fix

The first v2 capture stalled after25images and timed out at180seconds without a complete report; it is invalid, not a performance result. New capture uses the previously established synchronous `RenderingServer.force_draw()` only in the screenshot branch (`benchmark_fish_materials.gd:224–229`). Benchmark measurement still waits for natural `frame_post_draw` (`:176–195`), so forced screenshot rendering cannot contaminate measured case cadence. Window state is reported and an8second progress watchdog writes a failed receipt and exits; process timeout/log/report checks remain fail-closed.

Independent reviewer actually viewed `captures-v3/comparison/rest-head.png`, `rest-fins.png`, `Swim-whole.png`, and full-resolution baseline9/merged-mask `rest-head-front.png`. The white oral region is gone and accepted mouth/whole-fish appearance is retained at the reviewed views. Independently checked all144 capture file hashes,48images per variant, and identical labels, bone pose hashes, camera focus/direction/size; windows report can_draw and not minimized. No engine process, benchmark or new tests were launched during the formal matrix.

MASK capture comparison is approximately equivalent, **not pixel identical**:227pixels differ by more than1 channel step and122by more than8 over48images. OPAQUE changes29478pixels by more than1 and28641by more than8; visible fin edges differ, so its timings are only an alpha-disabled control, not an equal-quality replacement. Mouth-color High is resolved for v2. Actual formal matrix comparability remains pending.

## 6. Final controlled-protocol and data audit

Normal-window matrices were rejected when macOS reported non-drawable/minimized state; no partial valid-looking rows from them were mixed into the controlled protocol. The controlled implementation deliberately minimizes only its own window, disables automatic render-loop execution, refreshes normal engine/deferred state, calls `force_draw(false)` once, then synchronously reads back the actual1280×720 GPU texture. The explicit GPU, per-step counters and images establish work even though the own window is minimized; minimization alone is not treated as evidence of drawing. There is no call that restores/focuses another user window.

`benchmark_fish_materials_controlled.gd:79–127` separately reports direct motion-call, engine refresh/wait, forced draw+readback and total controlled-step wall time. The latter three include CPU/driver work, synchronization and readback/allocation; they are **not pure GPU milliseconds, normal frame latency or game FPS**. `run_fish_material_controlled_case.py:59–75` rejects missing/failed reports, logged errors, timeouts, stale inputs, wrong raw counts or incomplete GPU work even when Godot exits zero.

Independent audit of all adopted cases, without invoking rendering or rerunning benchmarks:

- 36 adopted successful processes:3variants×3counts×2motion modes×2rounds,2160 measured raw samples plus15warmup draws per process.
- 432 current per-case input-path/hash checks passed; case report SHA and execution status/timeout/error gates passed.
- Every measured sample has exactly one explicit draw signal,1710×N triangles and9×N versus1×N viewport draws. Exactly75signals per process. Each fish retains1465vertices/1710triangles/18bones; no zero-render/headless/dummy case accepted.
- 72actual first/last PNG hashes,1280×720 dimensions and nonblank content verified. Independently decoded images and reproduced SHA256 of hex-encoded RGBA bytes; static image/pose fingerprints remain equal, moving image/pose fingerprints change. The field called `first_image_RGBA_sha256` is a hex-encoded-byte fingerprint, not the standard direct-raw-byte SHA; PNG file hashes are standard SHA256.
- All60raw timing components are finite/nonnegative and compose the total within5µs. Independently recalculated each case P50/P95 and pooled120samples per condition using the declared lower empirical quantile; no averaged-percentile substitution.
- Actual completion timestamps match the planned global case order. Round1 uses baseline→MASK→OPAQUE and round2 reverses each group. The running manifest truthfully says it was created during execution; it does not pretend to be a pre-run artifact.
- The original `r2-1000-motion-merged-opaque` failed its own-window minimized postcondition and its execution was rejected. It is preserved and excluded. The explicit `-retry2` mapping reruns the whole last three-variant block with the same frozen source and opposite order, rather than replacing a valid slow case. The earlier33adopted cases were not reselected or rerun.
- Three old-capture reports retain their original29df capture-source hash through an exact archived script; other12capture bindings are current.144v3images and same-pose/camera binding audit passed as recorded above. R9 GLB remains `2e947fb…859a`, blend `ba78cd…7591`, and all18R9SOP candidate bindings remain current.
- `git diff --check` passed. No GPU process, model export, live benchmark or heavy task was started by this reviewer during timing.

### Independently reproduced1000fish pooled results

| Condition / metric | Original9surfaces | Packed MASK1surface | Packed OPAQUE1surface |
|---|---:|---:|---:|
| Static controlled-step P50 ms |23.855|6.936|6.909|
| Moving controlled-step P50 ms |2228.378|485.876|482.745|
| Actual viewport draws |9000|1000|1000|
| Actual triangles |1710000|1710000|1710000|

Moving baseline→packed MASK pooled controlled-step reduction is78.19598%; opposite rounds independently give77.93510% and78.86614%. This is the combined atlas/texture-binding, mesh and surface packing change, not an isolated “material-only” or draw-call-only effect. Normal controller direct-call cost remains substantial and does not disappear.

Moving MASK→OPAQUE pooled reduction is only0.64440%; rounds give−0.65979% and+2.20340%, so direction is not stable. OPAQUE additionally changes visible fin edges and is not equal-quality. No extra-face candidate was built or measured. Supported conclusion: prioritize packing while preserving cutout; these data do not justify extra geometry solely to remove cutout. They do not establish that added faces are universally more expensive.

## 7. Gate Decision

- [x] Python syntax and six packer behavior tests passed; six aggregate protocol tests independently passed.
- [x] Independent current-GLB geometry/normal/skin/directed-index/clip comparison passed.
- [x] Actual GPU oral-color High resolved by offline v2 patch and fresh actual visual review.
- [x] Path/material-extension guards fixed; no unresolved Critical/High findings.
- [x] Complete controlled36case evidence and retry/order/quantile provenance independently checked.
- [x] Review document complete with specific implementation and result scope.

**APPROVED** for the isolated material/performance experiment and qualified conclusions above. No production installation, editable-blend equivalence, full-fish user acceptance, conventional FPS promise or pure-GPU claim is approved. Any later chosen production packing/source changes need their own final asset/export and applicable acceptance process; the reviewed R9 asset is preserved.
