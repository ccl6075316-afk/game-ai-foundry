# Blacktip feeding reference, accepted2026-11-15

Current source/model and explicit replay are frozen in `projects/fishing-2d/plans/reviews/blacktip-feeding-20261115`; see its HANDOFF and Foundry `resources/volume-fish/blacktip-feeding-20261115/release.json` for hashes, validation and remaining scope. Canonical source/model installed, ordinary four-action runtime retained; no automatic feeding trigger or other-species rollout.

`FeedingMotion.gd` and `motion.json` are the accepted species-local R5 controls. `motion_math.py` is the Blender evaluator used in local diagnostics. Bone names, rest axes, gains and delays belong to this species; the stage/blend method is reusable, not its acceptance.

`build_feeding_preview.py` retains the historical parameterized cavity/head/floor authoring method, not a required reconstruction chain for the released asset. Maintenance starts from the current editable source. Historical local diagnostic/capture copies expect their documented work layout; use the versioned game handoff's standalone entry for supported replay.

One inner oral face's loop normals were corrected during acceptance, with unchanged non-normal face-corner streams and independent cold export equality. Formal490/072/077, actual147pose feeding root/full-fin and36canonical checks passed; full anatomical/style SOP stages remain pending. No tearing/swallowing simulation.
