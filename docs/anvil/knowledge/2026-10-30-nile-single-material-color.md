# Single-material fish packing: verify imported color behavior

## Problem and actual evidence

The R9 Nile tilapia has nine materials/surfaces, 1710 triangles, 1465 exported vertices and18bones. An isolated atlas candidate preserved indexed geometry, NORMAL, JOINTS/WEIGHTS, joint/rest data and animation channels, but actual Godot4.7.1 rendered the mouth white. Static GLB value checks alone had missed the displayed regression.

The first candidate used a white atlas patch multiplied by oral COLOR_0. Actual GLTFDocument import retained1465vertex colors yet material.vertex_color_use_as_albedo wasfalse. Array colors were also byte-quantized, so enabling the flag without a measured visual comparison would not establish equivalence. The source oral linear baseColorFactor was approximately(.1882353,.1868512,.1732411), and Godot exposed corresponding sRGB material color approximately(.4710713,.4694560,.4531871).

## Accepted repair method and limits

Bake textureless constant linear factors into a padded sRGB8 atlas patch using the standard piecewise transfer curve, and record the original factor, encoded target, quantized bytes, decoded linear value and error. The actual Nile patch is[120,120,116,255]. The corrected candidate omitsCOLOR_0 entirely, relying on the same ordinary texture path as the source-derived body and fins. Nonwhite textured factors, unknown material extensions and incompatible cull/PBR settings are rejected rather than silently generalized.

The pre-fix behavioral control failed: a synthetic(.188,.187,.173) factor rendered by a vertex-color-ignoring importer would readwhite[255,255,255,255] instead of known encoded[120,120,115,255]. Corrected packing passes six behavioral controls; actual GPU captures-v3 provide the required visual comparison. The near parity remains bounded by sRGB8 constant quantization and float32 UV addressing, not mathematically identical screen pixels.

## Reusable production boundaries

- A one-surface skinned mesh may contain disconnected body/fin islands; one material does not require welding them or losing independent bone movement.
- Preserve original sampled pixels without resizing; crop the actual UV domain, including repeat/clamp behavior for out-of-rangeUV, then pad and pack. Do not clamp a repeated UV domain to0..1.
- Merging source OPAQUE parts with MASK fins requires preserving body opacity in the atlas. Original transparent body texels must not become new body holes under the commonMASK pipeline.
- Geometry/normal/skin/animation equality and exact copied pixels do not prove final rendered appearance. Actual imported material flags, color space and same-pose camera views are necessary.
- Failed original candidates and images remain immutable. New correction candidates have a new directory andSHA. Do not rebind an old captured report to changed assets or scripts.

## Performance measurement status

The geometry remains1710triangles and18bones, so MASKversusOPAQUE is an alpha-mode control withzero added faces. It does not answer whether addingNtriangles to preserve silhouette is cheaper. Nine-to-one surface packing is a separate measured factor. Valid performance numbers must come from the completed adopted matrix and actual draw/primitive counters; no performance gain is inferred in this knowledge record.

macOS minimized/non-drawable windows rejected both window-based partial matrices, even withalways-on-top. A stall is not evidence of model cost; do not keep restoring or stealing the user's windows. The alternative controlled actualOpenGL draw/readback experiment has a different timingdefinition and must not be called regularFPS or pureGPU time. MissingGPU timers remain missing.

Evidence and current state: game `experiments/nile-dorsal-route-trial/round10-material-performance/`, code `resources/scripts/volume-fish/pack_fish_material_atlas.py`, species experimentprofile `resources/volume-fish/nile-tilapia-material-performance-20261030.json`, and debugsession `docs/anvil/debug-sessions/2026-10-30-nile-material-color-session.md`. R9 source/GLB and acceptance remain unchanged; R10isnot a neweditableblend or completefishSOP delivery.
