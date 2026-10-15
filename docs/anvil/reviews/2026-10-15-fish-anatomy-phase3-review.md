# 053 Fish anatomy — Phase 3 adversarial review

Date: 2026-10-15. Independent reviewer: anatomy_phase_review.

**Verdict: APPROVED to begin isolated implementation.** This approves the falsifiable hypotheses and baseline reproduction; it does not establish absolute anatomical targets or approve the proposed appearance.

## Checklist

1. **Specific/falsifiable — YES.** Y-only revision predicts unchanged eye-plane Z; independent fin placement predicts a physical root gap; too-small tail polygons predict missing source silhouette. These are separately measurable. Median girth provides a conditional torso scenario, not a claim about a proven global width.
2. **Tests exercise the causes — YES.** Independently ran check_053_regressions.py against hash-matched native inputs: 4 FAIL / 1 PASS, exit 1. HDOr is 9.556% provisional SL versus the source observed maximum 8.2%; the paired boundary test reports maximum exterior distances 3.269 cm and 3.768 cm; all 18 native poses fail contact; accepted-source tail retention is 43.21% / 48.40%. These would not pass merely because meshes are closed or inside a runtime envelope.
3. **Minimal/separate — YES.** Each test addresses one constraint, with no geometry/model changes performed by this reviewer. Shared report loading is not a bundled physical intervention. Implementation must preserve this separation when testing vertical head correction, root attachment and tail reconstruction.
4. **Alternatives considered — YES.** Native spatial gaps exclude camera and alpha explanations for detached fins; polygons nearly wholly inside opaque source exclude missing-opacity sampling as the cause of lost tail silhouette; unchanged Z rules out width-only changes as a correction to eye-plane height. Unknown mouth width remains explicitly unknown.
5. **No piling assumptions after an unconfirmed test — YES.** Baseline outcomes agree with stated predictions. Cross-study and station uncertainty are retained instead of silently converting the scenarios into biological truth.

## Limits required for final verification

- Preserve these baseline reports/tests and regenerate diagnostics for changed models. Current tests name 052 and therefore cannot prove a 053 candidate passed until explicitly parameterized or supplied candidate-specific measured data. Native hashes guard geometry freshness, but the tail test currently does not check the recorded profile hash: candidate outline comparisons must also bind the profile/actual geometry used.
- A root band defined as t<=.05 is a production attachment region, not an anatomical standard. Its maximum-distance test is conservative and cannot distinguish every legitimate exposed proximal membrane from a faulty gap. Use the actual attachment seam/boundary for final posed checks; retain sampled coverage, not only a single nearest point.
- Ninety-five percent retention checks source-fidelity only. Tail correctness also requires real-reference lobe/peduncle review and coordinated motion. Do not meet retention by adding a broad opaque panel that ruins the tail.
- Median circumference result (95.356 cm, inferred transverse widths about 28.2–28.7 cm with Z held fixed) is a conditional comparison at sensitivity stations, not a measured straight width. The illustrated DM station is not exactly registered, and constant girth across these stations is not an established species contour. Report observed and target scenario separately after any slimming.
- Mouth rounding has no quantitative biological target in current evidence. It needs independently viewed real closed-mouth references and whole-model comparison, not an invented centimeter requirement. Passing HDOr does not validate mouth shape.
- Native Swim tests do not replace four actual Godot action contact checks and orbit/clay review. Final conclusions must distinguish technical pass, numerical scenario pass, and pending visual/anatomical review.

No fixes made.
