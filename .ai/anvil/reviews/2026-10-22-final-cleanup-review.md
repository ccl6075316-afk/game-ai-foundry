# Review Report: `2026-10-22-final-cleanup`

## Metadata

| Field | Value |
|---|---|
| Reviewer | Independent Anvil reviewer `/root/source_ink_sampler_doer` |
| Author | `/root/yellow_ridges_review` |
| Review Date | 2026-10-22 |
| Status | **APPROVED — byte restoration and future exact cleanup boundary only** |
| Scope | Fish108/final-cleanup-plan; no model acceptance, Godot/import/GPU/LOD approval, current deletion execution or Git operation |

Final input bindings:

- Plan SHA256: `0445f2c9222bf27eb2a105e66643b101d0249efa240333aa706d32ca0c561ff6`.
- Restore script SHA256: `2abb2a3bcbd24b3f57ca191bb4fc9f49348cee5bdeb6a17960827a639d99d8b0`.
- README SHA256: `2bb4c4b4df575e1fec6b03bbfa1f76d62a7610691ab4852eff5f9de9ad5d22fc`.
- Author safety package SHA256: `2a50d11cc51632b709f2153e69345b75b53c9f19789335b651b344deea7dae85`; all9 member sizes/hashes independently verified.
- Independent proof: [2026-10-22-final-cleanup-independent.validation.json](2026-10-22-final-cleanup-independent.validation.json).

## 1. Automated Pre-checks

| Check | Result | Actual evidence |
|---|---|---|
| Syntax | PASS | Compiled current restore source without running Godot or creating bytecode cache |
| Lint/type infrastructure | N/A | Standalone local POSIX CLI; behavioral refusal and exact byte checks used |
| Full current tree | PASS | Independently enumerated6 ignored fixtures/310 files; complete paths/types/sizes/SHA match final plan; no symlink/nested Git |
| Active source | PASS | All243 active references actually Git-tracked; ordinary index blobs equal working bytes, LFS index pointer oid/size and local LFS object match materialized bytes |
| Independent real restoration | PASS | New-script real CLI restored107candidate and108, each48active; complete file sets and bytes match including3 .import and11 UID each |
| Temporary provenance | PASS |29 exact paths/31 files:25 gzip original-byte decode matches,3 actual tracked source references,3 copyrighted originals referenced only |
| Independent CLI boundaries | PASS |32 real cases:16×normal/`-O`, including2 valid runs and30 refusals; no external/existing file overwrite |
| Author regression corroboration | PASS | Final plan/script-bound30 refusal cases and6 complete legitimate restores; package members checked |

Initial vulnerable script SHA `7517c9b5ecf837ae68b2dddce198f668634ae831bc43298cfefb9ea62b464a55` and initial byte-only evidence remain explicitly historical. Gzip decoding of that old script matches its exact original bytes. Initial legal byte restoration was never a retrospective safety approval.

## 2. Security Scan

**CLEAN within the reviewed local boundary.** Initial High finding at old `restore-active-fixture.py:5–10` is fixed, not waived. Current lines17–29 reject absolute/parent relative paths and symlink components. Lines53–74 constrain sources to Foundry, no-follow-open regular files, and check exact size/hash. Lines83–111 refuse existing/relative/symlink outputs, unknown/duplicate fixtures and duplicate/prefix-conflicting destinations before mutation. Lines113–139 use exclusive root creation and anchored no-follow directory handles with `xb` writes. No guard relies on `assert`, including under `python -O`.

The recovery script has no shell/Git/delete/network operation. Scoped script/README scan found no hardcoded credential assignment. New output can remain partial after an unrelated I/O failure; it is not reported successful or eligible for overlay. No claim of a universal backup service or hostile concurrent-filesystem proof is made. Actual final cleanup still requires all relevant work idle and a fresh full snapshot check.

## 3. Karpathy Adversarial Principles

| Principle | Assessment | Verdict |
|---|---|---|
| Think Before Coding | Source availability, cache regeneration, active dependencies and snapshot invalidation explicit; unsafe path assumptions replaced by enforced checks | PASS |
| Simplicity First | Exact byte source map plus bounded copy; no Godot, automatic deletion or general backup framework | PASS |
| Surgical Changes | Safety patch/provenance confined to plan; original fish, textures, model parameters and failed evidence preserved | PASS |
| Goal-Driven | Whole-set byte recovery and real negative CLI behaviors tested independently; mere hashes or successful process exit were insufficient | PASS |

