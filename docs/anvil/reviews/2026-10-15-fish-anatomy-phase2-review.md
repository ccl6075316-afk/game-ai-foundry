# 053 Fish anatomy — Phase 2 adversarial review

Date: 2026-10-15. Independent reviewer: anatomy_phase_review.

**Verdict: APPROVED for pattern analysis → hypothesis/testing.** No model or fix accepted.

## Checklist

1. **Multiple working patterns — YES.** Surface eye patches resolve actual body/head geometry and normal; continuous body rings share adjacent edges and spine weights. They provide separate examples for geometric attachment and continuity. Alpha-aware UV sampling provides a third relevant comparison: sampling correction does not change geometry.
2. **Reference implementation read completely — YES.** Inspected complete eye placement/weight branches, body section interpolation/ring face construction, fin triangulation/anchor/depth/weight construction, UV donor lookup, native revision shifts and source/hash guards. The eye method offsets a small surface patch and is not automatically a complete solution for an extended fin root; this distinction must survive implementation.
3. **Relevant differences enumerated — YES.** Surface-dependent versus independent placement; shared ring edges versus disconnected but closed meshes; body spine weights versus fin/body blends; side silhouette versus paired lateral geometry; geometry versus donor UV; Y-only edits versus unmodified X/Z; body/overlay union versus single mesh; matched local dimensions versus global extrema. Separate upper/lower tail fin bones also matter to posed continuity.
4. **Dependencies/configuration checked — YES.** Native rest mesh, Blender coordinates/aspect, accepted multi-source ownership, UV/topology preservation, root-band identities, native Swim and Godot overlays are distinguished. Eye querying assumes matching target coordinates; current revision's shared mesh/armature coordinates are guarded. Source/profile hashes are recorded. Current biological references do not supply a confirmed maximum trunk width or precise closed-mouth target.

## Requirements for Phase 3

- Test each causal component separately. A fin-root test must fail on 052 and cannot be passed by one buried vertex while the attachment boundary floats.
- A tail silhouette test measures retention of accepted source art, with its own explicit region/alpha threshold. Anatomical lobe/peduncle quality and animated connection still need separate visual evaluation.
- A head test must report provisional landmark ratios and their range/assumptions. A numeric envelope pass must not stand in for literature comparison, mouth shape or anatomy acceptance.
- Any inferred artistic correction without a measured target must be labeled as such and remain reviewable in clay and full runtime motion.

No fixes made.
