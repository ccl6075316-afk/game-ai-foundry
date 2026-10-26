# Review Report: `2026-10-26-aquarium-visitors-v2`

## Metadata

| Field | Value |
|---|---|
| Reviewer | anvil-lead and independent visitor_validation agent |
| MR / Commit | Working tree; no commit requested |
| Author | visitor_assets, visitor_runtime, visitor_validation |
| Review Date | 2026-10-26 |
| Status | APPROVED for integrated trial; user visual acceptance remains pending |

Scope: rebuild the user-rejected visitor art/model implementation, six archetypes and 18 appearances using shared resources. Unrelated fish work is excluded. Original v1 technical passes do not establish acceptance of v1 appearance.

## 1. Automated Pre-checks

| Check | Result | Evidence / limit |
|---|---|---|
| Frozen source workflow | PASS | v2 Foundry manifest done/human_review, three sources actually viewed, soft asset review accepted for agent trial only |
| Godot parser | PASS | New runtime/harness and actual Metal scene completed without visitor errors |
| Navigation and population | PASS | Final frozen report: 92 checks, 133,769 segments; 23/24 visitors move over 1 m; actual populations 24/200 and all 18 combinations; current resources bound |
| Mesh animation sweep | PASS | All 18 sampled: maximum radius 0.3566700535 m, navigation radius 0.37 m; six static sole minima at zero; animated minimum range −0.000779 m to +0.016547 m |
| Saved resource reload | PASS | Six saved meshes cold loaded; CUSTOM0–3 floating data verified by exporter reload; all 18 variants rendered |
| Actual renderer / normal entry | PASS | Metal actual counts 0/24/100/200/0; 41 current bindings; camera/layout unchanged; six groups read all appearance values 0/1/2; normal entry has 24 visitors, six groups and 18 variants; off/walk controls pass |
| Shell syntax / dry run | PASS | Scoped Mac Metal launch and normal main route, v2 log directory; both repository diff checks and Python AST parsing pass |

## 2. Security Scan

| Category | Finding | Status |
|---|---|---|
| Hardcoded secrets | No new credentials or secrets in visitor code/provenance | CLEAN |
| Injection | Quoted CLI arguments; no eval; local source/profile paths | CLEAN |
| XSS / database | No such execution surface | N/A |
| Dependencies | Existing Godot, NumPy and Pillow; no added package or service | CLEAN within scope |
| Network / logs | Existing user-authorized Foundry service and original style reference; no API keys retained | CLEAN |

## 3. Karpathy Adversarial Principles

| Principle | Adversarial question | Answer | Verdict |
|---|---|---|---|
| Think Before Coding | Does 18 mean 18 individually expensive rigs? | Six shared meshes with per-instance appearance; geometry deltas/UV slots share one material and actions. | PASS |
| Simplicity First | Is a generic crowd framework necessary? | Existing bounded navigation remains; only concrete six/18 contract and source-driven model build added. | PASS |
| Surgical Changes | Does this change fish/save/economy logic? | Only visitor resources/runtime/harness and practical launch docs; existing hall hooks retained. | PASS |
| Goal-Driven Execution | Are technical checks replacing visual judgment? | First sample explicitly blocked by both reviewers; actual gray/profile/painted defects fixed before family expansion. Final 29 views reviewed independently; lead inspected family front/profile/rear/clay/walk/ground, selected head closeups and actual hall. User judgment pending. | PASS |

## 4. Adversarial Dimension Review

### 4.1 Design

Six archetypes × three appearance selections retain six runtime MultiMesh groups, one shared atlas/material and GPU motion. No individual skeleton, material, physics body or light. Face/hair geometry can vary through stored deltas. The 200-person session trial and future 3000-person target are distinct; present floor area cannot justify a 3000-person claim. PASS for bounded trial architecture.

### 4.2 Functionality

`HallVisitorCrowd.gd:44` allocates ceil(200/6)=34 slots/group, avoiding truncation. Appearance coverage/distribution, missing elderly mesh, zero/clamped count, pause/recovery and geometry-only layout signature are tested. `HallVisitorNavigation.gd:6` uses 0.37 m after a sampled 0.35667 m mesh extent; separation derives from radius. Renderer-backed custom-data readback is required because headless dummy returns default Color values. Final evidence passes. GPU readback confirms 0/1/2 selectors in each of six groups with one material; visible differences among 18 identities were independently viewed.

### 4.3 Complexity

New complexity serves measured problems: source landmarks prevent facial distortion; separate pelvis/waistband prevents hem/thigh overlap; open nonplanar hair boundary avoids face-covering caps. No speculative economy, needs or broad animation system. PASS.

### 4.4 Naming

Six archetype resource names and three appearance selectors are explicit. Requested/actual count, active groups/variants and trial cap are exposed separately in review snapshots. PASS.

### 4.5 Comments

Comments explain float custom data, opposite Godot winding, hair cap geometry and source silhouette cleaning. They must describe the final method rather than claim perfect source equivalence. PASS; comments inspected against final behavior.

