> 2026-11-05 历史制作记录退役说明：本批十一鱼已获用户成品接受，旧实验图片、模型、密集数据与候选专用重放链已按授权清理。本页旧路径/命令仅为历史方法记录，不是当前可运行入口或仍存在的图证据。以后从canonical fish.blend修改；当前依赖与保留方法见 `resources/volume-fish/eleven-fish-release-20261105/METHODS.md` 和游戏正式release/history-new-eleven.md。

# Hairtail standalone body adapter, 2026-11-04

This private 077 adapter preserves the upstream closed-body, full opaque donor,
actual GPU paired coverage (16 captures), unchanged pose/camera, source bindings
and transparent-material negative-control checks. Its copied body inspector is
bound to the upstream file SHA; an upstream change requires an explicit audit.

The auxiliary branch accepts only `Hairtail_Ribbon_Body`, the three named hairtail
fins, two `Eye_native_*` closed mixed-skin eyes, and six `Oral_tooth_*` closed
mixed-skin upper-tooth components. Their kinds are
`closed_mixed_skin_eye_lens` and `closed_mixed_skin_upper_tooth`. Every definition
must declare `underlying_body`, and must not claim `rigid_bone`.

Checks cover actual shared body skin, normalized four-influence weights, closed
oriented nondegenerate geometry, normal/winding agreement, OPAQUE materials, and
conservative nearest-pixel coverage of each actual UV triangle. Native texture
may be `baseColorTexture` or the actual `emissiveTexture`; the private GPU capture
records which donor Godot uses and its decoded RGBA hash. No product color,
emission, geometry, UV or material is changed by the checker.

This does **not** establish anatomical tooth count, eye height, attachment or
continuous motion safety. Those require the fish's source, support, motion,
fin and visual evidence. A geometry preflight is not complete 077.

Use the upstream standalone plan schema with the explicit auxiliary kinds above.
For a full check, freeze the absolute adapter path and SHA in `frozen_inputs`.
All outputs must be new directories below the hairtail static-merge experiment.

```powershell
.venv/Scripts/python.exe resources/scripts/volume-fish/hairtail_20261104/validate_body.py --game <game> --godot <godot> --plan <current-plan> --output <new-hairtail-output> --geometry-only
.venv/Scripts/python.exe resources/scripts/volume-fish/hairtail_20261104/validate_body.py --game <game> --godot <godot> --plan <current-plan> --output <new-hairtail-output>
.venv/Scripts/python.exe resources/scripts/volume-fish/hairtail_20261104/test_auxiliary_contract.py
```

Synthetic contract results are in `output/hairtail-adapter-check-20261104/`.
Actual candidate status belongs to the original hairtail README and its current
validation reports; neither this method document nor synthetic tests accept a
fish. The original model is always loaded for GPU capture, with no factory or
diagnostic substitute model.

`exact_finite_contact.py` is a separate read-only fallback for an isolated
triangle pair already found by the complete surface checker. It converts the
supplied binary coordinates to exact rationals, intersects both triangles'
finite edges with the opposite plane, and uses exact triangle containment. Its
coplanar branch clips the actual finite polygons. Only an intersection confined
to the exact shared vertex or edge is exempted; it never increases an epsilon.
Eight controls include proper crossing, coplanar overlap and a positive-area
overlap only `1e-14` units wide. It is not a whole-fin inventory or motion gate.
The caller must first establish one or two shared physical source-vertex IDs
and verify the exact coincident points against that identity. GLB UV/normal
splits can create several render indices for one source vertex: such indices
require an unambiguous position-and-skin mapping to the source, with the full
triangle multiset verified. Distinct source IDs at coincident positions must
not be promoted into a legal topological edge by this coordinate-only predicate.

The original hairtail dorsal pair 194/350 at `Range:FinsOnly`, 12.375 seconds,
was replayed using both reconstructed binary64 points and the actual full Godot
Vector3 binary32 skin export. These are actual imported rig/weight pose arrays,
not GPU buffer readback; the historical diagnostic dataset key saying `GPU` is
corrected by `source-method.validation.json`. Both exact finite intersections
contain only the shared point.
The preceding halfspace test alone could not prove the Godot pair, so that
inconclusive result and the original floating-point failure remain retained.
Inputs, source/matrix/full-export hashes, all supplied points and the exact
result are in the original experiment's
`lowpoly-20261104/shared-contact-diagnostic-20261105/` (no deletions).

```powershell
.venv/Scripts/python.exe resources/scripts/volume-fish/hairtail_20261104/exact_finite_contact.py --input <retained-exact-halfspace.validation.json> --output <new-hairtail-diagnostic.json>
```

This diagnosis changes no geometry and does not waive the separate real
pectoral membrane penetration. The current per-fish review must decide which
unchanged evidence is retained after any actual model repair.
