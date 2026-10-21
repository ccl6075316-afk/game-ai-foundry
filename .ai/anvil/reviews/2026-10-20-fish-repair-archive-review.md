# Review Report: `2026-10-20-fish-repair-archive`

## Metadata

| Field | Value |
|-------|-------|
| Reviewer | audit_capture_review, independent anvil reviewer |
| MR / Commit | Uncommitted Foundry 093–103 reusable scripts/runtime/docs and Fish documentation/evidence; 104 excluded (separate review) |
| Author | Current fish production session |
| Review Date | 2026-10-20 |
| Status | `APPROVED` for archive commit only; R1/R2 verified resolved on 2026-10-21 |

Initial R1/R2 observations below are retained as review history. The final re-review section and gate decision record their resolution.

Large change: interface/abstraction review, whole-file reads of reusable Python and Godot helpers, configuration and evidence spot checks. Formal `projects/fishing-2d/game` has no Git modifications. This is an archive review, not production delivery or fish acceptance. Historical failed trials are valid negative evidence and are not themselves commit blockers. Raw large pose/sample JSON was not scanned.

---

## 1. Automated Pre-checks

| Check | Command | Result | Notes |
|-------|---------|--------|-------|
| Lint | Python `ast.parse` for 12 Foundry Python files | PASS | Syntax checked without executing historical mutation scripts; dedicated lint configuration N/A for this scope. |
| Type Check | Seven argparse entry points `--help` | PASS | All exit 0; no new configured static type checker. |
| Unit Tests | 102 independent capture receipt/model/runtime/frame hashes | PASS | Previously independently verified 22 fish, 352 frames, zero requested/actual action mismatch; three clean complete GPU logs. |
| Evidence regression | Inspect 101 preservation and rejected-100 receipts | PASS | Nine-view normal-body preservation has zero outside-ROI changes; rejected100 negative has 34,279 outside-ROI changes and `expected_failure=true`. Historical tests, not a new full gate run. |
| Formal game preservation | `git -C projects/fishing-2d status --short -- game` | PASS | Empty. No new fish-model/fin/body delivery claimed. |

---

## 2. Security Scan

| Category | Finding | Severity | Status |
|----------|---------|----------|--------|
| Hardcoded Secrets | No keys, bearer tokens or credentials found in reviewed scripts/runtime | — | CLEAN |
| Injection Risks | Godot launcher uses subprocess argument arrays; no shell interpolation | — | CLEAN |
| XSS Vulnerabilities | Audit HTML uses escaped report text; no new service endpoint | — | CLEAN within reviewed scope |
| Dependency CVEs | No dependency changes; vulnerability scan N/A | — | N/A |
| Sensitive Data in Logs | Historical receipts contain workstation paths; no credentials identified | Low | Paths are provenance, not secrets |

**Security Verdict:** CLEAN

---

## 3. Karpathy Adversarial Principles

| Principle | Adversarial Question | Author's Answer (Explicit or Inferred) | Verdict | Severity |
|-----------|---------------------|----------------------------------------|---------|----------|
| Think Before Coding | Are single-view hidden geometry and donor colors misrepresented as fact? | Parameters/docs distinguish source constraints and artistic inference; 100 rejection retained. | PASS | — |
| Simplicity First | Do separate prototypes serve actual iterations? | 093/095/097/098/099 represent distinct observed failures. Keeping negative evidence is justified; no forced generic mouth abstraction. | PASS | — |
| Surgical Changes | Was the rejected whole-body remap installed? | No formal game diff; 101 restores099 and proves finite-view ROI preservation. | PASS | — |
| Goal-Driven Execution | Does the authoritative state describe the finished archive? | Final103 record is done/human_review, accepted=false; no ongoing job; remaining work explicitly unresolved. | PASS (R1 resolved) | — |

**Karpathy Score:** 4/4 after R1 correction verified.

---

## 4. Adversarial Dimension Review

### 4.1 Design — "Should this exist at all?"

| Line(s) | Question Asked | Author's Answer | Reviewer Assessment | Severity |
|---------|---------------|-----------------|---------------------|----------|
| `resources/scripts/godot_background.py:1–45` | Does hidden execution preserve tool contracts? | Explicit binary env; headless direct process; macOS GPU uses background LaunchServices. | Appropriate; documents that engine exit code is unavailable and fresh receipts/log checks remain required. | — |
| `resources/scripts/volume-fish/smooth_chin_contour.py:1–22` | Is this falsely a universal fish builder? | Frozen input/source hashes and two-surface structure; documentation limits it to current canvas/model. | Acceptable experimental interface; no promotion as biological template. | — |

