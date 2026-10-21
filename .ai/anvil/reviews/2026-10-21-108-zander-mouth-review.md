# Review Report: `2026-10-21-108-zander-mouth`

## Metadata

| Field | Value |
|-------|-------|
| Reviewer | Independent adversarial reviewer, `mahi_phase_review` |
| Review Date | 2026-10-21, Asia/Shanghai |
| Phase | 108 Phase3c CPU upper97 CDT, selection-v2 closure |
| Status | **APPROVED within the scope below** |
| Asset acceptance | **Not accepted**; no whole-mouth/fish/runtime approval |

Read the debug session, current package/result/completion documents, frozen CDT input and API output, superseded-selection archive, preparer and current validator. This review does not rerun CDT or change model/source/runtime files.

## 1. Automated Pre-checks

| Check | Result | Evidence |
|---|---|---|
| Current package file hashes | PASS | All7 listed files match SHA256. |
| Completion input hashes | PASS | All4 listed inputs match SHA256. |
| Frozen precursor hashes | PASS | All5 frozen input references and raw107 GLB match SHA256. |
| Superseded archive hashes | PASS | All4 archived snapshots match archive hashes. |
| Independent selection/boundary reconstruction | PASS |97 new faces,68 forced-selected origin points; boundary37, all68 points used. |
| CPU validator reproduction | PASS | Exit0;9353 pairs/1005 selected triangles,0 proper crossings,0 coplanar positive-area overlaps. |
| Lint/type checks | N/A | This gate reviews the CPU closure, not a general production-code release. |
| CDT rerun | NOT RUN | Frozen API output reused; no new triangulator invocation. |

The independent validation report was written only to a temporary directory. The report's original input/output artifacts were not overwritten.

## 2. Security Scan

No new network, credential, runtime installation or arbitrary execution capability was introduced by the reviewed selection fix. The validator reads declared local evidence and emits JSON; current audit only reproduced that CPU check. **Scoped security verdict: CLEAN.**

## 3. Adversarial Principles

| Principle | Assessment |
|---|---|
| Think before coding | The POSITION-only selection omission is explicitly identified; topology change is now conservatively included. |
| Simplicity | All68 upper origin points are selected; no special exemption for the two formerly omitted faces. |
| Surgical scope | Frozen field, epsilon, points and CDT result remain unchanged; only checker coverage/result were corrected. |
| Goal-driven validation | Original and Stage1-old-connectivity controls distinguish baseline0 from negative6 crossings; corrected CDT returns0. |

**Verdict: PASS for this Phase3c gate.**

## 4. Adversarial Dimension Review

| Dimension | Result | Specific assessment |
|---|---|---|
| Design | PASS | Topology changes participate in selection independently of position motion. |
| Functionality | PASS, bounded | Faces2/3 contain only originalX≤1988 points but are now included through the68-point selection. |
| Complexity | PASS | Canonical unordered pairs retain both static-low/active-high orderings and shared-vertex pairs. |
| Naming | PASS | Reports distinguish CPU base checks, geometry origins and unused returned-coordinate diagnostics. |
| Comments | PASS | Limitations explicitly exclude exact arithmetic, continuous animation and whole-fish acceptance. |
| Style/consistency | PASS | Current result and archive distinguish incomplete-v1 from corrected-v2 without rewriting history. |
| Context | PASS | No new parameter tuning, lower reconnection or Stage2 is hidden in this correction. |
| Tests | PASS, scoped | Validator reproduction and synthetic static-low-index regression pass; actual GLB/LOD/visual gates remain pending. |

## 5. Findings and Verified Evidence

### Selection correction

`validate_oral_cdt_108.py` now sets `changed[n+point_raw_ids]=True` for all68 upper origin points before testing the new connectivity. Independent reconstruction confirms all97 new faces are selected. The two previously omitted topology-only faces are exactly local faces2 and3. Their original X coordinates all lie at or before1988, so POSITION-only selection was insufficient.

The corrected positive check reproduces:

- 9353 canonical pairs and1005 selected triangles;
- 0 proper crossings;
- 170 coplanar candidates,0 positive-area overlap pairs above the documented threshold;
- 335 pairs that the earlier `js>i` ordering would miss;
- shared-vertex pairs retained rather than unconditionally skipped.

The synthetic static-low/active-high counterexample produces one crossing and one old-ordering omission. Original geometry produces0 crossings/0 coplanar overlap; Stage1 with old connectivity produces6 proper crossings. These are discrete finite-tolerance checks, not continuous collision proofs.

### Topology/origin/boundary closure

- 68 input and output points,97 faces, all68 points used; no inserted or merged geometric point.
- Euler count `2*68-37-2=97` agrees.
- All37 directed patch-boundary edges match the prior order exactly; complete397 skin/oral interface edges remain exact and nonmanifold count is0.
- All upper projected signed areas have the expected direction; minimum absolute doubled XZ area is`3.0969293952700508e-9`.
- Projected patch/polygon area difference is`-3.7947076036992655e-19`; no positive-area internal overlap.
- Kept oral indices are exact; lower connections are not replaced. Skin is not retriangulated.
- Final CPU positions come from the frozen Stage1 origins. Returned API coordinates are explicitly diagnostic only and are not substituted into geometry.
- Raw same-position groups have matching J/W/UV; differing original NORMAL groups are not falsely described as identical. New active-face normals may use separate attribute vertices, while kept attributes remain subject to exact preservation.

### Unchanged CDT and honest history

Frozen input SHA256 remains`6392eeef850c4d61f16e21d7e397c91b6b4b8d64f3d798eca9cc13dfd4de7de2`; API output remains`49cf20aa7b20f26a3b74de14c8513ef5d16cc1aac8ded8004949b2da6858e85f`.

Both match the older package hashes as well as the current files. The API output records one invocation, fixed epsilon`1e-9`, and returned coordinates unused. This audit verifies those immutable records; it does not independently observe the past Blender process.

The old9295-pair/1000-triangle result and prior checker are archived as `selection-v1-incomplete-freeze`. They are superseded as incomplete coverage, not retrospectively promoted to a complete pass. The older Phase3b two-crossing report likewise remains historical; the six-crossing control uses the newer broader checker.

**No blocking finding remains for the current Phase3c CPU closure.** A future selection change must re-establish all97-face coverage; this approval is bound to the verified current validator/package hashes.

## 6. Gate Decision and Authorized Scope

**APPROVED: proceed only with an isolated Stage1 + existing upper97 CDT grey-model GLB candidate using the same68 geometric origins and37 frozen directed boundary edges.**

Permitted scope:

- Apply the already reviewed Stage1 deformation; protected eye region, posterior region and Z invariants still apply. Skin connectivity is retained; this is not a claim that every front skin POSITION remains unchanged.
- Reconnect only these97 upper oral faces through frozen origins.
- Keep lower connectivity, source images, materials, J/W/UV, rig, fins, animation and kept-face attributes unchanged. Active oral face-normal attributes may be split/rebuilt as already disclosed.
- Compare actual emitted float32 geometry and raw attributes, then inspect grey-model views. Newly imported actual LOD tables must be separately frozen and checked; historical failures are not erased.

Not approved here:

- Stage2/chin/lip-Y fitting, source thickness proposals or a new mouth shape target;
- UV/material correction, new source acceptance or eye binding changes;
- new LOD acceptance, body/fin/animation acceptance, runtime installation or whole-fish acceptance.

The current package remains `accepted=false` and CPU-only. A saved GLB candidate is a subsequent asset gate; neither its existence nor this CPU approval implies it passes visual or runtime review. The independent builder/raw-BIN review requested afterward is recorded separately when complete.


## 7. Actual Stage1 GLB preservation and grey-model audit

**APPROVED only for the isolated Stage1 + upper97 emitted candidate's preservation/base geometry scope. Whole-mouth visual acceptance remains withheld.**

Read the builder, emitted checker and actual reports. Independently reread the source/candidate GLBs and verified source/model SHA256, all six build-input hashes, the byte-exact original BIN prefix, unchanged nodes/skins/animations/images/materials/textures/samplers and all other meshes. Skin indices are exact; the 1092 kept oral faces remain in their prior order. Original J/W/UV and original oral NORMAL values are exact; new upper faces receive copied origin attributes and their own actual-float32 flat normals. Source candidate SHA256 is `002c34131da631de768cf938413c4d7047c894ad57c58f66ae763607c0edc2b8`.

The actual/raw face mapping does not assume matching order. It finds 1189 unique geometric triangle matches, detects uniform reversed winding and reverses the new upper faces for raw glTF. It uses the frozen 68 origin positions, not triangulator-returned coordinates, with 291 additional attribute vertices and no additional geometric points.

