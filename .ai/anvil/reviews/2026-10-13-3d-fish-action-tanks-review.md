# Review Report: `2026-10-13-3d-fish-action-tanks`

## Metadata

| Field | Value |
|-------|-------|
| Reviewer | Independent anvil reviewer |
| MR / Commit | Local task 042, uncommitted |
| Author | 3D motion, gallery, and CLI doers |
| Review Date | 2026-10-13 |
| Status | `APPROVED` after formal native GUI, 16-combination and five-view evidence |

---

## 1. Automated Pre-checks

| Check | Command | Result | Notes |
|-------|---------|--------|-------|
| Lint | Project has no mandatory lint command for this mixed Python/GDScript change | N/A | Static review completed. |
| Type Check | Native Godot 4.7.1 runtime and Main integration | PASS | Apple M4 run loads the gallery; `MAIN_3D_INTEGRATION True`. |
| Unit Tests | `/tmp/foundry-motion-full-tests.log` | PASS | 687 run, 685 pass, 2 skip. |
| Game Tests | .NET game suite | PASS | 173/173 passed in the parent review run. |
| Runtime probe | `/tmp/foundry-motion042-tests/results.json` | PASS | All four species and four actions pass its head/path, speed, loop, overlay and bounds assertions. |
| Fresh workflow validation | `motion-validate` on completed handoff | PASS | `ok=true`, `done/human_review`, five technical checks pass; runtime/config/validation hashes remain fixed. |
| Native GUI | `projects/fishing-2d/output/042-3d-fish-action-qa/validation.json` | PASS | 260/260 checks pass for 16 species/action combinations, framing, controls, pause, return, and rendered style. |
| Five-view probe | `/tmp/fishing-042-probes/visual/report.json` | PASS | 36/36 native captures exist across four species, five views and Turn phases; reviewer sampled representative images and parent inspected all 36. |

---

## 2. Security Scan

| Category | Finding | Severity | Status |
|----------|---------|----------|--------|
| Hardcoded Secrets | No credentials in new motion code or profiles. | — | CLEAN |
| Injection Risks | Declarative bounded profiles; fixed bundled GDScript; no script field. `safe_cli` accepts only registered volume subcommands. | — | CLEAN |
| XSS Vulnerabilities | No web surface. | — | N/A |
| Dependency CVEs | No new dependency introduced by task 042. | — | N/A |
| Sensitive Data in Logs | Motion receipts and snapshots contain local asset paths/hashes, not secrets or save data. | — | CLEAN |
| Filesystem bounds | `safe_output` rejects symlink artifacts and escape paths, with regression tests. A local concurrent symlink swap remains a general TOCTOU risk, outside this single-operator workflow. | Low | REVIEWED |

**Security Verdict:** CLEAN for the intended local workflow.

---

## 3. Karpathy Adversarial Principles

| Principle | Adversarial Question | Author's Answer (Explicit or Inferred) | Verdict | Severity |
|-----------|---------------------|----------------------------------------|---------|----------|
| Think Before Coding | Are coordinate, asset and save assumptions explicit? | Four accepted GLBs, skin chain, local tank path, length scale and no save dependency are specified and checked at setup. | PASS | — |
| Simplicity First | Is the controller/provenance split justified? | Fixed controller handles pose; CLI pins four models/profiles/receipts. Each has a distinct required caller. | PASS | — |
| Surgical Changes | Can changes be traced to four actions and gallery? | New motion commands/runtime/profiles and standalone hall serve task 042. Older GLBs are not rewritten. | PASS | — |
| Goal-Driven Execution | Do tests prove rendered user behavior? | Mechanical probes, 260 formal native GUI checks, 16 rendered combinations, 36 five-view/phase captures and Main entry/return checks pass. | PASS | — |

**Karpathy Score:** 4/4.

---

## 4. Adversarial Dimension Review

### 4.1 Design — "Should this exist at all?"

