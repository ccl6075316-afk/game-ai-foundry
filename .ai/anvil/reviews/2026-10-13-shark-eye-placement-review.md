# Shark eye placement — independent adversarial review

Reviewer: `/root/mac_perf_review`. Date: 2026-10-13.
Scope: read-only production inspection; no generation, Blender/Godot run, production edits, or repair experiment. Checklist: anvil debug adversarial-checklist.md.

Reviewed `docs/anvil/debug-sessions/2026-10-13-shark-eye-placement-session.md`, complete Foundry backend, formal 040 profile/handoff/render report, both unchanged native sources, formal side/front/oblique images, complete older silver-arowana builder and existing silver runtime image. Independently replayed `/tmp/shark-eye-investigation/analyze.py` to `reviewer-replay.json`, checked runtime/formal GLB identity and counted the 804 source dark pixels.

## Phase 1 — APPROVED

| Question | Answer | Evidence |
|---|---|---|
| Q1 Actual root, not downstream symptom? | YES | Material ownership starts in head polygon selection and replaces native lateral eye UV with front y/z projection. Eye pigment is sheared over tapered surface; no separate eye object exists. Renderer displacement is downstream. |
| Q2 Sufficient evidence? | YES | Exported UV triangles reproduce source-center loss and bilateral widened front-eye support; rendered side/oblique views show corresponding distortion. Native source, profile and GLB hashes are identified. |
| Q3 Complete data flow? | YES | Accepted side/front pixels → profile contour and depth → polygon selector → material/UV replacement → exported GLB → identical runtime model. `eyes:null` and absence of eye meshes exclude an alternative geometry path. |
| Q4 Recent changes correlated? | YES | Git history/status inspected; backend/profile are untracked and have no implementation commits. Local notes explicitly record front-source calibration and tolerated elongation. No fictitious historic commit used. |
| Q5 Reproducible or documented limit? | YES | Independent probe replay reproduces the frozen exported defect. Existing Blender and actual Godot views agree. No new live renderer run was claimed; position measurements are explicitly rest-space texture support, not screen-space bbox. |

Scope of approval: causal investigation, not a proposed repair. Center error (<5 side-equivalent pixels) is distinct from axial expansion/shear. Source dark support is 804 pixels; 140 bilateral hits represent 70 unique retained pixels, 8.71%, not complete eye removal. Front ROI support is a manual dark-pixel subset, not a complete anatomical eye segmentation; its bbox touches ROI bounds, so it should remain a conservative support metric, not a precise whole-eye anatomy claim.

## Phase 2 — REJECTED (initial submission)

| Question | Answer | Evidence / required correction |
|---|---|---|
| Q1 Multiple verified working examples? | YES | Same-model unoverwritten flank/gill UV path plus separately anchored silver iris/pupil geometry, confirmed by complete source and existing runtime picture. Flat source images add view constraints; they are not themselves proven 3D reconstructions. |
| Q2 Reference read completely? | YES | Full older silver builder and current Foundry builder were read, including coordinate transforms, UV insets, materials, skinning, animation, export and validation. |
| Q3 All comparison differences listed? | NO | Table omits concrete coordinate normalization, sampling/inset, material/filter and pose differences. Old silver uses S=1800/CX918/CY260, 109×48 rings, 2px inset, Linear texture, metallic=.15/roughness=.55/emission=.10; current shark uses image-width/aspect coordinates, 129×64, up-to-12px plus opaque repair, nearest/0/1/.35. These confound direct cross-fish visual comparison and must be disclosed. |
| Q4 Dependencies/config/environment checked? | NO | Old frames 1..49 vs current 0..48, different body rig/shape/source resolution and different review camera/material contexts are not enumerated. Need explicit statement that only correspondence/ownership pattern is transferable; a same-shark fixed-pose/camera/material experiment establishes causality. |

Required correction is a documentation comparison/dependency inventory, not new code or rendering. Phase 3 and Phase 4 are NOT REVIEWED and NOT APPROVED.

## Phase 2 — re-review APPROVED

The session now includes the complete implementation-differences/confounders table and dependency boundary. Only initial failing questions were reopened; no build or experiment was performed.