The emitted float32 report checks 9325 pairs / 1002 changed triangles, all 97 new faces selected, zero proper crossings and zero positive-area coplanar overlaps. These differ legitimately from the CPU double report's 9353 / 1005: the emitted checker selects actual moved float32 vertices plus every appended upper attribute vertex. Both reports retain their own selection/counts. The emitted interface has 397 exact opposed skin/oral edges, zero nonmanifold edges and combined multiplicity two. This review read that emitted result; it did not rerun its crossing computation.

Actually viewed `grey-comparison.jpg`: reach improves, but the upper anterior tip still has a conspicuous local angular transition in side/oblique views. Chin/front-lip Y and UV remain unfinished. This is a partial geometry candidate, not a completed mouth. No fresh imported LOD or runtime dynamic result is inferred from this audit.

## 8. Phase2d revised outer-join method gate

**APPROVED for one CPU-only construction/check with the conditions below; no GLB, UV or Stage2 normal write authorized by this gate.**

The read-only outer table supports replacing the narrow windows with longer monotone C1 joins. Forehead: old protected-exterior anchor X≈1922.1949, Y≈357.1379 and left derivative +0.4277006 to source X1960.5/Y365; secant +0.2052503. Chin: old X1780/Y≈509.7775 and left derivative −0.2859498 to source X1870.5/Y494; secant −0.1743366. These are compatible with a monotone cubic Hermite construction. Freeze every endpoint derivative/coefficient and check the derivative quadratic's extrema for sign, not merely a dense plot. Default PCHIP alone is not proof of preserving the old endpoint tangent. Retain source residual inside joins rather than creating a new extremum to hit early conflicting source points.

Required CPU gates:

- Strict branch ownership: the first script's lower test `max(V)>0` includes straddling triangles. Report straddlers and either exclude them using `min(V)>0` or precisely clip to the branch plane before deriving an envelope; do not silently claim the two branches are strictly separated.
- Ordered targets and finite strictly positive old/target spans, except the explicitly documented collapsed upper cap role. No epsilon replacement for invalid spans.
- Exact baseline POS/NORMAL/UV for the frozen 659/231 eye groups and all 640 posterior-mouth vertices. NORMAL is not modified during this CPU proposal. The 397 interface edges/points must map identically between the two surfaces, retain opposed directed edges and remain closed; their anterior positions are allowed to change and are not required to equal baseline. Unknown posterior lip X≤2000.5 is invariant relative to the Stage1 input; existing Stage1 movement at X1988..2000.5 is retained, not reverted to baseline.
- C1 join values/slopes, no new contour extrema, actual old/source residual tables and identical X/Z. All proposed skin/oral shared points must agree, including new upper CDT origin use.
- Half-pixel inward source correspondence is reasonable as an in-memory UV proposal. It does not prove entire UV triangles remain opaque or that material alignment passes; those and emitted float32 topology/normals/dynamics remain separate gates.

The old narrow-window proposal remains frozen as unsuccessful. Neither this method approval nor one successful CPU check constitutes asset acceptance.


## 9. Phase3d single CPU result and subsequent structure-method review

**Phase3d REJECTED.** Independently checked all six package hashes and read the frozen result/proof/completion. Hermite curve/C1, positive spans, eye and posterior protections and interface closure pass within their stated scope, but the actual finite base has 28 proper crossing pairs and nine reversed triangles (skin six/oral three), minimum transported-normal cosine approximately −0.9723. These are blocking geometry failures. No model/UV/NORMAL/runtime asset was emitted or accepted. The reported minimum dY′/dY≈0.7857 is evaluated at vertices/centres; it is not an analytic global-domain injectivity proof.

The 275 transparent original-source samples versus 416 under old UV are not an opacity acceptance result. The frozen fallback samples are opaque but include dark edge donors; neither a body hole nor a visually correct material is inferred from these finite samples.

Conforming local subdivision before evaluation is a reasonable proposed method, not a proven cure and not yet authorized for another trial. It must freeze its region, deterministic source-pixel scale and finite vertex/face budget. Map newly interpolated Stage1-domain points through the unchanged field; do not midpoint already-deformed endpoints and call that field evaluation. Comparing true mapped midpoints against straight mapped-edge midpoints supplies direct evidence of approximation error. Explicitly account for branch/chart breakpoints and verify continuity and positive derivative over each affected piece, rather than relying only on previous point samples.

Minimum next CPU gates:

- Preserve old source/field/targets; exact protected original attributes and posterior-support identity under their established baselines. Fail if conforming closure reaches a protected incident face that cannot be split while satisfying the protection contract.
- No hanging nodes. Shared skin/oral geometric edge identity and exact split parameter must use one cache, with separate attribute lineage as appropriate. If a former 397 interface edge is subdivided, preserve its parent-edge lineage and exact opposed subedge chain; do not falsely require the new boundary count to remain 397.
- Record each new point's original parent face/edge and barycentrics. Interpolate joint weights by the union of joint IDs, merge equal IDs and normalize; joint indices themselves are not numerical quantities to average. Reject unsupported influence truncation unless its deterministic rule/error is explicitly approved. UV seams retain separate corner/side attributes rather than welding UV blindly. Evaluate the new source chart after original-attribute interpolation. New normals are subsequently derived/transported explicitly, not misrepresented as unchanged originals.
- Include every topology-changed and newly created face in canonical pair selection. Require zero proper crossings, zero positive-area coplanar overlap, zero reversed/degenerate faces, closed opposed interface and no nonmanifold/T-junctions. Test local patch against all unchanged nearby geometry, not only patch-internal pairs.
- Retain original-source/fallback UV diagnostics and the exact pre-change negative control. Geometry success alone does not approve colour, UV, emitted float32, fresh LOD, animation or fins.

A constrained edge flip or current-point retriangulation could introduce fewer points, but requires a valid single-valued local parameter domain and unchanged boundary/attribute constraints. A blind 2D CDT of the already intersecting patch is not a justified smaller fix. Do not iterate flips/windows/resolution until a pass without a separately frozen causal test.


## 10. Phase2e frozen conforming-refinement proposal gate

**APPROVED for one bounded CPU experiment only.** Read the complete proposal and verified all three SHA-bound files. No GLB/UV-asset/runtime write or subsequent acceptance follows from this gate. Phase3d remains rejected.

The proposal fixes Stage1-domain XY longest-edge scale at one native pixel, uses original-domain dyadic barycentric lineage and evaluates the unchanged F at new points. It explicitly distinguishes this scale from geometric error tolerance, permits continued deterministic refinement of failing faces within the same run, and stops at depth eight or 50000 cumulative child triangles. Every closure child counts toward that budget; depth is the maximum binary refinement depth in each original-face lineage.

The geometric edge/t cache, all397 parent-interface chains, separate corner domains, bone-ID weight aggregation with rejection above four influences, hard-normal-group handling and exact unknown-rear F2/UV identity provide an adequate construction contract for this diagnostic. Existing UV alpha and dark fallback defects are explicitly outside what subdivision can cure.

Execution interpretation remains binding: retain exact baseline640 checks as well as Stage1-relative rear checks. Do not turn reporting a newly expanded region into authorization for arbitrary patch growth: if crossing-driven refinement requires expansion beyond the frozen761-face patch plus necessary conforming-neighbour closure, stop and archive failure under the proposal's no-auto-expansion rule. All added/changed topology participates in global-neighbour canonical intersection checks; one-pixel scale does not exempt any crossing, reversal, degeneracy or protection failure.

No further parameter/window/source/epsilon adjustment is approved within this trial. A successful result would establish only finite CPU geometry evidence, requiring independent review before asset emission.


## 11. Phase3e bounded CPU failure closure

**REJECTED; stopped without another run or asset write.** Verified package SHA256 `bd15011fe1de8d63574df92bcfd26ddfb4eac0fe04fc43d8ceae64f996aa3d6f` and all six listed file hashes. The independent depth-eight limit was reached before completion of the initial one-pixel scale phase: 5640 new geometric points, 22560 cumulative child triangles and 35410 final stopped faces. The subsequent cross/flip-driven refinement phase was not entered.

The stopped mesh reports 237 proper crossing pairs and 85 opposite/degenerate faces, so it fails. These counts cannot be compared directly with the former 28-pair result as evidence that the field is worse, and the stopped mesh must not be described as a completed one-pixel approximation. Closure/protection/JW successes do not override geometry failure. The result honestly states that no final UV/NORMAL arrays were assembled; original-untouched flags are not proof of completed corner-attribute or GPU gates. No depth increase, target/window adjustment or rerun is approved.

