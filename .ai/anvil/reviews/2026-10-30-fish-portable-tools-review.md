# Review Report: `2026-10-30-fish-portable-tools`

## Metadata

| Field | Value |
|---|---|
| Reviewer | anvil-lead primary operator, implementation delegated by component |
| Date | 2026-10-30 |
| Scope | New portable source/spec/parity, actual part import, discrete body GPU, viewer and evidence tools; existing Nile assets/helpers frozen |
| Status | APPROVED for stated technical tool capabilities |

## 1. Automated Pre-checks

- Final 55 portable unit tests pass, including 13 guard regressions added after the initial 42. Independent debug Phases1–4 are APPROVED; one same-root outer-runner digest omission was rejected, reproduced, repaired and re-reviewed before final approval.
- Six part tests pass, including14 real headless Godot calls: two inventories with normal/winding/count/partition/multiplicity negatives, dangling output-link and existing-directory negatives. The final raw receipt is retained; the dangling target was not created.
- Two actual Blender4.5.3 synthetic source runs:11vertices/9triangles/3bones/2clips and7vertices/5triangles/2bones/1clip. Saved original/authored rig/rest/pose/action/NLA retained; fresh cold-source export bytes equal; current full semantic comparison errors0.
- Post-debug final current-source import/GPU receipt: `work/fish-portable-tools/final-current-validation/validation-report.json`; final runner cold-source receipt: `work/fish-portable-tools/deepseek-final-source-run/validation-report.json`. Their source dependencies match the frozen code. Earlier two-inventory and viewer proofs retain their original version identities.
- Actual final GPU discrete body coverage: two native poses × eight views,0missing pixels; transparent negative4278missing pixels. Same source/actual textureRGBA, pose/camera, current dependencies and probe cleanup bound.
- Actual viewer native and controller smoke, camera controls, declarative capture and nearest contact sheet inspected; report visual review remains pending for biological assets.
- Python syntax, credential-pattern scan, CLI contracts and `git diff --check` checked. No dedicated standalone type-checker/linter configured.
- Opening snapshot confirms460 original code/asset/runtime/SOP-input files unchanged. No current Nile re-export, full490run or36case performance matrix.

## 2. Security Scan

No provider credential/private-key pattern found in new source. Input refs are SHA-bound and resolved inside repository; artifact destinations are fresh descendants of work/output/projects/<project>/experiments. Native subprocesses use argument arrays, not shell interpolation. Configured runtime controller references deliberately execute that local script by its hash; arbitrary untrusted controllers are not sandboxed by this viewer.

The initial optional DeepSeek request was rejected before execution; the user explicitly authorized the five source files. Three Flash/high requests were sent: two manual caps ended in `length` without findings; after the user removed manual generation caps, the provider-default third request ended in `stop` with seven findings. Total99,801API tokens/400.970seconds; no provider cost or measured Codex savings. Four root categories were reproduced and fixed with independent staged review. PNG container identity, intermediate source-rest operation status and optional expected counts were not blindly strengthened. No image/credential payload, reasoning retention or returned-code execution occurred. Current summary: `work/fish-portable-tools/deepseek-review-final.validation.json`; the earlier two-failure summary remains historical. Exact reviewed source bytes were archived before changing code.

## 3. Karpathy Adversarial Principles

| Principle | Assessment |
|---|---|
| Think before coding | Explicit capabilities distinguish same-contract portability from species anatomy, special materials, full077 and490 acceptance |
| Simplicity | Reuse frozen signed exporter; a scoped path-policy adapter restores original predicate in `finally`; no new rendering/animation framework |
| Surgical changes | New namespace preserves existing fish/source/proofs; shared counting/roles/paths replace repeated per-fish source edits |
| Goal driven | Vary counts, body surfaces, part inventories and clips; use real Blender/Godot plus meaningful corruption negatives |

Score4/4.

## 4. Adversarial Dimension Review

### 4.1 Design and 4.2 Functionality

`fish_asset_spec.py` binds actual packed inventory, explicit source-surface ownership, material contract, input hashes and artifact roots. `prepare_spec.py` derives numbers/SHA while retaining actual role/landmark decisions as data. It neither guesses anatomy nor locks new roles to an enum. Body aliases cannot opt out of opacity checks.

`build_source.py` keeps original source rig/rest/actions and writes source-owned exact corner UV/NORMAL and identity/part attributes; layer handles are re-fetched after creation. `export_source.py` adapts only output routing around the frozen exporter; all signatures, row-identity compaction and material guards remain. Unsupported nonidentity source transforms or multiple rigs are rejected rather than silently transported.

