# Review Report: `2026-10-21-106-107-retention`

## Metadata

| Field | Value |
|---|---|
| Reviewer | Independent adversarial reviewer, mahi_phase_review |
| Review Date | 2026-10-21 |
| Scope | Retained 106/107 eye code, strict body-checker compatibility, evidence cleanup and reconstruction |
| Change size | Large; interfaces, source binding, negative contracts and reconstruction checked |
| Status | APPROVED — 106/107 retention-code commit scope only |
| Asset acceptance | None; no whole-fish, formal replacement or 108 field approval |

Read the review skill/template, existing 106/107 reviews and debug sessions, knowledge, runtime READMEs, helpers/templates, freezer scripts, body-checker diff and contract tests, experiment READMEs, cleanup/rebuild manifests and completion reports. No implementation was modified.

## 1. Automated Pre-checks

| Check | Result | Evidence |
|---|---|---|
| Both repositories `git diff --check` | PASS | Independent current run |
| Freezer Python syntax | PASS | Independent AST parse of both scripts |
| Freezer behaviour | PASS | Both independently run into temporary directories; six 106 and seven 107 PNG outputs exactly match archived runtime PNG hashes |
| Retained evidence hashes | PASS | All 386 106 and 709 107 listed preserved files checked |
| Frozen runtime/model/pruned manifest | PASS | All 19 frozen runtime entries, both tracked model hashes and both pruned-manifest hashes checked |
| Completion evidence and current body checker | PASS | Every completion evidence hash matches; both body-completion capture-script hashes equal current checker |
| File-only overlay reconstruction | PASS, bounded | Independently restored fixtures/overlays/frozen data/models in temporary directories; all 23/21 overlay files match actual candidate |
| Godot/GPU checks | Existing evidence only | Installation/rejection/GPU reports and hashes reviewed; no new full engine/GPU run claimed |
| Exact `.import` reconstruction | PASS, file-only | Six archive/actual/restored SHA comparisons match after independently executing both restoration CLIs in temporary directories; no importer/GPU/LOD run |

The available installed Godot reports are relevant prior gate evidence, not a claim that this independent cleanup review reran their GPU work. There is no separate lint/type-check configuration for these experimental scripts.

## 2. Security Scan

| Category | Assessment | Status |
|---|---|---|
| Secrets | No new credential or secret handling in retained runtime/freezers | CLEAN |
| Injection | No network or shell execution in helpers/freezers; shader sampler grammar rejects unsupported uses | CLEAN |
| XSS / SQL | Not applicable to these local assets and runtime scripts | N/A |
| Dependencies | No dependency additions reviewed | N/A |
| Logs | Local source paths, hashes and validation output; no credential logging identified | CLEAN |

**Security Verdict: CLEAN within this scope.** Receipts/hash checks are local validation contracts, not a security boundary against an attacker rewriting the entire program and metadata.

## 3. Karpathy Adversarial Principles

| Principle | Question and assessment | Verdict |
|---|---|---|
| Think Before Coding | Eye/source/fallback/retired cleanup domains and old LOD failures are distinct, written assumptions | PASS |
| Simplicity First | Duplicated frozen species helpers preserve already-reviewed cases; no speculative universal eye detector added | PASS |
| Surgical Changes | Shared body checker dispatches only the two explicit species; original fixed path and coverage algorithm remain | PASS |
| Goal-Driven Execution | Negative shader contracts and pixel identity/probe evidence verify observable behaviour; reconstruction checks verify bytes rather than claiming fresh visual success | PASS |

**Karpathy Score: 4/4.**

## 4. Adversarial Dimension Review

| Dimension | References | Assessment | Result |
|---|---|---|---|
| Design | 107 helper:230–247; body checker:63–131 | Actual shader/include/profile/uniform/geometry bindings are frozen; unsupported assemblies fail | PASS |
| Functionality | 107 helper:313–322; body checker:90–130 | Exact single legacy-eye term/return retired, sampler wrappers keep original expressions; current textures, mode/projection and mesh/LOD/binding are checked | PASS |
| Complexity | 106 LOD helper:35–70; both freezers | Packed preservation avoids re-encoding; native mirror copies preserve alpha/outside RGBA; species constants are explicit | PASS |
| Naming | Runtime/experiment READMEs; completion summaries | Local preview versus whole-fish acceptance, import rebuild versus GPU revalidation are distinguished | PASS |
| Comments | LOD helper:57–58; cleanup README sections | Explains byte preservation and limits; deleted PNG hashes are explicitly not reversible image archives | PASS |
| Style | Existing experimental scripts | Compact style is consistent with retained tools; no broad formatting change | PASS |
| Context | Knowledge and production skill rule15 | Per-fish source/side/all-LOD checks required; 22/11px and retired-LOD exception not promoted to defaults | PASS |
| Tests | Both contract scripts; completion/evidence hashes | Invalid modes, probes, samplers, stale receipt/code/template and forbidden coverage-token cases retained; no fresh GPU claim | PASS, import supplement pending |

## 5. Findings Summary

### Resolved reconstruction finding

Exact import-setting inputs must be archived and restored with file hashes before describing the local trials as reproducible from committed sources. Import settings can change actual generated LOD/material behaviour, so excluding them from byte reconstruction is material. This is an evidence/retention blocker, not a demand to rerun every GPU check during cleanup. Final restore success must still be described as file-only, not a fresh Godot import or LOD pass.

### Preserved acceptance boundaries

- 106 local eye trial may be retained; old LOD5 was explicitly retired, not passed. The original left pectoral membrane still fails 35/490 poses at the frozen tolerance.
- 107 retains all original six skin/two oral LOD tables; original 439-face LOD5 remains failed and blocks formal integration. Other fin/body local gates do not erase it.
- Export packages/raw-PNG inclusion remain unverified. Formal game replacement and `volume accept` were not performed.
- No 108 shape/field/protection change is authorized by this cleanup review. Unfinished 108 experiments and negative evidence retain their separate gates.

No unresolved code High/Critical finding was identified in this bounded retention review. The exact import-setting supplement was independently verified below; no blocking commit condition remains in this scope.

## 6. Gate Decision

| Gate | Status |
|---|---|
| Code/security/record scope | PASS |
| Evidence and file reconstruction hashes | PASS |
| Exact import-settings supplement | PASS, file-only |
| Commit gate | APPROVED for valuable local-trial code/records only |
| Whole-fish/formal/runtime acceptance | NOT GRANTED |

Approval is limited to committing the valuable local-trial implementation, documentation and retained evidence. It does not approve the failed assets for installation.


## 7. Import supplement final verification

Read both updated rebuild manifests, restore scripts and README supplements. Independently executed each `restore-import-settings.py` against a fresh temporary directory. For all six settings, archived `.import.txt`, the original current trial `.import`, and restored bytes match the declared SHA256. The restore scripts validate all input hashes and relative `.import` paths before writing; neither invokes Godot. The three settings per fish cover GLB, embedded/source-image import and opaque-skin import. The original values are retained.

The observed current engine `4.7.1.stable.mono.official.a13da4feb` is explicitly not asserted as a historical GPU-engine version. File restoration is not a new import, GPU run or LOD acceptance. Updated entry documentation continues to distinguish106/107 local eye trial success from106 fin failure,107 LOD5 failure and rejected108 shape work. The skill's removal of the obsolete absolute installation path correctly requires current-workspace discovery. Final independent both-repository diff checks are clean.

**Final commit-scope verdict: APPROVED.** No new implementation or asset was modified by this independent review. All existing whole-fish/runtime/export blockers remain.
