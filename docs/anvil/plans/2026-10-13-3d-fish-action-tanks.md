# Plan: 3D fish action tanks (042)

## Architecture

Keep all four accepted game GLBs unchanged. Foundry owns a reusable Godot motion controller plus four declarative calibrated species profiles. Compose the existing calm-swim clip with local body bend and a bounded path/orientation; advance the base AnimationPlayer deterministically before adding pose rotations, never accumulate last-frame overlays. Cache body bone indices, rest-axis conversions and path data. No per-frame source-image/bounds/asset decoding.

Foundry volume motion commands validate existing GLB skin/clip/bone mapping and bounded parameters, pin inputs/profile/runtime hashes in a handoff, generate runtime configuration and the fixed bundled controller. Final acceptance uses actual Godot validation and operator visual review; technical success alone does not certify motion quality. This is existing-model motion production, not new source/geometry generation; retain original model/source provenance including the accepted041 shark handoff and historical original-fish reports.

Godot hall uses one world/viewport, four real tanks/species, one active observation camera, overview and per-tank focus. Independent timelines preserve pause and allow selected action/replay. Calibrate different tank sizes/turn radius/body bend/speed/vertical motion per fish. Expanded conservative posed bounds avoid clipping; paths/tank dimensions evaluated before integration. Turn heading follows path tangent and bone bend has head-to-tail delay; Ascend/Dive loop returns smoothly to its start. Keep all existing navigation/material/lifecycle controls.

## Work Ownership

Runtime/controller and calibrated profiles: motion doer. Hall and GUI: gallery doer. Foundry CLI/provenance/bounded validation/tests: CLI doer. Root plans, coordinates contracts, runs formal CLI and real native Godot QA, reviews all output and cleans temporary probes. Independent review mandatory after implementation.

## Implementation Order

Agree runtime profile and API contract; add bounded motion handoff/commands and runtime helper; configure four tanks/actions; formal generate/copy artifacts; native import and16-combination GUI/pose/containment/continuity checks; inspect rendered actions from side/top/oblique; fix concrete issues; record operator acceptance and knowledge. Preserve all prior uncommitted work; no commit/push in this request.
