# 053 Fish anatomy — Phase 1 adversarial review

Date: 2026-10-15. Reviewer: independent anatomy_phase_review agent.

**Verdict: APPROVED for investigation → pattern analysis.** This approves the causal investigation, not either fish's anatomy or appearance.

## Checklist

1. **Root rather than symptom — YES.** The failure chain reaches authored data and the validation contract: paired membranes derive Z from a ventral image anchor and Y from independent root_depth, without querying the body surface; tail geometry follows narrow authored polygons; the native 052 revision multiplies Y only, retaining the convergent muzzle and excessive eye-plane height. The CLI CHECKS tuple and builder checks measure mesh/animation/material integrity, not biological dimensions, contact or silhouette. Runtime envelope success cannot fill these gaps.
2. **Evidence sufficient — YES, with stated bounds.** The native root-band report gives positive minimum distances for both pectorals (~2.645 cm) and both pelvics (~1.977 cm), unchanged between 051 and 052, throughout 18 native Swim samples. Independent source-coordinate inverse and boundary sampling support the band identity. Arapaima mesh-plane intersections report visible outer-body union, separate from paired-fin span: HWop candidate 25.37 cm; eye-plane height 17.29 cm; mouth converges to ~2.20 cm near the anterior cap. This supports geometry defects, while reference comparisons remain provisional.
3. **Data flow traced to origin — YES.** Read fin triangulation/finpos/depth/weights in build_fish.py, width_scale and revision_source in cli/volume_shape.py, revise_native, authored 052 profiles, measurement script and diagnostic JSON. A bone head is correctly distinguished from membrane contact. The per-station widths do not establish actual eye separation or whole-fish maximum-width biology.
4. **Recent changes correlated — YES.** Reviewed current builder diff against committed 51ec6c9 plus earlier history. The new rest_shape_revision path preserves prior topology/UV and changes Y; original fin anchors and polygons predate 052. Therefore 052 inherited detached fins rather than demonstrating that head narrowing caused them.
5. **Repeatable reproduction — YES.** Native inputs are hash identified; arapaima station intersection script is saved; shark diagnostic includes rest band indices, boundary samples and animation rows. Reproduction is native Blender Swim only. Four Godot runtime actions have not been checked for anatomical contact and must not be claimed as checked.

## Constraints on subsequent phases

- Compare literature quantities at corresponding landmarks and axes. HDOr is a provisional but substantial mismatch: 17.29 versus a derived 10.31 cm scenario; the neighboring tested stations remain high. This is not the same uncertainty as trunk width: there is currently no aligned measured trunk-width target. Do not describe global 36.32 cm model width as a measured biological overage against opercular/shoulder width.
- Cross-study SL/TL conversion, size extrapolation and interpreted source-image stations must remain visible in reports. Ratios of group means are scenarios, not an exact individual specimen or universal species constraint.
- Follow-up evidence checked: shark diagnosis now persists tail coverage percentages (43.21% / 48.40%), pixel counts, source/profile hashes, alpha threshold and restricted regions. The unsupported upper-root-no-overlap claim has been explicitly withdrawn after boundary sampling. Source alpha remains generated artwork, not independent biological ground truth.
- Fin pass criteria must assess the proximal attachment boundary/strip and animation contact; a single touching vertex or bone head is insufficient. Tail anatomy also needs lobe outline, shared peduncle and movement review; mere root contact is insufficient.
- Subsequent validation must produce numerical anatomical comparisons/contact results plus clay and actual runtime orbit/action review. Envelopes and closed meshes alone cannot justify acceptance.

No fixes made by this reviewer.
