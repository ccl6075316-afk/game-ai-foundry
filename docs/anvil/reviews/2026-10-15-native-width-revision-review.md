# Review Report: `2026-10-15-native-width-revision`

## Metadata

| Field | Value |
|-------|-------|
| Reviewer | Independent anvil review agent |
| MR / Commit | Uncommitted native width revision |
| Author | native_revision agent |
| Review Date | 2026-10-15 |
| Status | `APPROVED` — code gate only |

Scope: `cli/volume_shape.py`, `cli/volume_fish.py`, `cli/test_volume_shape.py`, and `resources/scripts/volume-fish/build_fish.py`. Species profiles, generated models, and visual acceptance are outside this code review.

## 1. Automated Pre-checks

| Check | Command | Result | Notes |
|-------|---------|--------|-------|
| Whitespace | `git diff --check` | PASS | Current tracked diff |
| Lint | N/A | N/A | No configured lint command found |
| Type Check | N/A | N/A | No configured type checker found |
| Unit Tests | From `cli/`: `../.venv/bin/python -m unittest test_volume_shape test_volume_fish` | PASS | 36 tests, including six native revision tests |
| Actual Blender builds | Both `052-knowledge-width` validation reports below | PASS | Eight checks each; both `ok=true`, `done`, `human_review` |

An initial invocation from the repository root selected the root `gamefactory.py` shim and failed to import the CLI. Running from `cli/`, as the test module expects, resolves the collision. This is an invocation issue, not a regression in this diff.

## 2. Security Scan

| Category | Finding | Severity | Status |
|----------|---------|----------|--------|
| Hardcoded Secrets | None introduced | — | Clean |
| Injection Risks | Strict declarative fields; no expression/script hook; native file opens with `use_scripts=False` | — | Clean |
| XSS Vulnerabilities | No web output change | — | N/A |
| Dependency CVEs | No dependency changes | — | N/A |
| Sensitive Data in Logs | No credential reads/logging added | — | Clean |

**Security Verdict:** CLEAN for the reviewed diff. Historical native files remain trusted, hash-bound inputs.

## 3. Karpathy Adversarial Principles

| Principle | Adversarial Question | Author's Answer (Explicit or Inferred) | Verdict | Severity |
|-----------|---------------------|----------------------------------------|---------|----------|
| Think Before Coding | Does the code infer anatomy from images? | No: it applies explicit station ratios to an accepted native model; shared coordinate matrices and unsupported shape keys are checked | PASS | — |
| Simplicity First | Is the abstraction needed? | A small Blender-independent module shares validation/provenance/interpolation between CLI and builder | PASS | — |
| Surgical Changes | Does each change serve the two native revisions? | One optional profile field, two freshness checks, one builder branch, and extraction of unchanged export logic | PASS | — |
| Goal-Driven Execution | Do tests prove observable behavior? | Midpoint/endpoint/smoothness/bounds, invalid data, changed hashes, changed textures, and input overwrite rejection are asserted | PASS | — |

**Karpathy Score:** 4/4

## 4. Adversarial Dimension Review

### 4.1 Design — "Should this exist at all?"

| Line(s) | Question Asked | Author's Answer | Reviewer Assessment | Severity |
|---------|---------------|-----------------|---------------------|----------|
| `volume_shape.py:44–74`; `volume_fish.py:428–432,502–506` | Can legacy native geometry be reused without replaying its obsolete generator? | Verify historical acceptance, native hashes, source hashes, and style contract at plan and freshness checks | The accepted native model remains the geometry authority; a new generator does not reinterpret its old head UV procedure | — |

**Dimension Verdict:** PASS

### 4.2 Functionality — "What is the author missing?"

| Line(s) | Question Asked | Author's Answer | Reviewer Assessment | Severity |
|---------|---------------|-----------------|---------------------|----------|
| `volume_shape.py:19–41` | Can station interpolation overshoot, divide by zero, or accept NaN? | Strict ordered stations, positive bounded widths, finite values; convex smoothstep ratio interpolation with constant extension | Correct; C1 at each station and at extended endpoints | — |
| `volume_shape.py:59–65` | Can the revision overwrite accepted native inputs? | Resolve inputs and reject matching model output paths | Correct; covered by regression test | — |
| `build_fish.py:486–525` | Are fin span and eye roundness unintentionally flattened? | Paired fin meshes and bones translate together; eye patches translate around their center; other points scale Y only | Correct for the named native meshes produced by this toolkit. Rest X/Z coordinates remain unchanged | — |
| `build_fish.py:527–538` | Can a new export silently lose closure, textures, or swimming? | Recheck closed meshes, normalized weights, texture byte hashes, finite GLB, loop motion, nearest filters and roughness | Technical checks remain active; this does not establish visual quality | — |

