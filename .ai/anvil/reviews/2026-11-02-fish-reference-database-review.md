# Review Report: `2026-11-02-fish-reference-database`

## Metadata

| Field | Value |
|-------|-------|
| Reviewer | anvil-lead |
| MR / Commit | Pre-commit scope: fish database, root README entry and scoped .gitattributes/.gitignore |
| Author | Codex |
| Review Date | 2026-11-02 |
| Status | APPROVED |

## 1. Automated Pre-checks

| Check | Command / evidence | Result | Notes |
|-------|--------------------|--------|-------|
| Lint | Python AST parse; strict JSON; staged diff whitespace | PASS | Research helpers, no application lint target changed |
| Type Check | N/A | N/A | No typed product code changed |
| Unit Tests | Native kernel/steering reports, 330+65 source ARM64 comparisons | PASS | Previously rerun from retained canonical scripts; no implementation changes since |
| Integrity | Stream SHA256/length of all1261 artifacts (3083042770 bytes), path registration and LFS attributes | PASS | Rechecked at commit preparation |
| Historical bytes | git filtered bytes of original migration evidence | PASS | Original CRLF CSVs explicitly exempted from newline conversion |

## 2. Security Scan

| Category | Finding | Severity | Status |
|----------|---------|----------|--------|
| Hardcoded Secrets | Plaintext private-key/GitHub/OpenAI token-pattern scan in retained text found no matches | — | PASS |
| Injection Risks | Helpers use fixed snapshot roots/URL and argument-list subprocess calls; inputs parsed as data | — | PASS |
| XSS Vulnerabilities | Local generated catalog pages are research browsing artifacts; source labels/links inspected | — | PASS |
| Dependency CVEs | No product dependency or runtime change; analysis package versions documented, tools removed; no live CVE audit claimed | — | N/A |
| Sensitive Data in Logs | Source URLs, hashes, metadata and research diagnostics; no user credentials found | — | PASS |

**Security Verdict:** CLEAN within this research change scope. APK/native bytes are retained input data and are never executed by the helpers as an Android application.

## 3. Karpathy Adversarial Principles

| Principle | Question | Answer | Verdict | Severity |
|-----------|----------|--------|---------|----------|
| Think Before Coding | Are game shapes and defaults presented as biological truth? | README use boundaries and per-source hashes explicitly distinguish references, unknown species/units and production acceptance | PASS | — |
| Simplicity First | Is a new service or framework necessary? | Plain manifests, files and narrowly scoped offline research scripts; no new service | PASS | — |
| Surgical Changes | Does scope include concurrent deletion work? | Only database, entry, LFS rules and this review; active cleanup in both repositories excluded | PASS | — |
| Goal-Driven Execution | Do comparisons prove the reconstruction? | Original ARM64 executes independently against readable formulas, with explicitly stubbed managed access/expf; no game/FPS claim | PASS | — |

**Karpathy Score:** 4/4.

## 4. Adversarial Dimension Review

| Dimension | Line / interface | Question and assessment | Verdict |
|-----------|------------------|-------------------------|---------|
| 4.1 Design | resources/fish-database/README.md:28; manifest.json | Versioned sources, LFS raw inputs, ordinary Git evidence; no coupling to production importer | PASS |
| 4.2 Functionality | motion-reconstruction/prepare_native_input.py:24; validate_reconstruction.py:35 | APK/native SHA-bound inputs; slices, signatures and synthetic cases align. Missing game runtime/configuration remains explicit | PASS |
| 4.3 Complexity | collection-scripts/acquire.py:39; reference_model.py:25 | Acquisition confined to one declared snapshot; readable core preserves observed quirks to reproduce evidence, not a new production engine | PASS |
| 4.4 Naming | FishFlock.type-map.cs:1; reconstruction-report.json | Metadata placeholders clearly labelled; lexical base-name counts do not claim biological species | PASS |
| 4.5 Comments | motion-reconstruction/README.md:5 | Runtime, scheduler, live Lua configuration and animation coupling unknowns documented; source defects not passed off as intended biology | PASS |
| 4.6 Style | .gitattributes; historical migration CSV entries | General indexes normalize to LF; original hashed historical CSV bytes require explicit -text exception, now fixed | PASS |
| 4.7 Context | README.md:76; fish-database/handoff.md | Durable recovery entry and cleanup record preserved. No current fish/plant assets or active maintenance outputs changed | PASS |
| 4.8 Tests | verify_full_step.py:31; verify_native_kernels.py:57 | Tests execute original code with deterministic fixtures and null-pointer guard; all395 comparisons pass, including known negative cases. Not real engine playback | PASS |

Edges reviewed: zero-distance NaN,180-degree heading stall, per-group neighbor cap, repeated priority entries, in-place update order, box/sphere point-only avoidance and missing source dependencies. Research scripts intentionally preserve source failures; no production adoption asserted.

## 5. Findings Summary

| Severity | Location | Finding | Resolution |
|----------|----------|---------|------------|
| High | .gitattributes; migrated fish-catalog.csv/all-indexed-objects.csv | text/eol=lf would change hashed original CRLF bytes on another checkout and break migration evidence | Added two exact-path -text / cr-at-eol exceptions; filtered staged bytes checked against migration SHA |
| High | .gitignore | Generic media/progress ignores omitted original preview PNG and durable progress.json | Added canonical database exception; exact disk/index file-set comparison and all1261 pointers pass |
| Low | Generated type map/disassembly and reference_model.py EOF | Generated padding and extra EOF blank lines | Removed whitespace only; Python AST unchanged, method-file SHA updated |
| Critical / High unresolved | — | None | — |
| Medium / Low unresolved | — | None in this scope | — |

## 6. Gate Decision

| Gate | Status |
|------|--------|
| All applicable automated checks pass | PASS |
| Security scan clean within scope | PASS |
| Karpathy score =4/4 | PASS |
| No Critical findings unresolved | PASS |
| No High findings unresolved | PASS |
| Review document complete | PASS |

**APPROVE** for the scoped database commit. Concurrent history-cleanup changes in docs/MAINTENANCE-ARCHITECTURE.md and projects/fishing-2d remain owned by the active cleanup chat and are not included. No merge request or deployment requested.