A next diagnostic may only examine whether each separately frozen left/right and upper/lower skin patch is a valid single-valued destination-XY chart, while preserving the X-constant front cap separately. No CDT, coordinate edit or asset emission is approved. Absence of duplicate XY vertices is insufficient: report simple directed boundary, projected zero-area faces, non-neighbour projected positive-area overlaps and incompatible Z values at common XY. Do not automatically repair a multivalued chart or mix cap/skin/oral ownership to force a usable projection. A new construction method requires another gate after these read-only results.


## 12. Destination-XY chart diagnostic and orientation-gate clarification

Verified chart package SHA256 `ed3d7f6a60c51afbbc09c1155519da010e4de87bf03cab8eda1bc13fa3c18271` and all three linked hashes. The four destination-point charts have simple boundaries, Euler one, points inside and no reported coincident-XY/different-Z conflicts. Existing upper connections contain four/five opposite-signed XY faces; these are the existing discrete negative control, not a reason to prohibit defining a different triangulated graph from the boundary and point cloud. The earlier section's projected-overlap diagnostic is not a requirement that the old defective connection must first become valid before proposing reconnection.

**Method direction supported, no CDT execution authorized yet.** Upper-only reconnection is smaller and avoids the two lower internal UV-group conflicts. It must transparently describe a new piecewise-linear interpolation surface Z=f(X,Y), not preservation of the complete former continuous surface. Keep all current point XYZ, attributes, directed boundary and interface constraints exact; retain all 15 cross-Z non-cap faces, all 46 X-constant caps and every lower connection. Freeze concrete upper inputs/origin/normal handling before the next CPU gate. Output must retain all points and constraints, introduce no new geometric point, cover the simple polygon without overlap and reconnect attributes by verified origins.

**Orientation clarification:** negative cosine between a finite triangle normal and the cofactor-Jacobian-transported original normal at its centroid demonstrates differential/finite approximation mismatch; it alone is not a proof of topological inversion. For the new graph method, require fixed consistent nonzero oriented chart area, nonzero 3D area, opposed shared edges, closed/manifold interfaces and zero actual 3D proper crossings/positive-area coplanar overlap, including all retained neighbouring/cap/oral faces. Preserve transported-normal cosine diagnostics and subsequently inspect actual grey-model normal/crease appearance. Do not merely recompute or reverse normals to conceal geometry defects. Historical Phase3d/e rejection remains unchanged because their actual intersection failures remain, irrespective of terminology for negative cosine.


## 13. Phase2f frozen upper-only CDT CPU gate

**APPROVED for one CPU experiment, comprising one fixed CDT invocation for each upper sheet. No asset emission, epsilon tuning or retry authorized.** Verified package SHA256 `ab6f7f51e7c7755aa62f89612de069e181ce86c7ca936e7849fa71a00bf97ed5` and all four bound file hashes; frozen input SHA256 `96f823e163a19f1cd976e4920d02a38d188dcf9a57a7246a7000520301512ed0`.

Input is mapped float32 REST XY, epsilon 1e-9 rest, output_type=1 and need_ids=True. Preserve left68/right70 original points, expected103/106 faces and31/32 directed boundaries. Returned coordinates are diagnostic and discarded; singleton one-to-one orig_verts must cover all inputs with no merged/new/unused point or split boundary. Recover frozen XYZ/JWUV and normal provenance by exact input origins. One uniform winding follows frozen boundary, left negative/right positive; do not fix individual faces by normal-cosine comparison.

All209 new topology faces must enter canonical global intersection selection, including unmoved-point faces. Require complete polygon coverage without internal overlap, nonzero consistent chart area, nonzero actual3D area, preserved directed boundary/skin-oral closure and zero global proper crossings/positive-area coplanar overlap. Lower connections/UV groups,15 cross-Z faces,46 lower caps,97 oral CDT and all other geometry/attributes remain in scope as unchanged comparison inputs. Transported-normal cosine remains disclosed diagnostic; future actual face/corner normals require a separate emission contract. Phase3d/e failures and unfinished UV/dark-donor, grey/LOD/body/fin/runtime gates remain unchanged.


## 14. Phase3f finite CPU closure and Phase4 normal contract

**APPROVED for the finite CPU topology gate and an isolated complete-Y + upper-CDT geometry candidate. No whole-mouth/fish/material/runtime acceptance.** Package SHA256 `d21ca34c8605646926bf965c66869a7982f1df647e1936dfe76c936080faf043` and all six files independently match. Reproduced the validator into `/tmp/108-phase3f-independent.validation.json` without rerunning CDT or writing an asset; exit zero and the entire reproduced report equals the frozen completion report.

Reproduced left68/right70 origins and103/106 faces, all209 new faces selected,63 exact directed patch edges and397 closed opposed skin/oral edges. All24130 final base faces are conservatively selected after float32 comparison, testing166174 canonical pairs with zero proper crossings or positive-area coplanar overlap; zero zero-area3D faces. Lower495,15 cross-Z and46 cap connections remain exact. This is a finite-tolerance discrete check, not exact arithmetic or continuous animation proof. Eleven negative transported-normal cosines (skin eight/oral three, min≈−0.99471665) remain fully recorded under the previously clarified diagnostic rule.

### Explicit prospective normal-policy amendment

For this isolated candidate, recomputing actual-surface normals is reasonable because the new graph changes face interpolation. Freeze the exact eligible corner/vertex IDs and weighting method before emission. Only original mouth normal groups incident to actual changed geometry or connectivity may change. Compute from actual emitted float32 faces, with all incident-face contributions within the original smooth group; do not average across existing hard groups, skin/oral ownership or separate normal/corner seams. Oral new-face/hard-group normals follow actual new geometry, with provenance retained.

Eye659/231 and all outside-mouth/posterior-body normals remain byte-exact. Within rear640/unknown704, only eligible mouth corners incident to altered geometry/topology may receive new normals; enumerate each exception, magnitude/angular difference and reason. Their protected POS/UV/JW contracts do not change, and nonincident posterior normals remain exact. This is an explicit prospective relaxation of rear NORMAL identity, not a claim the former exact-normal gate was already satisfied.

Require finite normalized output normals, raw/actual winding agreement and actual-face/corner angular diagnostics plus fresh grey views, including posterior join and the previous upper-tip kink. Normal recomputation must not conceal crossing, winding or geometric defects. Any conflict with eye/exterior exact protection must fail or return for review, not silently expand the normal domain.

The isolated candidate must independently verify emitted float32 geometry, origin/JWUV/kept-face preservation, protected attributes, full interface and original metadata/BIN contract. Fresh grey/material, UV/dark fallback, imported LOD, body/fin/motion/runtime checks remain unapproved. No install or production replacement is authorized.


## 15. Complete-Y emitted candidate: visual rejection and Phase1 return

**Phase4 complete-fix Strike1: REJECTED.** Actually viewed fullY side/front/oblique grey renders from `geometry-candidate-y`. The chin has a conspicuous near-vertical recessed crease; upper lip remains shield-like with local downward hook. Front view also exposes a sharp transition above the oral aperture. These defects exist in untextured geometry/shading and cannot be accepted or hidden through a UV stage. Earlier reach-only Stage1 was explicitly a partial step and is not retrospectively counted as a complete-mouth fix.

The emitted report identifies GLB SHA256 `227b7a1671bae5f8010924046014a0ad1d712bd7ab806168c97bd4ecc1b0b071`, zero crossing/positive-area overlap/degeneracy and397 opposed closed interface edges. Those mechanical checks do not establish visual success. This section reads the emitted report and views images; it does not claim a new independent full emitted-validator reproduction.

Read the fixed F2 formula: lower anchor comes from floor+2 and the conservative eye maximum, with a two-pixel eyeX fade. The source currently contains eyeY=453.9518894851208, so eyeY+2≈455.9519 and full-fade logaddexp anchor near X1920 is≈455.9536, not456.95. Preserve these actual values when quantifying the proposed narrow-span expansion mechanism. The mechanism is plausible and consistent with the crease location, but needs actual affected-vertex/cross-section evidence before a remedy.

Only read-only follow-up supported:

- Derive full actual107 eye-layer support from the real shader mask, displacement and triangle projection/raw origins, including sampling boundaries and incident-normal dependencies. Compare this to the enlarged conservative prism; a source-image eye bounding box alone does not justify shrinking protection.
- At actual chin-crease vertices and transverse sections around eyeX..eyeX+2, report old bottom, anchor, source target, available span, displacement and dY′/dX/dY′/dY alongside Z thickness and face normals. Distinguish real geometric crease from normal-only shading.
- For upper hook, overlay original source mouth ink/alpha with explicit upper/roof/lower boundary roles and actual projected interface. The fixed2000.5..2002.5 front blend is a relevant hypothesis location, not yet sufficient proof that changing a window is the correct repair.

