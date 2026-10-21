# Review Report: `2026-10-20-source-ink-104`

## Metadata

| Field | Value |
|-------|-------|
| Reviewer | Independent material_repair_review agent |
| MR / Commit | Uncommitted experimental module; Foundry runtime only |
| Author | Implementation agent |
| Review Date | 2026-10-20 |
| Status | `APPROVED` — experimental code/evidence archive only |

Scope: `FishSourceInk.gd`, `FishSourceInk.gdshaderinc`, `README.md`, and the added `check_source_ink_contract.gd`. The initial review blocked two rejection-guard defects; both are resolved below. No formal game installation or fish visual acceptance is approved.

Reviewed helper SHA256: `47da2224cd1e4543245723d755348826fd2cdcabf2a40c17e5d78b5f161547e2`.
Shader template SHA256: `b6fdd6c74288e69ed1011d7fe75c1d44bb455d1a5572f1ebb3b80ad29d81bfc8`.
Contract check SHA256: `e5dd78a5210a8ef595fb9350e84af9b10f68ee0a434815ed72e198be8c96640b`.

## 1. Automated Pre-checks

| Check | Command | Result | Notes |
|-------|---------|--------|-------|
| Lint | Whole-file inspection; no dedicated GDScript linter configured | N/A | No cosmetic changes requested. |
| Type Check | Godot headless `--check-only --script <FishSourceInk.gd>` with configured DOTNET_ROOT/PATH and `/tmp` log | PASS | Exit0 after fixing host launch environment. |
| Unit Tests | Godot headless `--script <check_source_ink_contract.gd>` | PASS | Independently run after fixes: exit0, contract assertions passed. Covers real helper expansion/wrapping plus unsupported calls, aliases, extra args, false comment hints, duplicate declarations, mip storage and alpha-zero RGB equality. macOS emitted a system CA certificate error after completion; not a module assertion failure. |
| GPU integration | `source-ink-104/preservation.validation.json` | PASS, bounded | Independently summed47 rows: mode0/baseline mismatch0; candidate outside RGB-probe influence0;51710 changed pixels.31 static +16 action frames, not continuous proof. |
| Fallback provenance | `source-ink-104/provenance.validation.json` | PASS | Actual opaque fallback reconstruction0 RGBA mismatches;3473 original ink texels extend to129827 coordinates, including126354 transparent coordinates. |

## 2. Security Scan

| Category | Finding | Severity | Status |
|----------|---------|----------|--------|
| Hardcoded Secrets | None found | — | CLEAN |
| Injection Risks | Explicit local shader transformation, known includes, no shell/network execution | — | CLEAN |
| XSS Vulnerabilities | No web output | — | N/A |
| Dependency CVEs | No new package dependency | — | N/A |
| Sensitive Data in Logs | Paths and rejection reasons, no credentials | — | CLEAN |

**Security Verdict:** CLEAN

## 3. Karpathy Adversarial Principles

| Principle | Adversarial Question | Author's Answer (Explicit or Inferred) | Verdict | Severity |
|-----------|---------------------|----------------------------------------|---------|----------|
| Think Before Coding | Are unsupported sampler operations and false declarations rejected? | Every protected sampler reference is inspected; only unique real native-nearest declarations and exact supported calls pass. Negative checks run against the actual helper. | PASS | — |
| Simplicity First | Are abstractions necessary? | Known include expansion and tokenized call-prefix rewriting preserve composite UV expressions without inventing a new material pipeline. | PASS | — |
| Surgical Changes | Does each change serve the request? | Exterior0 material copy only; same shader branches, RGB replacement only, original alpha, no source/GLB edits. | PASS | — |
| Goal-Driven Execution | Do checks reject defects rather than merely count calls? | Initial negative counterexamples now fail correctly; imported base-level equality and actual pixel preservation are separately checked. | PASS | — |

**Karpathy Score:** 4/4

## 4. Adversarial Dimension Review

### 4.1 Design — "Should this exist at all?"

| Line(s) | Question Asked | Author's Answer | Reviewer Assessment | Severity |
|---------|---------------|-----------------|---------------------|----------|
| `FishSourceInk.gd:152–259` | Is ownership bounded? | Assembled exterior ShaderMaterial duplicated after existing helpers; actual model path/hash and mesh are checked. | Appropriate experiment layer. Formal game remains untouched. | — |
| `FishSourceInk.gdshaderinc:8–34` | Is composite sampling preserved? | Source and fallback wrappers share RGB replacement while downstream calculations remain. | Appropriate for the demonstrated defect. | — |

**Dimension Verdict:** PASS

### 4.2 Functionality — "What is the author missing?"

| Line(s) | Question Asked | Author's Answer | Reviewer Assessment | Severity |
|---------|---------------|-----------------|---------------------|----------|
| `FishSourceInk.gd:75–115` | Can unsupported reads escape? | All occurrences of either sampler must be a valid declaration or two-argument texture first argument. | F1 resolved. texelFetch, custom functions, aliases, LOD and bias are rejected. | — |
| `FishSourceInk.gd:117–150` | Can comments masquerade as native-nearest declarations? | Comment-free tokens; real declaration grammar and unique count; conflicting filter/repeat hints rejected. | F2 resolved. | — |
| `FishSourceInk.gdshaderinc:9,26,29–34` | Is alpha/mode0 identity preserved? | OriginalRGBA at mode0; only RGB replaced otherwise. | Static review agrees, mode0 integration matches original. | — |
| `FishSourceInk.gd:189–226` | Are data inputs validated? | Raw PNG SHA/dimensions, every decoded baseRGBA byte, binary red mask, nonempty mask, donor bounds/alpha/exclusion. | Adequate technical constraints. Donor anatomy remains manual. | — |
| `FishSourceInk.gd:199–209` | Does clearing mips weaken source equality? | Only temporary decoded Image mips removed; all baseRGBA bytes, including alpha0 RGB, compared. Native sampler explicitly forbids mip sampling. | Correct comparison of the data actually sampled. Imported alpha-border RGB must be frozen as the real runtime snapshot rather than ignored. | — |