- Q1 YES (unchanged): multiple inspected correspondence controls, not a claim that another species is an anatomical gold standard.
- Q2 YES (unchanged): complete implementations were inspected.
- Q3 YES: native source dimensions, coordinate units/centers, sampling/inset, filters, body and eye materials, separate eye geometry, donor/front ownership, frame interval, rig and animation differences are now explicit. Current Godot overrides are distinguished from old native Blender materials.
- Q4 YES: camera/light history is explicitly unknown rather than assumed identical; all source/mesh/pose/render dependencies must be frozen on the same shark for the upcoming ownership experiment. Cross-species appearance is only a pattern reference, not causal evidence.

This approves progression to hypothesis/testing. It does not approve the candidate as a production fix, any unperformed experiment, or Phase 3/4. Check full-eye visual coverage in addition to the stated manual dark-pixel ROI metric; include both sides/front/oblique, residual eye fragments and seams. Restoring a side-eye material assignment alone is insufficient for final visual acceptance.

## Phase 3 — APPROVED (causal experiment only)

Reviewed the full experiment/measurement scripts, baseline-failing-assertions.json, experiment.json, before/after metrics, and all ten matched images (five per case). Independently replayed the variant UV probe; verified 310 unique changed polygon IDs, matching frozen hashes, two restored center hits, 1608 bilateral dark-pixel hits, zero hits for both measured front ROIs, and unchanged formal blend/GLB hashes. No reviewer Blender/Godot build/render was run.

| Question | Answer | Evidence |
|---|---|---|
| Q1 Specific/falsifiable? | YES | Claims front ownership causes lateral spreading/shear and predicts restored side-source support with geometry/pose held fixed. Does not predict final all-view success. |
| Q2 Actually tests root cause? | YES | The independent exported-UV measurements plus matched renders show compact eyes return on both side and oblique views. This is stronger than checking a material setter alone. Sources, geometry and pose remain fixed. |
| Q3 Smallest single-variable change? | YES | Only material/UV ownership of the measured bilateral eye footprint changes; 310 polygon IDs recorded, no vertex, weight, topology, source, lighting or pose changes. Enlarging the trial region to include the entire measured front support was declared before mutation, and prevents an ROI-only cosmetic pass. Other loop UVs/material assignments and matched cameras are asserted unchanged. |
| Q4 Alternatives considered/ruled out? | YES | Source/model identity, separate eye mesh, global displacement, camera and skin pose alternatives were examined in Phase 1. The same-shark frozen-geometry/pose paired result further excludes those variables as the cause of the lateral improvement. |
| Q5 Honest response to confirmation/failure? | YES | The causal prediction is confirmed, while the proposed ownership-only substitution fails front-view quality. The report explicitly distinguishes these outcomes and rejects the variant as a final repair; it does not add assumptions to claim overall success. |

Visual finding independently confirmed: ownership-only side/oblique eyes become compact; front eyes regress into elongated brow-like marks with visible narrow transitions. Thus this is useful causal evidence but not an acceptable delivered model. Zero measured front-ROI hits is not proof of no possible pigment elsewhere; final acceptance must inspect complete eyes and seams. Phase 4 remains NOT REVIEWED / NOT APPROVED. No production import of this temporary variant is authorized by this review.

## Phase 4 — partial contract pre-review (NOT a final gate)

Reviewed new CLI/backend `eyes.mode=surface_patch` and `head_projection.uv_patches` contract plus five test groups. The full CLI log reports 675 tests, OK with 2 skipped. Explicit-mode whitelist, required companion fields, legacy omitted-mode behavior, finite scalar checks, donor bounds, and the 16×128 front-patch budget match between CLI and backend. No code execution or extra path fields are introduced.

**Open P2 finding — derived eye height is unbounded/non-finite despite valid input fields.** `source_rect=[0,0,1e-320,1]` passes the current CLI gate because its finite coordinates are increasing and lie inside [0,1]. The backend computes `height=radius*dv*H/(du*W)`, which becomes infinity for that input. Independently reproduced with a temporary existing test fixture and the same expression (`cli_accepts=true`, `derived_height=inf`); no Blender run. The contract needs a finite, bounded derived half-height check using the profile aspect at CLI validation and actual native dimensions before backend geometry creation, plus a positive-but-tiny rectangle-width regression case. This is an input validation defect, not evidence against the actual selected shark profile.

