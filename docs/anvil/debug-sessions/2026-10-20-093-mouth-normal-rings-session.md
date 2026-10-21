# 093 mouth revision: introduced grey-model rings

## Entry

Normal mode. Evidence: actual Godot captures `yellow-mouth-093/baseline/oblique-grey.png` and `candidate/oblique-grey.png`; model SHA `ba67d5e…` versus `09363e7d…`; Godot capture logs and successful body/motion gates do not imply visual acceptance. Main reviewer observed smooth baseline but newly ringed candidate. Earlier attribution to existing topology was incorrect.

No formal candidate/model/config changed by this diagnosis. `candidate-normal.glb` is an alternate diagnostic specimen only.

## Phase 1 — investigation (review pending)

Reproduction: current normal-field candidate grey front/oblique has horizontal ridges absent in the same-view baseline. The deformation script transforms source normals through a finite-difference Jacobian; local section extrema come from linearly interpolated sampled triangle intersections, followed by source target PCHIP curves. This derivative is a normal field of the interpolated deformation function, not necessarily the normal field of the actual emitted coarse deformed triangles.

Actual geometry comparison: area-weighted triangle normals were computed from current emitted POSITION/index streams and joined only across coincident positions within the same primitive. Skin head vertex deviation between stored normals and these triangle normals:

| model | p50 degrees | p90 | p99 |
|---|---:|---:|---:|
| baseline | 0.192 | 1.400 | 6.407 |
| candidate | 2.188 | 18.973 | 36.441 |

This strongly implicates the normal transformation but does not alone prove positional shape is visually smooth. No POSITION, UV, index, weight, joint or image edit is proposed at this stage.

## Phase 2 — pattern (review pending)

Working reference is the original baseline GLB: stored normals closely follow triangle-derived area-weighted smooth normals. Failing change is the local full-jaw mapping plus its inverse-transpose derivative normal transport. Existing 091 method was a method reference, not proof that all target curves support its derivative assumptions. Normal generation must be checked against emitted deformed triangles, not just positive deformation determinant.

## Phase 3 — single hypothesis and minimal test (review pending)

Hypothesis: analytic/finite-difference normal transport through interpolated section bounds creates the prominent rings, while actual emitted positions can be shaded smoothly without changing the shape.

Minimal contrast specimen `candidate-normal.glb`: same current candidate POSITION, UV, index, weights, rig and source image. Only NORMAL changes to area-weighted actual deformed triangles, welded by rounded equal positions within each primitive; no skin/oral cross-boundary averaging. Posterior x<=0.29 normal bytes remain original, transition 0.29..0.315 is smooth. Hash `3f05745c8ad1334fae3484e2e543602b82714c1fc28547fd2109fd95a162b939`.

Test: standalone `normal-diagnostic-game` with all three frozen files, identical native pose, grey material, lighting and camera. Front/side/oblique captures compare baseline, failing candidate and normal-only specimen. This does not use or mutate the isolated full exhibit being checked by the main agent.

Phase 4 implementation remains blocked on main agent review of this evidence. Alternate specimen is not accepted or installed.

### Minimal-test result: REJECTED

All nine native-pose grey renders completed in the standalone project. Lead implementer and independent reviewer both observed that normal-only still retains side silhouette waves and oblique head rings. Thus the hypothesis that NORMAL alone explains the regression is rejected; no diagnostic specimen was installed. Return to Phase 1. Pixel-alpha target contours (sigma1.1px) can encode small steps across full transverse sections. An alternate sigma5.5 contour-only hypothesis was proposed for review, with explicit terminal jaw landmark protection: global filter maximum16.69px near the upper-jaw ending is unacceptable to treat silently as accurate anatomy. No extra shape trial applied yet.

### One approved bounded source-contour test: visually failed

Lead and independent reviewer approved a single alternative target-curve strategy: base=Gaussian sigma1.1 native pixels; proposal=sigma5.5; final=base+clip(proposal-base,+/-2px). No new endpoint fade or threshold was added. Original Jacobian normal chain, all mouth-edge targets, x/z, rig and other parameters remained unchanged. Diagnostic specimen `candidate-bounded.glb` hash `b5b211b4569a943ea0a9d5970dd2c1c914b55be6b48bfc491be3aa48436bc3b0`.

Actual native-pose oblique capture still shows clear rings, reduced but not gone. Lead implementer does not propose acceptance or installation. Return to Phase1 data flow (old section bounds, piecewise section/cleft mapping); no further sigma/cap trial proposed. Full arrays and all numeric metrics are stored in `bounded-section-curves.json` and `bounded-diagnostic.validation.json`. Actual shared rim projection changes max0.762px/p95 0.069px despite unchanged mouth-edge configuration; this is disclosed. The 2px bound is relative to previous filtered target, not original alpha: original sigma1.1 already has15.38px max upper-end alpha difference, bounded test17.38px.

### Phase1 data-flow revisit (no new specimen)

`section-chain-trace.validation.json` records712 true unique-x triangle-intersection sections and53 regular vertex-ring meridians. This replaces the earlier station-subset min/max table, whose partial oral vertex groups were not full surface bounds.

- Anterior pre-oral x0.29..0.425: 400-sample interpolation errors are small (upper max0.038px/p950.005; lower max0.027/p950.004). This cannot explain all large full-head rings.
- Oral x0.425..0.495: estimated upper bound misses narrow actual upper-lip geometry by max7.317px/p952.822px.102 station samples have estimated high<old upper-cleft threshold. `max(high-ou,1e-5)` masks this order error.
- Identity-target no-write control does not recover original y: max1.145px at x0.491619. Actual high=-0.014943, estimated high=-0.018576, ou=-0.014944. An actual skin point just above ou enters an above-branch whose denominator has been forced to1e-5. This is a distinct defect, not a claim that all rings have one cause.
- Original meridian adjacent-slope-change RMS: top0.254/bottom0.053; target section0.880/0.610; final1.075/0.576. Pixel-alpha target contour and derivative-normal transport remain contributory. Failure of the bounded contour test does not rule out alpha contribution.

Scope table `scope-contour-diagnosis.validation.json` records native GLB skin triangle projection into unchanged source2014x727 coordinates. In preoral x0.36..0.425 source contour p95 improves from baseline27.41/36.13px (top/bottom) to0933.56/3.25px, but this is an extensive head reshape and not a small mouth-only edit. Influence0.29→0.36 originated from091 method reuse, not a species biological measurement. The mouth-region upper max63.39px bad tip is retained in the evidence; side improvement does not mean source tips or mouth topology are accepted. No automatic replacement follows from these diagnostics.
