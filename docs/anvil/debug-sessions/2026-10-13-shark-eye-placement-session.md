# Shark eye placement — investigation session

- Date: 2026-10-13 (Asia/Shanghai)
- User report: 最终鲨鱼眼睛位置很奇怪，要求处理。
- Mode: **Normal**. Existing Blender build/render reports, actual Godot Apple M4 probe output, and fixed-angle screenshots are available. This is not a code-only inference.
- Initial scope: Phase 1/2 were read-only. After their independent gates, root authorized a temporary Phase3 experiment, then the bounded Phase4 implementation recorded below. Original040 accepted inputs/artifacts and both PNGs remain unchanged; new041 inputs carry the repair.
- Gates: Phase 1 **APPROVED** by independent reviewer after rerunning GLB measurements and checking source dark-pixel count/runtime hash. Phase 2 initial review **REJECTED** for missing comparison confounders, then **APPROVED** after supplementation. Independent review: `.ai/anvil/reviews/2026-10-13-shark-eye-placement-review.md`. Only entry to Phase 3 is approved, not a candidate fix. Phase3 approved as a causal experiment; Phase4 implemented after explicit root authorization and awaits final independent gate/formal integration.
- Prior acceptance explicitly allowed elongated oblique eyes. That acceptance is historical evidence, not a reason to reject the user's current defect report.

## Evidence inventory and identity

All repository paths below are relative to `/Users/czl/projects/game-ai-foundry`.

| Evidence | Location / identity |
|---|---|
| Formal handoff | `projects/fishing-2d/experiments/blender-fish/models/blacktip_reef_shark/040-foundry.handoff.json` |
| Production profile | sibling `040-blacktip.profile.json`; SHA256 `a624f436efd8b56ff19885a89c90115eda3f6b1c91600b7acc4af44569dd825e` |
| Formal artifacts | sibling `040-foundry.handoff-artifacts/{fish.glb,fish.blend,validation.json,render.json}` |
| Formal and runtime GLB | Both SHA256 `723597f32472f830c9d8b176acabe2213a50ad9e27cca79904fff9a0f4cc656b`; runtime `projects/fishing-2d/game/assets/models/fish/blacktip_reef_shark.glb` |
| Accepted side source | `projects/fisher-pixel-volume-040/output/char_blacktip_pixel040_nobg.png`, 1834×618; SHA256 `46bcbb995edb66055ffa159f753077bfe15fc2454f892ed7a4b2c6ce18b4b56a` |
| Accepted front source | `projects/fisher-pixel-volume-front040/output/char_blacktip_front040_nobg.png`, 891×654; SHA256 `b1e194b615c83b711d0028510da47f1932c895d7c325caaf0976c0e215bce96d` |
| Blender fixed views | formal `review/{side,front,oblique,style-comparison}.png` |
| Actual Godot result | `projects/fishing-2d/output/040-foundry-pixel-volume-qa/{blacktip_reef_shark-final.png,validation.json}` |
| Actual Godot angle controls | `/tmp/fishing-040-probes/FinalAngles.gd` and `blacktip_reef_shark-angle-{0.0,1.5707963267949,3.14159265358979}.png` |
| Read-only GLB probe | `/tmp/shark-eye-investigation/analyze.py`, results `/tmp/shark-eye-investigation/metrics.json` |

Existing build: 8 mechanical checks pass, 9162 vertices, 18 bones, 1817 body polygons assigned front material. Existing Godot probe checks texture dimensions/filter/material/bones/controls/lifecycle. None measures eye landmark position or shape. Formal handoff acceptance hashes match the inspected runtime GLB; a stale model or alternate import is not the explanation.

## Phase 1 — reproduction and trace

### Reproduction from existing runtime evidence

The recorded Godot probe selects blacktip, enters close view, pauses, and records yaw `0`, `.58`, `PI/2`, `PI`; pitch is `.12` only for yaw `.58`, otherwise zero. Actual images show:

- Side: eye is swept/slanted backward, unlike the compact near-round source eye.
- Front: two oval eyes and mouth look coherent in isolation.
- Oblique: eye has an elongated upper/backward streak; the defect is visible in both Blender and actual Godot rendering.
- Opposite side is subject to the same mapping; GLB measurements below quantify both sides independently. Front source itself is not perfectly bilateral, so exact pixel symmetry is not assumed.