No new field/window/protection change, model or UV experiment is authorized by this rejection. Source/UV/LOD/body/fin/animation/runtime remain unaccepted.


## 16. Post-rejection Phase1 evidence: anchor strain and actual base eye support

**APPROVED for the narrowed Phase1 diagnosis/method only; no protection replacement or repair authorized.** Verified package SHA256 `8ccecf157c510c9af5f3839aef1a1a169765cab7b3cd1b840b651b3e5e7288af` and all five linked hashes. Read the source/shader/support algorithm and actually viewed the native mouth/rim overlay.

At X1920.5, old bottom458.218718 minus actual anchor455.772080 leaves2.446638px for target expansion+21.781282px; middle dY′/dY≈17.6923. Middle dY′/dX near X1921≈30.4928 falls to≈2.0269 after the eye-anchor fade. Together with actual transverse vertex differences, this supports the artificial conservative-eye anchor and narrow retreat producing a high-strain interior crease. Smooth external Hermite curves alone did not constrain transverse strain.

The eye method uses the complete6039-pixel layer mask multiplied by source alpha, actual11-pixel shift and nonzero absZ owner gate, clips actual triangles before nearest/floor source-pixel-cell intersection and preserves all contributing triangle corners/co-position normal attributes. This matches the relevant shader sampling semantics and is stronger than a pupil/image-bbox proxy. It finds246 direct base vertices (123 each side), support maxY436.5612, versus338 normal-incident-ring vertices with maxY446.1601 and former659 support maxY453.9519.

**Scope correction:246 is current actual base support only, not all-LOD completeness.** Before replacing the old659 contract, collect actual old base and passedLOD0–4 eye-footprint support unions, corresponding attributes and shared oral coupling. Preserve oldLOD5 failure separately. A subsequently imported candidate must freeze/check every fresh actual LOD again; the old union cannot guarantee newly simplified topology. Do not use this evidence to promise unchanged complete eyes before those checks.

A new protection proposal may distinguish direct feature interpolation from normal-recompute dependencies: preserve contributing corners' POS/UV/JW/lookup and original fragment-normal interpolation; the338 incident ring need not automatically freeze all POSITION if protected corner normals remain explicit unchanged values. This is a prospective contract design, not an executed reduction. Peripheral geometry can still change eye occlusion/ownership, so fresh dynamic/LOD and actual-eye visibility remain mandatory.

Upper hook diagnosis is also narrowed: fixed posterior R, the rapid transition to alpha-derived416 and return to401.5 directly produce a down-hook target. Alpha extent alone does not identify the solid gold lip. The proposed gold-to-dark boundary near407 warrants continuous, role-labelled read-only source annotation; the two dark bands and isolated white pixels prevent a threshold-only anatomical conclusion. No new mouth boundary, blend window, UV or model fix is authorized here.


## 17. Upper-lip source-material semantics gate

**APPROVED as narrowed Phase1 source evidence and prospective local material constraints, not a new shape execution.** Verified package SHA256 `c8749e391bc8a050368f5c8a8beef110a2f64315245d52b97ef84986ddc4fe24` and all four hashes; actually viewed the labelled native-grid comparison.

At1990/1995, the bright cream band ends at cell boundary413. At2000/2005/2010, the gold-to-dark candidate is407; alpha either remains connected or reaches413/412. The explicit RGB transitions support rejecting the assumption that retained source alpha is itself the solid bright upper-lip boundary. Including the additional opaque dark band as newly extended exterior skin is an evidenced modelling-assumption error contributing to the shield/down-hook target. This does not prove that every dark pixel is mouth interior or establish a biological lip boundary.

The labelled bright-to-dark edges at these measured columns may be used as local source-material constraints in the next proposal, retaining their pixel values and roles. Unknown1998–1999 connections may only be an explicitly labelled engineering interpolation, checked for continuity and absence of new hook. Dark2015/2019 endpoint semantics remain unknown; do not silently infer or alter the tip. No colour threshold excavation, blanket dark-pixel cut or UV concealment is approved.

This gate authorizes no Y-field/model/UV execution. The next bounded C1 proposal remains dependent on actual passed-LOD eye-support union, shared oral coupling and available per-X protected-support-to-floor/bottom spans, with all historical failures retained.


## 18. Base feature versus retired coarse-LOD dependencies

**APPROVED to formulate a revised protection contract, not to execute a field or shrink protection yet.** Read the clearance-minima and actual base+LOD0–4 union data; all four listed dependency hashes match. The304 union includes remote coarse-triangle endpoints (18 outside the previous659), including points near the mouth rim and a former coarse endpoint whose mapped Y changes substantially. Those are dependencies of the old coarse interpolating triangles, not necessarily physical eye-surface points that must permanently pin a newly imported model.

It is reasonable to freeze the actual base246 feature precisely while treating304 as disclosed old-LOD dependencies rather than permanent base-shape anchors, provided every old LOD table is explicitly retired and every regenerated actual LOD is freshly frozen and checked. If any old LOD is reused, its supporting endpoint/attribute constraints remain necessary unless that LOD is separately revalidated. No previous LOD0–4 pass transfers to changed geometry. OriginalLOD5 failure remains recorded.

Base preservation must include the complete original eye-bearing triangle topology (204tri per side), corners/normal groups, POS/NORMAL/UV/JW and shader lookup correspondence, not just a point pin set: retriangulating fixed vertices can change fragment interpolation. Shared oral coupling remains checked. Fresh actual LOD gates must cover complete6039-layer support, unique ownership and left/right source feature preservation, normals, dynamic visibility and actual renders; any failure blocks formal acceptance. These future gates may not be skipped because the base feature is exact.

The zero L−Y gap belongs to a posterior closed-body branch point, not evidence that the physical lip must remain fixed there. Nor may the minimum positive gap silently replace a zero-gap contract. A new per-X field proposal must explicitly distinguish branch-envelope semantics, true source roles and protected-support margins. No field, asset or new acceptance follows from this contract decision.


## 19. Second complete-fix attempt: Phase2 single CPU gate

**APPROVED for one fixed CPU evaluation only; no GLB/UV/runtime asset construction.** Read `phase2-attempt2-proposal.md`, the parameter file and compact read-only facts. All six frozen dependency hashes match. No new field has been executed at this gate; the first fullY Phase4 Strike1 remains recorded.

The unified U/R/L/B chart removes the V-branch discontinuity and conservative global-eye anchor. Unit-endpoint-slope Hermite derivatives agree across upper/gap/lower boundaries, with positive derivative exactly when rho>1/3 for compression. The rear lower quintic has nonnegative expansion derivative for nonnegative DeltaB; the front mixture preserves positive Y derivative because beta depends only on X. These are appropriate method conditions, not proof that reused finite connectivity or transverse shape passes.

Gold-material upper-lip targets replace the alpha-derived dark-band endpoint. The1985.5 local join and unknown1998–1999/dark-tip engineering curves are explicit. The former640/704 posterior-rim POSITION-exact contract is prospectively released to complete per-ID displacement disclosure, with unknown X≤1985.5 strictly below0.25 native pixel. SourceUV/JW and the original408 eye-bearing triangles/246 vertices/corner normal/lookup remain exact. Previously passed old LOD tables are retired; actual new LOD acceptance is still future work.

Binding CPU conditions:

- Check positive spans, ordered targets and rho/derivative conditions over the actual used X intervals, not merely target knots. No epsilon repair of invalid intervals.
- Prove the full eye triangle/corner interpolation contract from original IDs/attributes; no changed-field mask copying to hide unintended movement.
- Fresh canonical global finite geometry checks include all97 oral and209 skin topology changes, all moved faces and their neighbours. Require zero proper crossings/positive-area coplanar overlap, zero3D degeneracy and exact closed opposed interface.
- Enforce the frozen strict0.25 posterior bound and≤1px source-node actual side-projection error before any acceptance. Report every original endpoint, including formerly exact640/704 IDs and source/unknown roles.
- Collapsed upper endpoint is mapped once; do not divide by a zero span or claim full-direction Jacobian regularity there. Fresh finite geometry and later actual normal/grey checks remain required.
- Report actual internal strain/sections and contour, not only the smooth outer curve. Any failure stops this trial; no knot, field, epsilon, window, connectivity adjustment or CDT rerun is authorized.

A passing CPU result would still require independent result review before the second actual asset candidate. It does not solve pending UV/dark-fallback/source colour, LOD, body/fin/animation or whole-mouth visual acceptance.


## 20. Attempt2 CPU stop and permissible diagnostic boundary

