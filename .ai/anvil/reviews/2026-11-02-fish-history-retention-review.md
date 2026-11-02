# Review Report: `2026-11-02-fish-history-retention`

## Metadata

| Field | Value |
|-------|-------|
| Reviewer | anvil-lead |
| MR / Commit | Foundry maintenance/documentation and independent fishing-2d historical cleanup, pre-commit worktree |
| Author | Codex maintenance task; concurrent completed documentation reviewed separately |
| Review Date | 2026-11-02 |
| Status | `APPROVED` |

Scope: large evidence/asset deletion with two live restore tools, one focused test module, archival method snapshots and documentation. No model or gameplay changes. Current assets/original inputs/sources/key evidence are protected. Active unrelated dependency installation under `work/fish-database-nile-trial-20261102` is excluded from staging and deletion.

## 1. Automated Pre-checks

| Check | Command | Result | Notes |
|-------|---------|--------|-------|
| Lint | Both repositories `git diff --check`; AST parse live Python helpers | PASS | No configured linter for archived evidence helpers. Method snapshots are historical, not live executors. |
| Type Check | N/A | N/A | No static type checker configured for these maintenance helpers; no application API/dependency change. |
| Unit Tests | `.venv/bin/python -B -m unittest projects/fishing-2d/plans/reviews/local-cleanup-20261102/history-curation/test_restore_curated.py` | PASS | 21 behavioral tests, actual compressed archives and real files; fixtures under `work/`, removed. |
| Runtime / preservation | Existing before/after entry trace, protected hashes, read-only editable dependency audit | PASS | 28 current GLBs, 270 source entries unchanged; 27 loaded species, 524 resources, 216 digests identical. Existing blacktip assertion persists. |
| Recovery | Actual main-pool multipart restore, old-tool delegation, supplement and LFS rehydration | PASS | Exact SHA/size; retired content explicitly refused. |
| Git | Both `git fsck --connectivity-only --no-dangling`; deletion-scope validation | PASS | 15,527 tracked deletions all accounted for by authoritative cleanup lists. |

## 2. Security Scan

| Category | Finding | Severity | Status |
|----------|---------|----------|--------|
| Hardcoded Secrets | No credentials/private-key or token patterns in submitted text/evidence; local paths are provenance | — | CLEAN |
| Injection Risks | Restore copies selected member bytes into a guarded output file; does not extract paths or invoke shell | — | CLEAN |
| XSS Vulnerabilities | No web code changed | — | N/A |
| Dependency CVEs | No dependencies changed | — | N/A |
| Sensitive Data in Logs | No SSH authentication tokens captured; native LFS verification summaries only | — | CLEAN |

**Security Verdict:** CLEAN

## 3. Karpathy Adversarial Principles

| Principle | Adversarial Question | Author's Answer (Explicit or Inferred) | Verdict | Severity |
|-----------|---------------------|----------------------------------------|---------|----------|
| Think Before Coding | Is lack of runtime references alone sufficient to delete? | No: current/intermediate inputs, all sources and explicit current/final/SOP/negative evidence references receive additional protection. Unknown-purpose inputs retained. | PASS | — |
| Simplicity First | Is a new application abstraction necessary? | No: local restore utility and indexed immutable content only. Historical analysis/deletion executors are nonrunnable snapshots. | PASS | — |
| Surgical Changes | Does every change follow the request? | History/duplicate retention, exact restoration, LFS safety and source-policy documentation; current game/model bytes unchanged. Active concurrent trial work excluded. | PASS | — |
| Goal-Driven Execution | Does evidence prove actual cleanup and recoverability? | Execution receipts identify deleted bytes/OIDs, independent hash checks validate retained bytes, real restore and negative-path tests exercise behavior. | PASS | — |

**Karpathy Score:** 4/4

## 4. Adversarial Dimension Review

### 4.1 Design — "Should this exist at all?"

