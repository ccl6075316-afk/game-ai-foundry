# 053 Fish anatomy — Phase 4 adversarial review

Date: 2026-10-15. Independent reviewer: anatomy_phase_review.

**Verdict: APPROVED for the scoped repairs and candidate preview.** Scope: paired-fin attachment, accepted-source tail-outline recovery, and provisional arapaima eye-height/girth-scenario correction. **Overall biological anatomy and visual asset acceptance remain pending.** This verdict does not authorize presenting either model as fully anatomically validated or replacing the accepted game model without its normal visual gate.

## Interim code review

- Rest-shape inputs are declarative, finite and bounded. Historical handoff/native hashes, accepted texture hashes and style contract are checked during plan/freshness/build. Accepted native outputs are protected from being reused as candidate destinations. Blender native revision explicitly disables embedded scripts.
- Vertical affine mapping preserves X and declared topology/UV; eye patches and fins translate from mapped anchors rather than flattening their own local shapes. The rig also receives a corresponding rest deformation. Head/torso parameters remain scenarios subject to measurement and visual comparison.
- Procedural root_attachment uses actual body closest points, an inset and a smooth fade. Fin-root own-fin weights become zero over the full declared root band, then increase distally. Source-t POINT data survive solidification for postprojection root identity. This addresses the independent-placement cause rather than hiding a gap with a global nearest-mesh statistic.
- Contact helper measures all selected root vertices and interior edge samples against the posed body. It explicitly aggregates only fins declaring attachment_required; reports for other fins must remain visible and must not be described as all-fish contact success.
- Independently ran test_volume_shape.py: **10 tests passed**. The parent reports the larger CLI suite separately; that larger run has not been repeated by this reviewer.

## Corrections requested before final gate

1. measure_anatomy.py currently filters absent sections out of its all(finite) condition. Missing all requested intersections can therefore produce ok=true. Missing requested stations must be explicit failures rather than a vacuous measurement success.
2. check_fin_attachment.py opens native data without use_scripts=False; use the same explicit read-only script policy as other helpers.
3. audit_native_revision.py verifies hierarchy but does not compare bone head/tail positions against the declared mapping. Extend the preservation evidence or clearly stop claiming the report proves corresponding bone geometry. This matters because rest bone changes affect animation despite unchanged curves.
4. Update the revise_native docstring, which still describes Y-only editing despite supported Z maps.

## Outstanding verification

- Recompute full 053 candidate section/girth comparisons with exact hashes and retain source/scenario/unknown distinctions.
- Four actual Godot actions: posed skin contact, sufficient seam samples, model/controller/profile hashes, and explicit action coverage. Native 18-pose Swim is necessary but insufficient.
- Tail source retention plus clay/runtime lobe and peduncle evaluation. Exact outline reconstruction is not proof of biological caudal form.
- Mouth bluntness and torso contour require real-reference visual review; the provisional HDOr range and median girth scenario cannot establish all anatomy.
- Keep formal model acceptance pending if remaining anatomy or visible defects persist.

No fixes made by this reviewer.

## Final verification addendum

- All four interim code requests were addressed: missing section intersections now fail explicitly; native loading disables scripts; bone rest head/tail mapping is checked at 1e-7 native units; revision description recognizes height changes. Arapaima preservation report has all 12 checks true, including declared_bone_rest_mapping.
- Independently checked fresh native hash for full arapaima 053 anatomy measurements. Eye-plane height is **11.0168 cm** versus 052's **17.2873 cm**; the three candidate median-region cross-section perimeters are **95.3610 / 95.3666 / 95.3146 cm**, near the explicitly derived **95.3561 cm** scenario. Opercular candidate envelope width is **25.3423 cm**. Terminal mouth width **7.7507 cm** is an artistic target, not published fish morphometry.
- Fresh shark 053 runtime report contains **32 actual skin samples: eight each for Swim, Turn, Ascend and Dive**. All four paired fins have zero failed samples; worst signed exterior distance remains negative (approximately -0.0247 cm). Baseline 052 has all four paired fins detached in all 32 samples. This directly demonstrates repair at the sampled phases; between-sample contact is not proven.
- Independently verified 053 model/controller/exhibit/motion-config/exporter/checker hashes against current files. The runtime checker resolves Godot's winding using signed closed volume before signed distance; this avoids mistaking an outward gap for burial. Its report expressly measures skin contact rather than tank bounds.
- Native helper now labels unpaired root-band metrics as unsupported anatomical gates. A proximal source-t band may include a free edge on these fins. Their positive distances cannot be silently treated as either a proven seam defect or a proven attached seam. Their anatomical status remains unresolved.
- Tail outline trace report retains **99.55% / 99.93%** of its explicitly defined source-alpha regions, with profile/source hashes. The reconstruction ROI differs from baseline diagnosis; use these figures as candidate source-fidelity results, not an exactly controlled baseline delta or biological tail measurements.
- Independently viewed both clay oblique renders. Shark paired fins appear connected and the tail lobes are fuller. Arapaima still has a long tapering head and a visible circumferential shoulder seam. The source-based head-height and girth corrections do not resolve those appearance defects. Parent inspected the 600-frame whole-model videos; this reviewer inspected the saved clay renders and runtime numerical evidence, not every video frame.

### Final checklist disposition

1. Failing baseline tests preceded fixes: **YES**, independently reproduced in Phase 3.
2. Repairs address traced causes: **YES** for the scope above; source alpha, head/torso parameters and fin placement are changed at origin.
3. Changes isolated to investigated causes: **YES**, separate head-only candidate and per-component diagnostics support attribution; no unrelated behavior included.
4. Security/provenance regression: **none found** in inspected paths; native read-only script policy and accepted-input hashes are explicit.
5. Regression verification: **YES**, 10 relevant unit tests independently passed; parent reports 701 CLI tests passed / two skipped, and both candidates retain eight technical checks. No extra broad run requested.
6. Failed-fix strike handling: no failed verified fix was hidden; unresolved anatomy/appearance is expressly retained as pending and must trigger further investigation if further repair is requested.

The user may now compare these limited improvements honestly. Do not claim the mouth, every shark fin seam, dorsal-fin proportions or all body dimensions have passed real-animal verification.

## 2026-10-15 archive and documentation addendum

The final trace evidence additionally compares exactly the original ROI, pixel-center rule and alpha216 threshold: upper source retention43.214%→99.294%, lower48.399%→98.612%. The earlier differing-ROI caution above remains relevant to the expanded-ROI figures.

Before commit, the parent reran all701CLItests (two skipped), the seven candidate-gate tests, and the actual current-hash candidate gate. New preparation/validation guides, species-card checklist and six-layer results matrix retain the scoped/pending distinction. Four orbit JSON reports were losslessly gzip archived with original and archive SHA256 recorded; representative053videos and view images retained. No production fish GLB replaced and no visual acceptance added by this archive step.