**Dimension Verdict:** PASS

### 4.2 Functionality — "What is the author missing?"

| Line(s) | Question Asked | Author's Answer | Reviewer Assessment | Severity |
|---------|---------------|-----------------|---------------------|----------|
| `resources/scripts/volume-fish/capture_surface_mouth_audit.gd:90–93,122–132` | Does each label match actual motion? | Consume queued action via step(0), then seek, assert actual action. | Independent receipts verify correction; finite samples only. | — |
| `resources/scripts/volume-fish/capture_body_coverage.gd:69–98` | Can manual rendering compare stale GPU bones? | First-view warm submission plus frame yield, unchanged actual/reference comparison. | Specific capture-timing correction; does not change models or tolerate coverage gaps. | — |
| `projects/fishing-2d/experiments/blender-fish/local-source-features-103/trial.validation.json:3–6` | Is there really a current pollable job? | Initially running/poll; final re-review verifies terminal done/human_review. | R1: invalid archive handoff state; next agent is directed to nonexistent ongoing work. | High |

**Key Edge Cases Probed:**
- [x] Empty / null input: argparse/hash/mesh assertions reject invalid inputs.
- [x] Boundary / maximum size: frozen model/source hashes; helpers expose fixed array/canvas constraints rather than broad compatibility.
- [x] Negative / invalid values: no new unbounded external input surface; production profile validation unchanged.
- [x] Race condition / deadlock: action queue consumption and manual render warm-up reviewed.
- [x] External dependency failure: launcher exit-code limitation explicit; report/log gate retained.
- [x] Concurrent access: archive-only invocation scope; no production writes added.

**Dimension Verdict:** FINDINGS (R1)

### 4.3 Complexity — "Can this be simpler?"

| Line(s) | Question Asked | Author's Answer | Reviewer Assessment | Severity |
|---------|---------------|-----------------|---------------------|----------|
| Mouth edit scripts | Why retain similar implementations? | Each is a reproducible historical trial with different lower-jaw/cavity hypothesis. | Do not refactor negative evidence during curation. Shared production abstraction is not asserted. | — |

**Over-engineering Checklist:**
- [x] No speculative production abstraction added.
- [x] No new generic hooks required to accept an asset.
- [x] Trial/runtime copies are traceable to actual experiments.
- [x] No extra rewrite requested during archival review.

**Dimension Verdict:** PASS

### 4.4 Naming — "Does the name lie?"

| Line(s) | Question Asked | Author's Answer | Reviewer Assessment | Severity |
|---------|---------------|-----------------|---------------------|----------|
| 093–103 completion reports | Does `ok` mean visual acceptance? | `user_visual_acceptance`, scope and `volume_accept_executed=false` separated. | Correct except stale running state in R1. Failed093/095/096/098/100 remain failures. | — |

**Naming Issues:**
- [x] Trial names distinguish iteration.
- [x] Edit functions explicitly mutate output models.
- [x] Known species-specific scope recorded.
- [x] Mechanical success not called whole-fish acceptance.

**Dimension Verdict:** PASS

### 4.5 Comments — "Does this comment add value, or excuse bad code?"

| Line(s) | Question Asked | Author's Answer | Reviewer Assessment | Severity |
|---------|---------------|-----------------|---------------------|----------|
| `resources/runtime/godot/yellow-material-100/README.md:3,11` | Is rejected100 still pending? | Top says rejected; line11 says visual pending. | R2: remove contradictory stale status and imperative current-game installation wording. | Medium |
| `docs/anvil/debug-sessions/2026-10-20-103-local-source-features-session.md:15` | Is incomplete investigation explicitly archived? | Phase3 says awaiting independent verdict. | Include final incomplete/superseded status under R1, without inventing approval. | High |

**Comment Quality Checklist:**
- [x] Capture warm-up explains the observed stale-bone failure.
- [x] Limits distinguish inference from measurement.
- [ ] 103 final-state note still required.
- [x] 100 is explicitly rejected in authoritative completion report.

**Dimension Verdict:** FINDINGS (R1/R2)

