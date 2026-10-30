# Review Report: 2026-10-30-nile-upper-lip-pixel-clusters

## Final B audit — 2026-10-30

Reviewer: independent `lip_phase_review`. Verdict: **APPROVED for the final standalone B asset and operator SOP review**. This supersedes the historical R8 whole-fish-pending status below. User approval remains limited to the mouth; the production exhibit/canonical fish was not replaced.

Frozen final GLB: `2e947fb4116f3dbdfc9128080efec0907c5cb87a7f4795e0a6f8bb87c8cf859a`. Editable source: `ba78cd884b3f01e79eb68a20aa9fc5df3cdc51dff61a3e6bab4ecb0015ec7591`. Complete model: 1710 triangles, within the 2000 hard limit and above the 1500 preference.

Independent evidence review completed before cleanup: the fresh 490-pose export and all sample/report hashes matched this GLB; all seven complete root and membrane checks passed at unchanged 0.5 mm collar / 0.02 mm penetration tolerance. The two membrane partitions covered every pose exactly once. All 16 actual/reference GPU pairs independently recomputed to zero missing pixels; the transparent negative produced 43,467 missing pixels. Motion receipts bound five cases × 96 phases and actual Turn/Ascend/Dive/Swim snapshots with no pending action. Mechanical checks passed; the head-envelope positive passed and controlled pinched-head negative failed as expected. These remain discrete coverage statements, not continuous collision or biological measurement claims.

Compared R8 and final GLB streams independently: body/mouth, caudal and pelvic geometry/UV/skin arrays are exact; materials, skins, animations and nodes are exact. Reviewed all ten whole/head/mouth/body-only/fin/motion/water/source contact sheets. Pixel-block lips, clean hidden skin, source appearance, complete fins and preserved tail are coherent in these views. Small fin-spine approximation and unknown biological width/thickness remain explicit limitations. All 124 capture hashes and 288 frame hashes matched; native animation had 48 distinct poses. Actual water renderer/shader/preset dependencies were bound, and capture restored the static material-binding digest.

Source-normal helper review initially blocked caller-owned export deletion and reversed-winding false passes. Both were corrected. The verifier now rejects existing-export arguments and input aliases, and removes only its own newly created temporary export. The parity comparator uses same-winding cyclic correspondence. Guard-v2 binds geometry, UV, skin, object/parent transforms, armature rest bindings, modifiers and the source-owned float-normal stream. Geometry, normal-stream, transform, modifier, rest-rig, input-alias and reversed-face negative controls all rejected their mutations. Current cold supported export proves zero NORMAL component error on all seven fins, geometry/UV/skin error at most 1.19e-7, exact embedded image bytes, material bindings and animation samples. **Only the documented guarded FLOAT_VECTOR corner-normal export is approved; ordinary Blender File Export equivalence is not claimed.**

Final ledger audit covered `final-sop/production-review.json`, `sop.validation.json`, `production-data.json`, `runtime-manifest.json` and `final-cold-load.validation.json`: 92 nested artifact path/SHA references checked, with no missing files or mismatches. SOP review hash, candidate roles, all evidence bindings, cold-load bindings and criterion references matched. All nine stages passed the actual CLI evidence-contract check, whose result remains `next_action=human_review` and explicitly grants no asset/user acceptance. Observations agree with the inspected reports and images. Standalone entry scope, authored-atlas provenance, user-mouth-only approval and supported-source-export limitations are explicit.

No unresolved Critical/High findings. No applications, asset edits, 490 reruns, network requests, commit or push were performed by this reviewer. Cleanup remains the primary operator's task: preserve final assets, original inputs, failure evidence, representative images/sheets/video and immutable receipts; record removal of reproducible dense samples separately.

## Metadata
Reviewer: anvil-lead + independent lip_phase_review. Scope: local material candidate. Status: APPROVED for local pending-user-review checkpoint; no commit or formal acceptance requested.

## 1. Automated Pre-checks
Python AST4files; newJSONparsed; gitdiffcheck; oldrasternegative/newrasterpositive;270cellsourcepalette; GLBfiniteattributes/exactgeometryskinning/54animationchannels; nearestOPAQUE/embeddedatlas; coldGLBbeforeafter3views. All affected checks pass. Lint/typechecker: no configured tool for isolatedscripts, syntax and runtime guards used. Unrelated repository-wide tests N/A to thislocalmaterial repair. Fullfishgates remainpending.

## 2. Security Scan
No credentials, network, external dependencies, or dynamic execution inputs introduced. Existing paths stay in explicit repository experiment. No sensitive logging. CLEAN.

## 3. Karpathy Adversarial Principles
ThinkBeforeCoding: traced R7profile source, independentPhase1–3 approval beforefix. Simplicity: reused atlaspacking/apply/viewer. Surgical: only upperliptexture/UV and reviewrouting. GoalDriven: oldactualraster fails,newfield/actualGLB visuallychecked; geometry unchanged.4/4.

## 4. Adversarial Dimension Review
### 4.1 Design
Painter adds2Darc/distance donor cells; staticmaterial stays inBlender/export. No runtimebodyrepair. PASS.
### 4.2 Functionality
paint_nile_upper_lip.py lines24–68: continuous actualjoin and sourcealpha guards; all270donorRGBA checked. Lines104–121: common cellphase acrossUV islands, wholecelltransition. Cold front/side/oblique actualimages checked. PASS.
### 4.3 Complexity
No duplicate modelingchain; existing65islandpacking retained. Reflection bounded tothissourceROI. PASS.
### 4.4 Naming
pixel-clusters and revision8 explicitly identify local experiment. PASS.
### 4.5 Comments
Explain sharedphase,2Ddonor and hostrenderercompatibility. PASS.
### 4.6 Style & Consistency
Existingcompact experimentstyle retained; no unrelated refactor. PASS.
### 4.7 Context
R7 preservednegative; userno-previewinstruction respected; no assetinstall. source5tohost4warnings retained with exactsemantic verification. PASS.
### 4.8 Tests
Independentartifactprobe existedbeforefix; reports bindrealassets, notmetadataonly. Newfieldalone cannotprovevisualnaturalness, so actualcoldviews and userpending explicit. PASS.

## 5. Findings Summary
No unresolvedCritical/High. Independent reviewAPPROVED all4phases. If user rejects cells/joins, returnPhase1 exactview/data, no stackedguesses.

## 6. Gate Decision
APPROVE local revision; finalwholefish/SOP/useracceptance pending. No previewopened, no commit/push.
