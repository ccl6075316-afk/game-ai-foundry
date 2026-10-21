# Zander107 eye ownership diagnostic

This is a single-species experimental fork of106. It supports **mode0 identity,
mode1 local RGB trial and mode2 diagnostic** after independent domain review.
The prior0/2 helper/template/profile/config/receipt are archived in
`eye-rollout-107/phase02-freeze`; those are not current mode1 evidence.
It is not a general eye detector or whole-fish acceptance.

## Scope and frozen data

- Only the actual assembled `zander/Closed_body/surface0` material is copied.
  The original body shader/include, old head profile, every uniform and sampler
  binding, GLB, source/fallback decodedRGBA, packed vertex order, all surface
  arrays and all originalLOD tables must match the profile.
- Source cleaning mask and separately traced fallback mask each contain7127
  pixels. The independently reviewed eye-layer alpha mask contains6039 pixels,
  including the upper white and outer black/white rim. Ordinary snout white is
  outside these masks. They are manually reviewed species data.
- RestXY pixel size is independently calibrated in both axes to
  `(1/2024,1/2024)`. AnchorXY is `(.4209895690220033,-.003507364876505719)`;
  source pupil is `(1864.0828877005347,378.09893048128345)`.
- The11 native-pixel downward shift is a **base-through-LOD4 partial diagnostic**.
  It is the integer ceiling of the10.86401554 lower bound using pixel centers,
  corners and edge midpoints. The full6039 footprint has unique bilateral full
  owner preimages and no central-gap hits for those sampled levels.
- Zander's own gap thresholds are `.00422370582818985` forbidden and
  `.009503338113427162` full owner. They are not106's thresholds.

**All six original skinLOD levels and both oralLOD levels remain installed.**
OriginalLOD5 has439 triangles and fails coverage/uniqueness. Every install
receipt retains `lod_geometry_gate.status=failed`. No retirement, rebuilding or
LOD acceptance is installed. Strict107 dynamic body-coverage authorization
binds the current actual material/code/data; unknown shaders remain rejected. Aggregate
primitive counts and requestedLOD pressure do not identify each actual selected
GPU level. Missing geometry is a failure even when no orange diagnostic appears.

## Old cleanup and probes

Mode0 preserves the original old-eye cleanup and samplerRGBA path. Mode1/2
retire exactly one original `source_eye_footprint*(1-source_eye_keep)` term;
the old mouth/rim/secondary code remains. Current unsupported enabled rim-local,
secondary, mouth or auxiliary head-blend assemblies are rejected rather than
silently adapted.

Mode1 replaces only the7127 old-domain RGB using separate source/opaque
native mirrored donor copies from `[1780,335,1808,360)`. Alpha everywhere and
allRGBA outside each respective mask remain exact. The new6039 eye layer
uses original sourceRGB × original sourcealpha × reviewedmask × owner,
preserving tint/COLOR and original lighting. Retired old cleanup adds no
diagnostic color in mode1.

Mode2 colors old source/fallback mask paths green and the new independent
left/right eye domains red/blue. Eye-layer weight is original source alpha ×
reviewed mask × side owner. Orange marks new eye footprint outside full owner;
magenta marks invalid vertex-index/rest/UV lookup. Normal source alpha and all
original shader coverage branches remain; no `ALPHA` or `discard` is added.

`--eye-probe=1|2|3` replaces RGB in all three actual influence routes: source/
fallback sampling, the new eye layer, and the retired old cleanup return path.
`--retired-probe=1|2|3` isolates only that old return path, weighted by the actual
`retired_eye_weight`. It leaves the other diagnostic routes off. This includes
old donor-tinted pixels outside the7127 source mask. Both probe types require
mode2 and cannot be combined. Neither probe changes alpha.

## Files and execution

- Profile: `resources/volume-fish/eye-zander-107.json`.
- Freezer: `resources/scripts/volume-fish/freeze_eye_features_107.py --input PROFILE --output DIRECTORY`.
  It freezes reviewed original/mask data plus separate RGB-only native mirror
  copies, with full-alpha and outside-maskRGBA identity proof.
- Runtime config: `res://assets/models/fish/motion/eye-ownership-107.json`.
- `check_eye_contract.gd`: real candidate0/1/2 installation, both sets ofRGB
  probes, mesh/LOD/source identity and rejected mode/sampler cases.
- `capture_trial.gd OUTPUT --eye-mode=0|1|2 [--eye-probe=N|--retired-probe=N] zander`:
  same47-view Hall/region/camera audit as102, with explicit107 uniforms.
- `capture_eye_diagnostics.gd`: same arguments; two true sides, front, top and
  two obliques, two distances and twoLOD pressure requests, lit/unlit48 images.
  `--baseline-reference` is restricted to mode0 with both probes0 and requires
  absent107 install metadata. Without it the real107 install receipt is
  mandatory. It enables independent original-baseline pressure comparisons.
- `capture_eye_transitions.gd`: same explicit mode/probe arguments;24 images
  across real Swim→Turn→Ascend→Dive→Swim blends. Calls `set_action(false)`
  and step0, then cumulative .25T/.75T/1.01T, asserting actual transition state.
- `capture_eye_audit.gd`: initial read-only current-game inventory and five
  head views; only zander receives complete packed array export.
- `export_pixel_trace.gd`: read-only original game head-top source attribution;
  full arrays go to `/tmp/fish107-pixel-trace.json`.

Actual install/CPU/source evidence is in the target game's
`experiments/blender-fish/eye-rollout-107`. The isolated candidate defaults to mode1; the common helper API defaults to0.
The baseline and formal game remain unchanged. Raw PNG data uses FileAccess
bytes and `Image.load_png_from_buffer`; exported games need explicit rawPNG
include filters. Export execution has not been verified.

## Limits

Mode0 GPU identity and mode2 visual-domain review remain separate required
checks against the current frozen helper/template/config. Prior0/2-stage
approval does not substitute for current mode1 domain/visual/coverage checks. CPU sample coverage does not prove every continuous pixelcell point,
animation pose or GPU-selectedLOD. Seeing an intact lateral eye from above is
not by itself a fault. The new layer must retain complete side rims without
joining across the head and must preserve normal white snout skin.

Full-mask oldUV has269 pixel centers /1147 boundary samples without an old
preimage per side. Pupil/gold measurements are complete and set scale; the
available old-rim subset is not described as a fully mapped original eye.
No whole-fish, fin, head-form or continuous transition acceptance follows
from this diagnostic.
