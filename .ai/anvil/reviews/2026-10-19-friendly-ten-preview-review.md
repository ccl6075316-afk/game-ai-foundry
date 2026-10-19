# Review: 2026-10-19 friendly ten fish preview

Date: 2026-10-19. Scope: isolated presentation trial; no commit or production replacement.

## Decision

APPROVED for preview code and reviewable evidence. Whole-batch fish delivery remains blocked by black seabream's standard full-fin failure. Code approval does not accept that fish.

## Automated checks and independent review

- Python compilation, actual Godot import/parse, GPU shader execution and interactive smoke passed. No implementation-mirroring unit tests added for this art trial.
- Source hashes for all 10 and original GLB hashes for all 23 match. Canonical helpers/config/shader/capture/audit match runtime copies.
- Scoped credential scan clean; no new external transfer or dependency.
- Independent encoding and UI/code reviews approved: `projects/fishing-2d/plans/reviews/083-friendly/083-encoding-review.validation.json` and `083-ui-review.validation.json`.
- Real rendering: 3,840 before/after frames; 10 individual 16-second comparisons; 160-second combined comparison; 16-second ten-fish gallery.

## Principles

Think before coding: ten species have distinct restrained presentation settings, explicitly aesthetic rather than biological measurements. Simplicity: existing sources, models, rigs and palette retained. Surgical changes: runnable isolated project; production unchanged. Goal-driven: actual engine footage and numerical gates accompany the subjective visual proposal.

## Eight review dimensions

| Dimension | Finding |
|---|---|
| Design | Shared `FriendlyFishPresentation.gd` drives capture, audit and interactive preview. Bounded optional affine body scaling avoids repeated configuration compounding. |
| Functionality | Every species selectable; finite replay and normal action controls verified in engine. Pending action is consumed before seeking. Actual manual path plus skin envelope checked. |
| Complexity | Existing fin/body geometry checkers reused. Encoder pads odd gallery height by one pixel; no new geometry kernel or frame resampling workaround. |
| Naming | Presentation parameters distinguish artistic adjustments from anatomy. Reports distinguish authored samples, standard poses and acceptance. |
| Comments | Discrete sampling and regenerated-normal diagnostic limits recorded; no continuous collision-safety claim. |
| Style | Reusable code resides in Foundry resources; isolated runtime copies have matching evidence. No unrelated production changes. |
| Context | Pixel palette retained; no source regeneration, fabricated acceptance or external image transfer. Catfish offset is a visual cue, not bottom navigation. |
| Tests | All 10 root177 and authored33 pass; body integrity passes for23 models/16 views each. Standard490 passes9; black seabream left pectoral fails35 poses, worst0.024176mm penetration against0.020mm tolerance. |

## Limits and remaining issue

Black seabream failure is freshly measured on the current candidate, not waived as an old failure. Its exact checker pose is replayed for the annotated failure image. Custom33 passing cannot replace standard490. Static/native reference and runtime-scaled scopes are documented. Before movement is a controlled comparison path rather than a reproduction of the complete production exhibit.

No Critical/High code findings remain. Model acceptance remains withheld for black seabream. See `projects/fishing-2d/plans/reviews/083-friendly/083-friendly-ten.validation.json` for current evidence and artifact hashes.
