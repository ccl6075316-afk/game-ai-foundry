# Review Report: `2026-11-12-arapaima-release`

## Metadata
| Field | Value |
|-------|-------|
| Reviewer | anvil-lead (primary agent, scoped independent inspection) |
| MR / Commit | staged Foundry and fishing-2d acceptance release |
| Author | Codex |
| Review Date | 2026-11-12 |
| Status | APPROVED |

## 1. Automated Pre-checks
| Check | Command | Result | Notes |
|-------|---------|--------|-------|
| Lint | git diff --cached --check in both repositories | PASS | No whitespace failures. JSON line-ending normalization in eleven table; semantic comparison proved other fish unchanged. |
| Type Check | Python ast.parse; actual Blender/Godot execution | PASS | New normal jaw runtime and current check/export entrypoints parsed and exercised. |
| Unit Tests | Existing asset integration validators | PASS | 490/072/077, actual canonical36,480controls/360transitions,4 pixel pairs, formal source independent byte-exact cold export. No unrelated application unit suite required. |

## 2. Security Scan
| Category | Finding | Severity | Status |
|----------|---------|----------|--------|
| Hardcoded Secrets | Narrow staged source/record pattern scan found none | None | CLEAN |
| Injection Risks | Export arguments parsed as Paths; subprocess lists and fixed project inputs, no shell interpolation | None | CLEAN |
| XSS Vulnerabilities | No HTML or web rendering changes | N/A | CLEAN |
| Dependency CVEs | No dependency changes | N/A | Not rescanned |
| Sensitive Data in Logs | Only model hashes, artifact paths, public references and validation output retained | None | CLEAN |

**Security Verdict:** CLEAN

## 3. Karpathy Adversarial Principles
| Principle | Adversarial Question | Author's Answer (Explicit or Inferred) | Verdict | Severity |
|-----------|---------------------|----------------------------------------|---------|----------|
| Think Before Coding | Can old fin acceptance survive a new body? | No; actual new490 identified and repaired roots, finite thickness and adjacent membrane. | PASS | None |
| Simplicity First | Is a runtime static builder needed? | No; source/GLB contain static changes, one species jaw wrapper uses existing normal controller. | PASS | None |
| Surgical Changes | Were accepted body or other fish changed? | Byte-level body/eye/mouth attributes and all texture bytes preserved; non-arapaima table entries equal, unrelated import products restored. | PASS | None |
| Goal-Driven Execution | Does success prove behavior rather than execution? | Signed actual skinned contact, GPU negative control, real hook, independent source export, exact pixel parity; full SOP limitations explicit. | PASS | None |

**Karpathy Score:** 4/4

## 4. Adversarial Dimension Review
### 4.1 Design — "Should this exist at all?"
| Line(s) | Question Asked | Author's Answer | Reviewer Assessment | Severity |
|---------|---------------|-----------------|---------------------|----------|
| Jaw wrapper, exporter | Can shared existing behavior be used? | Existing basal motion and FoundryJawMotion are reused; exporter freezes source-owned contracts. | Small species-specific entrypoints justified. | None |
**Dimension Verdict:** PASS

### 4.2 Functionality — "What is the author missing?"
| Line(s) | Question Asked | Author's Answer | Reviewer Assessment | Severity |
|---------|---------------|-----------------|---------------------|----------|
| Current fin domains | Can finite faces fail while root vertices pass? | Yes; original failure did. Finite surface refinement and whole490 membrane gate now pass. | Original domains and tolerances retained, no threshold workaround. | None |
| Mouth recipe | Is old head index reused? | No; explicit new upper rim vertex744 maps to outer808, two actual roof edges and real fishing binding checked. | Actual imported evidence passes. | None |
**Key Edge Cases Probed:** invalid/reused cold-export output rejected by assertions; maximum200cm budget3972/4000; jaw0/50/100%; maximum motion controls; fresh/cache; opaque reference and intentionally transparent body negative. Concurrent mutation excluded by input hashes. No new network-facing code.
**Dimension Verdict:** PASS

### 4.3 Complexity — "Can this be simpler?"
| Line(s) | Question Asked | Author's Answer | Reviewer Assessment | Severity |
|---------|---------------|-----------------|---------------------|----------|
| Repair history | Is the experimental chain required forever? | No; editable final source and cold exporter replace it. Small algorithm snapshots are historical only. | Dense poses/candidates deleted after numerical summaries; no new abstraction framework. | None |
**Dimension Verdict:** PASS

### 4.4 Naming — "Does the name lie?"
| Line(s) | Question Asked | Author's Answer | Reviewer Assessment | Severity |
|---------|---------------|-----------------|---------------------|----------|
| Release/SOP | Is all production labeled passed? | No; only runtime passed, full historical morphology/research/video pending. | User static acceptance is separated from motion aesthetics and complete SOP. | None |
**Dimension Verdict:** PASS

### 4.5 Comments — "Does this comment add value, or excuse bad code?"
| Line(s) | Question Asked | Author's Answer | Reviewer Assessment | Severity |
|---------|---------------|-----------------|---------------------|----------|
| Wrapper/method README | Is static geometry hidden in runtime? | Wrapper only normal jaw/motion; archive warns retired paths are not current reconstruction. | Comments match actual behavior. | None |
**Dimension Verdict:** PASS

### 4.6 Style & Consistency
| Line(s) | Issue | Type (Block / Nit) | Status |
|---------|-------|-------------------|--------|
| JSON runtime table | CRLF to LF normalization, non-arapaima parsed values identical | Nit | Documented; no semantic unrelated change |
| Measurement adapters | Existing local absolute paths reduce relocation portability | Nit | Documented; current exact audited adapters retained, canonical source is independent |
**Dimension Verdict:** PASS

### 4.7 Context — "Does this make the system healthier?"
| Line(s) | Question Asked | Author's Answer | Reviewer Assessment | Severity |
|---------|---------------|-----------------|---------------------|----------|
| Runtime/source/records | Can next work avoid stale experiments? | Formal source/GLB, current root domains, source cage, donors, release entry and explicit retirement records exist. | Static freeze and21/28 count recorded in both AGENTS. | None |
**Dimension Verdict:** PASS

### 4.8 Tests — "Do the tests prove it works, or do they just run?"
| Line(s) | Question Asked | Author's Answer | Reviewer Assessment | Severity |
|---------|---------------|-----------------|---------------------|----------|
| 490/077/canonical | Would wrong geometry/alpha/entry pass? | Earlier fin failures were rejected; transparent negative fails; canonical/static arrays and RGB checked independently. | Behavioral evidence adequate for scoped runtime release; unsampled continuous time not claimed. | None |
**Dimension Verdict:** PASS

## 5. Findings Summary
### Critical (Block Commit)
None.
### High (Block Commit)
None.
### Medium (Strongly Recommend Fix)
None.
### Low / Nit (Optional)
Measurement adapter absolute paths and runtime table line-ending normalization are recorded above. Historical method scripts are explicitly not runnable reconstruction entrypoints.

## 6. Gate Decision
| Gate | Status |
|------|--------|
| All scoped automated checks pass | Yes |
| Security scan clean | Yes |
| Karpathy score =4/4 | Yes |
| No Critical findings unresolved | Yes |
| No High findings unresolved | Yes |
| Review document complete | Yes |

### Verdict
- [x] APPROVE — scoped accepted static asset and runtime release. Full historical production SOP remains pending explicitly.

### Reviewer Notes
Baidu upload/readback and both Git pushes are operational closeout after this review, and must succeed before claiming submission complete. Primary agent review; no separate-agent review claimed. Numerical review receipt is under the game release directory.
