# Preserved constant oral material · 2026-11-06

Normal mode. Scope: existing accepted blacktip oral cavity material preservation;
no model repaint, new texture, mouth reconstruction or reduced protected domain.

## Phase 1 · evidence and root cause

Actual original canonical GLB and current R23 both consistently raise
`ValueError: Missing native base-colour image` through `extract_chart → append →
_material`. Reproduction/complete traceback is in the local root-review
`constant-oral-before.validation.json`; Peacock's textured body/oral chart works.
The resolver was introduced by `8de6b4bb`, and unconditionally requires a
baseColorTexture even for an accepted constant-colour oral primitive.

Both actual blacktip models have material3 `Source oral shadow / cavity only`,
doubleSided=true, baseColorFactor=[.03500000014901161,.03099999949336052,
.02800000086426735,1], metallicFactor=0, roughnessFactor=.5, with no texture.
The only serialized difference is the new export's explicit alphaMode=OPAQUE;
the original omits that standard effective default. The missing image originates
in the valid accepted original material, not the repair and not a failed bake.
The bug is confusing native texture ownership with preservation of every valid
accepted material representation. Protected geometry/UV/roles/rim, release and
source binding remain independently required.

Phase1 independent adversarial review: APPROVED, all Q1–Q5, by
bass_croaker_zander; independently read both real materials, traceback, entry
and introducing commit. Existing worker preserves the user's three-agent limit.

## Phase 2 · working patterns and bounded change

The complete current resolver preserves all texture/image/sampler/material
properties for textured charts; actual Peacock and arapaima are working controls.
The maintained `portable/validate_standalone_body.py` material branch already
accepts an opaque constant baseColorFactor, treats omitted alphaMode as OPAQUE,
and checks alpha=1. Blacktip's actual original/current077 also passed that model.
Unlike the textured cases, the actual accepted blacktip oral primitive has no
image to resolve, an explicit finite four-component colour and opaque alpha.

Pass the already-derived body/oral role into the material resolver. Only an
oral primitive with an explicit valid opaque constant RGBA may lack the texture;
body skin still requires its original image. Preserve the entire actual
constant material dictionary and canonicalize only its omitted OPAQUE default.
Old/new exact signatures, full protected geometry/UV/roles/rim, accepted release
and source-image binding still apply, so changing a textured mouth into a solid
colour is not preservation. No artificial image, skipped oral face, caller
whitelist or relaxed colour tolerance. Numpy/Pillow and all layout dependencies
are unchanged; this is only support for the actual accepted representation.

Phase2 independent adversarial review: APPROVED, Q1–Q4, by the independent
worker. Further actual comparison found all five materials differ only by the
OPAQUE key presence. Preserve raw snapshot dictionaries for compatibility;
normalize that one effective default only when comparing old/new signatures.
MASK/BLEND remain distinct. This amendment was independently APPROVED.

Constant oral has 216 original versus 242 new drawing rows, but exactly the
same 59 position/UV/skin semantic points and all88 oriented faces. Both
textured body/lip parts preserve their raw rows/indices/UV. Only this newly
supported constant-oral case will losslessly coalesce drawing aliases with
exact same position, UV and actual named FLOAT weights within each chart,
retaining complete raw-to-semantic maps and every oriented face. Old/new
constant points additionally compare actual Godot UNORM16 storage bins; this
is not a claim that glTF WEIGHTS_0 is UNORM16 or raw FLOAT bytes are unchanged.
Actual glTF type is5126; within-model ambiguous FLOAT groups=0, cross-model
FLOAT differences occur at2 of59 points while all runtime bins agree.
Independent review APPROVED this bounded alias amendment with the exact-FLOAT
within-model condition. Textured charts and distinct UV/skin aliases are not
coalesced.

## Phase 3 · falsifiable test before implementation

Hypothesis: the image-only representation assumption rejects an unchanged
accepted constant cavity; representing that oral chart losslessly and comparing
effective OPAQUE defaults admits actual preservation while rejecting recolour,
texture replacement, missing body images, transparency and changed face/skin
identity. No source model change is needed.