**Attempt2 CPU REJECTED under its frozen gate.** Verified the parameter and actual probe-script hashes recorded by the completion report. At upper-gold node X2000.5, target407 versus actual piecewise-linear lip408.305308987 gives1.305308987 native pixels, exceeding the predeclared1px bound. Unknown posterior displacement max0.228546px remains below0.25. Other reported chart/eye/closure/degeneracy checks do not override this failure. Global crossing checks were not reached and are not claimed passed. No asset was emitted.

**APPROVED only for read-only attribution and non-delivery, in-memory grey diagnostic images of this same frozen field.** Do not change knots, field, connectivity, epsilon or normal derivation, rerun CDT/refinement, save a new GLB candidate or revise the old failed report. Re-evaluating the frozen field for attribution must be labelled diagnostic rather than a successful repeat of the gated trial.

The1-source-pixel threshold is an engineering creation criterion proposed for this attempt, not a user-specified physical precision requirement. Actual game-camera evidence may justify a separately proposed future visual criterion, but not retrospective approval. Minimum diagnostic evidence is the defining PL lip edge/endpoints/origins at the failing plane, true field versus finite-edge deviation, local and maximum dY′/dY and dY′/dX/transverse sections, and side/front/oblique grey views at fixed real normal/near/closest reachable viewing conditions. Measure actual screen projection of the intended and actual positions, including corresponding Z; do not infer invisibility solely from source-pixel/image-width ratios. The same already-reviewed actual-geometry normal policy may be used consistently, without cosmetic normal tuning.

Label diagnostic images as CPU-stopped/source1px-failed/global-crossing-unverified. Such images are not delivery or whole-mouth acceptance. Intersection/degeneracy/interface hard gates remain unchanged by any future game-pixel visual tolerance discussion. Any next candidate or revised prospective gate requires a separate review after the evidence, with the failed run preserved.


## 21. Attempt2 RAM grey/camera interpretation and finite-connection attribution

Actually viewed the stopped RAM grey comparison. Side/oblique upper-lip sharp transitions and front midline depression remain visible; **visual rejection remains**. Verified all five actual-camera package file hashes. Normal-view0.12–0.15px projection is not proof of invisibility across permitted cameras: closest-front is≈2.028px at default height and≈3.863px at the720-high diagnostic viewport. The latter is explicitly a responsive-size diagnostic, not the current physical window. Projection is not rendered-pixel/occlusion evidence, and the camera report honestly distinguishes its headless cache equivalence and environment certificate log error.

Fifty-seven nonpositive skin face/corner-normal dot products remain diagnostic shading evidence, not a standalone topological inversion proof. The long defining PL edge at the source-node failure crosses the changed target's curvature, so reused CDT legality is a narrower justified hypothesis to examine before changing the head architecture.

**APPROVED for read-only finite-connection attribution only:** evaluate the same frozen attempt2 float32 positions with the existing209 skin/97 oral connections. Report per-chart consistent signed projected area, simple boundary, constraint-through-point and internal-edge/boundary crossing, same-projected-point/incompatible-depth conflicts and global canonical actual3D proper/coplanar intersection and degeneracy locations. Use the valid projection appropriate to each oral graph, preserve caps/cross-Z/kept lower faces and include them in global checks. Link failed geometry to the observed image defect and actual defining edge origins; do not infer cause solely from a scalar cosine.

No new field, smoothing, connectivity, subdivision, CDT invocation or asset output is approved. Preserve the original CPU-failed report and append diagnostic results, even if some formerly unrun hard checks pass. An illegal reused triangulation plus a feasible new point/boundary graph could justify another concrete frozen-CDT proposal; it does not authorize that trial or establish Phase3/whole-mouth acceptance now.


## 22. Reused-F2 connectivity evidence and original-skin control proposal

Read both attempt2-connectivity read-only reports. Each reused upper destination-XY patch has seven opposite-signed projected faces; the actual full float32 mesh has26 proper crossings, not merely negative shading dots. The failing source edge5919→369 is a former-F2 CDT diagonal whose adjacent faces participate in11 actual intersection pairs. Four former interior points also fall outside the changed projected boundaries, so blind same-point destination CDT is not currently justified. Tiny projected outside distances do not excuse those actual3D intersections or prove the3D continuous field itself folds.

**APPROVED as a minimal next proposal direction only, not execution.** On the identical frozen attempt2 point/attribute arrays, restore all original rawGLB skin connectivity, preserving the separately necessary Stage1 oral97 CDT. Removing the field-specific209 skin reconnection is a targeted single-connectivity-variable control before moving points, changing field, enlarging a chart or inventing a loft. Original skin's Stage1 success is contextual control evidence, not proof it will succeed under attempt2.

First freeze a concise proposal with the exact original raw skin-index hash, identical attempt2 float32 position/attribute hashes and unchanged oral97 input hash. Preserve the current209-connection26-cross negative control and failed1.3053px CPU report. A subsequently authorized single CPU must freshly check global3D crossing/positive-area overlap/degeneracy,397 opposed closed interface, original408 eye-triangle/246 vertex/corner/lookup preservation, source-node≤1px and unknown-rear<0.25px. Original circumferential skin connectivity need not be a single-valued destination-XY triangulation, but no actual3D finite-geometry gate is waived. Any failure stops; no automatic field, knot, epsilon or CDT alternative follows.


## 23. Frozen original-skin restoration CPU execution gate

**APPROVED for one fixed CPU test only; no asset, grey candidate, UV or runtime construction.** Read the concrete proposal/package SHA256 `d9d0c35d1aaa75b9f84ba4458992ce9b01832fe31546109df521837a53a2d473`. All nine dependency hashes match. Independently read the actual rawGLB and verified sourcec1b10d96…, all68823 original skin indices canonical uint32LE hash and both surfaces' original POSITION/NORMAL/UV/JOINTS/WEIGHTS hashes.

The package freezes attempt2 raw-order float32 point hashes and the unchanged oral97 origin/corner-copy contract. These are declared same-point constraints to be enforced during execution, not newly evaluated alternative geometry in this audit. The only variable is restoration of original complete skin indices; no new point, field, knot, epsilon or CDT invocation is permitted.

Fresh actualfloat32 global intersection/positive-area overlap/degeneracy and397 closure gates, eye408tri/246 corner/lookup identity, source-node≤1px and unknown-rear<0.25px remain binding. Conservatively select all actual faces or explicitly include every topology-restored face independent of position movement; do not repeat POSITION-only coverage omission. Any failure stops without another connection/field variant. Historical failed1.3053px/current26-cross reports remain immutable. Passing CPU still requires independent result/visual and later asset gates.


## 24. Original-skin CPU stop and causal diagnostics

**Original-skin CPU FAILED under its frozen source-node gate.** Read completion/implementation reports and independently verified actual probe-script and completion hashes. At X2000.5, upper target407 versus actualPL408.099224935 gives1.099224935px>1. The report states global intersection was not run after this stop; it does not claim original skin passes that gate. Other source nodes, eye/interface/rear/degeneracy results cannot retrospectively change this failure.

**APPROVED for read-only full actualfloat32 intersection localization, four-view RAM grey and the failing edge's original-Stage1 curvature attribution using exactly these unchanged original-skin points/connections.** Append diagnostics without modifying the failed CPU report or calling this a Phase3 pass. Compare against the26-cross F2-connection negative control under the same canonical checker and consistent previously approved normal derivation, with all kept/cap/oral faces included. Images must retain non-delivery/CPU-stopped labelling; no new GLB, field, epsilon, CDT or source threshold is authorized.

A future split at preidentified sourceX2000.5 is only a possible method to discuss after geometry and grey results establish the remaining problem. It is not approved here. Such a proposal would need exact parent edge and original-domain split parameter, shared skin/oral geometry cache, corner/JW/normal provenance, protected-feature and finite-budget contracts, plus selection of every new topology face. No automatic subdivision follows if the original skin still intersects or looks wrong.


## 25. 2026-10-22 Phase1: source colour-band versus geometric lip constraint

**APPROVED as a narrowed investigation conclusion; no new field or target curve authorized.** Actually viewed the original-skin three-column grey board and the species atlas page3 local render. The original-skin grey remains visibly stepped/folded at the front lip with a front midline crease. The post-stop report's16 actual crossings means restoring original skin did not establish that former-F2 diagonals alone caused the failure, or that the remaining problem is merely a small source-sampling discrepancy. Original-skin1.099px and earlier1.305px failures remain unchanged.

