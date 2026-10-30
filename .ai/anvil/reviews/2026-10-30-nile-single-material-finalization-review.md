# Review Report: `2026-10-30-nile-single-material-finalization`

## Metadata

| Field | Value |
|---|---|
| Reviewer | Independent `/root/nile_material_review` |
| Scope | R11 editable source, guarded cold export, actual logical-part validation; no production exhibit replacement |
| Baselines | Reviewed R9 source/GLB and measured R10 MASK candidate |
| Status | APPROVED — frozen R11 source/export, actual final gates, operator visuals and SOP bindings |

## 1. Automated Pre-checks

Initial R11 asset is internally consistent with the tested R10 geometry/material candidate: 1465vertices,1710triangles,18bones,1mesh/1surface,2048² nearest atlas. Existing target/cold parity reports show exact POSITION/NORMAL/UV and atlas PNG/RGBA, maximum weight component error1.1920928955078125e-7, exact IBMs and54clip channels; fresh cold-source GLB bytes match the candidate. These records do not substitute for source guard testing, actual Godot part mapping or final fin/body/motion/visual checks.

Read-only reviewer independently compared actual R10 and initial R11 node rest TRS/matrix fields and parent names: all27original named nodes remain identical; one additional non-mesh Empty is present and does not justify rebuilding the asset.

## 2. Security Scan

No secrets, network request or shell interpolation introduced. Current code uses parsed paths and known local tools. Output containment and evidence overwrite/alias findings below must be fixed before approval. No newly installed dependencies or repository-wide CVE claim.

## 3. Karpathy Principles

- Think before coding: source-owned precise UV/NORMAL attributes, ownership and material contracts are explicit; normal export must not read target data.
- Simplicity: retain existing rig/54channels, reconstruct only the measured single mesh and atlas; no new model shape or performance matrix.
- Surgical changes: R9 source and installed production asset remain unchanged; new R11 outputs are isolated.
- Goal driven: exact row/triangle/clip/atlas proof before expensive current-asset tests. Pending guards and actual import evidence prevent early approval.

## 4. Adversarial Review

### 4.1 Design

`build_packed_fish_source.py:27–38,55–75` copies the tested geometry/UV/normal/weights into an editable mesh, with explicit source vertex identities and9nonoverlapping source partitions. Body skin840 and mouth64 must remain one904triangle logical body during validation. `:39–54,83` retains established rig/action and replaces removed mesh objects with editing-only Empty objects without changing the actual single-surface production entry.

`export_packed_fish_source.py:75–120` validates source geometry, normal, UV and ownership hashes; exports source attributes; only compacts rows sharing the **same source vertex identity** after all five final attributes match. It never welds distinct source IDs. Parts derive from actual exported IDs and directed indices, not assumed exporter order. This approach is appropriate; validation helpers must independently prove actual Godot import correspondence and coverage.

### 4.2 Functionality / Findings

| Severity | Original location | Finding | Status |
|---|---|---|---|
| High | Original `material_signature:28–39` | `material.use_nodes` was not signed; texture projection/mute properties were missing. | FIXED: UseNodes and explicit four-node atlas/UV/BSDF/output graph required; mute, image alpha/color interpretation/projection and actual UVMap active/render settings guarded. |
| Medium | Original `build_packed_fish_source.py:24,90` | Fixed build report path lacked existence/input/recipe alias preflight. | FIXED: all resolved output/report paths are fresh and disjoint from recipe/inputs before authoring. |
| Medium | Original `export_packed_fish_source.py:137–138` | Report output was not constrained to artifact roots. | FIXED: source/output/report distinctness, source existence and format, output/report allowed roots/formats and no overwrite all preflighted. |
| High | Original `verify_packed_fish_parity.py:59–68` | Rig parity omitted rest-node transforms/parent hierarchy. | FIXED: all27original named node rest transforms, parent and skin.skeleton/mesh ownership compared; root-translation and parent negatives rejected. Known nonrender/nonrig editor Empty explicitly allowed. |

