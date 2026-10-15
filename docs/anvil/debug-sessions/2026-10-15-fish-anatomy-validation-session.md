# 053 Fish anatomy validation debug session

## Entry / mode

2026-10-15, normal mode: user supplied visible pointed arapaima mouth, overly thick body, detached shark fins, and malformed tail; 052 actual runtime videos/validation reports and native files available. Scope: reproduce structural faults, compare measured landmarks to primary references, fix confirmed geometry/attachment, make anatomy validation explicit. 052 candidates remain pending, official game files unchanged.

## Phase 1 — Root cause investigation

- Existing eight technical checks cover closure, weights, finite data, loops, root motion and textures. Runtime report checks readiness/envelope, but neither tests anatomy ratios or fin contact; success cannot validate species anatomy.
- Arapaima 052 only changed Y ratios. Actual outer head HW at u=.75 roughly25.37cm matches provisional25.33 scenario, but orbit plane u≈.922 height17.29cm vs provisional10.31 (+67.7%). Mouth cap still a tapered elliptical tube: widths6.63cm at .9742,3.95 at .985,2.20 at .9914. Maximum body width37.07→36.32cm, not a meaningful overall slimming. Measured station uncertainty and extrapolation must be retained. No matched global body-width reference has been established; do not falsely label max width as +39% relative shoulder.
- Hammerhead paired finpos = source ventral v + independent root_depth, vertical_scale flattens around that off-surface anchor. No body-surface contact constraint. Both051 and052 have chest root vertex-band gap2.645–4.118cm and pelvic vertex-band gap1.977–4.436cm (true boundary curves additionally sample chest1.809–3.269cm, pelvic2.116–3.768cm) in rest and all18 nativeSwim samples. 052 only revised head, preserving this pre-existing defect.
- Upper/lower tail polygon source coverage43.21%/48.40% in distal regions, virtually no polygon pixels outside source; authored polygons cut tail lobes into narrow strips. Tail cap-only observation withdrawn after boundary interpolation: upper root does have buried sections; tail issue supported by source silhouette undercoverage, not a demonstrated total root disconnection.
- History: native shape revision uncommitted diff extends prior builder commit51ec6c9. Original procedural finpos/polygon inputs are unchanged in052; new width field cannot fix these inputs. Repro: read native blend, BVH signed distance of t≤.05 root band; compare accepted source alpha and authored polygon; inspect052 paired actual Godot video. Diagnostics in fish experiments/blender-fish/knowledge-053/*.validation.json.

Status: awaiting independent Phase1 review. No model fix applied.

## Phase 2 — Pattern analysis

- Working surface attachment example: eye patch construction calls closest_point_on_mesh on the body/head, offsets along actual surface normal and weights to body spine. Paired fin construction uses no such surface query. Both consume the same world/native coordinates; the difference is placement constraint, not texture filtering or camera.
- Working continuous geometry example: body rings connect edges between each neighboring section and share the spine weighting field. Paired fins are separate closed meshes and can be individually manifold while wholly disconnected. Thus closed_mesh=true is orthogonal to body contact.
- Tail mapping example: source alpha-aware fin UV only moves sampling to opaque pixels; it never expands the authored polygon. A thin triangle remains thin even with a good image. Revision preserved original polygon/UV exactly, which preserves the faulty outline too.
- Arapaima measurement comparison: 052 correctly fits one width station but deliberately preserves X/Z. HDOr/HL/SnL concern vertical/longitudinal landmarks; width-only validation cannot address them. A physical maximum is not a local comparative datum. No measured maximum trunk width currently available; slimmer envelope is a labeled inference, not a claimed matching measurement.
- Dependencies: actual accepted native textures, 4.5 Blender armature rest coords and native poses, current Godot procedural controller. Existing multi-source UVs cannot be rebuilt via side-only patch. Preserve sources/material ownership; update geometry at rest then verify posed contact and projected silhouettes.

Status: awaiting independent Phase2 review.

## Additional primary measurement evidence

2020Table1 selected DM87.37±2.06cm with TL183.25cm, Fig1 tape wraps median trunk. Derived200cm scenario95.356cm (notdiameter). Actual052 cross-section perimeters u=.50:106.765cm, .579:107.893cm, .65:100.405cm. These are median-region sensitivity stations, not exact Fig1 registration (photo truncates tail). Numerical solve using actual polygon perimeter with Z held fixed yields widths28.19/28.32/28.75cm. Thus body slimming can be tied to a documented circumference scenario, while station uncertainty and cross-group extrapolation remain explicit. Report knowledge-053/arapaima-perimeter.validation.json. No new model edit yet.

## Phase 3 — Hypotheses and minimal failing reproductions

Before production model/code fixes, ran fish `knowledge-053/check_053_regressions.py`: 4 FAIL / 1 PASS, source/native hashes verified. Each falsifiable component is separate:

1. H-head: preserved vertical geometry leaves eye-plane height outside provisional published4–8.2%SL. Test measures9.556%SL and fails. Alternative width-only mismatch is ruled out because changingY leaves measuredZ bitwise unchanged. Mouth-width absolute truth remains unknown; no invented biological gate.
2. H-contact: independently placed paired root bands float. Entire sampledboundary maxdistance>0.05cm fails, rather than one minimum/buriedvertex. All18 nativeSwim phases also fail. Tolerance0.05cm is production contact threshold, not biological range. Camera/matting alternative ruled out by actual native geometric gap.
3. H-tail: authored outlines remove most accepted-source tail silhouette. Test fails43.2/48.4% vs95% production fidelity target, not true biological fin length. OpaqueUV alternative ruled out: polygons are already almostentirelyinsideopaque source, onlytoo narrow.
4. H-body: 052 preserved the bulging middle; realmesh perimeters exceed derivedmedian scenario at sensitivitystations by5.3–13.15%. This is source/landmark qualified evidence, not a hard globalwidth failure. New target can solve actualmesh perimeter rather than arbitraryYslider.

Minimal fixes proposed (pending Phase3 review): optional native vertical station map for arapaima eyeplane, bounded rounder snout geometry/flattened head requiring visual realphoto review, torsoY based actualmeshperimeter scenario; paired fin rootattachment constraint against truebodysurface with bodyweights at roots; shark tailoutline reconstructedfromacceptedalpha. Keep referenceprovenance/materialUV intact. Validate each component with regenerated geometryreports, additional skincontact in4Godotactions and20secondwholemodelvideo. No replacement before these checks.

## Phase 4 — Implementation and scoped verification

Attempt1: added optional native vertical station map, torsoY scenario and broader muzzle width profile; opted-in paired fin root attachment to actual body with root body weights; traced shark tail from unchanged accepted source alpha. No official runtime model replaced. Original8 technical checks pass; fullCLI701tests pass,2skip;40targeted volume tests pass. Helper review fixed missing-section vacuous success, disabled embedded scripts in read-only loads and added declared bone rest mapping audit.

Isolated053a eye-height-only candidate measured11.0168cm at .922 before combining inference edits. Full053: same eyeheight, opercularW25.342cm; median-region perimeters95.361/95.367/95.315cm. These match labeled scenarios, not individually measured biology. Terminalmuzzle .993 W7.751cm is artistic and does not prove mouth anatomy. Native preservation12checks pass incl declaredYZ+boneheadtail mappings.

Shark pairedrest+18nativeposes allcontact; actualGodot four actions8timepoints each32 total, CPU skinned boundary/edge samples allcontact. Baseline052 using same method fails all32. Same fixed alphaROI tailcoverage: upper43.214→99.294%,lower48.399→98.612%. This is sourcefidelity only. Nonpaired diagonal tband is not anatomicalroot; reports now identify its limitation and separately show connected membrane/body intersection, not fullseam acceptance. FAO dorsalheightrelation remainsunresolved.

Two actualGodot20second600frame videos and5views archived; each runtimeenvelope0failures distinctfromskincontacttests. IndependentPhase4review scopedAPPROVED at docs/anvil/reviews/2026-10-15-fish-anatomy-phase4-review.md. No structuralfix strikes; overallanatomy/visualacceptancepending because headtaper/shoulderseam/backUV and unknownmouth reference remain. Do not call localmetric success wholefish acceptance.