| Line(s) | Question Asked | Author's Answer | Reviewer Assessment | Severity |
|---------|---------------|-----------------|---------------------|----------|
| `cli/volume_motion.py:265-348`; `resources/runtime/godot/VolumeFishMotion.gd:37-96` | Why separate handoff, profile and runtime? | CLI freezes existing models, profile and helper hashes; Godot composes the swim clip with bounded action paths. | Separation matches ownership and prevents model regeneration. | — |
| `VolumeFishExhibit.gd:38-87,165-195` | Is one viewport enough for four physical tanks? | All four tanks share one world/camera; hidden gallery stops rendering and stepping. | Formal native checks confirm four distinct tanks, one viewport and hidden pause at two window sizes. | — |

**Dimension Verdict:** PASS.

### 4.2 Functionality — "What is the author missing?"

| Line(s) | Question Asked | Author's Answer | Reviewer Assessment | Severity |
|---------|---------------|-----------------|---------------------|----------|
| `VolumeFishMotion.gd:61-96,221-271` | Do local bone axes, manual clip and overlay avoid cumulative drift? | Rest-space axes are converted once; prior body pose is restored before each manual advance, then current base pose is captured and overlaid. | Mechanism is coherent; seek/step equality and repeated pose probes pass. | — |
| `VolumeFishMotion.gd:224-288` | Does the fish face its tangent, bend toward the tail, stay inside the skin envelope and keep moving? | Path derivative supplies heading/pitch; delayed per-bone coefficients supply bend; setup computes skin/chain bound; runtime probes cover min speed/containment. | Mechanical probes and all 16 native action captures pass; five-view and Turn-phase inspection shows intact skin and fins. | — |
| `VolumeFishExhibit.gd:231-288,357-445` | Do action/selection, pause/replay, close camera and hidden state work in the actual GUI? | Code queues actions, gates `_process` when paused/hidden, and scales camera by fish length. | Formal native GUI report passes all 260 checks, including these lifecycle cases and two window sizes. | — |

**Key Edge Cases Probed:**
- [x] Empty/null and invalid model/profile input
- [x] Boundaries, maximum model size, nonfinite parameters
- [x] Negative or invalid action values
- [x] External model/evidence/runtime hash changes
- [x] Static symlink and output escape paths
- [x] Actual GUI input and lifecycle across representative window sizes

**Dimension Verdict:** PASS.

### 4.3 Complexity — "Can this be simpler?"

| Line(s) | Question Asked | Author's Answer | Reviewer Assessment | Severity |
|---------|---------------|-----------------|---------------------|----------|
| `VolumeFishMotion.gd:161-219` | Is transition coefficient integration necessary? | It keeps base clip time continuous when clip speed changes. | Integration is justified by action switching; no speculative hook found. | — |
| `cli/volume_motion.py:93-257` | Is full GLB inspection justified? | It verifies real skin, clip and bone hierarchy and bounds accepted inputs. | Needed to avoid trusting unbounded declarative profile values. | — |

**Over-engineering Checklist:**
- [x] No speculative abstraction found
- [x] No unused generic extension hook found
- [x] Each layer has a distinct caller
- [x] Core behavior is not hidden in generated code

**Dimension Verdict:** PASS.

### 4.4 Naming — "Does the name lie?"

| Line(s) | Question Asked | Author's Answer | Reviewer Assessment | Severity |
|---------|---------------|-----------------|---------------------|----------|
| `VolumeFishMotion.gd:224-288` | Are local path and world head/heading distinguished? | Snapshot explicitly uses `head_path_local`, `head_world`, and world `heading`. | Names reflect coordinates. | — |
| `cli/volume_motion.py:294-348` | Do plan/build/validate names match effects? | Plan writes pending handoff, build writes artifacts, validate is read-only. | PASS. | — |

**Dimension Verdict:** PASS.

### 4.5 Comments — "Does this comment add value, or excuse bad code?"

| Line(s) | Question Asked | Author's Answer | Reviewer Assessment | Severity |
|---------|---------------|-----------------|---------------------|----------|
| `VolumeFishMotion.gd:116-118`; `cli/volume_motion.py:140-141` | Do comments explain envelope assumptions? | They state the rotation-only base constraint and identity mesh transform requirement. | Comments explain why conservative checks exist. | — |

