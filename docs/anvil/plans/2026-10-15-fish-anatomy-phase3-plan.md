# 053 Phase 3 — isolated hypotheses and proposed surgical implementation

Status: failing reproductions executed; implementation **not started**. Phase 2 review is APPROVED. This document proposes Phase 4 work and requires independent Phase 3 review before production changes.

## Minimal failing tests

Run `.venv/bin/python projects/fishing-2d/experiments/blender-fish/knowledge-053/check_053_regressions.py`.

The harness reads the existing geometry diagnostics and verifies their native blend/source hashes before interpreting values. It does not edit a model or replace the workflow state. Result: **4 expected failures, 1 pass**.

| Isolated hypothesis | Failing observation | Meaning and limitation |
|---|---|---|
| A Y-only field cannot reduce the excess vertical height near the eye | HDOr at provisional u=.922 is 9.556% of derived SL; published observed interval is 4.0–8.2% SL | Cross-study SL/TL extrapolation and eye station are provisional. This is an observed specimen range, not a chosen tolerance or complete anatomy approval. |
| Independent fin placement leaves the attachment boundary outside the body | Rest maximum signed boundary gap: pectoral 3.269cm, pelvic 3.768cm | Entire frozen attachment boundary is tested; one buried vertex cannot pass. 0.05cm is an explicit production contact tolerance, not a biological measurement. |
| Preserving old skin weights/geometry preserves animated detachment | All 18 native Swim samples fail the proximal-band maximum-gap criterion for all four paired fins | Native vertex band is a diagnostic region, not a measured biological fin-base curve. Runtime four-action boundary tests remain mandatory. |
| Thin authored polygons, rather than the accepted source image, cause the tail silhouette loss | Upper/lower source retention 43.21%/48.40%, below proposed 95% source-fidelity criterion | Pixel-center ROI u<.16, upper v<.535/lower v>.55, alpha>216/255. 95% is an engineering source-retention target, not adult tail morphometry. |

The passing test ensures mouth width and global trunk-width targets remain explicitly unknown, and none of the provisional dimensions is falsely labeled accepted anatomy.

## Proposed changes, one cause at a time

### A. Native vertical field, preserving accepted head texture ownership

Add optional `rest_shape_revision.vertical_stations` rows:

```json
[ [0.60, 0.30, 0.70, 0.30, 0.70], [0.80, 0.30, 0.70, 0.35, 0.65] ]
```

Each row is `[u, source_top_v, source_bottom_v, target_top_v, target_bottom_v]`; all v coordinates use source image height, consistent with the existing profile. Require 2–128 increasing u rows, finite values in [0,1], top<bottom and bounded positive height ratios. Interpolate the affine scale/center mapping using the same bounded smooth station interpolation as width. Do not interpolate top/bottom independently in a way that permits crossing.

Apply the same X-dependent Z mapping to `Closed_body` and `Frontal_head_overlay`. Move paired fin and eye attachment centers by the same field while preserving appendage shape. Move armature rest anchors; preserve animation action curves. Midline fins follow the local root shift, rather than floating above a shortened body. Never silently change source pixels, material assignment or UVs.

First candidate changes only vertical head height; regenerate measured union sections at the eye station and a neighboring station interval. Verify head height against mean and observed range separately. Only after that isolated change passes proceed to inferred mouth/trunk changes.

### B. Explicitly inferred broad muzzle/trunk candidate

No quantitative mouth-width or matched maximum trunk-width measurement exists in the present cards. Root agent must label chosen snout/trunk changes `inference`, give reason and review views; do not describe them as measured biology.

Use the existing width station field where possible. Inspect the terminal ring: a multiplicative Y field cannot create span from exactly-zero-width vertices. If the old terminal cap cannot form a broad flat muzzle within bounded deformation, stop and propose an explicit head-ring replacement rather than raising scale limits until a numeric test passes. Mouth form remains a visual gate using front/dorsal/side clay and textured runtime views.

### C. Fin root attachment, opt-in and local

Proposed per-fin field:

```json
"root_attachment": {
  "mode": "body_surface",
  "root_band": 0.05,
  "blend_end": 0.35,
  "inset": 0.00025
}
```