No new live application reproduction was run in this investigation. Inspection reproduces the diagnosis on the existing fixed-angle images and immutable exported triangles. Frame/camera differences cannot account for a distortion already present in rest-space UV support.

### Recent changes and data flow

`git status` reports the new backend/resources and production profile as **untracked**. `git log` for these paths returns no tracked implementation history; there is no historical commit diff to cite. Earlier local calibration changed both inferred head thickness and front projection coverage, then explicitly accepted eye elongation. That calibration record is evidence of origin, not proof of correctness.

Data flow:

1. Side source → profile body cross-sections → closed elliptical rings → side UV `u=X+.5`, `v=.5-Z/(618/1834)`.
2. `resources/scripts/volume-fish/build_fish.py:162–174` replaces entire polygon material/UV when its center is within the head interval and face-normal thresholds pass.
3. Current profile: `start_u=.6`, `end_u=1`, `normal_threshold=.08`, `side_limit=.94`, head rectangle `(210,238)..(681,615)`, model lateral range `[-.08,.08]`, model side-source height range `190..483`.
4. Front UV is a **lateral/vertical planar projection**, not a landmark correspondence or UV unwrap. In source-pixel form:
   - `front_x = 210 + ((Y+.08)/.16)*471`
   - `front_y = 238 + ((side_y-190)/293)*377`
   - Axial coordinate `X` does not enter either equation. It is inferred by the intersection with the curved head surface.
5. Entire head is then skinned/exported. `eyes:null` means there are **no separate eyeball meshes**. Front and residual side eyes are pigment on one closed body.
6. GLB has two body primitives: 12814 side-material triangles and 3694 front-material triangles. The front primitive extends back to `u=.671943`; it is not confined to a small nasal cap.

`abs(normal.y)<.94` allows faces close to a side-facing orientation (within roughly 20° of pure side). The gate is a polygon material selection, not a view-dependent switch. Looking from the side still sees front-textured head faces.

### Measurement method and limits

The read-only probe decodes formal GLB accessors and triangle indices, including actual UVs and material assignment. For a selected source pixel center, it solves barycentric coordinates in UV space, then maps to rest-space triangle position. glTF `(x,y,z)` is converted back to Blender `(x,-z,y)` for the reported head/lateral/up axes.

Eye ROIs were selected visually on unchanged native PNGs. Dark-eye support is defined as alpha >240 and `max(R,G,B)<100` within those ROIs. This captures pupil and dark eye border within each ROI, not an anatomical eyeball segmentation. Some front dark pixels touch ROI edges: the reported footprint is ROI support, not proof of the complete eye extent. Later experiments must inspect the complete eye and surrounding fragments, not improve the score by clipping the ROI. Native source pixels are counted uniquely; bilateral triangle hits are not counted twice as source area.

**All model dimensions below describe texture support on exported triangles**, reprojected to the side-image coordinate scale; they are not measured screen-space bounding boxes. No occlusion, camera perspective, shading, or animated pose is applied. The independent render evidence establishes that the support distortion is visible, but the precise screen ratio depends on view.

### Native landmarks versus mapped support

| Quantity | Side source / desired correspondence | Current model result |
|---|---|---|
| Side eye ROI | x1663..1714, y301..349 | Original eye center `(1688,326)` has no triangle hit in side-material primitive |
| Side dark eye support | x1665..1712, y305..344: 48×40 pixels; 804 unique dark pixels | Only **70/804 = 8.71%** remain in side material, x1665..1681,y330..343 (posterior/lower fragment) |
| Original side-material extent | Eye center u=.920393 | Side primitive max u=.917189, equivalent x1682.125; this alone proves center loss, **not** loss of the entire eye ROI |
| Front left ROI | x240..275,y378..446; anchor `(258,412)` | Anchor `(X,Y,Z)=(.418011,-.063694,-.008850)` → side-equivalent center `(1683.63,325.23)` |
| Front right ROI | x612..648,y378..446; anchor `(630,412)` | Anchor `(.420604,.062675,-.008850)` → side-equivalent center `(1688.39,325.23)` |
| Front left dark support mapped to side plane | Original front dark support x240..275,y382..441 | x1632.36..1709.92,y302.30..348.16: span **77.55×45.85** |
| Front right dark support mapped to side plane | Original front dark support x612..648,y382..441 | x1634.23..1713.32,y302.30..348.16: span **79.09×45.85** |