**Karpathy Score:4/4.**

## 4. Adversarial Dimension Review

### 4.1 Design

Exact active file maps are suitable for recovering these ignored fixtures. Regenerable cache is explicitly omitted. `.godot` import regeneration/LOD/GPU equivalence needs its own later verification; byte restoration cannot grant it. No deletion executor was introduced. **PASS.**

### 4.2 Functionality

Read all145 lines of current restore tool. Independent normal/`-O` cases cover valid restore, relative/existing/dangling/ancestor-symlink output, absolute/parent/leaf-symlink/ancestor-symlink source, absolute/parent/duplicate/prefix-conflicting destination, badSHA/size and unknown fixture. Every refusal was nonzero and left original/external files unchanged; invalid input did not create a new output root. Final107/108 actual restores matched all active byte records. **PASS.**

### 4.3 Complexity

The no-follow directory handles directly address the demonstrated ancestor/source path escapes. No additional abstraction or cross-platform framework is required. **PASS.**

### 4.4 Naming

`restore-active` accurately excludes regenerable cache. `delete_now=false`, NON-STATE and explicit “not Godot/GPU/LOD acceptance” prevent confusion between recoverability and fish acceptance. **PASS.**

### 4.5 Comments

README lines9,17,19 correctly state that URL/oid/SHA are not offline source backups, Git LFS materialization is required, and the original downloaded copyright files will disappear offline if later deleted. Printed page metadata now distinguishes `head-guide-1.png` page1, `head-detail-3.png` page3 and whole PDF relevant page3. **PASS.**

### 4.6 Style & Consistency

Safety assertions/packed one-line CLI were replaced by explicit refusal checks. This is required functional correction rather than unrelated style churn. POSIX directory_fd/O_NOFOLLOW dependency and current macOS-only validation are disclosed; Windows portability is not claimed. **PASS.**

### 4.7 Context

README lines3,11,19 and plan `protected_now` explicitly protect both107candidate and108fixture while they remain inputs. Their48active bytes being equal does not authorize deleting either now. The active `resources/scripts/volume-fish/continuous_lip_exact_108.py` is outside all whitelist paths. Other later scripts/tmp, reviewer scratch, toolchains and historic user Godot are excluded. No fish* expansion is permitted. **PASS.**

### 4.8 Tests

Reviewer independently checked final six current trees,243 Git/LFS-backed active sources,29/tmp paths, gzip raw bytes and two actual restores. Separate independent32-case CLI run verifies the patched script. Author30-case/6-restore final reports are additional corroboration, not the sole evidence. Before-fix failures are retained and not relabeled. No Godot, production mesh, original fixture deletion or Git mutation occurred. **PASS.**

## 5. Findings Summary

| Severity | Finding | Resolution |
|---|---|---|
| High | Original removable assertions/path escape/overlay boundary | FIXED in current lines17–139; independently verified under normal and`-O` execution |
| Medium |108 is active too; title render page metadata incorrect | FIXED in final plan/README; page1 actually viewed,107/108 explicitly protected |
| Limitation | Cache/import/GPU/LOD state not reproduced; POSIX/macOS only; LFS raw source required | Explicitly documented, outside byte-restore approval |

No unresolved Critical or High findings in this scope.

## 6. Gate Decision

- [x] Automated checks pass within byte-restoration scope.
- [x] Security finding fixed and refusal behaviors independently checked.
- [x] Karpathy score4/4.
- [x] No unresolved Critical/High finding.
- [x] Final hashes and independent evidence recorded.

**APPROVE only recoverability and the boundary of a future precise whitelist cleanup. This is NOT authorization to delete the currently active107candidate or108fixture now.** Root may later act under the user's existing cleanup instruction only after relevant work is finished/idle, dependency release is explicit, and full current trees/source bytes/whitelist contents and process use are freshly rechecked. Any new tree or source byte invalidates this snapshot; do not expand the whitelist by prefix or wildcard. Failed experiment evidence and current new CPU scripts remain retained through completion. No extra user authorization is implied necessary by this internal review.

The reviewer retained compact proof and, with root's explicit authorization, removed only6 exact newly-created own scratch paths (3 disposable test/restore directories and3 own oneoff files), totaling46,328,737 regular-file bytes. Each root's counts/manifestSHA and removal outcome are in the independent proof. No original fixture or any of29 listed/tmp source paths was removed. No commit, push or Git-state mutation was performed by this review.
