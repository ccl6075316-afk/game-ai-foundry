# Aquarium visitor trial architecture

Scope: projects/fishing-2d/plans/changes/aquarium-visitors-v1.production-delta.json. Match our original pixel visitor artwork; do not copy another game’s art. Default 24 visitors; 0–200 session-local count. No economic simulation.

## Assets and rendering
After Foundry source generation reaches done/human_review and visual source review, construct low-polygon reusable people with a single shared source-derived nearest-filtered atlas/material. Few meshes for proportions/hair, no independent skeleton or physics bodies. Save editable build source and prebuilt Godot mesh resources so game runtime only loads meshes. Use MultiMesh plus shader limb motion; per-instance phase and palette variation. Children have distinct proportions, not simply miniature adults. Gray hair differentiates older people. Preserve coherent natural compact proportions from source.

## Navigation and integration
A shared layout-derived walkable graph respects parcel union and inflated tank/furniture/wall footprints including actual doorway openings. Route decisions have a fixed budget, reuse reachable viewing goals, no per-agent nav nodes. Motion includes walk, smooth stop and facing a tank. Layout changes invalidate routes; no stale motion through new obstacles. Empty and disconnected layouts must not search forever. Session count and off control should be accessible in build and walking views without overlapping existing controls. No save schema change. Pause visitors while tank editor hides hall.

## Work ownership
Asset implementer: Foundry reusable model-builder source plus game visitor mesh/material assets and showroom capture. Runtime implementer: navigation/crowd, narrow hall integration, behavior tests. Lead: source artwork acceptance, interfaces, actual-renderer benchmark, visual inspection and mandatory anvil review. Do not touch concurrent fish-school or whale-shark changes.

## Validation
Actual Godot parser/runtime checks, path clearance and doorway/blocked layout tests, source-vs-model closeups, hall overview and walking frame samples. Benchmark fixed-camera 0/24/100/200 visitors with warmup and median/p95 frame, visitor CPU, draw calls and primitives; distinguish per-visitor increment from whole hall fish cost. Keep original art, source hashes, current models, compact reports and representative screenshots; remove failed duplicates and cache-only output. User acceptance stays pending until user reviews.