Compared with the side source's 48×40 support, mapped front eye support is about **1.62–1.65× wider** and **1.15× taller**. The center is only ~4.4 pixels back on one side and ~0.4 forward on the other, with <1 pixel vertical center discrepancy. Thus **large vertical displacement of the eye center is not supported**. The user's perceived odd position is consistent with posterior spreading/slant and mixed residual eye fragments, not a simply translated eyeball.

Mapping has measurable shear, not only width change:

- At front x258, moving source y402→422 changes model X `.411891→.420638` while Z changes `-.004612→-.013088`: roughly **16.0 side-equivalent pixels of axial drift across 15.5 vertical pixels**.
- At front y412, moving source x248→268 changes X `.406861→.425747`, equivalent to **34.6 axial pixels**, over a front-source width of 20 pixels. This is a projection onto a sloping nose, not a scale-preserving eye patch.
- The source front eye is vertically elongated (roughly 36×60 dark support) while the side eye is compact (48×40). Those independently generated views were accepted stylistically, but no shared 3D eye footprint or multi-view landmark consistency was enforced.

### Root cause statement

**Primary:** The head material selector overwrites most of the lateral eye region with a front-planar UV projection. That projection is only constrained by global head depth/height bounds. On the tapered curved head, front eye pixels spread axially and shear; 8.71% of the original side-eye dark pixels remain adjacent to them. The renderer faithfully displays this mixed, distorted texture support.

**Contributing process gap:** Acceptance checked overall three-view readability and explicitly tolerated elongated eyes, while mechanical validation checked topology, animation and native textures. There was no quantitative eye-identity/footprint gate, so a successful front face obscured a lateral-view defect.

### Alternatives assessed

- **Wrong Godot model or texture scaling:** formal/runtime GLB SHA matches; actual texture sizes are 1834×618 and 891×654, nearest. Same defect in Blender. Excluded as primary cause.
- **Extra procedural eye sphere:** `eyes:null`, no eye meshes in GLB. Excluded.
- **Bone deformation:** distortion and missing side-center UV exist in rest-space triangles. Front head's small swim rotation may move the appearance but cannot create the exported UV shear. Not primary.
- **Camera error:** recorded views include true side and true front; rest-space evidence is camera-independent. Not primary.
- **Pure global eye translation:** centers nearly coincide as above; support width/shear is much larger than center error. Not supported.
- **Depth shape as sole cause:** depth taper controls severity, but even a closed, smooth head cannot preserve a lateral eye under unconstrained frontal projection. Changing shape alone is not yet an evidenced minimal fix.

**Phase 1 verdict requested:** approve/reject this causal trace and measurement scope before any controlled modification.

## Phase 2 — comparison (revision after initial rejection)

### Working/reference patterns inspected

1. **Same backend, ordinary side UV path** (`build_fish.py:183–200`): coordinate `(source_u,source_v)` maps directly to axial/vertical mesh coordinates, apart from explicit pole/background/fin donor adjustments. Native side gills and flank are visibly retained in the final views. This is a within-model control: same renderer, texture, geometry, skeleton, lighting; projection ownership differs.
2. **Accepted side and front eye art:** both source eyes are legible in their own views. Matching the global front head rectangle does not establish that their eye footprints agree on a common 3D surface. Their aspect/position constraints must be compared explicitly.
3. **Existing silver arowana implementation** (`projects/fishing-2d/experiments/blender-fish/build_silver_arowana.py`, read in full): eye center `xyz(1617,233,±.035)` and explicit iris/pupil mesh dimensions tie eye position to a fixed source landmark. Body uses only side UV; there is no competing front-pigment projection. Existing runtime checks list Iris/Pupil/Glint meshes. This is a useful correspondence/control pattern, **not** a drop-in remedy: its procedural eye colors and earlier material setup differ from the required source-only native pixel contract.
4. **Reusable silver profile**: explicit `eyes` landmark and no `head_projection`; it cannot exhibit this particular two-source material ownership conflict. Its existence is not claimed as a fully validated anatomical gold standard for sharks.