**Key Edge Cases Probed:** empty domain rejection in implementation; unsupported sampler operations; nested UV expressions; duplicate install; unavailable/stale data; wrong hints hidden by comments; duplicate declarations; alpha-zero RGB; unused mip storage.

**Dimension Verdict:** PASS

### 4.3 Complexity — "Can this be simpler?"

| Line(s) | Question Asked | Author's Answer | Reviewer Assessment | Severity |
|---------|---------------|-----------------|---------------------|----------|
| `FishSourceInk.gd:63–150` | Are parallel parsers inconsistent? | Declaration checking now reuses comment-free tokens. | Initial inconsistency removed; intentionally small supported grammar. | — |

**Dimension Verdict:** PASS

### 4.4 Naming — "Does the name lie?"

| Line(s) | Question Asked | Author's Answer | Reviewer Assessment | Severity |
|---------|---------------|-----------------|---------------------|----------|
| `_sampler_is_native_nearest`, README | Are claimed guarantees real? | Exact declaration checks and explicit experimental limits. | Name now matches checks. No automatic classifier or fish-delivery claim. | — |

**Dimension Verdict:** PASS

### 4.5 Comments — "Does this comment add value, or excuse bad code?"

| Line(s) | Question Asked | Author's Answer | Reviewer Assessment | Severity |
|---------|---------------|-----------------|---------------------|----------|
| Include/token/base-level comments; README | Are non-obvious boundaries explained? | Preserve composite UVs, original alpha, strict snapshot bytes and nearest coordinates. | Useful reasons and limits; no speculative TODO expansion. | — |

**Dimension Verdict:** PASS

### 4.6 Style & Consistency

| Line(s) | Issue | Type (Block / Nit) | Status |
|---------|-------|-------------------|--------|
| All files | Self-contained Godot experiment with explicit errors/receipts | — | PASS |

**Dimension Verdict:** PASS

### 4.7 Context — "Does this make the system healthier?"

| Line(s) | Question Asked | Author's Answer | Reviewer Assessment | Severity |
|---------|---------------|-----------------|---------------------|----------|
| README/runtime snapshot contract | Are source/import differences hidden? | Strict imported base-level source snapshot plus original opaque-pixel/provenance comparison retained. | Correct. Do not weaken fullRGBA validation. | — |
| Experiment archive | Does successful pixel preservation equal visual acceptance? | Current output still contains thin dark lines and stretched bands; visual acceptance=false, production_replaced=false. | Archive tool, evidence and limits; do not promote material. | — |

**Dimension Verdict:** PASS

### 4.8 Tests — "Do the tests prove it works, or do they just run?"

| Line(s) | Question Asked | Author's Answer | Reviewer Assessment | Severity |
|---------|---------------|-----------------|---------------------|----------|
| `check_source_ink_contract.gd` | Do initial counterexamples fail? | Actual helper called for texelFetch on both samplers, custom functions, alias, LOD/bias, comment and duplicate cases. | Independently executed successfully. | — |
| Preservation/provenance reports | Is integration evidence bounded? | Independent102 baseline; three probes against baseline; actual candidate outside union0; fallback reconstruction0. | Accept as47-frame evidence, not continuous-time or fish-anatomy proof. | — |

**Dimension Verdict:** PASS

## 5. Findings Summary

### Critical (Block Commit)

None.

### High (Block Commit)

None unresolved.

| Original Finding | Initial Defect | Fix Verification |
|------------------|----------------|------------------|
| F1 | Sampler reads not beginning with texture, including texelFetch, escaped detection. | Lines79–89 inspect every source/fallback token; actual negative contract checks pass. |
| F2 | Raw regex accepted commented valid hints over an actual linear declaration. | Lines117–150 inspect comment-free real declarations, require uniqueness and reject conflicting filter hints; line/block comment fixtures pass. |

### Medium (Strongly Recommend Fix)

No blocking code defect remains. Archive freshness should bind the current injected helper/template/config/snapshot/mask/donor hashes in the experiment's final curation validation: the generic capture receipt currently lists original game dependencies but not all dynamic104 injection inputs. This review records current code hashes; the integration report must retain its own input binding rather than imply screenshots alone prove code freshness.

### Low / Nit (Optional)

No cosmetic findings.

## 6. Gate Decision

| Gate | Status |
|------|--------|
| All applicable automated checks pass | [x] Actual contract check and bounded integration evidence |
| Security scan clean | [x] |
| Karpathy score = 4/4 | [x] |
| No Critical findings unresolved | [x] |
| No High findings unresolved | [x] |
| Review document complete | [x] |

### Verdict

- [ ] **BLOCK** — findings must be resolved before commit.
- [x] **APPROVE** — experimental source-ink104 code and evidence may be archived/committed; compound the verified mechanism and failed visual outcome.

### Reviewer Notes

No formal game installation or fish acceptance is approved. The current red-seabream material still fails the intended visual goal because thin residual lines and projected texture bands remain. Source-outline classification, actual lip/eye protection, material appearance and new fish delivery gates remain independent. Do not present the3473-pixel manual mask as a generic ink classifier, or47 discrete views as continuous coverage.
