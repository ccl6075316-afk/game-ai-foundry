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


## 8. Subsequent pose-export cleanup supplement commit gate

**APPROVED for this separate narrow cleanup/metadata commit.** Read both pose-export cleanup reports, all four original-file manifests, archived export/completion/check metadata, input-chain/re-export templates and README additions. Independently verified24 retained metadata files by SHA/byte size, all four manifest hashes, all current-gates hashes, every rebuild-input-chain hash and all1334 exported sample hashes against the original-file manifests. The four exact whitelisted temporary directories are absent. This audit observes their current absence and retained records; it does not independently re-observe the historical deletion process.

Manifest totals reconcile to1358 removed files:1334 raw posed-mesh JSON samples plus24 archived metadata originals,4,109,020,676 logical source bytes. New archives/manifests total6,877,829 bytes; net logical reduction4,102,142,847 bytes. These are logical file-byte figures, not APFS physical-space measurements. Long-lived current-gates records and original failure outcomes hash-match; no broader deletion is authorized by this review.

READMEs explicitly disclose that raw posed meshes are deleted and cannot now be directly read: manifests are not backups. The retained model/controller/config/exporter/plan and prior fixture/import-setting chains support a future re-export attempt, with historical engine/export logs retained. The command templates have not been executed in this cleanup and do not establish a fresh Godot/GPU/LOD/fin rerun or byte-identical future generated output. Actual regeneration would require another real run and fresh report.

No code/shader/field change is hidden in this supplement; security/design scope is unchanged from sections2–4. Fish diff whitespace check passes. The106 fin failure,107 LOD5 failure and all108 trial gates remain unchanged. This approval does not alter the separately granted single108 CPU evaluation or authorize an108 asset.


## 9. Independent control-fixture reconstruction supplement

**APPROVED for the narrow reproducibility supplement commit.** Read all three control manifests, both restoration scripts and README additions. Independently executed each restore CLI in a separate temporary directory, then compared the complete restored file set against both its manifest and the original control fixture excluding only `.godot`. Sets and every declared byte count/SHA match:106 baseline32 files,106 LOD-only reference34 and107 baseline35. Each includes all three actual import settings; UID counts9/9/11 are restored. No unexpected original noncached file was omitted.

Referenced source models/textures and shared code/config hashes match; newly archived exact differences are3540/13639/3505 bytes respectively. This preserves the actual distinct controls rather than assuming candidate mode0 equals a baseline. Restoration is file-only: no Godot importer, GPU or new LOD check was run, and original fixtures still exist. Scripts validate all declared source hashes and relative destination paths before writing. Prior failure/acceptance boundaries and108 CPU authorization remain unchanged.

Fish diff whitespace check passes. No blocker was found for this supplement. Any later184-temporary-entry cleanup is outside this section and needs its own reviewed classification/whitelist evidence.


## 10. Final oneoff-source archive and future exact-path cleanup review

**Small archive commit APPROVED.** Reviewed both forensic source maps, READMEs, corrected pose-log mappings and `/private/tmp/fish106107-final-exact-cleanup-candidates.json`. Independently verified all171 forensic records: decompressing58 gzip records and resolving58 exact aliases plus34 archived source texts/21 tracked references produces the recorded original SHA/size. All originals still present match those bytes. The records cover39 historical oneoff sources, including already tracked references. The corrected nested-log names include content SHA; the earlier basename collision is disclosed as caught before deletion, not hidden.

The178 candidate temporary entries total67,311,388 logical bytes in the reviewed manifest. All present explicitly listed candidate file hashes/sizes match; no root candidate symlink was observed. The three rebuild-scratch directories are disposable restoration outputs. Other unarchived115 PNG/JPG entries are explicitly derived diagnostics, not promised recoverable backups. Their deletion intentionally discards those raw rasters; critical numerical/source/control/gate and selected visual evidence remains in the tracked experiment archive. The archival source texts preserve historical absolute inputs/outputs/scratch roles and explicitly warn they are not all runnable unchanged or production CLI. No old script was executed during this review.

All corrected pose-log `.log.txt` paths exist and retain their original byte hashes. Independently checked167 files across local-diagnostics, pose archives and control reconstruction against Fish Git ignore rules: zero ignored. Credential-pattern inspection of all decoded forensic payloads found no private-key blocks or recognizable API/cloud/Git token strings; no new network/credential capability is introduced. Fish diff whitespace check passes.

