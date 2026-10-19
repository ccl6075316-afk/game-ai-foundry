# Review Report: 2026-10-19-friendly-pixel-fish-preview

## Metadata

| Field | Value |
|---|---|
| Reviewer | anvil-lead / Agent self-review |
| MR / Commit | None; isolated visual experiment, no commit requested |
| Author | Agent |
| Review Date | 2026-10-19 |
| Status | APPROVED for preview code only; whole-fish acceptance remains pending/failing |

## 1. Automated Pre-checks

| Check | Command / evidence | Result | Notes |
|---|---|---|---|
| Lint/type | Actual Godot parse/import and 384-frame capture, headless audit | PASS | No standalone GDScript linter configured for this disposable project |
| Shader compilation | Actual OpenGL body GPU integrity capture | PASS | Actual GPU; opacity tested on current shader |
| Behavioral evidence | 082o-preview-code.validation.json | PASS | Six phases, burst/glide>3 ratio, all fins retain nonzero motion, source/GLB preserved |
| Unit tests | N/A | N/A | Art prototype; real engine and numerical fin/body checks used, no matching-implementation unit suite added |

## 2. Security Scan

Scoped new/modified scripts contain no credentials or network/shell execution; only explicit local model, settings, frames and audit files are read/written. No new dependencies. CLEAN.

## 3. Karpathy Adversarial Principles

| Principle | Answer / evidence | Verdict |
|---|---|---|
| Think Before Coding | User approved slightly reduced realism;6/10% shape and80% eye declared aesthetic choices, not anatomy claims | PASS |
| Simplicity First | Runtime prototype reuses original model/rig/motion/material; local eye mapping and six timed phases only | PASS |
| Surgical Changes | All new files isolated in fish-082o-friendly-preview; production asset hash unchanged | PASS |
| Goal-Driven | Actual before/after movie and face/body frames; collision/opacity evidence separate from subjective cute result | PASS |

## 4. Adversarial Dimension Review

### 4.1 Design

FoundryFishMotion.gd:127-132 applies a local optional affine scale from a frozen trusted trial profile, preserving first original scale to avoid repeated configure compounding. No production helper changes or reusable API claim. PASS.

### 4.2 Functionality

friendly.gd:36-65 explicitly restores baseline shape/eye for before and selects friendly shape/eye for after. Same camera/lights/source, manual carrier path is part of behavioral experiment. Presentation snapshot's inside_envelope refers to controller-computed internal motion; it is not proof of manual path tank containment. Movie visually checked for framing; no tank-safety delivery claim. PASS with scope limitation.

audit.gd:4-20 behavior source exactly matches friendly.gd:8-25, verified before numerical check. posed_export.gd selects original basal root vertices in model-local coordinates, then samples scaled actual posed surface in carrier coordinates. All7 fins present;33 authored-behavior poses include source-frame0 and final191, scale and variable controls. PASS.

### 4.3 Complexity

Scoped diagnostic copy of existing exporter keeps established triangle/weight sampling rather than inventing a second geometry kernel. Capture and audit share exact frozen behavior text verified by hash/content. For later production promotion consolidate behavior rather than extend these disposable copies. PASS for one trial; no general framework introduced.

### 4.4 Naming

presentation_shape_scale and friendly_eye_scale identify presentation choices. Reports distinguish source, shape, behavior and model acceptance. PASS.

### 4.5 Comments

No unowned TODOs or claim of biological measurement. Reports identify native/reference vs runtime scaled scope and discrete sampling limits. PASS.

### 4.6 Style

Main prototype follows prior SceneTree capture scripts; copied production helper has only isolated affine-scale addition. No unrelated code formatting. PASS.

### 4.7 Context

No source generation, asset acceptance or volume acceptance fabricated. Original red-seabream palette preserved. Known pectoral failure remains recorded. PASS.

### 4.8 Tests

Fresh177 root gate,16-view body integrity and33 custom full-fin poses. New behavior33 passes but cannot waive standard full490 or prior native failures. See final candidate report for full490 result. PASS for code prototype; model acceptance explicitly not granted.

## 5. Findings Summary

No Critical/High code findings in this fixed-input isolated preview. Low: duplicate behavior/exporter source should be consolidated if promoted into maintained runtime; current exact-content check prevents this trial's capture/audit drift. Global uniform baseline movement is a comparison, not a restatement of the full production exhibit path.

## 6. Gate Decision

APPROVE isolated preview code and evidence. Do not commit/install as accepted fish or infer complete continuous-time collision safety. No production deploy/commit authorized or performed.
