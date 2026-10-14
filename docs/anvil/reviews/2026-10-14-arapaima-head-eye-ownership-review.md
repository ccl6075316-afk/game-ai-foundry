# Review Report: `2026-10-14-arapaima-head-eye-ownership`

## Metadata

| Field | Value |
|---|---|
| Reviewer | anvil-lead / root |
| MR / Commit | Local v17 profile experiment; no commit |
| Review Date | 2026-10-14 |
| Status | BLOCKED |

## 1. Automated Pre-checks

Foundry `volume plan → build → render` succeeded. Closed mesh, skin weights, finite GLB, animation loop, native texture size, nearest filtering, roughness, and root motion checks all passed. `git diff --check` passed. No new executable code or dependency was added.

## 2. Security Scan

No new network request, secret, or code execution surface. CLEAN.

## 3. Goal and Visual Review

- [Front render](../evidence/arapaima-head/v17-front.png): circular shoulder/head silhouette remains; dark fragments appear above both eyes.
- [Side render](../evidence/arapaima-head/v17-side.png): the eye patch overlaps the original eye region, producing doubled detail.
- [Oblique render](../evidence/arapaima-head/v17-oblique.png): head shape is still a tapered tube, rather than the accepted front source's layered forehead and jaw.

The existing profile fields do not achieve a single coherent eye placement and cannot alter the projected head/shoulder contour. Mechanical validation does not prove visual quality.

## 4. Gate Decision

**BLOCKED.** Keep v17 as an unaccepted diagnostic candidate. Do not copy its GLB to the game or call `volume accept`. The game GLB SHA256 remains identical to accepted v11: `8d5d1678c3beebcdaa123fd1a8c607615138ee8f9ec9f232dffcc72d14b2886e`.
