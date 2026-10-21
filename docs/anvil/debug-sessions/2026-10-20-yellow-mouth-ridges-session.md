# Yellow mouth 093: new transverse ridges

Mode: Normal; actual Godot capture and runtime reports available. Date:2026-10-20.

## Evidence

Baseline `yellow-mouth-093/baseline/oblique-grey.png` is smooth. Candidate `candidate/oblique-grey.png` has new transverse ridges. Texture color streaks and geometry/normal ridges are separate. Frozen candidate09363e7d has passed body21 and motion21; these gates do not establish visual quality. The lead explicitly rejects calling these ridges pre-existing.

## Investigation gate

Compare unchanged-position/raw normal data, deformed triangle normals and finite-difference Jacobian normals. No final repair before root-cause evidence. Recalculated-normal versus geometry-smoothing alternatives are hypotheses, not established causes. Implementation agent investigates; lead performs adversarial phase review. Production game is unchanged.

## Investigation result / completed trial

The independent reviewer rejected NORMAL-only and bounded sigma diagnostic proposals; neither was applied. No final Phase4 fix was performed. The trial ended with an explicit failed visual result, not a resolved bug or accepted fish. See fish `yellow-mouth-093/debug-normal-review.validation.json` for phase/checklist evidence.

Actual section trace: preoral400sample bound error is small (.038px max upper); stair-step source targets still contribute. In oral region estimated upper bound misses actual skin by up to7.317px;102 stations put high below upper-cleft threshold. The max(...,1e-5) denominator hides wrong anchor ordering; identity control still changes y by1.145px. Old normal/position assumptions are therefore not a safe production mapping. Bounded sigma changes stay within2px of prior target but do not remove visible ridges; this does not exclude alpha contribution.

Current trial retains lower-jaw/source improvements but has new head ridges and a shallow planar oral interior. Production is unchanged. Model09363e7d passed490 roots/membranes, body21 and motion21, while visual acceptance is rejected. Next engineering effort must establish correct actual rim/section anchors and local oral topology before any further deformation; no further parameter guesses or acceptance claim.
