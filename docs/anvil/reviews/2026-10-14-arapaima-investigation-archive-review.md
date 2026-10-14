# Review Report: arapaima head investigation archive

## Metadata

| Field | Value |
|---|---|
| Reviewer | anvil-lead / root |
| Scope | Diagnostic profile snapshots, code patch, visual evidence and documentation |
| Review Date | 2026-10-14 |
| Status | PASS for archival commit; no model acceptance |

## Automated Pre-checks

- `cd cli && python3 -m unittest test_volume_fish`: 30 tests pass on the updated remote branch.
- `git diff --cached --check`: pass.
- Eight arapaima profile JSON files parse; all relative links in the evidence index and copied reviews resolve.
- Active `resources/scripts/volume-fish/build_fish.py` has no staged change. The pre-sync local overlay diff is archived as a patch based on `d7a8c6a`, not applied to current code.

## Security Scan

No credentials, network call or executable behavior is introduced by this archive. Source images are review renders, not input secrets. PASS.

## Design and Functional Review

- The archive labels every v12–v18 candidate as visually rejected and keeps the accepted v11 GLB hash separate from those experiments.
- v15/v16 profiles depend on withdrawn prototype schema fields; the index states they cannot be rebuilt with the active builder. Their presence is historical evidence, not an endorsement.
- The patch is intentionally not merged: the remote commit `51ec6c9` changed the same builder to support top and belly sources, and the local overlay still leaves visible arapaima head defects. Applying it without a fresh integration and visual gate would risk other species. **No active model change is part of this commit.**
- Real world length and image silhouette are distinguished from artist-estimated depth and cross-sectional curvature.

## Gate Decision

**PASS for this documentation/code-snapshot commit.** This review does not approve any arapaima candidate for `volume accept` or game installation. Future active builder edits require new tests and visual review.