| Line(s) | Question Asked | Author's Answer | Reviewer Assessment | Severity |
|---------|---------------|-----------------|---------------------|----------|
| `history-curation/restore_curated.py:51-78` | Can the 6.7GB pool actually be pushed? | Split its existing byte stream into seven ordered volumes <=1GiB; verify each SHA and concatenated original SHA; stream without reconstructing another large file. | Original blocking size finding fixed; no content reclassification. | High, resolved |
| `history-curation/methods/*.snapshot` | Could obsolete deletion lists be run accidentally? | Execution context and hashes retained as snapshots; mac-audit executors likewise moved to snapshots. | No historical destructive script presented as a current tool. | PASS |

**Dimension Verdict:** PASS

### 4.2 Functionality — "What is the author missing?"

| Line(s) | Question Asked | Author's Answer | Reviewer Assessment | Severity |
|---------|---------------|-----------------|---------------------|----------|
| `restore_curated.py:81-146` | What happens after a truncated/bad restore? | Remove only the newly created destination file, never overwrite existing output; verify final SHA/size. | Retry behavior and existing file guard tested. | Medium, resolved |
| `restore_curated.py:149-171` | Can an existing cache bypass keep/size checks? | Consult retained record first; verify exact size and SHA even for existing cache; hard-link install refuses concurrent overwrite. | Retired existing-cache and altered-size cases tested. | Medium, resolved |
| `restore_curated.py:64-76` | Can wrong order, missing volume or symlink appear valid? | Per-part boundary/size/hash followed by combined original hash before output creation. | Failure tests cover all cases. | PASS |

**Key Edge Cases Probed:** empty parts, unknown/retired OID, corrupt/missing/wrong-size/reordered parts, destination equal to output directory, path traversal, symlinks, existing output/cache, failed-output retry, old backward hardlinks and ZIP providers. Concurrent edits to immutable archive bytes during a restore are outside the supported workflow; full final payload digest remains checked.

**Dimension Verdict:** PASS

### 4.3 Complexity — "Can this be simpler?"

| Line(s) | Question Asked | Author's Answer | Reviewer Assessment | Severity |
|---------|---------------|-----------------|---------------------|----------|
| `restore_curated.py:32-78` | Why not rebuild a monolithic archive? | That would temporarily duplicate 6.7GB; a bounded sequential reader is sufficient. | Small purpose-specific reader; no dependency or generic framework. | PASS |
| `restore_curated.py:105-139` | Are provider branches needed? | Existing retained working sources, old ZIP/tar archives and evidence supplements require compatible exact restoration. | Each branch exercised by behavioral tests. | PASS |

**Dimension Verdict:** PASS; no speculative hooks or abstractions.

### 4.4 Naming — "Does the name lie?"

| Line(s) | Question Asked | Author's Answer | Reviewer Assessment | Severity |
|---------|---------------|-----------------|---------------------|----------|
| `pool-verification.json`, `curation-index.json.gz` | Is pool.path still a physical file? | It is explicitly a logical archive label; `pool.parts` and `pool_repo_paths` name existing volumes. | Documentation and consumer updated together. | PASS |
| `restore_curated.py:149` | Is cache writing explicit? | `rehydrate_lfs` and the explicit CLI flag name the write effect. | No hidden mutation in ordinary restore. | PASS |

**Dimension Verdict:** PASS

### 4.5 Comments — "Does this comment add value, or excuse bad code?"

| Line(s) | Question Asked | Author's Answer | Reviewer Assessment | Severity |
|---------|---------------|-----------------|---------------------|----------|
| `restore_curated.py:126,166` | Do comments explain real constraints? | Backward tar hardlinks and no-overwrite cache installation have nonobvious reasons. | Relevant, no vague TODOs. | PASS |
| README / HANDOFF | Do old retained-cache statements conflict with the new deletion? | Earlier reports remain historical; submission supplement records successful direct-SSH remote verification and exact follow-up deletion. | History is not rewritten as if remote confirmation existed earlier. | PASS |

**Dimension Verdict:** PASS

### 4.6 Style & Consistency