Verified source-anatomy package SHA256 `905424abafde70527b1533ca8f8a811ea223da81130c9d2def4eb7437fc8f3be` and its two relative-file hashes. The actual viewed primary source is Javier Blasco-Zumeta's species sheet043, *Sander lucioperca*, printed page3, available at [the atlas PDF](https://monteriza.aranzadi.eus/wp-content/uploads/peces/043.sander-lucioperca.pdf). This review inspected the local full-page image; the web fetch timed out and is not presented as a successful online text extraction. Side/near-closed frontal/open-mouth photos support qualitative continuous oblique lips, transverse frontal arch and a volumetric jaw. Handling, perspective and different opening states prevent metric fitting or transferring the wide-open pose into the slightly open game source. The photos do not establish universal mathematical smoothness or forbid normal pixel-game faceting.

The gold/cream-to-dark transition remains real source-material evidence, but repeated Y samples at413 or407 do not themselves encode zero geometric endpoint slopes or planar lip steps. Attaching zero slopes to the material plateaux was an additional engineering assumption. Current plateau-to-plateau steepness/curvature co-locates with the failing finite faces; this supports investigating target-curve/finite-interpolation interaction, not a single-cause proof from the photograph.

A future specification may prospectively separate (1) reproducing material-colour boundaries from (2) placing the actual geometric lip within a confirmed source lip band while following a continuous low-curvature guideline. Required evidence before a new curve/CPU proposal:

- Freeze per-X confirmed bright-lip band bounds and explicit unknown transitions/end semantics. Do not use a uniform±3px allowance or silently promote an uncertain dark endpoint to measurement.
- Retain intended micro-opening state, physical tip/mouth-corner roles and eye protection. Atlas morphology is qualitative; transverse metric shape remains a disclosed engineering choice.
- Specify the C1/slope/curvature or unique minimum-curvature construction rule before evaluation. Its constants are modelling rules, not biological measurements; choose neither them nor band width by repeatedly trying until crossings disappear.
- Check the actual finite3D lip's source-side projection against those bands, not only analytic knots. Separately inspect transverse sections and fixed-game-camera front/side/oblique grey appearance. Original R lying in a band is a control, not automatic geometric/material acceptance.
- Source-colour alignment and actual UV sampling are distinct: a geometric point projecting inside the band does not prove its frozen UV samples appropriate material.

This is not retrospective relaxation of the old1px gate. Any replacement criterion must be separately frozen/reviewed prospectively, preserve rejected evidence and keep zero actual crossings/overlap/degeneracy, closed opposed interface and exact eye-feature contracts. No new Rt, split, CDT, field, model or UV run follows from this Phase1 decision.


## 26. Manual source lip-band evidence layer

**APPROVED as evidence for a prospective engineering admissible-region proposal, not as a biological rim or cutting authorization.** Actually viewed the manual band figure and read both source-band/continuous-lip result documents. Verified package SHA256 `08eef0cf4ef57356edf92e83f05350911e3c7263879f7b07c414f9ef26fb1662` and all three files. Native cell ranges1985≤X<1998,Y[407,413] and2000≤X<2010,Y[402,407] correspond to manually recognizable cream/gold clusters.2010≤X<2012 continuation is lower confidence;1998–1999 and later dark endpoints remain unknown. Context explicitly separates body colour, multiple rear bright bands and isolated lower white pixels.

These regions can constrain where a future geometric lip proposal is permitted to lie, without pretending a material-colour edge is itself a measured entity boundary. They do not permit arbitrary removal/thinning of the entire bright band, dark-pixel cutting or implicit completion of unknown spans. A0.5px inward cell-centre margin would be an engineering contract to review in the concrete proposal, not a source observation already approved here. Actual finite PL location, lip thickness/opening, grey appearance and later UV sampling remain independent checks.

The continuous-lip report also establishes that simply combining oldR endpoint401.296404 with currentUt endpoint401.5 produces negative upper span≈−0.203596. Matching the shared collapsed endpoint401.5 is a compatibility requirement under the current top/endpoint role, not a biological metric. The unresolved terminal neighbourhood still needs positive-span/finite-geometry proof.

No1972 join expansion, posterior protection release, degree-five solver or new field is approved in this evidence-layer gate. Review a concrete frozen prospective rule before solving; do not relabel old1px/16-cross failures as passing the future band criterion.


## 27. Continuous-lip Phase2 → one solver/CPU implementation gate

**APPROVED for one fixed solver + CPU complete-fix attempt2; no actual asset/UV/runtime execution.** Read the full proposal and verified package SHA256 `f066e2ca1c4626dee794947feaa86386c6461efec0cbafd5e94a9ddcd4e86f03` plus all19 frozen input hashes. The degree≤5 representation has two free coefficients after four endpoint value/slope constraints; integrated squared second derivative is strictly convex on this nullspace. The monotonic semi-infinite constraints and fixed band/endpoint constraints define a convex feasible set, if one exists. Approval does not assert feasibility.

The prospective engineering contract is explicitly approved for this attempt:

- Join1972 is a predeclared engineering transition choice, not a biological landmark. Permit13.5px posterior support release relative to the former1985.5 join. Keep originalX≤1972 posterior displacement strictly<0.25px and report every released old endpoint, distinguishing original/Stage1 X.
- Confirmed band cells1985..1997 and2000..2009 use the declared ranges;2010..2011 retains its medium-confidence label but may use the explicitly requested same hard constraint.0.5px inward analytic-curve margin is an engineering cell-centre rule. Unknown connections/dark endpoint remain engineering unknown, not newly observed anatomy.
- The former upper exact-colour-edge1px criterion is prospectively replaced only in this semantic region by full-cell actual-finite-PL band membership. Lower source1px, full-eye408tri/246 corner/lookup/JW exactness and all real geometry/interface gates remain unchanged. Old1px/16-cross failures are not reclassified.

Freeze actual solver implementation and numerical/precision records before its first solve. Use only the fixed degree, join, endpoint slopes, objective, bands and64-exchange ceiling. Verify derivative extrema/roots and all required ordered-span/rho conditions on piecewise intervals; uncertainty, infeasibility or iteration limit fails without changing epsilon/degree/join/band. Do not use intersection counts or rendered appearance in the optimizer. Internal solving of this one fixed convex problem is not permission for another geometry variant.

Fresh CPU must retain original skin and oral97/291-corner provenance, conservative fullactual24130-face canonical intersection/overlap/degeneracy checks,397 opposed closed interface, actual finite-PL band envelope and posterior disclosures. Keep local/transverse strain and collapsed-tip limitations explicit. Normal derivation retains the previously approved incident-group/eye/exterior rules, including the zero-newfaces[-0:] guard.

This is recorded as one complete repair attempt: CPU hard failure counts as failure of this fix and stops; later visual failure likewise cannot be renamed a mere diagnostic to permit automatic retries. CPU success first returns for independent result review before RAM visual/actualGLB authorization. New actualLOD/eye/body/fin/motion/material/runtime acceptance remains separate and ungranted.


## 28. Continuous-lip complete attempt2 infeasibility and next function-space hypothesis

**Complete-fix Strike2: FAILED, correctly stopped before field/geometry.** Read exact/checks/probe implementations, execution freeze, completion,12 synthetic control results and Farkas certificate. Verified freeze SHA6676a9f8… and completion SHA9b774cc6…, all three implementation hashes and controls hash. Independently reconstructed the three relevant inequality rows from the frozen start/end values and endpoint slopes using separate Fraction algebra. Rows match exactly. Nonnegative certificate weights `2899232/29612145`, `933156/1974143`, `12715573/29612145` cancel both free coefficients to zero and yield exact bound `-303935469030376087752429737/1524541301236717132238028800`≈−0.19936191219209462. Thus the approved finite-band constraints alone are infeasible in this two-degree-of-freedom global polynomial family, before monotonicity exchange. No new production solve was run by this review.

The actual firstQP stop is not numerical-precision evidence or an optimizer failure. The exact active-set2D code checks feasibility/KKT under the positive-definite bending objective; the independent Farkas contradiction establishes failure without trusting that implementation. The12 synthetic controls are implementation evidence, not a candidate or downstream geometry pass. No new Rt coefficients, field evaluation, target-span certificate, eye/rear/actualfinitePL, crossing/interface, grey or asset result exists for this attempt; all remain NOT RUN rather than inherited passes.

### Input-context clarification required for final record

The completion's generic `package_sha256=d9d0c35…` identifies the prior original-skin/raw-attribute/oral-origin baseline contract; `input_sha256=3ed55f5…` identifies the unchanged top/chin/lower parameter input. Code separately validates the actual approved phase2 packagef066e2ca… against execution freeze6676a9f8… before calling the new fixed1972 solver. This is not evidence that the wrong proposal was solved. However, a new explicitly named input-context sidecar must bind these roles and the completion hash; generic legacy fields must not be mistaken for this attempt's authorization package. Preserve original failed bytes.

### Prospective Phase1 direction, not another trial approval