Negative witness for rest-check gap: using original checker SHA `37685114c77e0d528cbee856e1576596156c48af1ff290de1961bca3cfab45f0` and initial R11 GLB SHA `2ec51a58e8d273910f22cf5414cb4969e92b00827131e829d942ecb15f96e28a`, change only the `root` skin-joint node's translation.x by+.001, retaining all geometry/IBMs/material/clip arrays. `verify(reference_R10, mutated_copy)` incorrectly returned `ok=true`. The temporary copy was reviewer-owned under repository work and automatically removed; original asset was not written. Actual unmodified R11 rest transforms/parents separately match R10, so this is a checker false-negative rather than current asset corruption. Required fix: original named node transforms/parent and skin root/mesh attachment validation; allow the known additional non-mesh Empty only.

### 4.3 Complexity / 4.4 Naming / 4.5 Comments

The export report correctly declares `generated_BIN_unchanged_after_source_binding=false`: final source-row compaction changes generated streams, unlike the older NORMAL-binding-only helper. This prevents a misleading claim that only a single accessor binding changed. “Complete parity” requires the rest/hierarchy fix. A normal export reading only the blend and signature contract is materially different from authoring once from the tested reference; keep that distinction documented.

### 4.6 Style / 4.7 Context

Compact utility style matches this repository. No need to change or delete the extra editing Empty. Do not retarget R9 passing reports to the new R11 hash; final current checks must run against the frozen exported R11 candidate. New source metadata fixes with unchanged GLB bytes require refreshed source/cold proof, not shape rework.

### 4.8 Tests / Expected Actual Proof

Use bounded negative controls for edited source UV/NORMAL/geometry/ownership/material settings and path aliases. Import mapping must consume a complete directed-triangle multiset with seam multiplicity, a single consistent glTF→Godot winding conversion, existing position/UV/normal/skin tolerance and an actual cold engine import. MASK body safety requires all actual body UV texels opaque plus same-pose GPU coverage and a transparent negative, not a vertex-only alpha check. No full GPU or490test launched by this reviewer.

## 5. Source guard and actual-import adapter fix verification

Frozen source is now SHA `98c18cd9f1419eb7ed3b0b215742af97fa6b9437e87658ff305e67a1ee19ae82`; exported GLB remains `2ec51a58e8d273910f22cf5414cb4969e92b00827131e829d942ecb15f96e28a`. The old0775source is retained as a historical snapshot. Read and reviewed14actual Blender guard negatives: material UseNodes/mute/projection/alpha interpretation, actual named/active/render UV maps, geometry, exact normal/UV, part labels, unsupported modifier and CLI report alias/outside-root. Positive cold export with current exporter remains byte identical to frozen GLB; fresh source parity is exact. Both rest-transform and parent negative controls reject, original inputs remain unchanged. No mesh rebuild or new triangle allocation was required by these fixes.

`PackedFishValidation.gd` code reviewed: source manifest/model hash and expected9source partitions/8logical parts are bound; actual imported vertices match by position/UV/normal and bone-name skin weights, with spatial candidate search and seam alternatives. A fixed CCW→CW reversal is used for every imported triangle, with complete directed-triangle multiset consumption and unique logical ownership. Validation-only subsets copy actual imported arrays/material/skin without modifying production arrays. Runtime remains1mesh/1surface. Source body consists of840skin+64oral triangles; all7fins and1710triangles are covered. Position/UV1e-6, normal0.001, and existing16bit-weight quantization tolerance remain distinct from collision thresholds.

Actual import smoke records position/UV error0, maximum normal component0.0000981092 and weight0.0000152290,18bones,7fin tracks,54raw channels resolved, normal Turn behavior and904triangle body probe sharing the actual material/skin. Partition controls accept equivalent source-row reorder and reject one reversed triangle, wrong loop normal and omitted dorsal part. The earlier light smoke refers to helper33713543; later helper118981c9 is the frozen implementation reviewed for the complete final checks. That earlier smoke must remain historical, and current complete gates must bind their actual executed helper hash; this does not justify stopping/repeating the final batch solely for a duplicate light test.

`packed_fish_parts.py` conservatively checks the entire body/mouth UV bounding rectangles, inside the atlas with nearest sampling, for alpha255, rather than sampling only vertices. `validate_standalone_body.py` keeps zero missing pixels, closed-body/winding/skin checks and rejects unsupported material opacity extensions. `capture_standalone_body.gd` uses temporary body-only probes of actual imported arrays/skin/material, compares identical pose/camera to opaque reference and injects a transparent-material negative. Production cold entry remains single-surface, and source scene/geometry is not recreated at runtime. Fin exporter and motion validator use the same proven partition helper without changing old ordinary defaults or fin collar/penetration thresholds.