| Line(s) | Issue | Type (Block / Nit) | Status |
|---------|-------|-------------------|--------|
| Live restore helper and tests | Standard Python; no formatting changes to gameplay or source assets | — | PASS |
| Documentation | Local-library policy changes separated from retention maintenance commits | — | PASS |

**Dimension Verdict:** PASS

### 4.7 Context — "Does this make the system healthier?"

| Line(s) | Question Asked | Author's Answer | Reviewer Assessment | Severity |
|---------|---------------|-----------------|---------------------|----------|
| `per-fish-manifest.json`, `assets-manifest.json.gz` | Are source completeness and acceptance overstated? | Four preexisting pointer-only sources and unknown exact export lineage explicitly recorded; no new fish acceptance. | Honest practical limits retained. | PASS |
| `runtime-retention/restore_retired.py` | Do old restore instructions silently point to deleted containers? | Superseded archive keys delegate to final index; retired bulk explicitly refused; owner directories carry redirects. | Full-file review and actual delegation test passed. | PASS |
| Fish reference policy docs | Does source reuse weaken species evidence? | Actual file/source SHA, species/body-part applicability, normalization and unknowns remain mandatory; modelling method independent. | Context/naming/comment review only; no new biological claim. | PASS |

**Dimension Verdict:** PASS

### 4.8 Tests — "Do the tests prove it works, or do they just run?"

| Line(s) | Question Asked | Author's Answer | Reviewer Assessment | Severity |
|---------|---------------|-----------------|---------------------|----------|
| `test_restore_curated.py` | Can digest/order checks be removed without failing tests? | Tests corrupt, remove, reorder and resize real compressed volumes, and assert absence of destination. | Behavior tests detect failures, no mocks of filesystem/archive internals. | PASS |
| Actual multipart smoke | Do tiny test files hide production layout errors? | Restore a real indexed object from production volumes and compare original SHA/size. | Real restore recorded; original monolith then deleted. | PASS |

**Dimension Verdict:** PASS

## 5. Findings Summary

### Critical (Block Commit)

None.

### High (Block Commit)

H1: Monolithic pool exceeds remote per-file limit. **Resolved** with byte-identical ordered volumes and tested reader; no single new LFS payload exceeds1GiB.

### Medium (Strongly Recommend Fix)

M1: Partial restore leftovers could block retries. **Resolved**, tested cleanup.

M2: Existing LFS cache bypassed preservation/size guard. **Resolved**, tested explicit retained-record check.

### Low / Nit (Optional)

None unresolved. Exact source-export lineage and preexisting pointer gaps are recorded limitations, not fabricated fixes.

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

- [x] **APPROVE** — all applicable review gates passed.

### Reviewer Notes

Only exact reviewed changes may be committed. Push/LFS completion and final disk/cache cleanup are execution checks after this code review; they must be verified before delivery. Do not stage unrelated active `work/` dependencies or claim clean status while a concurrent writer has unfinished changes. No history rewrite or force push authorized or needed.

Submission follow-up: the previously active Nile reference trial finished with its own done/ok report. Three immutable inputs and five output SHA records were checked; all 52 representative stations have valid engineering coordinates. Evidence moved once into the library, original paths mapped, script retained as a nonrunnable snapshot, linked records checked and duplicated unknown text removed. It was committed separately as `4d58f2e` (Foundry) and `73dc7d5d` (fish handoff). No model changed. Native raw logs keep original final blank lines under a narrowly scoped `.log` whitespace attribute, rather than rewriting evidence to satisfy formatting checks.

M3 submission-cache postcheck: deleting temporary cache hardlinks changed preservation-file ctime, and native Git clean rematerialized 12 independent cache copies. **Resolved** by normal index refresh followed by exact remote/source-hash-checked removal of independent copies; default status/diff/status repeated three times without regeneration. No filter or index suppression flags. Real proof: game history-curation/submission-review/cache-stabilization.validation.json. Current models still all match baseline. New concurrent shape-authoring code/profile and candidate outputs remain outside the reviewed/committed scope.