The certificate proves this fixed globaldeg≤5/four-endpoint-condition family is too restricted for the frozen bands. It does not prove that source/endpoint constraints are globally compatible in every broader family or that a proposed spline will be feasible. A single-variable next hypothesis may change only the Rt function space to a clampedC2 cubic spline with fixed source-boundary knots `[1972,1985,1998,2000,2012,2019.5]`, unchanged endpoint values/slopes, source bands and minimum integrated squared curvature objective.

Four interior knot values determine the clamped cubic spline. A finite sufficient monotone domain can require all three quadratic Bezier derivative-control values per segment nonpositive (equivalently endpoint slopes and `3*secant−m_left−m_right` nonpositive). This is a more conservative admissible set, not proof it contains all monotone splines. Use a strictly positive-definite reduced4D bending Hessian for uniqueness; PSD alone is insufficient. Freeze the finiteQP/constraint/proof method in the concrete third proposal, reject infeasibility rather than relaxing knots/bands/domain, and retain all previous geometry/eye/interface/source-unknown contracts. No spline solve, curve, field or asset execution is approved here.


## 29. Final retention and skill-scope precheck (not a new experiment gate)

**HOLD final all-scope commit pending the narrow record items below.** This is a static retention precheck, not approval of a spline solver, future results, model/UV/runtime or any107/108 deletion. Reused the phase-specific reviews above; no historical failed experiment, GPU gate or production solver was rerun.

Inspected current fish-production skill/reference,108 session, Fish SESSION106–108 entry, zander species card and108 README. Their rules preserve source/material/geometry distinctions, scope local eye results, retain LOD5/fin failures and reject mechanical checks as whole-fish acceptance. New guidance is qualitative and per-case: it does not universalize108 numeric landmarks or biological measurements. Current changes do not touch formal game files. Historical082 acceptance is explicitly historical and108 reopened its mouth review, rather than silently changing that old decision.

Checks performed:43 retained108 Python sources parse by AST; both repositories' tracked diff whitespace checks pass; local Markdown links in the six reviewed entry/skill documents resolve.108 currently has231 retained files and noPDF. The atlas is recorded by author/URL/page/hash and qualitative observations, not redistributed as a copyrighted full document/photo archive. Literal credential-pattern scan of108 sources/session found no candidate secret. Runtime/oneoff paths and107 candidate references are diagnostic dependencies, not a new portable production API. The cleanup-plan README explicitly preserves active107/108 inputs, separates byte restoration from Godot/GPU/LOD reproduction, and states that URL/hash is not an offline PDF backup. It does not authorize deletion.

The new `continuous-lip-cpu/context.validation.json` now binds six distinct roles. Independently checked all six input hashes; they match. It correctly distinguishes approvedf066 proposal,6676 execution freeze,9b77 failure completion, reusedd9 original-skin contract,3ed unchanged parameters and the actual probe. This resolves the generic legacy package/input-field ambiguity without modifying original failed result bytes.

### Required before final retention commit

1. Narrow the overbroad sentence in continuous-lip `result.md` claiming a change of polynomial degree cannot change the contradiction. The certificate only covers the frozen degree≤5/four-endpoint-condition two-free-parameter family. Preserve frozen bytes where required and append an explicit contextual correction. A larger function space may be feasible or infeasible; neither is proved here.
2. `attempt2-cpu/actual-camera-projection-run.log` is ignored by Git. If retained as original camera evidence, preserve its exact bytes under a nonignored archive name (for example `.log.txt`) and update any referenced path/hash mapping; otherwise explicitly remove it from the retained evidence contract. Do not silently lose it at commit.
3. Finish the current terminal README/session/knowledge and dependency inventory when the actual last authorized phase is known, retaining complete-fix Strike1 and Strike2 and all NOT RUN downstream gates. Current entries explicitly say unfinished; they cannot yet be represented as a completed final archive.

The12 synthetic controls currently have result/expected records, but their input construction/executor is not preserved as a reproducible test suite. Keep them as historical implementation evidence, not a claim that another reviewer can rerun those exact12 tests. This does not weaken the separately independently reconstructed exact Farkas certificate. Future solver/test implementation requires its own concrete gate.


## 30. Fixed C2 spline Phase2 → one complete-attempt3 solver/CPU gate

**APPROVED for one fixed implementation + solver/CPU complete-fix attempt3, not assets or rendering.** Read the complete concrete proposal and independently verified final package SHA256 `f8030d89c9c9a5ae6cf6b4899b9a00cff6b3a5f7a95bd71883f0b7a983e930dc` and all32 input hashes. Earlier package versions are not this authorization. No new solve, coefficients, field or mesh was produced by review.

The method is a supported single change of Rt function space. Fixed knots `[1972,1985,1998,2000,2012,2019.5]`, endpoint values/slopes, source bands/margin, posterior release and original-skin/oral97 contracts remain those explicitly requested. Four internal values uniquely define a clamped C2 cubic spline. The specified tridiagonal equations, local cubic formula and integrated squared-second-derivative energy are consistent. The reduced Hessian must be exactly SPD: zero curvature of a nonzero endpoint-clamped perturbation is impossible, but the actual assembled4×4 matrix still requires exact positive-pivot verification before productionQP. Do not regularize a bad assembly or substitute PSD.

All three Bezier derivative controls nonpositive per segment are a valid finite sufficient monotonicity condition and define a conservative linear-inequality domain. They do not characterize every monotone spline. Within that domain, interval-band limits follow from endpoints; retain2010 as an evaluated interior polynomial position and the declared high/medium roles. The actual finite-PL whole-cell envelope and float64/f32 comparison remain separate hard checks, not consequences of the rational reference curve alone. Unknown intervals acquire no new anatomical/source authority.

With at most25 rows, enumerating active subsets of size0..4 has exact upper bound15,276. The SPD objective and finite polyhedron justify KKT sufficiency; conic minimal-support representation allows at most four independent active normals. Singular Schur subsets may be skipped and counted, but all remaining subsets, exact nonnegative multipliers, full inequalities and stationarity must be checked as specified. Exhaustion can establish infeasibility only after exact valid assembly and completed enumeration; interruption/implementation uncertainty is an unsuccessful, undecided attempt, not an infeasibility certificate. Neither cross counts nor appearance may select the QP or its constraints.

Before the first production solve, retain actual implementationSHA/software/precision freeze and concrete small control inputs plus a runnable executor/command. Controls must cover SPD rejection, unique interior and four-active KKT, explicit infeasibility, spline interpolation/end slopes/C2/energy assembly and adapted root/PL checks. They are synthetic implementation controls, not candidate iterations. Original frozen failures/helpers remain immutable.

Approval permits one solver/CPU execution only: no alteredknots/join/endpointslopes/Bezier domain/bands/field, no newCDT/split or epsilon adjustment. Full actual24130-face crossing/positive-area-overlap/degeneracy zero gates,397 opposed closed interface, complete eye408tri/246 point/corner/lookup/JW identity, posterior disclosures, ordered spans/rho and all actualPL/lower/source gates remain in force. CPU success must return for independent result review before any actualGLB construction or RAM/asset rendering authorization. No newLOD/runtime/body/fin/motion/material acceptance is granted.

Any solver uncertainty/infeasibility, CPU hard failure or later visual failure is complete-fix **Strike3**, followed by STOP, architecture reassessment and knowledge/retention closure. There is no automatic fourth variant or diagnostic-label exemption. The context-errata sidecar now explicitly limits the old Farkas conclusion to the frozen degree5/twoDOF system and records the historical12 controls as non-replayable evidence; its hash is bound in this final package. The separate ignored-camera-log/final-archive commit items in section29 are not waived by this experimental gate.


## 31. Complete-attempt3 CPU result and RAM-grey gate

**CPU mechanism gate APPROVED; authorize only four-view RAM grey diagnostic from the same frozen result.** Verified completion SHA256 `bf90691c0ea89775b806f869b55cd60ba2aaabba0f80f3d195cab48281d11cc6`, pre-solve freeze `52a14f2739e4bd6d3e08632704c5c40e14a494072f11fb01e648728d022dc14e`, all eight implementation hashes and the retained control input/executor/result hashes. Read exact-spline, span/PL-check, probe and synthetic-control implementations. No new production solve/field/mesh was run by this review.

Independently recomputed from recorded rational coefficients (without calling production solve): all four positive LDL pivots match; all19 inequality slacks are nonnegative; active rows9/12/13 have zero slack and nonnegative recorded multipliers; the complete KKT gradient is exactly zero. Thus the recorded feasible point is the unique minimum for the frozen SPD quadratic and conservative linear domain. Independently checked piece interpolation, both endpoint slopes, every C2 junction and every recorded nonincreasing Bezier control. NodeYs are419.0686412505533,412.5,407.5,406.5,403.3667398882294,401.5.19 deduplicated rows retain all27 raw source/derivative roles, including constant endpoint controls and medium2010 role;1056 examined subsets lie within the declared finite enumeration bound. No feasibility-by-epsilon or objective change appears in these paths.

