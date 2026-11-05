# 真鲷/黑鲷成品钓鱼接入 · Debug session

Mode: Normal. Date: 2026-11-05, Asia/Shanghai. Current phase: 1, awaiting independent adversarial review. No production fix has been written. User authorized the two body repairs and their usable game delivery; no unrelated fish routing is in scope.

## Evidence inventory

- Actual canonical Godot 4.7.1 Mono headless process, native runtime scripts, unchanged canonical models. Local DOTNET_ROOT set to the existing toolchain. Not a mocked unit test.
- `projects/fishing-2d/experiments/top-body-repair-20261105/root-review/diagnose-bream-fishing.gd` created before any production fix.
- `bream-fishing-baseline.validation.json` and full `bream-fishing-baseline.log` beside that script: piranha configure/ready true; red_seabream and black_seabream false, exit 1.
- Complete stack traces read. Both failures enter `FishingVolumeFish.gd:41`, load a cached imported PackedScene, then fail on retired `final172/red_seabream/old-native-animation.res` or `final171/black_seabream/old-native-animation.res`; `instantiate` is called on null.
- Both breams have current canonical packed exports whose actual mesh owner is `Anal_mesh`. The later fishing fallback only recognizes body-named meshes, and its bream controller paths still point to deleted `review_candidates/<species>/FoundryFishMotion.gd`. Those are statically confirmed subsequent incompatibilities, not yet reached runtime failures.

## Phase 1: root cause investigation

The accepted width-batch models were finalized and history retired, but the fishing entry only routes the later eleven-fish table through its final source-owned loader, motion profile/controller selection and explicit packed upper-lip recipe. Width-batch breams fall through to the pre-finalization PackedScene/controller/body-name path. This consumes stale imported animation dependencies before it can use the new packed source. A null check would hide the failure; restoring retired animations/controllers would restore the wrong dependency chain.

Data flow: configure(species) → eleven.matches_path false for the two width-batch species → legacy PackedScene load → old cached scene references retired animation resource → missing dependency/null scene. The finalized width helper already has current model SHA, direct GLTF loader and canonical motion bindings used by the aquarium entry. Current ordinary-body fallback also cannot select the packed `Anal_mesh` upper lip, so simply reimporting the cached scene does not establish the complete current contract.

Recent changes examined: game commits d9238cbc (eleven-fish release/retirement), e0f6c146 (six-fish release/retirement), d5904362 (five-fish release), and current full runtime/helper source. The new eleven route was added, while the width-batch route was not added to fishing. No canonical model/source has been changed by this investigation.

Reproduction: run the recorded one-off script with the actual game `--headless`, plus its absolute output JSON argument. It loads current piranha and the two breams without changing files or bypassing model guards. Baseline result is saved, rather than inferred from source code.

## Phase gates

The user requested exactly three working agents; an existing independent agent will review each phase, without spawning a fourth worker. Reviewer may veto. Phase 2/3/4 remain pending, strike count 0. This session is not fish shape acceptance or a current repaired-model validation.

### Phase 1 independent verdict

`bass_croaker_zander`: APPROVED Q1–Q5. Independently read the complete runtime/helper and relevant e0f6c146/d9238cbc diffs, and reproduced the same actual canonical failure. Independent receipt: `group-b/bream-fishing-independent-baseline.validation.json`. The reviewer confirmed missing finalized routing is the source; stale-cache failure is only its first symptom. No production fix yet.

## Phase 2: pattern comparison (awaiting review)

Working patterns read in full: the eleven-fish fishing branch and `FinalizedElevenFish20261105.gd`; current aquarium `VolumeFishExhibit._add_fish` and `FinalizedWidthBatch20261101.gd`. The baseline piranha is a live successful packed example, and the width helper is the existing source-owned bream aquarium path. Differences:

| Contract | Eleven fishing / width aquarium | Bream fishing fallthrough |
|---|---|---|
| Model | Canonical SHA guard, direct GLTFDocument | Stale imported PackedScene with retired extracted animation dependency |
| Profile/controller | Table-bound current files, dependency SHA | General motion.json plus deleted bream review_candidates controller |
| Packed body socket | Explicit body-owned actual upper-lip recipe | Mesh-name/max-X fallback cannot own packed Anal_mesh |
| Materials | Embedded reviewed material; nearest binding | Legacy cloning branch |
| Scale | Reviewed source bounds / model scale | Full imported-scene bounds |

Dependencies verified: local engine and .NET work because the piranha control succeeds; both canonical bream model/source files exist and retain release SHA; width motion profiles and FoundryFishMotion.gd exist. A current GLB is self-contained. Red/black packed body and oral roles are explicit, so an actual shared upper-roof/skin lip can be identified and independently checked in a fresh process. Any socket ambiguity must fail rather than use a forehead extremum.

Bounded design for review: only width-table rows explicitly furnished with a reviewed mouth recipe enter a complete finalized-width fishing route. Keep canonical SHA, profile/controller and recipe hashes enforced; use the existing width loader/profile/controller, embedded materials and verified socket. Do not modify fish not opting into that record, restore old resources, relax guards, or add a runtime static builder. This is one routing fix, not a general fish renderer rewrite. Production implementation waits for phase 2 and 3 approvals.

### Phase 2 independent verdict

`bass_croaker_zander`: APPROVED Q1–Q4 after reading both complete patterns and the actual entry. Added test obligations: actual FishSurfaceOwnership packed inventory, one skeleton/player, reviewed scale and controller/carrier ownership; check non-opt-in behavior and bad recipe fail-closed. No production change yet.

## Phase 3: hypothesis and actual tests (awaiting review)

Hypothesis: both current canonical bream GLBs are self-contained and usable through their existing source-owned width contract; fishing fails because it selects the pre-finalization contract. Directly using the current width loader and bindings, without restoring any retired resource or changing models, should succeed. A missing/invalid source GLB, missing engine/.NET runtime or broken current motion profile would also fail this independent contract test.

Test `root-review/probe-finalized-width-contract.gd` assembles only existing current methods in an actual fresh Godot process: guarded width loader, actual FishSurfaceOwnership.apply, canonical width motion profile/controller, current skeleton/player, existing FishingVolumeFish socket identity and skin/hook methods. No FishingVolumeFish or helper production implementation was edited. The same two canonical SHA-bound GLBs from the failing baseline passed 22 checks, exit 0, no stderr: source load, packed inventory with zero builders, one skeleton/player, motion configure, actual imported fixed lip identity, four real skin poses and hook placement. Evidence: `bream-existing-width-contract.validation.json` and full log.

The minimal differing load operation eliminates the retired-resource error while retaining the original GLB bytes. Full existing-contract assembly establishes that subsequent motion/socket support exists without reviving legacy resources. Original failure test remains false/false for the breams because production routing remains unchanged.

Regression baseline also captured all 24 canonical fish through the unchanged real FishingVolumeFish.configure in `all-canonical-fishing-baseline.validation.json`: eleven current finalized-eleven fish succeed; thirteen preexisting non-eleven entries fail. These are baseline facts, not regressions created by this repair. The bounded fix must improve only the two opt-in breams and preserve every other baseline result; scope does not authorize repairing the remaining unrelated old entries. Phase 4 must include wrong-model/recipe rejection and compare the complete before/after snapshot. Strike count remains 0.

### Phase 3 independent verdict

`bass_croaker_zander`: APPROVED Q1–Q5, independently reran the actual existing-contract probe, true/22, exit 0, no stderr. Separate independent receipt saved. The actual upper-lip side point is identified and its nonzero lateral offset is retained; it is not relabeled a central vertex.

## Phase 4 trial 1 and return to investigation