### Differences that matter

| Dimension | Current shark | Reference/control |
|---|---|---|
| Eye semantic anchor | No shared multi-view eye constraint | Side coordinates or explicit eye center |
| Eye material ownership | Most replaced by front source, posterior/lower side fragment remains | Single eye source/explicit region |
| Projection orientation | Frontal depth/height onto near-lateral curved surfaces | Side axial/height or explicit local eye geometry |
| Apparent shape guarantee | None; depends on head taper and polygon normal | Direct side correspondence or bounded mesh dimensions |
| Review | Overall readable front + tolerated long oblique eye | Needs per-view eye support and continuity measurements |
| Runtime pipeline | Same native texture, nearest, rig | These working pieces need no changes for this investigation |

### Full implementation differences and comparison confounders

This comparison concerns the **old silver builder implementation**, not an assertion that its original materials equal the current runtime overrides.

| Variable | Old silver builder | Current shark Foundry builder | Confounder / dependency |
|---|---|---|---|
| Source dimensions | 1838×515 | Side1834×618 plus front891×654 | Different aspect, species and source eye shapes; no shared output pixel scale |
| Units and center | `xyz=((px-918)/1800,depth,(260-py)/1800)`; S1800, CX918, CY260; METRIC scene | `xyz=(u-.5,depth,(.5-v)*(618/1834))`; unit longitudinal source width | Positions/radii are not transferable numerically; must normalize from each native source |
| Body samples | 109 axial rings ×48 radial; manually fixed sections | 129×64; normalized profile sections | Surface slopes, triangulation and eye-adjacent samples differ |
| Pole inset/background | 2 source pixels; no opaque-pixel inward search | min(12 source pixels,20% section height), plus bounded `opaque_uv` repair | Could change pole colors independently of eye ownership |
| Native builder texture filter | Linear | Closest, GLB min/mag9728 | Current Godot nearest override does not retroactively make old Blender renders identical |
| Native body material | metallic .15, roughness .55, emission .10 | metallic0, roughness1, specular0, emission .35 | Contrast/highlights differ. Silver fin, iris and pupil materials additionally have their own metallic/roughness values |
| Eye representation | Uniform-color iris/pupil/glint spheres at explicit centers; no front source | No eye spheres; side/front source pigment on body | Only the principle of explicit shared landmark ownership is relevant. Copying old procedural eye colors violates current source-texture contract |
| Source/body UV | Single side projection with coordinates derived from native pixels | Side projection with fin-donor UV patch plus front material replacement | Only shark has competing projections over the same eye region |
| Animation interval | 24fps, frames1..49; phase `(frame-1)/48`; sample frame1 before save | 24fps, frames0..48; phase modulo48; frame0 review | Equal nominal period does not mean equal pose or same import duration; frame labels cannot be interchanged blindly |
| Rig/pose | Nine body bones plus segmented dorsal/anal/paired fin bones; body angle `(.003+i*.003)*sin(phase-i*.48)` | Eight body bones plus nine fin bones and staticroot (18 total); profile amplitudes .004..108, phase_step .6 | Body deformation and fin silhouette differ even at visually similar times; a species comparison cannot isolate UV cause |
| Review camera/environment | Old script primarily saves/exports; its original review camera/light setup is not defined by this builder | Current formal Blender fixed side/front/oblique, neutral world/area light, native pixel material | No evidence that historical silver Blender camera/light/pose matches shark. Do not claim matched visual control |
| Current Godot environment | Same hall pipeline can apply nearest/nonmetallic runtime override to silver | Same hall pipeline applies nearest/nonmetallic runtime override to shark | Shared runtime explains readability comparisons only; different source, meshes, material colors, camera framing and animation phases remain uncontrolled |