**Dimension Verdict:** PASS.

### 4.6 Style & Consistency

| Line(s) | Issue | Type (Block / Nit) | Status |
|---------|-------|-------------------|--------|
| `cli/volume_motion.py`, new GDScript files | Compact formatting differs somewhat from older Python style. | Nit | Does not obscure contracts or behavior. |

**Dimension Verdict:** PASS.

### 4.7 Context — "Does this make the system healthier?"

| Line(s) | Question Asked | Author's Answer | Reviewer Assessment | Severity |
|---------|---------------|-----------------|---------------------|----------|
| `cli/volume_motion.py:28-55,294-348` | Are source receipt/evidence and output hashes frozen without mutating old GLBs? | Receipt, model/profile/runtime and evidence hashes are rechecked before build/validate; outputs are hashed. | Fresh formal validate passes with fixed runtime/config/validation hashes; older GLBs remain untouched. | — |
| `VolumeFishExhibit.gd:304-343`; `Main.Screens.cs:47-52` | Is gallery independent of the player save? | Scene instantiates fixed GLBs/profile without loading the save; return uses existing screen host. | No save/schema dependency in gallery. | — |

**Dimension Verdict:** PASS.

### 4.8 Tests — "Do the tests prove it works, or do they just run?"

| Line(s) | Question Asked | Author's Answer | Reviewer Assessment | Severity |
|---------|---------------|-----------------|---------------------|----------|
| `cli/test_volume_motion.py:91-229` | Do invalid input, stale receipt/evidence, symlink and output tamper fail? | Tests mutate each relevant artifact and assert CLI failure. | Behavior-focused tests cover provenance contract. | — |
| `/tmp/foundry-motion042-tests/results.json` | Do all 16 actions have real runtime assertion samples? | Four species each have Swim/Turn/Ascend/Dive samples and checks for head/path, min speed, loop, overlays and bounds. | Mechanical probes, 260 GUI assertions, 16 rendered combinations and 36 view/phase captures pass. | — |

**Dimension Verdict:** PASS. Static and sampled visual checks cannot certify every frame, but no remaining release gate was identified.

---

## 5. Findings Summary

### Critical (Block Commit)

| # | Dimension | Line(s) | Description | Required Action |
|---|-----------|---------|-------------|-----------------|
| — | — | — | None identified. | — |

### High (Block Commit)

| # | Dimension | Line(s) | Description | Required Action |
|---|-----------|---------|-------------|-----------------|
| — | — | — | None unresolved. Earlier GUI evidence gate was resolved by 260/260 formal checks, 16 action renders, 36 five-view/phase captures and fresh workflow validation. | — |

### Medium (Strongly Recommend Fix)

| # | Dimension | Line(s) | Description | Required Action |
|---|-----------|---------|-------------|-----------------|
| — | — | — | None identified. | — |

### Low / Nit (Optional)

| # | Dimension | Line(s) | Description | Required Action |
|---|-----------|---------|-------------|-----------------|
| L1 | Security | `cli/volume_motion.py:64-85` | Static symlink bounds are tested; concurrent local directory substitution is a residual race in path-based writes. | Document as local single-operator assumption if exposed to concurrent untrusted writers. |

---

## 6. Gate Decision

| Gate | Status |
|------|--------|
| All automated checks pass | [x] |
| Security scan clean | [x] |
| Karpathy score = 4/4 | [x] |
| No Critical findings unresolved | [x] |
| No High findings unresolved | [x] |
| Review document complete | [x] |

### Verdict

- [ ] **BLOCK**
- [x] **APPROVE** — all gates passed

### Reviewer Notes

The reviewer independently read the new CLI, profiles, Godot motion/gallery code, tests and reports, and sampled native images; the parent inspected all 36 five-view/phase images. Parameters are artistic calibration, so visual quality remains subject to player taste. This approval covers the reviewed task 042 state; recheck later code changes before commit.