`root_band` and `blend_end` use the existing anchor-to-tip t; inset is source-width units. Require 0<=root_band<blend_end<=1 and small bounded inset. `mode` has only the declared enum; no executable input.

For the frozen root band, query the actual closed body surface/BVH in shared rest coordinates, choose the matching body side and shift just inside the surface. Extend that displacement smoothly to zero by blend_end. Update the fin-bone anchor consistently. Root-band weights must follow the corresponding body-spine field (fin-bone influence zero at the attachment), with a smooth body-to-fin blend farther out. Preserve distal geometry, UVs, source image and unrelated fin parameters.

Validate the complete boundary and band at rest and all18 native Swim samples. Regenerate native contact measurements after every geometry/weight change. A positive maximum gap beyond engineering tolerance fails, even if minimum distance is negative. Also report excessive penetration rather than hiding it behind a signed-distance pass.

### D. Tail outline as a separate fix

Trace upper/lower polygons from accepted-source alpha in the fixed documented ROI. Root agent freezes those authored coordinates after inspecting the source and species illustration. Change polygon shape before considering fin amplitudes or camera changes.

Prefer replacing only `CaudalUpper`/`CaudalLower` membranes using the existing procedural triangulation/UV/weight method and existing bones. If native replacement is needed, add an explicit allowlist such as `rest_shape_revision.rebuild_fins: ["CaudalUpper", "CaudalLower"]`; reject unknown or nonexisting fin names. Reuse one shared fin-building function instead of rebuilding the accepted head. Source pixels/material ownership remain unchanged; replaced tail topology/UV differences must be reported as intentional per-part exceptions, not labeled whole-model preservation.

Run source-retention test separately from peduncle attachment and runtime lobe movement. No tail-fidelity numeric result substitutes for anatomical/visual review.

## Anatomy comparison CLI/report proposal

Keep research in a frozen reference card, referenced by optional profile `anatomy_reference: {"path": "...", "sha256": "..."}`. The card is input evidence, never a second workflow status. Do not add an unbound mutable research file to build acceptance.

Proposed `volume anatomy-validate --handoff <handoff> --json` reads current source/profile/model hashes, evaluates the native model using bundled code and writes a validation report associated with that handoff. Avoid changing historical `expected_outputs` contracts globally; use an optional anatomy-report output only for newly planned handoffs that carry the frozen card. Technical `volume validate` remains distinct and must expose anatomy as pending/incomplete when no current anatomy report exists.

Report each comparison with:

- Named anatomical metric and native station/landmark uncertainty; measured visible mesh union and units.
- Published mean/range and denominator; citation/table/sample/stage; no invented range.
- Conversion and provenance category: `published_ratio`, `derived_cross_study_scenario`, `inference`, `unmeasured`, or `noncomparable`.
- Actual percent difference from mean and comparison with the published observed interval, separately from any engineering tolerance.
- Mouth form and unmeasured traits explicitly pending; no numeric blanket anatomy pass.
- Contact boundary/band samples, maximum/minimum gaps and penetration, pose/action identity and input hashes.
- Tail source-retention region/alpha threshold and explicitly separate anatomical/visual state.

For actual Godot Swim/Turn/Ascend/Dive, freeze root sample vertex IDs/edge barycentric coordinates from rest, CPU-skin their positions using current Skeleton3D global poses and skin bind transforms, and compare to the equally posed closed body triangles. Reuse the existing controller; do not count envelope membership as contact. Report actual maximum boundary gaps for each frame/action. The prior runtime recorder can display the same frames, with synchronized before/after views.

## Required Phase 4 completion evidence

1. Each failing component retested after its own change, with regenerated current-hash diagnostics.
2. CLI/profile malformed/unknown/nonfinite parameters rejected; unchanged profiles retain prior behavior.
3. Technical closure/weights/loop/texture checks pass; declared native preservation audited per part.
4. Same-landmark biological comparisons and unknown/inference classifications recorded.
5. Root contact at rest,18nativeSwim poses and four actual Godot actions; explicit sampling/tolerance and penetration data.
6. Clay and full runtime orbit comparison of the whole fish, including both head sides, back, belly, tail and paired fin roots.
7. Independent Phase 4 review before any completed/accepted claim. Formal models remain unchanged until actual visual review.