Remaining Phase 4 gate depends on this correction, final backend/profile and current formal CLI/Godot artifacts, all-angle eye/seam evidence, experiment metrics, and regression results. No final approval yet.

## Phase 4 — final APPROVED

Approval targets the **formal** 041 GLB SHA256 `5190f78e2cc6dfc37ca1d2b708102f46be6a38d5c65f37dd45582c0f63810929`, not the earlier smoke artifact. Independently checked formal/runtime byte identity, read the final all-mesh landmark and original-geometry reports, inspected the four official render artifacts and actual Godot five-view evidence, and ran the existing read-only `validate_volume` on the formal handoff. All eight mechanical/freshness checks pass. Handoff style review was still pending during this independent gate, as intended.

P2 is **CLOSED**: CLI and backend validate derived eye half-height as finite, positive, <=.05; backend additionally recomputes using actual native W/H before geometry creation. Independently retried widths `1e-320` and `5e-324`: both are blocked by CLI. Regression tests include tiny widths, excessive ratio, profile-aspect dependence and valid boundary. No Blender/model generation was rerun by the reviewer.

| Question | Answer | Evidence |
|---|---|---|
| Q1 Failing test before fix? | YES | Phase3 baseline assertions executed before any eye repair, showing source-center absence and oversized frontal support. The retained all-mesh checker also rejects unchanged040:70/804 per side, no source anchor and1680 competing front dark pixels. |
| Q2 Addresses identified cause? | YES | One bounded native-textured physical region now owns each eye, while side/front donor mappings remove competing old pigment. Eye location is anchored to the actual body surface, avoiding unconstrained global frontal projection of the anatomical feature. |
| Q3 Exactly one scoped change? | YES | All backend/profile/CLI/test changes implement and bound that eye ownership repair. Formal comparison confirms all10 original meshes retain canonical geometry and skin joints/weights; only two eye surfaces are added. Source PNGs, body shape, rig, world/camera behavior are not changed to hide the defect. No unrelated refactor found. |
| Q4 Introduces security risks? | NO — PASS | New fields are whitelisted declarative geometry/UV data with bounded counts, finite values, donor range guards and derived geometry bound. No executable profile fields, shell command, network path or provenance bypass added. Existing freshness/accepted-source gates remain operational; the identified non-finite-height hole is fixed. |
| Q5 Full regression suite? | YES | Final log `/tmp/foundry-shark-eye-final-tests.log`:676 total,674 passed,2 skipped,0 failures. Actual Apple M4 Godot report has66/66 passing checks, including native textures, animation, controls, switching, visibility and lifecycle. Formal read-only mechanical validation independently passed. |
| Q6 Explicit investigation-return plan? | YES | Session now labels attempt2 and explicitly stops further parameter tweaking if the same defect fails acceptance, returns to Phase1 with current hashes/UV/full-view evidence, and requires architecture re-review after a third failed repair rather than proceeding to a fourth trial. |

Formal `eye-landmark-validation.json` has all7 checks true:804/804 native dark-eye pixels per side, approximately44.50×39.87 side-equivalent support, anchor error<.59 pixels, and zero competing front-eye dark mappings in expanded ROIs. `original-geometry-validation.json` binds the original10-mesh comparison to the formal5190… artifact. The metric script inspects all meshes by embedded source image; mesh naming alone cannot make it pass. Pixel identity is separately protected by Foundry validation.

Visual acceptance scope: both side and oblique views retain compact anchored eyes; frontal view shows the same eyes as natural narrow ellipses, without the earlier eyebrow streaks or duplicate eye fragments. The tiny far-eye rim in oblique view is an actual bounded surface edge and is accepted at the inspected views. This is an authored two-view reconstruction, not a claim of anatomical accuracy at every possible angle. Final operator `volume accept` remains the root's state-recording step after this review; this report does not claim the human user has personally approved the visuals.