**Key Edge Cases Probed:** empty/unknown/nonfinite/unsorted stations; width and ratio bounds; altered handoff/native bytes; source texture substitution; legacy output paths; accidental input overwrite; unsupported shape keys and coordinate transforms. Concurrency is unchanged from the existing single-build handoff contract.

**Dimension Verdict:** PASS

### 4.3 Complexity — "Can this be simpler?"

| Line(s) | Question Asked | Author's Answer | Reviewer Assessment | Severity |
|---------|---------------|-----------------|---------------------|----------|
| `build_fish.py:135–147,479–539` | Is there an unnecessary second modeling system? | Native mutation is limited to rest Y coordinates; the exporter is shared with procedural builds | Scope is justified by preserving existing accepted meshes and UV ownership | — |

**Dimension Verdict:** PASS. No speculative executable hooks or new dependencies.

### 4.4 Naming — "Does the name lie?"

| Line(s) | Question Asked | Author's Answer | Reviewer Assessment | Severity |
|---------|---------------|-----------------|---------------------|----------|
| `volume_shape.py:32`; `build_fish.py:479` | Does width mean a forced absolute width? | Width scale is the interpolated target/source ratio; native revision changes the transverse axis only | Names and interpolation docstring accurately describe behavior | — |

**Dimension Verdict:** PASS

### 4.5 Comments — "Does this comment add value, or excuse bad code?"

| Line(s) | Question Asked | Author's Answer | Reviewer Assessment | Severity |
|---------|---------------|-----------------|---------------------|----------|
| `build_fish.py:496–497` | Why are fins/eyes treated differently? | Keep appendage shape and eye roundness while the attachment follows the body | Explains the anatomical reason for the exception | — |

**Dimension Verdict:** PASS. No non-actionable TODOs introduced.

### 4.6 Style & Consistency

| Line(s) | Issue | Type (Block / Nit) | Status |
|---------|-------|-------------------|--------|
| Changed builder branch | Dense formatting follows existing builder style; no unrelated style rewrite | — | Pass |

**Dimension Verdict:** PASS

### 4.7 Context — "Does this make the system healthier?"

| Line(s) | Question Asked | Author's Answer | Reviewer Assessment | Severity |
|---------|---------------|-----------------|---------------------|----------|
| CLI planning/freshness and builder entry points | Is this a game-only bypass of the source review gate? | Both normal planning and freshness run before the optional native branch; the source remains historically accepted and hash-bound | Reusable code stays in Foundry; no alternate acceptance-state database is introduced | — |

**Dimension Verdict:** PASS. Existing exporter, source review flow, and procedural path were inspected alongside the diff.

### 4.8 Tests — "Do the tests prove it works, or do they just run?"

| Line(s) | Question Asked | Author's Answer | Reviewer Assessment | Severity |
|---------|---------------|-----------------|---------------------|----------|
| `test_volume_shape.py:26–57` | Would linear interpolation, unsafe native replacement, or stale provenance pass? | Smooth midpoint and derivative checks, mutation tests, hash and overwrite assertions | Tests exercise behavior; no Blender mock pretends to prove anatomy or animation | — |

**Dimension Verdict:** PASS for pure logic and existing CLI regressions. Actual Blender build and visual review remain required for candidate models.

## 5. Findings Summary

### Critical (Block Commit)

None.

### High (Block Commit)

None.

### Medium (Strongly Recommend Fix)

None.

### Low / Nit (Optional)

No change requested.

## 6. Gate Decision

| Gate | Status |
|------|--------|
| All applicable automated checks pass | [x] |
| Security scan clean | [x] |
| Karpathy score = 4/4 | [x] |
| No Critical findings unresolved | [x] |
| No High findings unresolved | [x] |
| Review document complete | [x] |

### Verdict

- [x] **APPROVE** — code gate passed.
- [ ] **BLOCK** — no code blockers identified.

### Reviewer Notes

Actual CLI build evidence inspected after the initial code review:

