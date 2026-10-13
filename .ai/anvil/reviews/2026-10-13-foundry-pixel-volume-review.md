# Review Report: 2026-10-13 Foundry pixel fish volume

## Metadata

| Field | Value |
|---|---|
| Reviewer | anvil-lead / root |
| Author | CLI, modeling and game integration doers |
| Scope | Reviewed Foundry pixel source → declarative geometry → skinned GLB → native review → operator acceptance |
| Status | Passed: source, official dual-source volume workflow, visual review and actual Godot integration |

## 1. Automated Pre-checks

Full CLI suite: 670 tests, 668 passed, 2 existing skips, no failures. Evidence: `/tmp/foundry-volume-final-front-gate-tests.log`. New command tests exercise source review/provenance, frozen inputs and shards, stale/failed builds, topology/weights/root movement, original pixel embeddings, nearest/nonmetal materials, optional front source, changed render images and explicit operator acceptance. `git diff --check` passes. Blender single-source smoke output and real GLBs were independently inspected; official two-source shark build/validate/render/accept completed. All four current images plus actual Godot front, both sides and oblique were inspected. The final game GLB hash matches the accepted handoff. Godot Apple M4: 64 GUI/material/bone/lifecycle checks pass, 173 game tests pass; import/runtime contain no errors.

The older test requiring an untracked magic-prince fixture now creates an inline temporary Brief with the same graph assertions; it no longer depends on a private ignored file. Front helper production required an explicit `front` Brief view and deterministic prompt lock, tested without side/three-quarter confusion.

## 2. Security Scan

No new credentials, credential logs or game dependencies. Execution uses a fixed bundled Blender script and argv, without shell interpolation. Declarative profile fields and numeric budgets are allowlisted; arbitrary code/output paths are rejected. Handoff artifact paths and symlink redirection are checked. Image transmission remains in the existing Foundry API path. User explicitly approved the existing configured service for the first image; automatic approval separately requested authorization for the newly derived shark reference. The user then authorized continuation of that specific operation; the frontal generation completed and its source review is accepted.

## 3. Four Principles

- Think before coding: pixel art remains the art direction; volume is geometry and skinning. Source and optional frontal helper must be generated and accepted first. Unseen thickness and movement parameters are authored estimates.
- Simplicity: five concrete commands and bounded fish profiles, using existing handoff/assets/validation state. No additional database, queue, generic plugin runner or new game systems.
- Surgical changes: generic modeling moves to Foundry; game changes are pixel-preserving material settings and review diagnostics. Existing local 038/039 work is preserved.
- Goal-driven: tests reject bypassing source review, hiding unused source PNGs in a GLB, non-nearest/metallic materials, stale acceptance and incorrect frontal source view. Visual comparisons remain a separate actual review.

## 4. Eight Dimensions

1. **Design:** `volume plan/build/validate/render/accept` freezes source, style, resolved asset/shards and profile. Build and render clear old acceptance. Five commands compose with existing image workflow rather than duplicate it.
2. **Functionality:** completed generated source ledger and accepted canonical transparent still required. Optional front source requires paired flags, a frozen front-view Brief and a calibrated projection. Actual GLB pixel identity, materials, skinning, closure and loop are inspected; source files merely existing is insufficient.
3. **Complexity:** species-specific contours and inferred depth are data, not injected Python. Profile templates stay draft until calibrated. The failed single-side nose UV strategy was removed, not hidden behind approval.
4. **Naming:** generation reference and review reference are recorded separately. `front_source` denotes an independently accepted frontal source. `style_visual_review` identifies the operator review state, not an automatic stylistic score or the user's endorsement.
5. **Comments:** explain source projection, fin separation, unsupported glTF mixing, pixel filtering and provenance gates. Reports state limits of single-view inference.
6. **Consistency:** existing JSON response/status enums, source review and state types retained. Front is added to the existing view enum and prompt lock rather than forged as a three-quarter view.
7. **Context:** source resolution is preserved, texture pixels are embedded and checked; nearest and rough diffuse settings preserve authored pixels. Art notes and source/model comparison are documented. No inventory/save behavior is introduced.
8. **Tests:** behavioral fixtures cover refusal and acceptance, actual GLB corruption and changed hashes; image generation is not called by unit tests. The separate final game rendering gate passed after actual native import, GUI checks and visual inspection.

## 5. Findings and Resolution

- Initial procedural shark lacked an approved pixel source: replaced production policy requires Foundry source generation; side art is now generated and accepted, replacement model now accepted by operator visual review and installed.
- Side-only head mapping produced concentric distortions: rejected in visual review. Added optional independently reviewed front source/projection; calibration completed and current output visually reviewed.
- Front input could originally be a side-view Brief: now rejected unless `project.view=front`, tested.
- Old local fixture made a clean checkout fail: moved to inline temporary data while preserving assertions.

No known blocking code finding remains. Final E2E/art gate passed. The operator review records slightly elongated oblique eyes and narrow nose texture bands; hidden geometry and swim amplitude remain authored estimates.

## 6. Gate Decision

**Passed.** Both source workflows completed and their asset reviews are accepted. Official `volume plan → build → validate → render → accept` completed; subsequent validation returns accepted/none. Shark has 18 bones, 10 closed meshes, native 1834×618 and 891×654 textures, 2.0-second imported loop. Godot: 64/64 checks; game regressions: 173/173. Existing silver arowana, piranha and hairtail remain accessible. New temporary probes and extra engine captures moved out of the game; two final engine images and compact evidence remain. This is the command operator's review, not a claim that the user has personally accepted the new appearance. No commit or push was performed.