### 4.6 Style & Consistency

Existing hall line endings retained; practical launcher follows normal main scene route. Reusable builders/profile remain in Foundry resources, prebuilt final assets in the game repository. Both repository diff checks pass; no unrelated style rewrite.

### 4.7 Context

V1 remains rejected comparison evidence. V2 source sheets are agent-accepted modeling inputs; native adult head sheet is 1254² rather than requested 1536². Dedicated heads govern faces/hair and bodies govern clothes. No rear source exists; rear geometry/UV requires actual inspection. User acceptance is pending regardless of technical success.

### 4.8 Tests

Movement/clearance tests use actual resources and sampled movement, rather than only node existence. Appearance selectors are verified separately from visible identity differences. Static headless checks cannot validate shader output or appearance. Fixed-camera graphical measurements and motion images were completed and inspected.

## 5. Findings Summary

| Severity | Location / issue | Resolution / state |
|---|---|---|
| High | V1 aesthetic quality was rejected by user | New sources and substantive topology/UV rebuild; no automatic acceptance |
| High | `Sculpt.hair`: nonplanar bottom cap formed curtains across cheeks | Lower hair cap removed; skull closes hidden interior; actual profile/front inspected |
| High | Generic hair ellipse was smaller than skull and buried fringe | Hair follows authored skull envelope; full short cap visible in R4b |
| High | Face/profile source outlines became mask straps and duplicate ears | Face-only chart, measured landmarks, clean cheek donors, one geometric ear; same method individually applied to all 18 source charts and inspected |
| High | Independent thigh lofts overlapped shirt and made a crotch tab | Unified pelvis/waistband and proper shirt hem; actual front/profile inspected |
| Medium | Backlit clay preview hid facial geometry | Front key lighting, close gray profile/oblique proof; actual nose/brow/chin now visible |
| Medium | Border extrusion extended eyebrows into stripes | Boundary sampling chooses skin pixels while preserving central features; R4b inspected |
| Medium | Orange back-cheek band / regular hair / chin fragment / shoulder seam | Hard defects fixed in the final family; mild hair/beard simplification and painted cloth seams remain documented art limitations |
| Medium | Source-only cache and duplicate trial images | Two unique failed images and 29 final views retained; 14 stale/duplicate files removed after reference checks; source-only cache removed separately |

## 6. Gate Decision

| Gate | Status |
|---|---|
| Scoped automated checks | PASS; final hash-bound behavior, sweep, renderer and entry reports |
| Security scan | CLEAN |
| Karpathy principles | 4/4; final visual/behavior evidence reviewed |
| Unresolved High findings | None for the integrated trial |
| User visual acceptance | Pending |

**APPROVE the integrated trial.** User appearance acceptance remains pending; this review does not override their earlier rejection of v1. No commit or push performed.

Final actual-renderer medians (M4, Forward+ Metal, 1920×1080 hall SubViewport, 45 warmup and 180 measured frames/count): whole hall 7.848 ms at 0, 8.3025 ms at 24, 8.8805 ms at 100, and 10.114 ms at 200. Visitor CPU is 0.133/0.4265/0.7835 ms at 24/100/200. Repeat-zero median is 8.0465 ms, drift 0.1985 ms. This is one ordered run, without isolated GPU timing, a controlled six-versus-18 comparison or proof of 3000-person capacity.

Known limits: cap/bob/ponytail forms simplify source hairstyles; the Black elderly male side jaw does not reproduce the full source beard; painted clothing seams remain. Appearance vertex deltas reuse base normals, so shading is approximate for small shape changes. The gait has no IK or foot planting; sampled submillimeter penetration and up to 16.6 mm phase lift are recorded. Stills do not prove continuous foot contact. Existing dark blue hall lighting reduces color readability. Existing fish PNG export warnings and the Mac Compatibility fish sampler limit remain; packaged export and Windows execution were not certified.

Evidence: `output/visitors-v2/review/{asset-handoff,capture-manifest,swept-radius,navigation-behavior-validation,launcher-entry-validation}.json`; `plans/reviews/aquarium-visitors-v2/{runtime.validation,visual-review.validation,production.handoff}.json`. Editable sources: `build_visitors_v2.py:29,163,208,270`, `save_visitor_meshes_v2.gd:29,46`, `VisitorMaterialV2.gdshader:20`, `HallVisitorNavigation.gd:6`, `HallVisitorReview.gd:231,283`.

## Submission preparation (2026-10-26)

User requested commit and push. No runtime code or model changes in this preparation: 41 renderer source bindings, 11 frozen asset hashes and 29 capture hashes remain current. Python AST, launcher shell syntax, scoped secret scan and both repository diff checks pass. Visitor-only byte-preservation attributes, Chinese experiment summaries and the explicit 27-file scaffold/cache cleanup receipt were reviewed for naming, comments and context; no blocking finding. APPROVE visitor submission; preserve unrelated concurrent fish changes and pending user visual acceptance.
