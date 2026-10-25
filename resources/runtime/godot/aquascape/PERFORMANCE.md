# Fish appearance startup cache

`FishRuntimeData.gd` and `FishAppearanceCache.gd` are reusable Godot runtime
helpers. Deploy both to `res://scripts/aquarium/` together with the active
appearance helpers. `produce_hall_3d.py` deploys them for the existing hall.
Other exporters using the updated appearance helpers must include
`FishRuntimeData.gd` even if they do not enable prepared templates.

Start one `FishAppearanceCache.begin_entry()` at the top-level gallery or hall
entry. Factories embedded in that scene share the epoch; do not restart it for
every fish or embedded tank. Original source SHA checks are memoized only within
this frozen construction batch. Outside a batch, `FishRuntimeData.sha256()`
still reads current source bytes on each call. Shared JSON values are read-only
inputs; callers needing to edit a profile must duplicate it first.

Prepared templates are recorded only after the original appearance pipeline has
validated the actual source and before animation starts. New instances retain
the original pre-assembly bounds and independently duplicate skeleton nodes,
controllers and material parameters. Read-only mesh/skin/shader/texture data is
shared. No LOD, topology, UV, fin binding, pixel donor or acceptance status changes.

Source-code/config hashes, actual model/donor dependencies and all eye probe modes
invalidate the template. No timestamp-only shortcut or persistent derived-model
cache is used. Inputs changed during a batch need a new epoch or process; Godot's
normal imported-resource lifetime rules still apply. `--gf-uncached-appearance`
replays preparation without template reuse. `FishRuntimeData.clear()` explicitly
clears parsed documents and digest state for standalone investigations.

`FishLoadingReview.gd` measures synchronous construction separately from the
first rendered frame. `--verify-cache` compares current uncached/template output
for geometry, shader text, uniforms and actual texture bytes, then verifies
per-instance state and content-based invalidation. Timings exclude verification
work. `FishCacheReview.gd` verifies review-probe invalidation headlessly. No
performance measurement is a fish anatomy/visual acceptance or full-load FPS gate.

The 2026-10-25 findings and before/after evidence are in the fishing project's
`docs/AQUARIUM-HALL-3D-V1.md` V7 section and
`plans/reviews/aquarium-loading-v7/`. New review output must stay within the
project's designated review directory. Preserve compact measurement/visual
evidence and clean redundant outputs after each experiment.