### 4.6 Style & Consistency

| Line(s) | Issue | Type (Block / Nit) | Status |
|---------|-------|-------------------|--------|
| Python prototype scripts | Compact semicolon-heavy code reflects existing experimental tools; no new mandatory style violation established. | Nit | No style rewrite requested |

**Style Checklist:**
- [x] No formatting-only rewrite mixed into formal game.
- [x] Runtime copies retain surrounding interfaces.
- [x] Historical code distinguished from validated production entry points.

**Dimension Verdict:** PASS

### 4.7 Context — "Does this make the system healthier?"

| Line(s) | Question Asked | Author's Answer | Reviewer Assessment | Severity |
|---------|---------------|-----------------|---------------------|----------|
| New outline/mouth documentation | Does it preserve the user's actual constraints? | No source ink on added skin, no broad normal-body remap, distinguish chin from lip contour. | Good reusable knowledge; no claim that all fish are fixed. | — |
| Historical experiment capture scripts | Are workstation paths executable production dependencies? | Foundry reusable entry points have no local absolute path; experiment-specific scripts still contain local paths and older foreground calls. | R3: archival-only limitation, not a production blocker. Do not present old scripts as portable/background defaults. | Low |

**System Health Checklist:**
- [x] Whole reusable helpers inspected.
- [x] No new production dependency introduced.
- [x] Source-ink rule and rejection make future work clearer.
- [ ] Stale103 authoritative state must be closed accurately.

**Dimension Verdict:** FINDINGS (R1)

### 4.8 Tests — "Do the tests prove it works, or do they just run?"

| Line(s) | Question Asked | Author's Answer | Reviewer Assessment | Severity |
|---------|---------------|-----------------|---------------------|----------|
| 101 preservation / rejected100 negative | Would a broad remap pass? | Negative changes34,279 pixels outside frozen mask. | Meaningful counterexample; finite cameras/pose limitations explicit. | — |
| 102 action capture | Would mislabeled Swim frames pass? | Before264/352 mismatch; after0/352 with per-frame assertion and hashes. | Meaningful failure regression. No transition/continuous proof claimed. | — |
| Historical geometry | Do numerical normal/topology checks guarantee mouth shape? | Reports/docs preserve user rejection and unknown transverse shape. | No forced re-run of rejected trials, no false acceptance. | — |

**Test Quality Checklist:**
- [x] Negative cases fail their actual behavior checks.
- [x] Coverage changes do not weaken tolerance.
- [x] Scope limits documented.
- [x] No new full production delivery asserted.

**Dimension Verdict:** PASS

---

## 5. Findings Summary

### Critical (Block Commit)

None.

### High (Block Commit)

No unresolved High findings. R1 below is retained as the original finding and is **RESOLVED** by final re-review.

| # | Dimension | Line(s) | Description | Required Action |
|---|-----------|---------|-------------|-----------------|
| R1 | Context / state accuracy | Fish `experiments/blender-fish/local-source-features-103/trial.validation.json:3–6`; Foundry `docs/anvil/debug-sessions/2026-10-20-103-local-source-features-session.md:15` | The authoritative103 trial still reports running/poll and future repair/submission tasks while being prepared for archive. There is no corresponding live job to poll. Debug record ends at an unapproved phase. | Record actual terminal archive disposition, unfinished/failed visual scope and any104 successor. Remove stale poll/continuation instructions. Preserve incomplete phase verdict honestly; do not mark visual or debug acceptance that did not occur. |

### Medium (Strongly Recommend Fix)

R2 below is **RESOLVED** by final re-review.

| # | Dimension | Line(s) | Description | Required Action |
|---|-----------|---------|-------------|-----------------|
| R2 | Documentation | `resources/runtime/godot/yellow-material-100/README.md:8–11` | Rejected100 README still says visual pending and instructs writing a chart into the current game. | Describe these as historical reproduction steps in a disposable experiment only; say visual rejected. Keep negative evidence and technical results. |

### Low / Nit (Optional)

| # | Dimension | Line(s) | Description | Required Action |
|---|-----------|---------|-------------|-----------------|
| R3 | Portability / archived capture | E.g. Fish `yellow-material-100/open_game.gd:3,36`, `local-source-features-103/capture_trial.gd:1` | Historical experiment scripts contain original machine paths and old foreground activation. No such hardcoded paths found in new Foundry reusable interfaces. | Keep them explicitly archival, or remove abandoned scripts during curation. Future runs use parameterized background helpers. Do not rewrite historical hash-bound evidence just for portability. |