No new GPU process,490run, asset write or duplicate test was started by this reviewer while the parent executes the frozen final batch. The source helper/path/rest findings are resolved. No further code-style or harmless-Empty work is required.

## 6. Final actual evidence and SOP audit

Final source remains `98c18cd9f1419eb7ed3b0b215742af97fa6b9437e87658ff305e67a1ee19ae82`, GLB `2ec51a58e8d273910f22cf5414cb4969e92b00827131e829d942ecb15f96e28a`. The source-owned single material/mesh export remains1710triangles/1465vertices/18bones; no source shape, bone or native-track reduction was introduced during finalization.

Independent read-only terminal audit completed, without repeating any engine, physical or validation test:

-238artifact-path/SHA references and68current frozen-dependency bindings checked across the complete review, SOP, runtime/cold manifests, production facts and actual gate reports.
-All18candidate roles and every evidence entry bind the same current candidate snapshot. `sop.validation.json` has all9stages passed, no failures and the actual current review hash; dedicated cold report binds the same roles and cites current actual capture, mechanical, motion, source and target-parity proofs.
-Fresh R11 full490 export has current2ecmodel hash and current packed helper/manifest bindings. All7fin roots and membranes have490samples and0failed poses; root-collar0.5mm/free-membrane0.02mm tolerances remain unchanged. Root-completion explicitly reuses current490coverage rather than inventing a second177run. Passing raw490samples were cleaned only after validation; all490removed-path/SHA entries exactly match the retained frozen export manifest.
-Body closure/winding/normalized skin, complete alpha255skin+oral source rectangles and16actual same-pose GPU views pass with0missing pixels; transparent-material negative correctly exposes43467missing pixels. Two logical body partitions are explicitly an analysis/probe view of one actual runtime surface, not a second production assembly.
-Current head-envelope positive passes and controlled needle-class negative remains rejected. Current native loop/mechanical checks and5×96motion controls/four actual transitions pass; actual action snapshots are Turn/Ascend/Dive/Swim with no pending action. These are current R11 reports, not R9passes with replaced model hashes.
-124actual current capture PNG hashes checked. Packed import proof consumes1710triangles and confirms actual runtime1mesh/1surface; body/fin isolation uses temporary actual-array probes and `clear_probes` removes them before full-fish movie/runtime observations. Static arrays/UV/material digest is restored and unchanged; no production shape/UV/color builder runs.
-288frame/24second movie confirmed by ffprobe. Movie-frame manifest remains288entries;23representative originals remain,265deleted originals match the explicit passing cleanup receipt. Native portion records48distinct actual bone-pose hashes. No claim of watching every video frame or mathematical continuous clearance is made.
-Unchanged original-art/style, anatomy and accepted-mouth provenance is explicitly retained as provenance rather than relabeled a current final gate. R11 UV/material addresses are honestly described as packed, not byte-identical R8material objects. R10RGBA8oral quantization and finite near-texel sampling limits remain documented.
-Source-assets and total-assets manifests independently checked:32additional artifact bindings pass after source-only handoff was separately snapshotted. Source-assets SHA at review is `349073c2826c7d83b8ee350ef5cd3de2888b6d298fb3a62afb80777c266200df`.

Independent actual visual review: viewed current R11 `sheets/whole.png`, `mouth.png`, `water.png` and `motion.png`. Original silhouette, accepted block-scale upper lip, oral contrast, tail/fin appearance, actual freshwater readability, native/live action and representative transition poses remain coherent. Existing front-mouth donor/projection banding is a documented inherited limitation, not a newly introduced white-cavity regression or a reason to redo the accepted mouth. Primary operator reviewed all9current sheets. This is operator review; no new whole-fish user approval is inferred.

## 7. Gate Decision

**APPROVED. No unresolved blocking finding.** Source/export and validation adapters are reviewed; current specialized gates, real visual evidence, source/model/recipe bindings and9stageSOP are coherent. Finalization is for the complete standalone GLB/default B entry. Main installed production exhibit is explicitly unchanged. Ordinary Blender File Export equivalence is not claimed; the signed source exporter is the supported reproducible procedure. The1710triangle budget satisfies the user-accepted level, and no normal-game FPS or pureGPU claim is attached to finalization.

No engine,490, GPU or repeated automated check was run by this reviewer during this final audit. Necessary path/material/rest guard findings were fixed; no unrelated modeling or code-style work remains.