`cli/test_volume_native_chart_material.py` existed and ran BEFORE any checker
fix:9 tests,4 failures/2 errors, including the positive unchanged constant case
failing at the original Missing-image guard. A fully textured control using the
same closed body/cavity and complete fixture rim passes20 protected faces
(fixture rim upper1/lower1/commissure2). The actual real old/current blacktip
one-variable in-memory constant-material probe admits extraction and independently
finds the same complete rim upper2/lower2/24 geometric side edges, all634
anterior faces. No model, baseline or checker was patched for that probe.

Real old/current raw/semantic census: total anterior raw799/825; semantic642/642;
constant oral59/59, exact position/UV set difference0 and runtime skin-bin
difference0. Original/current all1730 oriented UV face-corner multiplicities
agree (A worker independently measured); oral88 and lip104 also retain actual
position+UV corners. Aliases do not explain any lost triangle or changed donor.

Negative tests use an honest new model identity and the full preservation
checker, not a stale-hash rejection: changed RGB, textured-to-same-colour solid,
BLEND/culling, missing body image, alpha/NaN/range errors, and different actual
FLOAT alias weights even when they land in the same runtime bin.

Phase3 independent adversarial review: APPROVED, all five questions, by B and
independently A. A's fresh pre-patch9-test rerun recorded3 failures/2 errors
after the culling assertion was separated; the initial local9-test run was
4 failures/2 errors. Both show the intended positive constant case failing at
the original image guard. The later draw-alias count is explicitly a second
representation-layer obstruction, not attributed to that single guard alone.

## Phase 4 · implementation and verification

One bounded representation extension in `volume_native_chart_preservation.py`:
only explicit opaque constant oral materials may omit their base image;
textured/body requirements remain. Exact FLOAT skin/position/UV aliases within
that constant oral primitive coalesce losslessly, with complete original row
maps and every oriented triangle retained. Cross-export runtime bins additionally
match; no claim of identical source FLOAT bytes. Comparing signatures handles
only absent/explicit OPAQUE equivalence, preserving all other fields.

9 new tests and37 existing SOP/packed tests pass (46 total). Real R24 complete
native preservation passes1730 faces/1215 semantic chart rows and full28-edge
rim (2 upper,2 lower,24 geometric side edges). Three actual GLB negatives have
honestly updated model SHA and are rejected for changed oral RGB, missing body
image and dropped oral face, rather than a stale-hash shortcut. Their6,050,380
temporary bytes were immediately removed; numerical receipts remain local.
No model, original texture or mouth shape was changed to accommodate validation.

Implementation strikes:1. Phase4 independent review rejected a narrow checker
case: legal near-unit FLOAT weights `[.2,.8] -> [.200008,.8]` preserve raw
truncation bins but Godot first normalizes them, changing the second stored bin
52428 -> 52427. The real engine probe reproduced this; no candidate was changed.

Return to phases1–3: actual engine commit a13da4feb imports four FLOAT slots with
an ordered float32 sum and float32 division, then packs float32*65535 by
uint16 truncation. Primary source: `modules/gltf/gltf_document.cpp`1661–1682
and `servers/rendering/rendering_server.cpp`843–853 at that commit. The proposed
single fix preserves original slot order during normalization/packing; named
sorting happens afterward. Exact source FLOAT alias keys remain unchanged, and
any same-key aliases with different runtime bins are rejected.

Revised phase4 adds that single-variable honest-identity negative and produces
47 passing tests. The expected bins are asserted against the actual engine
probe. Accepted old/current chart runtime fields must be rebuilt before the
final actual-model preservation/SOP check. Independent re-review APPROVED
(A, all six phase4 questions); A independently repeated all47 tests. Matching
engine sources are [glTF normalization](https://github.com/godotengine/godot/blob/a13da4feb/modules/gltf/gltf_document.cpp#L1661)
and [weight packing](https://github.com/godotengine/godot/blob/a13da4feb/servers/rendering/rendering_server.cpp#L843).

Reusable lesson: distinguish source FLOAT equality within a draw-alias set
from engine-imported deformation identity across exports. Never infer the
latter from raw-weight multiplication alone. Preserve original slot order,
actual scalar precision and importer normalization, and prove a boundary case
against the actual runtime. This exception applies only to preserved explicit
opaque constant oral materials; all native body/image/oriented-rim protections
remain mandatory. Models and pixels were not modified by this checker repair.
