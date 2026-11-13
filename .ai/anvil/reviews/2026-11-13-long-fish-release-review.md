# Review Report: 2026-11-13 long fish material release

| Field | Value |
|---|---|
| Reviewer | Primary agent |
| Scope | Hairtail and silver arowana release |
| Status | APPROVED |

## Automated pre-checks

Both Git diffs pass whitespace checks and the Python authoring files parse. The retained cold export command independently produced both installed GLBs byte for byte. The actual game passed 74 first-load, cached, movement and fishing checks. Each model passed the complete 490 fin pose set, 072, and both poses of the 077 GPU body gate. Each fish passed 480 control comparisons, 360 transition comparisons, and four pixel-identical direct and canonical action pairs.

## Security scan

No changes to network, credential or dependency handling. The cold exporter accepts an explicit local source and a fresh GLB output in the work directory. The release uses the existing Baidu LFS transfer path and retains SHA/size receipts. No credential data is part of the change.

## Adversarial review

- Design and simplicity. The game reads the packed assets through the existing finalizer. The exporter reuses the source contracts already used for each fish.
- Functionality and tests. Material alpha and native mesh, UV, skin and animation arrays match the previous installed fish. The unchanged semantic mouth recipes are rebound to the current GLB hash, and the actual hook placement is exercised. The fin gate covers the full finite basal domains and membrane surfaces at the sampled poses.
- Scope and style. Comparing parsed tables proved that every other species entry stayed byte-equivalent in meaning. The two selected rows change only model and mouth-recipe hashes. Historical bake scripts document an already completed bake and the current cold export has no candidate dependency.
- Evidence limits. Static appearance has the user's acceptance. The runtime SOP passes. Full historical reference-shape, preparation and video criteria remain pending.

## Gate decision

Approved. No critical or high findings. The six staged LFS objects were independently read back before the push.