Independently reran only the21 frozen synthetic controls into `/private/tmp/fish108-spline-controls-independent-review.validation.json`; all pass and their result rows match the archived control rows. Concrete input and runnable executor are retained. This is not a second production solve. The historical12 controls remain non-replayable historical records, not silently replaced.

The actual CPU paths preserve originalskin22941 and oral1189 (including97 reconnected faces/291 raw corner origins), complete24130 finitefloat32 faces and canonical changed-geometry/topology pair selection. Restored209 skin and oral97 are selected; lower/cap/crossZ/kept faces remain present. Reported24,762 tested pairs give0 propercross,0 positive-area coplanar overlap and0 zero-area faces; shared-vertex pairs are not blanket-excluded.397 boundary pairs are opposed/closed, with geometricedge incidence2 and matched direction. These are the frozen floating geometry checks, not continuous-time/exact-arithmetic collision proof.

Eye408tri/246 supports, original triangle/corner/lookup and rawPOS/NORMAL/UV/JW contracts remain intact in CPU. OriginalX≤1972 posterior displacement max0.228546142578125px is strictly below0.25. Newly released table has **104 endpoint samples representing52 unique actualskinIDs**, not104 independent vertices; max release displacement1.687530517578125px. Complete high/medium actualPL envelopes pass their original cell bands using actual finite edges, clipped endpoints, cell boundaries, line intersections and verticals; unchanged lower known-source error max0.771217360604453px remains≤1. Reference all-open-interval span/rho checks and separate0.025px/actualX float coverage are explicitly distinguished, with only the frozen collapsedtip exception.

**No whole-mouth or visual acceptance.** Actualvertex dYdY reaches12.427132210359849 near the collapsedfront; maximum tangent stretch21.708603375578694 and minimum0.18355604930518948 are material visual risks, not evidence of natural shape. All numerical hard gates can pass while shieldlike lips, steps, front seam or local folds remain. The principal user goal must be judged from the actual grey views and source/section comparisons.

Permit only deterministic RAM reconstruction from the recorded frozen spline coefficients/coordinates and originalskin+oral97, with the same cameras/lighting for baseline and prior failedF2-connection control. Do not re-optimize/re-solve, adjust field/normal parameters, generate GLB/blend/UV/runtime or claim actual-import/newLOD evidence. Use the already approved actualfinite-face areaweighted normal policy within original seam groups, preserve eye/exterior attributes, and retain the explicit `nnew>0` guard so zero newskin faces do not select the entire body. Capture the mouthfront/side/oblique and remaining frozen view, sufficient local sections/source-canvas context and the known highstrain region.

Return rendered evidence for independent visual review. A bad shape is completeattempt3 failure and triggers **Strike3 STOP**, not another field/connection/UV retry. Only a later explicit gate can authorize actualasset construction or material work.


## 32. Attempt3 RAM-grey initial visual observations (final visual verdict pending)

Actual viewing completed for all four spline PNGs, baseline front/oblique and the four-column baseline/F2/originalskin/spline comparison board, plus the newly available nearest-source lip overlay detail. **Do not advance to UV/normal repair or asset construction.** This is initial form feedback while the remaining frozen-camera/section/context evidence is assembled, not a whole-mouth pass.

The spline improves the previously abrupt upper-lip step in side/oblique views; the mouth line reads more continuously and the top view does not introduce an extra projecting hook. The source-canvas side envelope remains a separate useful alignment check. These improvements are real and should be retained in the record even if the attempt ultimately fails.

The front view still has a conspicuous narrow raised longitudinal lower-jaw stem with paired light/dark grooves extending downward from the front lip. Baseline has a shorter rounded lip-front highlight, whereas the new lower form extends over a larger jaw region. Do not confuse it with the old central upper-snout lighting crease, which is already visible in baseline. Oblique view likewise retains several lobed/hard underside turns. The front stem is the principal current visual concern; isolated tiny facets near the tip are less decisive for a pixel game. This observation is based on visible shape under identical lighting, not rejection from stretch/Jacobian numbers.

These are close orthographic diagnostic images (ortho_scale≈0.205), not actual gameplay-camera proof. No universal subpixel/invisible claim is justified; equally, their full900px close framing must not be represented as normal gameplay scale. Final verdict should use the promised mouthfront sections/source context and the existing frozen normal/near/closest camera relationship, without generating a new shape, changing normals or moving acceptance thresholds. The atlas supports qualitative jaw volume/continuous arch, not evidence for this specific central longitudinal ridge. If the complete evidence confirms the visible ridge/underside form as unacceptable, count visual failure as completeattempt3/Strike3 and STOP.


## 33. Complete-attempt3 final visual verdict — REJECTED / Strike3 STOP

**REJECTED as the current complete mouth repair. Strike3: STOP.** The successful CPU result in section31 remains a real technical pass; it is not retrospectively failed or promoted to visual acceptance. No new GLB, UV, formalgame, runtime or LOD asset is accepted. No fourth field/connection/normal/material repair is authorized.

Actually viewed the four standalone spline grey PNGs, baseline front/oblique, the four-column baseline/F2/originalskin/spline comparison board, source-canvas lip overlay detail, and six equal-native-scale actual-triangle sections atX1920/1950/1980/1995/2005/2015. RAM receipt binds recorded CPU coefficients without a production solver call, and both reconstructed rawfloat32 point hashes match CPU. Camera receipt hash also matches. This assessment uses those visible forms and section geometry, not merely high strain numbers or the existence of prior failed reports.

**Improvement retained:** upperlip steps are substantially reduced relative to the failed controls, side/oblique mouth lines are smoother, and source-side upper/lower alignment is improved. Slight local facets alone would not be sufficient reason to reject this pixel-game asset.

**Blocking form:** front view has an elongated raised lower-jaw central body with distinct paired light/dark side grooves; oblique underside remains segmented by several hard turns. Together these read as a deep, extended lower cup rather than a small lip-alignment change. The same-scale sections explain why this is a broad volume change: atX1920/1950 the original innerfloor remainsY447.625/436.407, while exterior centre moves458.414→480.132 and446.683→471.451. Lower shell depth grows approximately10.79/10.28→32.51/35.04nativepixels across a substantial jaw length. These stations are behindRtjoin1972, so do not attribute the whole defect to the new spline; the retained top/chin/lower architecture also determines this result. A continuous source-side silhouette and nonintersecting finite triangles do not establish a satisfactory transverse jaw volume.

The section centres are **not mathematical needle spikes**: Z0 prominence relative to±5 changes only≈0.654→0.783 and0.761→0.961nativepixels at those stations. The rejection concerns the elongated central form/grooves and broad cup-depth change visible under matched lighting, not a fabricated sharpness measurement. The old upper-snout central shading line is also distinct from the newly extended form below the lip. Atlas photographs support qualitative jaw volume and continuous arch but neither measure this shell depth nor validate a central longitudinal protrusion. Source material bands remain engineering/source constraints, not measured biological rim surfaces.

Camera-scale supplement reproduces96 old actualbaseline point projections with maxknown-world residual0.000155858px and meshrest residual0.000281116px. Its924attribute/633physical-binding ROI separates610purejoint1 points from23mixed affine-only approximations. For purejoint1, overall lower-jaw maximum displacement at configured378h is≈2.845normal/5.131near/33.674closest pixels (720h formula case≈5.420/9.774/64.141). These are **overall edit displacements, not ridge-error magnitude**, not visibility measurements or newGPU screenshots. They do not independently prove a defect, but rule out treating the entire changed jaw region as universally invisible/subpixel.720h is a mathematical old-camera response case, not a new actual host screenshot; candidate bounds normalization was not validated. The close orthographic views remain diagnostic, not asserted normal-game framing.

The broad visual/section problem is sufficient to reject the current form despite improved source alignment and permission to tolerate modest facets. Do not hide it using normals/UV/material or interpret missing newruntime evidence as approval. Per the prospectively frozen policy, this visual failure ends completeattempt3. Preserve Strike1 visualfailure, Strike2 fixed-family solverinfeasibility and Strike3 CPU-pass/visualfailure separately; preserve the earlier partialStage1 and other investigative controls without relabeling them as accepted repairs.

Proceed only with architecture reassessment, knowledge capture, retained-evidence/dependency closure and separately reviewed authorized cleanup/commits. Section29's final record/ignored-log items still require closure. No new repair trial or deletion is approved by this terminal verdict.