### Deletion boundary and current indirect dependency

Archive approval is not a blanket `fish*` deletion. Root may use only the immutable reviewed exact candidate list after committing the archive and rechecking current hashes, exact directory membership and process use immediately before execution. Any changed/new file returns for classification; do not kill historical PID54404 or touch either toolchain. Original tracked gates/failure reports remain immutable.

**Do not delete `projects/fish-107-zander-eye` while108 is active.** It is an indirect108 input: current108 support audits read its eye config/mask/source, the oral preparer reads its GLB, and grey render/UV diagnostics read its GLB/opaque skin. Reconstructibility does not make an active input disposable. Root explicitly agreed to protect this directory alongside the108 fixture and nine108 temporary inputs. The three old controls and106 candidate have restoration contracts, but actual fixture deletion remains a later root action with fresh exact-path/hash/process checks; none was performed by this review. Any proposal to delete107 candidate must wait until108 releases it or reviewed inputs have explicitly migrated and been re-frozen.

No new cleanup execution or GPU/LOD/geometry validation is inferred. Existing106 fin failure,107 LOD5 failure and108 CPU/visual gates remain unchanged.


## 11. Gzip preservation correction and exact178 executor safety

**Gzip-only archive correction commit APPROVED.** Independently verified all71 current107 forensic records against decoded archive bytes and still-present originals. The two historical whitespace-sensitive texts retain exact original SHA256: baseline patch `607c35cd0a401f5dcf839b818d504641418b97cdc8d0a54b15305ea3a84ac30e`; body-function snapshot `d8eda9f84347e6ceb82402c64daafdb451aace5282363682a4e6e2ba2e9bfcbe`. Gzip changes storage only, avoids treating historical patch formatting as current code and does not rely on `.gitattributes` whitespace exemptions. Updated source-map pins match; Fish diff whitespace check passes.

**Executor static safety review APPROVED for root's separately authorized exact178 temporary-path operation, after archive commit and successful live preflight.** Read `/private/tmp/fish106107-exact-cleanup.py`. Independently confirmed manifest SHA256 `ff178bb0bcd9c392b944fd8e7b76d6f8b34fd97b61c02ce122c64ba2bc58ee15`, exact ordered178 unique path list and both source-map SHA pins. It defaults to dry-run; execution requires an explicit exact whitelist digest. It rejects project roots, fish108-prefix entries, nested roots, changed types/trees/bytes and symlinks, verifies permanent decoded archives, and checks related processes/engine handles without killing anything. It revalidates before the first mutation.107 candidate is not in this executor; it remains protected as108's indirect input.

The independent default dry-run returned blocked because this review sandbox denied `ps` with Operation not permitted. No deletion occurred. This is not recorded as an independent successful live preflight. Root must run with working process-read access and keep the process guard intact; a prior root successful dry-run is separate evidence, not a substitute for execution-time checks. No `--execute` was run by this reviewer. Original fixture, failure,108 and asset-acceptance boundaries remain unchanged.


## 12. Executed178-temp cleanup audit archive commit gate

**APPROVED for the seven-file audit archive commit (2026-10-22).** Independently verified archived manifest SHAff178bb0…, executor SHA977c6474… and result SHAc9dfd442… against completion and still-present original `/tmp` audit files. The result's exact ordered178 unique paths equals the reviewed whitelist; all are immediate `/private/tmp` entries, no fish108-prefix/project root is included, every path is currently absent and logical bytes sum exactly67,311,388.

All nine protected108 temporary files still exist, the108 fixture remains and protected107 candidate GLB retains source SHA `c1b10d96c7aa83e41129df16170d7302f4c4335b226785c5f5b5bd562b6e0aef`. Archived executor source-map pins match current permanent maps; all decoded forensic payload original SHA/size checks pass.107 shared audit points to matching106 summary/manifest hashes. All seven files are not Git-ignored; credential-pattern checks found no private-key/token strings; Fish diff whitespace check passes.

No executor was run or deletion performed by this review. Present absence and signed-by-hash local audit consistency are independently observed; historical successful live process guard/execution timing remains attributed to the recorded root run. The earlier reviewer sandbox-denied dry-run is not relabelled successful. Existing whole-fish/failure/108 gates remain unchanged; this audit archive is not a new Godot/GPU/LOD validation.
