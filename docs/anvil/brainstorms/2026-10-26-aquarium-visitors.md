# Brainstorm: Aquarium visitors

## Problem Statement
The editable aquarium hall has no visitors. Add a small functional crowd without scaling draw calls or node counts per visitor.

## Assumptions (Explicit)
User clarified: match our own existing pixel art; other games inform reuse/crowd organization only. Geometry stays simple under detailed coherent pixel material. Adult and child proportions, palette/hair variants for women, men and older people. Default 24, cap 200; these are trial limits, not measured capacity promises. Walk and watch tanks only. Existing save data remains compatible; population preference is session-local.

## Domain Language
Visitor: decorative hall person. Base: shared geometry/proportions. Variant: palette, hair and face appearance. Viewing point: reachable position outside a tank, facing it.

## Functional Requirements
Generated source sheet through Foundry workflow and visual review. Few base meshes and shared actions. Walk around current obstacles, stop to watch exhibits, support empty or blocked halls. Layout edits invalidate routes. User can disable or change count. Keep existing edit/play modes and saves.

## Non-Functional Requirements
Shared rendering/material resources, bounded movement decisions, no physics or independent skeleton per visitor. Record measured CPU/draw/triangle deltas in actual renderer at 0/24/100/200, without conflating isolated crowd benchmark with full-hall frame rate.

## Security Concerns
No PII, accounts or credentials in artifacts. Existing configured Foundry image service receives only the design prompt. No new dependency or permission configuration.

## Open Questions
Style resolved by user: our existing artwork, not either reference game. Final visual acceptance remains user-pending.

## Success Criteria
Source artwork inspected; actual hall visibly populated with few reusable visitor types; walking and stopping visible; no observed tank/wall crossing in tests; count bounds and blocked layout pass; cost evidence and retained output inventory recorded.
