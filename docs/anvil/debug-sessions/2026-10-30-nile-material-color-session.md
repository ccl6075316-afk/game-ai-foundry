# Nile single-material mouth color — debug session

Mode: normal; actual Godot 4.7.1 material dump, source arrays and same-view GPU images available. Scope is isolated round10 candidates, not accepted R9 fish.

## Evidence and reproduction

- `round10-material-performance/captures/comparison/rest-head.png`: merged MASK front mouth visibly white while baseline mouth gray; root and independent reviewer identified ~948 changed front pixels, max channel difference132.
- `inspect_material_colors.gd` reads both actual GLTFDocument scenes; `actual-material-colors.validation.json` preserves the runtime material fields and ARRAY_COLOR data.
- Merged material has `vertex_color_use_as_albedo=false`, `albedo_color=(1,1,1,1)`, texture present. Its COLOR_0 array exists (1465 values, white and dark mouth colors), so missing data is not the cause.
- Source oral glTF linear factor is `(0.1882352978,0.1868512183,0.173241064,1)`. Godot baseline material exposes sRGB albedo approximately `(0.47107127,0.46945605,0.45318711,1)`.
- Source model SHA and candidate generation hashes remain recorded; source asset was never written. Repro command is actual Godot headless script against frozen baseline and failed candidate.

## Phase 1: root cause

The combined material samples a white atlas patch and relies on COLOR_0 for the mouth. Actual Godot GLTFDocument import retains vertex colors but does not enable their use as albedo, so the rendered material remains white. This is distinct from the four near-texel-boundary UV probe differences, which are too small and in unrelated coordinates to explain this region.

## Phase 2: working pattern

The baseline's ordinary texture material renders native RGB correctly, and the baseline uniform mouth factor is converted by Godot from glTF linear to sRGB material color. A constant atlas RGB patch encoded from that linear factor can therefore use the same texture path as the rest of the fish, without depending on a per-mesh runtime vertex-color flag. No need to change geometry, motion, sampling or source assets.

## Phase 3: hypothesis and failing test

Hypothesis: a white atlas patch plus ignored COLOR_0 produces the white mouth. Confirmed by actual Godot inspection: vertex array present, material flag false and global albedo white. Runtime dump is the failing behavioral witness before any fix. GPU front still reproduces the user-visible failure.

Proposed single fix: bake textureless constant linear baseColorFactor into an sRGB RGBA8 atlas patch and omit COLOR_0. Current textured source factors are white; reject nonwhite textured factors rather than silently introduce another bake path. Quantization is explicitly reported and checked (at most half an sRGB byte per channel). New candidates must use `candidates-v2`; failed candidates/captures remain immutable.

Independent phase review requested before implementation. Strike count: zero mouth-color fix attempts; earlier uint8 writer mapping failure is separate pre-render implementation scaffolding, not a mouth-color repair.

## Phase approval and implementation

Independent `nile_material_review` approved Phases1/2/3 after actual material dump. It also noted Godot COLOR_ARRAY itself is byte-quantized, so simply toggling the material flag would not establish exact preservation.

A failing automated synthetic-scene test was added before the fix: textureless source `.188/.187/.173` linear must produce known sRGB8 `[120,120,115,255]` even when an importer ignores vertex colors. Old implementation produced `[255,255,255,255]` and failed as expected.

Single fix: textureless baseColorFactor now uses standard piecewise linear→sRGB conversion and nearest RGBA8 encoding in a dedicated padded atlas patch. COLOR_0 is omitted. Nonwhite textured factors are rejected rather than silently generalized. Per-part source linear, target sRGB, quantized bytes, decoded linear and component errors are preserved in the packing report. Body/fin RGB pixels and geometry did not change.

New `candidates-v2` preserves original failed candidates and captures. Six behavior tests pass; actual Nile patch is `[120,120,116,255]`. Builder SHA `9b518e82712c06e3614e344a4d05f1c4aa8dcd3821a5a7902c17389b9f05fb85`; MASK SHA `b8a7794a87803aa0e01fa56a071a6166f9699f5f9bd2199acefb2d60dee16cec`; OPAQUE SHA `ec57d720629f015dd0781584388afb9c45fc959910fddc050900d63f1f1f1c37`.

Verification still pending: root is capturing v2 merged MASK/OPAQUE actual GPU views against the unchanged baseline. Six unit behaviors do not waive this High visual blocker. No formal timing matrix until actual mouth parity is reviewed.

Strike count: fix1 implemented; actual GPU outcome pending. No additional repair attempts made.

## Final actual GPU review — success

Root captured the corrected candidates in captures-v3. Independent nile_material_review actually inspected rest-head/rest-fins/Swim-whole sheets and the complete baseline/MASK rest-head-front pair, and approved the corrected offline-color scope; the white-mouth High was removed. It does not create whole-fish user acceptance. The144currentPNGs andsixsheets remain preserved.

Across48MASKviews,227pixels differ bymorethan1channelunit and122pixels bymorethan8, with isolated maximum158 at nearest pixel edges. OPAQUE differs more broadly (28641pixels above8), confirming cutout dependency. These counts are descriptive, not visual quality percentages. NativeRGBA8 mouth quantization and four diagnostic near-texel-boundaryUV differences remain explicitly limited.

Fix attempts: one verified mouth-color fix. No second or third repair attempt. Controlled performance conclusions are separately recorded in round10 validation-report.json; sourceR9 and prioracceptedmouth were notmodified.