**Dependency boundary:** Native image hash/dimensions, projection coordinate convention, profile shape, material assignment, skin pose, camera and light together determine the rendered eye. Existing silver is a pattern reference for anchoring/ownership only. Its attractive appearance cannot demonstrate that a proposed shark change works. Source eye shapes and the shark's gills are stronger local controls, but still do not replace a same-shark experiment.

**What may be transferred:** Treat the eye as one identified anatomical region with a fixed relationship to accepted landmarks across views. **What is not justified:** copying silver coordinates, body widths, sphere dimensions, materials, sampling, animation or claiming a shark fix solely because silver looks good.

A causal test must freeze the **same shark**, same source bytes, exact vertex/triangle data, weights and bone pose, matched view camera/projection and lighting. Only the explicitly selected material/UV ownership changes. Render improvements from material/lighting/pose differences would not test this hypothesis.

### One-variable minimal test candidate — NOT EXECUTED

**Question:** Does front material ownership over lateral eye triangles cause the distorted side-eye support?

Use a temporary copy of the current accepted mesh and unchanged source images; preserve vertex positions, topology, bone pose, camera, resolution, lighting, source bytes, sampler and all other UV/material assignments. Change **only material/UV ownership for the two lateral side-eye footprint regions** (use the recorded side ROI plus one source pixel margin): those selected triangles use the existing side UV formula. This is one causal variable: whether lateral eye triangles are overwritten by frontal projection. Do not concurrently alter depth, source_rect, thresholds, source art, or eye geometry.

Before any trial, freeze triangle IDs selected from side coordinates and compare before/after `POSITION`, skin weights, animation accessors and source hashes. Baseline assertions should fail: side eye center not side-owned; only 8.71% dark support retained. Predicted positive result is restoration of that correspondence on lateral regions. Also measure front eye completeness, ghost eye fragments and seams in front, both sides, and ±45° fixed views: the test can confirm causality while failing as a final art solution. It is **not pre-approved as the production fix**.

A later remedy must retain both accepted native images and be parameterized in Foundry; it cannot rely on camera-specific hiding, changing original PNG pixels, or unreviewed replacement eye art.

## Review / state

- Phase 1: **APPROVED**, independent reviewer reproduced GLB measurements, 804 dark-pixel baseline and identical runtime hash.
- Phase 2: initial **REJECTED** for incomplete differences/dependency comparison; full confounder table added above; independent re-review **APPROVED**. Permission is to enter Phase 3 only.
- Phase 3: authorized one-variable experiment completed below; causal result supports hypothesis, candidate fails frontal visual acceptance; independent gate pending.
- Phase4: one root-cause repair implemented below; initial eye-patch candidate refined for face-level donor interpolation and bounded protrusion before acceptance. No production integration claimed by this agent.
- At the end of Phase1/2 all production files remained untouched. Subsequent authorized changes are limited to the backend, new041 profile and retained regression test; original040 profile/handoff/GLB and source PNGs remain unchanged.


## Phase 3 — single-variable experiment (submitted for review)

### Hypothesis and baseline failure

Hypothesis: the front-planar projection owning lateral eye triangles causes the backward spreading/shear seen in side and oblique views. Restoration of side ownership should restore side-source footprint without any geometry change. This predicts causality, **not** that the same operation is sufficient for final all-angle art quality.

Before mutation, the executable experiment verifies the baseline GLB hash, then checks expected failures: the original side-eye center has no side-material hit, and the front dark ROI's side-plane span exceeds 1.25×48=60 pixels (actual77.55). Evidence: `/tmp/shark-eye-investigation/baseline-failing-assertions.json`. These checks ran before opening/mutating the Blender model.

### Controlled change and retained scripts

- Reusable executable: `/tmp/shark-eye-investigation/ownership_experiment.py`.
- Measurement scripts: `/tmp/shark-eye-investigation/{analyze.py,analyze_variant.py}`.
- Before/after metrics: `/tmp/shark-eye-investigation/{metrics.json,ownership-only-metrics.json}`.
- Frozen-variable proof and exact changed polygon IDs: `/tmp/shark-eye-investigation/experiment.json`.
- Temporary output only: `/tmp/shark-eye-investigation/ownership-only.{blend,glb}`.
- Five matched views per case: `/tmp/shark-eye-investigation/{baseline,ownership-only}/{side-left,side-right,front,oblique-left,oblique-right}.png`.

