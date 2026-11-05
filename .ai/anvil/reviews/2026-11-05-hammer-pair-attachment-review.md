# Review Report: `2026-11-05-hammer-pair-attachment`

## Metadata

| Field | Value |
|---|---|
| Reviewer | anvil-lead (Codex operator) |
| MR / Commit | Scoped Foundry and fishing-2d candidate changes; not canonical installation |
| Author | Codex |
| Review Date | 2026-11-05 |
| Status | APPROVED for scoped candidate commit; user visual acceptance pending |

## 1. Automated Pre-checks

| Check | Command | Result | Notes |
|---|---|---|---|
| Lint | git diff --check in both repos; Python AST parse | PASS | Current changed/new Python source parses; actual Blender/Godot execution separately required |
| Type Check | No configured standalone Blender/Godot static checker | N/A | New-process author/cold/native scripts provide runtime type and binding evidence |
| Unit Tests | PYTHONPATH=cli:resources/scripts/volume-fish python -m unittest test_volume_sop test_volume_cleanup | PASS (33 tests) | Initial wrong import-path invocation failed; corrected invocation recorded |
| Actual assets | Fresh complete490 root/membrane, 077 GPU, source/export parity, finite normal thickness and tail section, mouth and native visual review | PASS | Current R40 full490/072/077/volume/cold/control/native receipts; rejected intermediates excluded |

## 2. Security Scan

| Category | Finding | Severity | Status |
|---|---|---|---|
| Hardcoded Secrets | No new credential literals or authentication material in scoped author/review scripts | None | CLEAN |
| Injection Risks | Local explicit paths; subprocess argv arrays, no shell execution of source text | None | CLEAN |
| XSS Vulnerabilities | Local review page uses constant species labels and owned artifact names | None | CLEAN |
| Dependency CVEs | No new package/dependency installation | None | N/A |
| Sensitive Data in Logs | Local asset paths and diagnostics; generation/provenance must remain credential-free | None | CLEAN after staged scan |

Security Verdict: CLEAN for reviewed scope; final staged scan required.

## 3. Karpathy Adversarial Principles

| Principle | Adversarial question | Answer | Verdict |
|---|---|---|---|
| Think Before Coding | Does a root point on body prove whole cap attachment? | No. R35/R36 point gate passed while original cap triangles crossed body facets. Exact full-footprint clipping is required. | PASS: exact full-footprint finite clipping |
| Simplicity First | Is another renderer or runtime builder needed? | No. Ordinary editable sources/GLBs; current standalone renderer reused. | PASS |
| Surgical Changes | Is every shape change requested? | Chest only to measured blue-white boundary; accepted R27 head/back retained; tail joint geometry corrected. High .58/.60 root placement was rejected and is retired. | PASS after final visual check |
| Goal-Driven Execution | Do checks detect the actual failure? | Whole-cap distances/membranes reject vertex-only projection. Constructed thin/flat/transparent negatives remain active; geometry photos are still separately inspected. | PASS: current R40 actual gates |

## 4. Adversarial Dimension Review

| Dimension | Specific evidence/question | Assessment |
|---|---|---|
| 4.1 Design | author_hammerhead_fin_attachment.py full-root relocation and shared tail envelope; separate finite cap clipper | Existing source flow retained; no common runtime static patch or canonical fish mutation |
| 4.2 Functionality | Root boundary across multiple finite body facets | High finding fixed by finite_cap_fix under review §6; exact whole footprint retained, 4524/3970tri; current full gates pass |
| 4.3 Complexity | New exact clipper versus material-only workaround | Necessary to preserve full region and pose-conforming body triangles; rejected alternative code is not production default |
| 4.4 Naming | Author, compare, validate and capture roles | Explicit CLI roles; numerical reports never name user acceptance |
| 4.5 Comments | Geometric assumptions/unknowns | Distinguish source art and engineering interpolation from biological measurement; preserve rejected direction and cause |
| 4.6 Style & Consistency | Existing Python/Blender/Godot helper patterns | Surgical extensions; no unrelated formatting changes; parse and actual process checks |
| 4.7 Context | Sources, evidence, cleanup and two repo scope | Preserve current source, original art, full numeric records and few representative images; retire dense/rejected outputs; exclude concurrent bream/salmon work |
| 4.8 Tests | Whole surface instead of point-only/full-plane width alone | Final fresh pose, cap, opacity and cold proof required; no threshold relaxation |

## 5. Findings Summary

| Severity | Location | Finding | Action / status |
|---|---|---|---|
| High | author_hammerhead_fin_attachment.py projection + embed_shark_fin_roots_in_body.py constraints | Projected endpoints do not make old cap triangles lie on current finite body; selected centroid patch shrinks footprint | Exact full-area body clipping, mirrored cap topology/weights and free-edge splits; dispatched to finite_cap_fix |
| High | Rejected R34/R35 root fraction .58/.60 | User requested small move to blue-white border, not high blue flank | Fixed: actual five-section body-pigment measurement gives .28/.30; dz .091602/.038773 m at 4/3 m display length |
| Medium | Tail cross-section single-plane check | Correct width at cap can coexist with visible V-notch/ledge behind it | Shared upper/lower/width envelope across both sides; actual gray-model before/after required |
| Low | Test runner path | Package-style unittest invocation cannot resolve CLI local imports | Correct PYTHONPATH invocation; no test assertions changed |

## 6. Gate Decision

- [x] All final asset checks pass
- [x] Corrected unit tests pass
- [x] No new dependency or credential handling
- [x] Final staged security/size scan clean
- [x] No unresolved High findings
- [x] Full source/candidate references retained after exact cleanup

Verdict: APPROVE the scoped code/current-source candidate commit. No user acceptance or canonical installation. Current root/membrane/volume/opacity/cold/mouth/side-flow evidence is green. The shared unfinished CLI import patch is excluded; SOP is independently validated against the exact published HEAD + own scope via a read-only source snapshot, with unchanged criteria. Snapshot and dense artifacts are not shipped.

Fix verification: rebuild_finite_pectoral_caps.py full-area clipping, reverse body cap and matching free-edge splits; finite-cap-r40/*.validation.json and current fins490-r40, volume-r40 receipts. Current standard SOP reports use the published-code hash set in sop-code-isolation.validation.json. Original blocked vertex-only/cap-centroid candidates retired. No unresolved High/Critical findings.