| Candidate | Validation report (repository relative) | Preservation / validation metrics |
|-----------|---------------------------------------|-----------------------------------|
| Arapaima | `projects/fishing-2d/experiments/blender-fish/models/arapaima/052-knowledge-width.handoff-artifacts/validation.json` | `native_revision=true`, `width_only=true`, `topology_uv_unchanged=true`; 18 bones, 9,346 vertices; all nine meshes closed; zero unnormalized weights and nonfinite components; all loop seams zero; packed original textures, nearest and roughness checks pass |
| Scalloped hammerhead | `projects/fishing-2d/experiments/blender-fish/models/scalloped_hammerhead/052-knowledge-width.handoff-artifacts/validation.json` | Same three revision flags true; 18 bones, 20,454 vertices; all 13 meshes closed; zero unnormalized weights and nonfinite components; all loop seams zero; original side/front/top/bottom images retained; nearest and roughness checks pass |

Candidate GLB hashes: arapaima `4480381d9a32f39d97c6266b75d048fcc867bc752e2c10ab28a4163b2bf03b5a`; scalloped hammerhead `3269a09242bf95ae3662edc8230f904131be478939141450eb16b3c8d6fbdc96`. Arapaima pectoral roots translate inward by approximately `0.01049566` model units on each side; pelvic translations are approximately `0.000001625`. Hammerhead paired fins have zero shifts because their roots lie outside the changed head-width zone. These are report metrics, not invented anatomical acceptance criteria.

Both reports retain `style_visual_review=pending` at this inspection. Root operator has inspected rendered top/oblique views; actual runtime orbit review and final visual acceptance remain pending. The original caution below is narrowed by successful real Blender builds, but the counts/active-UV assertion is still not a complete before/after native-data audit.

- The native-revision path deliberately does not validate that each declared source half-width equals a measured mesh section. Profiles must use measured, corresponding anatomical stations; changing the ratios alone does not prove biological accuracy.
- The in-build unchanged assertion checks vertex/polygon counts and active UV coordinates. It is not a general proof of unchanged topology, all UV layers, materials, bone hierarchy or animation curves. The mutation itself only edits vertex Y and rest-bone head/tail Y and does not write those other data. A read-only before/after audit of actual candidates is stronger evidence for the preservation claim.
- Export validation proves animation exists and loops; it does not prove fin attachment or swimming quality. Review actual whole-fish orbit/action video for both candidates before visual acceptance or installation.
- This report approves the implementation. It does not accept the new fish profiles, infer user acceptance, or authorize replacing runtime assets without their workflow gates.

### Final helper and runtime evidence review

Additional reviewed files: Foundry `resources/scripts/volume-fish/audit_native_revision.py` and game `experiments/blender-fish/knowledge-052/review_knowledge_revision.gd`. No blocking findings. No additional broad test run was needed; both helpers have actual successful executions for the two requested species.

The read-only Blender helper loads native files with scripts disabled, compares exact polygon/edge connectivity, every UV layer, vertex-group membership/weights, parent/connected bone relationships, all collected action curves and packed image bytes, and verifies rest-vertex X/Z within `1e-7`. It writes a report without saving either input blend. Both `052-knowledge-width.handoff-artifacts/native-audit.json` reports have `ok=true` and all eight preservation checks true: mesh names, bone hierarchy, actions, textures, X/Z, topology, UVs and weights. This supplies actual before/after evidence beyond the builder's counts/active-UV assertion. It does not compare every possible Blender property or independently approve anatomy.

The game helper instantiates the existing exhibit and motion controller for both panels, retains the old PackedScene for the before panel, and assigns the candidate scene to the after panel. It steps both at the same rate, uses matching fish-relative cameras, records Swim/Turn/Ascend/Dive and checks readiness/envelopes from actual controller snapshots. Reports inspected at `/private/tmp/fish-knowledge-052/arapaima/validation.json` and `/private/tmp/fish-knowledge-052/scalloped_hammerhead/validation.json`: each records 600 frames at 30 fps, 1280×720, `ok=true`, and zero failures. Their `visual_review=pending` remains appropriate: motion readiness/envelope checks do not constitute human visual approval. Retain compact delivery evidence elsewhere before deleting temporary frames.

Measurement interpretation was checked explicitly: arapaima station `u=.75` in the native audit measures `Closed_body` alone (approximately 32.266 → 24.773 cm). The profile's approximately 33.046 → 25.33 cm corresponds to the outer cover including the frontal overlay. These are different mesh sets at the same plane, so the report must not present them as a failed exact-width prediction or silently substitute one for the other. Section widths interpolate finite mesh edges; an applied smooth ratio can differ slightly at a plane lying between mesh rings.

Security and scope remain clean: fixed file IO, no added network/dependencies/secret access, accepted inputs not mutated by either review helper. **Code review remains APPROVED.** Final viewing/acceptance is owned by the operator using the produced runtime evidence.
