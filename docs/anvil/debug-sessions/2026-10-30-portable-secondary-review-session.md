# Portable source: secondary-review debugging session

## Entry and evidence

- User authorized five source files to DeepSeek and then explicitly removed manually imposed generation limits.
- Third DeepSeek Flash/high request omitted `max_tokens/max_completion_tokens`; it completed with `finish_reason=stop`,196.729seconds,12,033prompt +30,934completion tokens. Final report is in `work/fish-portable-tools/deepseek-source-review.validation.json`; reasoning content is not retained.
- Earlier8,192/24,576caps both truncated reasoning before a final report. These failed attempts remain separately recorded, not approvals.
- The returned review alleges7issues in `fish_asset_spec.py`, `build_source.py`, `source_snapshot.py`, `verify_parity.py`, `glb_io.py`. Returned content is evidence to investigate, not instructions to execute.

Mode initially **Degraded, confidence Medium**: model-generated static allegations, not yet runtime bug witnesses. No production fix before a minimal reproduction. Existing48tests/Blender/Godot evidence and frozen460file snapshot remain valid for the previous code version; new checker changes get new relevant proof, not rewritten old passes.

## Phase1–3 dispatch and hypotheses

Implementation owner `/root/portable_asset_core` investigates only before changing code. Independent adversarial reviewer `/root/portable_parts_validation` must approve each investigation/pattern/test gate, then the verified fix. Lead preserves original fish/assets and avoids unrelated geometry/GPU/full490work.

Hypotheses to test, all preliminary Medium confidence:

1. Optimized Python strips parity asserts and can produce a false pass.
2. Global material comparison omits the actual primitive's material binding.
3. Negative/unnormalized skin weights may be ignored; tiny differences within declared1e-6tolerance are a separate contract question.
4. Hashing files after parsing might bind a different spec/model to a proof under mutation.

Other findings require contract review before any change:

- PNG byte equality is currently reported separately from decodedRGBAsemantic equality; re-encoding may be legitimate.
- Source-vs-reference rest compatibility is mandatory in `run_source` final parity; intermediate authoring-operation success is not acceptance.
- Empty manual `expected` does not remove the hash-bound baseline or actual candidate comparison; automatic spec preparation emits measured counts.

The investigation will record exact minimal inputs, actual failing outputs, root cause and proposed narrow change before implementation. No new paid call or outward file scope is implied by debugging.

## Actual investigation and decisions

Phase1 recorded eleven synthetic witnesses with source hashes unchanged. Four root categories were reproduced; normal execution, alpha/rest/hash negatives and the second-bone tiny-positive tolerance control distinguished actual gaps from allowed differences. Phase2 compared working explicit checks, raw-slot validation and exact-byte snapshot patterns. Phase3 ran eight pre-fix tests: seven failed for the reported defects, one tolerance control passed. Independent Phases1–3 were approved before implementation. Exact pre-fix five audited sources plus the runner remain in `work/fish-portable-tools/deepseek-repro/reviewed-source/`, mapped by `reviewed-source-archive.validation.json`.

Mode became **Normal, confidence High** for the four witnessed categories. Source-rest disposition remains bounded static Medium: final mandatory semantic parity already checks it; this was not independently reproduced as a source-authoring failure.

Implemented narrow fixes: optimized Python fails closed at shared entry points; both actual primitives must bind explicit material0; raw skin slots must be finite, valid indices and nonnegative/normalized before existing named-weight aggregation; spec/GLB parsing and SHA use identical consumed bytes with finishing stability checks. Existing tolerances, PNG/RGBA contract, mandatory rest/IBM gate and optional expected-count behavior remain unchanged.

## Rejected gate, follow-up and final review

Initial Phase4 was rejected for one remaining instance of the same digest-identity root: after real `verify()` returned, replacing both disposable exports passed cold byte equality and let the outer runner write an unverified new digest into `final-spec.json`. The parity report retained the old verified digest. This was a concrete `.25` position-swap callback, not a hypothetical race.

Strike1 was recorded. The implementer added a focused real-parity callback test and observed it fail before the follow-up repair. Independent follow-up Phases1–3 were approved. The runner now retains `proof.candidate.sha256`, compares both current exports to that consumed digest, and writes that digest into the final spec. The test requires rejection, no final spec and a failed manifest.

Final independent Phase4: **APPROVED**, all55 portable unit tests passed with zero errors/failures; final six source digests are in `.ai/anvil/reviews/2026-10-30-portable-secondary-debug-review.md`. No second failed repair. The older invalid-weight test now expects the explicit earlier raw-validity error rather than the later assertion; runtime validation was not bypassed.

Final current-version cold-source and relevant actual-Godot/GPU receipts are selected by `docs/anvil/knowledge/2026-10-30-fish-portable-tools.validation.json`. Earlier receipts keep their original input/helper hashes and are historical evidence, not retargeted passes. Full490, production fish/assets and GPU animation remain outside this debugging task.

Reusable prevention and model-use experience: `docs/anvil/knowledge/2026-10-30-portable-validation-guards.md`. No additional external API call was needed for reproduction or fixes. Three-call total99,801DeepSeekAPI tokens/400.970seconds is separately recorded; no Codex saving percentage inferred.