`verify_parity.py` preserves1e-6component limits, directed-triangle multiplicity, bone-name weights, rest parent/skin root and IBMs, all native clips/times/values, atlasRGBA and material semantics. `run_source.py` defaults to dry-run; execute stages stop on first failure/timeout, retain logs and manifest, require unchanged source refs and byte-identical initial/cold export before binding the final model.

`parts.py`/`PackedFishParts.gd` support arbitrary explicit inventory and body surfaces; source coverage is complete and mutually exclusive. Actual imported arrays map by POS/UV/NORMAL/named weights and consume every oriented triangle once, including multiplicity. Existing correspondence tolerances are retained; no physical collision tolerance was changed. Probe surfaces copy actual arrays/skin/material and are removed after validation.

`validate_body_gpu.py` recomputes the manifest from actual model/spec ownership; GPU success requires16matching pairs, nonempty reference, alpha255whole-bodyUVrectangles, actual matching donorRGBA, two different rig poses, transparent negative, clean engine logs and unchanged source dependencies. This intentionally does not claim full077 or continuous/controller coverage.

`view.py`/`FishAssetViewer.gd` require an explicit final model or explicitly labeled reference mode, hash-bound controller inputs, configurable camera/scale and matching runtime inventory. The evidence writer never converts inventory success into visual approval. Interactive mode waits for the user; smoke/capture have bounded timeouts.

### 4.3 Complexity / 4.4 Naming / 4.5 Comments

Small CLI modules separate source authoring, immutable-source export, import diagnostics, GPU coverage and evidence inventory. Scope words and limitations prevent generic pass/final-fish confusion. No fabricated passing ledger, new fish profile or animation/GPU implementation was introduced.

### 4.6 Style and 4.7 Context

Old hash-bound files remain intact; new entrypoints and a dedicated SOP avoid invalidating prior receipts. Production skill routing selects new tools before editing old per-fish scripts. Output paths and role declarations remain common configuration rather than another set of species constants. Narrow root Git attributes retain byte-exact new work evidence, the validation index and linked review across checkouts; no model content or old review is rewritten.

### 4.8 Tests and Resolved Findings

| Finding | Resolution and behavioral proof |
|---|---|
| Initial output policy restricted new tools to one test folder | Shared whitelist supports three artifact areas; aliases/ancestors/outside roots rejected; frozen exporter path adapter scoped and restored |
| Body role could opt out via `opaque_uv:false` | Both spec/part inventory reject; auxiliary explicit opacity remains data; negative covers aliases |
| Exit0 plus an old-looking report could conceal Godot errors | Viewer/bodyGPU reject ERROR/SCRIPT ERROR/Parse Error/Assertion failed; negative covers this behavior |
| Default contact-sheet downsampling blurred pixel evidence | NEAREST used; original captures retained |
| Repeated positive joint slots were overwritten in parity dictionaries | Sum by bone name; mass-changing earlier duplicate slot negative rejects |
| Malformed hierarchy could loop ancestor traversal | Cycle/out-of-range hierarchy bounded and rejected |
| Dangling output basename symlink bypassed existing-file check | Reject basename link and existing directory before assigning output path; actual Godot negative proves no target creation |
| An early CPU-only test teardown replaced headless receipt | Receipt writes only when cases exist; final full test re-execution retains all14actual cases; old summary is not used as new raw evidence |
| Optimized Python stripped required assertions | Shared new entry points explicitly reject optimization; optimized verifier and direct parser regressions fail closed |
| Correct global material hid missing/invalid primitive binding | Reference and candidate require explicit integer material0; negative fixtures reject |
| Filtered named weights concealed invalid raw slots | Validate four finite slots, integer in-range joints and nonnegative normalized mass first; small positive second-bone tolerance remains accepted |
| Late file hashes could bind bytes that were never verified | Parse/hash one snapshot, finish against consumed digest; final runner compares both exports to the proof digest and reuses it in finalspec. Real-verifier post-return swap failed before follow-up and rejects after fix |

## 5. Findings Summary

No unresolved blocking finding for the implemented capabilities. Unknown anatomy, unsupported transforms/materials, complete077/root/membrane490adapter and GPU animation are explicit limits, not passing results. The primary also viewed the final post-debug synthetic body coverage/negative contact sheet and the earlier viewer contact sheet; they demonstrate technical paths only.

## 6. Gate Decision

**APPROVED.** Evidence index: `docs/anvil/knowledge/2026-10-30-fish-portable-tools.validation.json`. This approves new tool behavior, not a new fish, biological acceptance, production installation, user whole-fish acceptance, performance capacity or automatic source-animation baking. The user subsequently requested durable handoff, scoped cleanup and commit+push of both relevant repositories; submission follows this approved gate. The unchanged game repository needs synchronization confirmation, not an empty commit.