---

## 6. Gate Decision

| Gate | Status |
|------|--------|
| Applicable automated checks pass | [x] |
| Security scan clean | [x] |
| Karpathy score = 4/4 | [x] R1 resolved |
| No Critical findings unresolved | [x] |
| No High findings unresolved | [x] R1 resolved |
| Review document complete | [x] |

### Verdict

- [ ] **BLOCK** — no unresolved archive commit blocker.
- [x] **APPROVE** — corrected 093–105 experimental code, evidence, documentation and knowledge may be archived/committed; no formal fish promotion approved.

### Reviewer Notes

This review does not demand repairing historical fish candidates. Failed trials, rejected100, and incomplete103 can be committed as accurate negative evidence. No formal fish acceptance, model replacement, continuous-time motion, or fresh fin/body delivery is approved by this archival review. 104 has its own independent review and is outside this gate.


## 7. Final Re-review — 2026-10-21

### Corrections verified

- **R1 resolved:** Fish103 `trial.validation.json` is now `done / human_review`, `accepted=false`, `production_replaced=false`, with `remaining_work_is_not_running=true`. It records unfinished material/mouth findings and the104 successor without calling them fixed. Deleted clone paths are historical; actual105 preview fixtures are identified. The103 debug session records completed bounded investigations and the terminal archive scope instead of an ongoing pending stage.
- **R2 resolved:** Rejected100 README now describes historical isolated100 setup, explicitly says the user rejected the appearance, and forbids installation to formal game. Its old clone path remains historical context under the105 archive warning.
- **R3 addressed by archive scope:** 105 README explicitly warns that old experiment scripts/absolute paths and old `ok=true` receipts are historical; it directs reopening through self-contained fixtures. No forced rewrite of hash-bound old captures.

### Additional evidence checked

| Check | Independent result | Limit |
|-------|--------------------|-------|
| Four105 fixtures | All four `fixture.validation.json` hashes match the aggregate report; all86 listed input files match manifest SHA256 values (21 yellow,19 black,25 red,21 zander). | These are review projects, not fresh fish delivery gates. |
| GPU fixture logs | Four expected `FISH_FIXTURE_SMOKE <species>` markers; no ERROR/SCRIPT ERROR/SHADER ERROR. | Logs contain the documented Control-anchor warnings and red raw-PNG export warnings; do not call them warning-free or exported-build tests. |
| Source provenance reproduction | Ran `source-ink-104/verify_provenance.py`: old opaque RGBA mismatch0, extended mask mismatch0, donor RGBA mismatch0 under OpenCV5.0.0. | Reproduces only the frozen3473 source-ink domain; does not identify new species ink. |
|104 retained capture evidence | All47 records have off_mismatch0/outside0; every referenced baseline/candidate/probe PNG SHA256 matches disk. | Bounded multi-view/discrete-action evidence, not continuous coverage or visual acceptance. |
| Cleanup manifest | Item byte/file sums equal37,788,696,962 bytes (35.1935GiB) and67,933 files. | This verifies manifest arithmetic, not an independent pre-deletion disk survey. |
| Final summary paths/state | Fish `2026-10-20-MOUTH-MATERIAL-REVIEW.md` and105 README/completion consistently state no production replacement, unresolved20-fish findings, red/black unaccepted previews and missing new103/104 delivery gates. | Historical101 gates are retained historical evidence, not propagated as105 fixture acceptance. |
| Compound knowledge | Read `docs/solutions/logic/source-outline-contaminates-fish-skin-20261020.md`; validated actual Anvil YAML schema with Ruby: required keys, enums, types, min lengths, symptoms count and date pattern pass. | Documents verified mechanism and failed visual outcome; no automatic critical-pattern promotion or whole-fish acceptance. |
| Formal game | `git -C projects/fishing-2d status --short -- game` remains empty. | Review-only archive. |

**Final verdict: APPROVED for archive commit.** No unresolved Critical/High findings. This approval does not authorize installing trial materials/models as accepted fish or claim new fin/body/transition acceptance. Source-ink104 implementation approval remains covered by its separate independent review; this pass checked its archived evidence and integration boundaries.