Starting twice from the same formal `.blend`, freeze all vertex positions/topology/weights/pose and original PNG hashes. The only mutation switches 310 front-owned eye-region polygons to the existing side material and side UV formula. Region is side-coordinate rectangle x1590..1740,y285..365, with polygon overlap and minimum absolute lateral depth .03; it covers the **entire measured front eye support plus margin**, not merely the old side-eye bounding box. Polygon IDs are frozen in the report. Every other polygon's material and loop UVs are asserted identical.

All geometry/weight/pose/source hashes before and after match. Both cases render frame0,1000×650,Cycles12 samples, same world/light and matched per-view camera matrices/ortho scale. Views are two opposite sides, axial front, and directions `(2,-3,1.2)` / `(2,3,1.2)` for the two obliques. They are not claimed to be exact45° views. No production artifact was changed.

### Results

| Check | Baseline | Ownership-only temporary result |
|---|---|---|
| Source side-eye center mapping | Missing | Present on both sides at `(1688,326)` equivalent |
| Side dark eye support | 70/804 source pixels retained | 804/804 retained (1608 triangle samples across two sides) |
| Side dark support extent | Residual x1665..1681,y330..343 plus competing front eye | x1665.5..1712.5,y305.5..344.5, matching native pixel-center range |
| Front eye ROI dark support remaining in front material | 797/831 mapped samples | 0/0; no original front-ROI ghost is left in the selected region |
| Side and both obliques | Backward-swept eye | Compact native side eye, visibly improved |
| Front appearance | Coherent oval front eyes | **Regressed:** side eye pigment stretches along the curved surface from the front and produces eyebrow-like streaks/narrow texture transitions |
| Frozen data/other UV/cameras | Baseline | All assertions pass |

The predicted lateral restoration occurred while geometry, pose and source pixels stayed fixed. This supports the stated ownership/projection root cause. The front-view regression shows that merely protecting a broad eye rectangle is **not a finished repair**: one planar eye projection cannot be substituted for the other without checking the shared surface footprint and transition across views. ROI scores alone cannot approve the result; complete rendered eyes and neighboring pigment were inspected.

No second experiment or production fix has been attempted. **Phase 3 APPROVED by independent reviewer (causal experiment only).** The current temporary variant must not be imported as the final shark.


## Phase 4 — bounded surface-eye fix

Root approved one physical native-textured eye region per side, after independent Phase3 approval. Implementation keeps original body positions/weights and all bones/animation, introduces optional `eyes.mode=surface_patch`, and removes competing original eye pigment using existing side donors plus bounded front `uv_patches`. New production input is `041-eye.profile.json`; original040 profile/handoff/artifacts remain unchanged.

Surface patch takes native side `source_rect`, center/radius/depth plus thickness and surface_offset. It finds the actual nearest body surface normal, forms a local tangent frame, and creates a thin closed ellipsoid with bounded source UVs. UVs come from the same accepted native side image. Missing mode preserves legacy behavior. Front donor changes are whole-face UV islands: applying offsets to only some face corners was found to interpolate across removed eye pixels, so a face whose projected polygon overlaps a donor receives one consistent offset. The original PNG is never changed.

### Safeguards and test evidence

