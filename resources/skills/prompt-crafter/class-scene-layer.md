# Class: scene layer (plate-first extraction)

The asset has `scene_master`, `scene_box_norm`, and `scene_scale`. The image
generator receives a pixel-exact crop of the complete scene plate as its
reference. This crop is the source of truth for camera, horizon, lighting,
palette, pixel density, and apparent size; it is not a loose style sample.

Describe only the requested element within that crop. Preserve its silhouette
and perspective. A `type: character` layer is an isolated element on pure flat
white, then validated and matted without trimming the canvas (which would lose
its position within the source crop). A `type: background` layer is an
opaque edge-to-edge rectangular band, without white studio margin or matting.
Do not invent a new island, cloud, water texture, or lighting scheme. Do not
zoom or shrink the subject in the generated canvas; `scene_scale` is applied
only at runtime.

When `scene_occludes` is present, keep the real irregular edge from the plate
so the front layer partly covers the named back layer. The authored boxes must
intersect and `scene_z` must put the occluder above its target. Do not create
a flat rectangular overlap or invent new foliage/rocks to fill the seam.

The complete scene plate is created and validated first. If the intended
subject is missing or the crop cuts it off, repair the Brief box or master
plate before generating this layer. A prompt cannot repair wrong source
geometry.