The bounded routing trial was written after the failing test and all three approvals. It failed to parse before any actor setup because the appended width helper methods used spaces in an otherwise tab-indented GDScript file. Direct `--check-only --script FinalizedWidthBatch20261101.gd` reports the exact mixed-indentation parse error at line 63 (the engine returns exit 0 despite logging this parse failure, so logs must be checked).

Strike count: 1. This is an implementation formatting error; no original model/loading hypothesis was disproved. Both production runtime files were immediately restored byte-for-byte to pre-task HEAD, while the trial is saved under `root-review/staged-runtime/`. Canonical source/model files remain unchanged. New recipe data only adds unused fields to the old width table until the reviewed route is active. Other agents must not be blocked by the failed parser trial.

Re-entry phase 1: the helper parse log directly identifies mixed leading spaces/tabs, which prevents the width script and therefore Fishing script from loading. Re-entry phase 2: the entire existing width helper uses tabs; the new Fishing file uses spaces consistently with its own file. Re-entry phase 3: direct engine check-only is the minimal failing test, and changing only leading indentation in the appended helper block is the falsifiable correction. No routing logic or source asset should change. Await independent approval of these three re-entry findings before correcting the isolated trial.

### Re-entry verdict and phase 4 trial 2

Independent reviewer `bass_croaker_zander` APPROVED each re-entry phase 1/2/3, after checking the staged file's actual indentation, the direct parser log and the restored production bytes. Only leading indentation in the staged appended helper block was changed to tabs; a proof confirms every line's nonwhitespace logic is unchanged.

Both staged runtime scripts then passed real Godot `--check-only` with explicit error-log rejection. A separate minimal project mirrors actual scripts/assets but overrides the two staged scripts and copies only test metadata; production runtime stays restored throughout the tests. Actual FishingVolumeFish.configure passed both breams and piranha control. Four negative cases, each in a fresh process, rejected the red bream while black bream and piranha still succeeded: wrong model SHA, wrong recipe SHA, changed native lip UV despite an updated recipe hash, and a fin/non-body vertex index. No fallbacks or parse/null errors were accepted. Receipt: `bream-route-isolated-test-suite.validation.json`.

After that isolated success, the two reviewed staged scripts were installed. New actual canonical process passed 34 checks via the real Fishing entry: configuration, exact imported packed upper-lip identity, canonical controller, reviewed scale, one rig/player, no static builders, Swim/Turn/Ascend/Dive, fishing-owned carrier transform, unchanged static arrays and actual hook placement. Receipt: `bream-route-canonical.validation.json`, no stderr, exit 0.

Full 24-species actual configure regression changed exactly black_seabream/red_seabream from false to true; the other 22 results match baseline. The eleven preexisting out-of-scope old-entry failures remain recorded, not declared passing. Scoped regression receipt: `bream-route-regression.validation.json`. Current exact five runtime/data files are bound in `bream-route-files.validation.json`; no source/model was replaced by this routing fix. Strike count is 1 total, trial 2 successful. Final independent phase 4 review and knowledge capture remain pending. New repaired bream model bytes will require a later binding update and fresh cold-entry check, not inherit this baseline-model pass.

### Final phase 4 independent verdict

`bass_croaker_zander`: APPROVED Q1–Q6. Fully inspected both production diffs and the actual positive/negative/regression receipts, confirmed no static model builder or guard bypass, and explicitly limited approval to the current baseline two-model route. All four original phase gates, the three re-entry gates and final implementation gate approved. No commit/push performed. Knowledge captured in `docs/anvil/knowledge/2026-11-05-bream-finalized-fishing-route.md`. Runtime repair is verified for these baseline model bytes; nine-fish geometry repair remains in progress and will require fresh canonical validation after final installation.

本轮收尾：完成调试的fishing-route-game/staged-runtime隔离夹具已按清单退休，仅保留实际输入SHA、正负例结论及生产实现；不是可重放旧模型证据。该调试时的canonical为身体返修前版本，后续新模型实际入口读fish-shape-repair-20261105正式记录。