- CLI/backend fields synchronized with separate CLI implementer; explicit mode accepts surface_patch only. Patch count<=16, bounded polygons/offsets, final donor UV bounds guarded.
- Reviewer found an extreme source rectangle could yield infinite eye height. Input precheck and actual native-image height calculation now require finite positive half-height<=.05. CLI tests cover subnormal widths and valid boundary.
- Main body geometry/topology/skin-weight hash before and after is identical: `/tmp/foundry-shark-eye041-smoke/frozen-body.json`.
- Build validates12 closed meshes (two eyes added),18 unchanged bones, finite values, normalized weights, static root, loop seam and original nearest matte textures.
- Prior-to-fix baseline failing assertions remain `/tmp/shark-eye-investigation/baseline-failing-assertions.json`.
- Retained all-mesh regression script: `projects/fishing-2d/experiments/blender-fish/models/blacktip_reef_shark/041-eye-landmark-check.py`. It classifies primitives by embedded native image dimensions and maps all GLB meshes; no eye mesh name determines pass. Source image identity is independently protected by Foundry hash validation.
- Expanded baseline check exits1: each eye70/804 pixels, missing anchor,1680 frontal eye dark source pixels still mapped. `/tmp/shark-eye-investigation/all-mesh-baseline.json`.
- Fixed candidate exits0: each eye804/804 pixels; left footprint44.496×39.871 source-equivalent pixels, right44.499×39.857; anchor errors0.581/0.579 pixels; old front-eye pigment mappings0. `/tmp/foundry-shark-eye041-smoke/all-mesh-eye-check.json`.
- Candidate GLB SHA256 `02d8f6ae0bc01da30856fe469aaba4246e576ad049ac02b2471582a85e9ebeb2`.

Root reviewed `/tmp/foundry-shark-eye041-smoke/five-view/{side-left,side-right,front,oblique-left,oblique-right}.png`: eyes remain compact and anchored; frontal eyes are natural narrow ellipses instead of eyebrow streaks; no duplicate-eye fragments; tiny far-eye rim is acceptable physical geometry. Production041 profile marked approved only after that explicit visual approval and all-mesh checks passed. Formal CLI build/validate/render/accept and actual Godot review remain root's next steps. Full-suite and independent Phase4 review are required before final closure; not claimed complete here.


### Phase4 attempt tracker

| Attempt | Evidence | Outcome |
|---|---|---|
| 1, first surface-patch candidate | Side eye restored, but front donor boundary interpolated across source regions and far-side eye patch protruded visibly | Not accepted; one failed candidate. Returned to the concrete donor/geometry evidence, no new source generation |
| 2, same scoped repair after correction | Whole-face donor UV island, thinner bounded eye patch; all-mesh metrics and root's five-view inspection pass | Candidate accepted for formal pipeline; independent Phase4 gate/full-suite and actual integration still tracked by root |

The Phase3 ownership-only experiment was a causal test, not a production fix attempt.

### Rejection / return-to-investigation plan

This is fix attempt 2. If the same eye defect fails subsequent visual acceptance, stop parameter tweaking and return to Phase 1 with the current GLB/profile/source hashes, UV ownership/support measurements and fixed multi-view renders. Re-evaluate the projection/geometry evidence before another hypothesis; if the third repair fails, stop and request architecture review rather than attempting a fourth repair.

### Formal current production evidence (root)

Official `volume plan/build/validate/render` completed using `041-eye.handoff.json`; formal GLB SHA256 `5190f78e2cc6dfc37ca1d2b708102f46be6a38d5c65f37dd45582c0f63810929` matches the installed game GLB. Formal eye-landmark check passes all seven checks (804/804 each eye, anchor error <0.59px, side support approximately44.5×39.9px, old front pigment mapping0). `original-geometry-validation.json` confirms all ten original mesh triangle positions and skin weights are unchanged; only the two eye patches were added. These formal reports supersede temporary smoke identity for final verification.

Final CLI suite after the complete implementation:676 total,674 passed,2 existing skipped,0 failed; `/tmp/foundry-shark-eye-final-tests.log`. The first root rerun used the wrong working directory and imported the root launcher instead of the CLI module; rerun from `cli/` matches the existing test convention and succeeds, no unrelated source fix. Actual Godot Apple M4 GUI/material/bone/lifecycle checks:66/66, no import/runtime errors. Root inspected official four images and actual game front, both sides and both obliques. Output: game `output/041-shark-eye-qa/validation.json`, `blacktip_reef_shark-final.png`, fixed game angle captures in `/tmp/fishing-041-probes/`. Independent Phase4 verdict and final operator accept are pending.

## Terminal result

Independent Phase4 APPROVED. Official volume accept completed and subsequent readonly validate returns accepted/none. Installed game GLB identity matches current handoff; no new image/video generation, commit or push. Final validation: game plans/reviews/2026-10-13-shark-eye-placement-validation.json. New probes and surplus captures moved to /tmp; native production evidence retained.
