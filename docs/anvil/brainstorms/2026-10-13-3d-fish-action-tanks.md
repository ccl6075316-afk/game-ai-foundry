# Brainstorm: 3D fish actions in individual tanks

## Problem Statement

User wants every existing3D species to perform visible actions in the3D hall, optionally in separate tanks. User explicitly selected first batch: Swim, Turn, Ascend, Dive.

## Assumptions (Explicit)

Cover blacktip reef shark, silver arowana, piranha and hairtail. Give each one a distinct physical tank in a shared gallery and offer per-tank focus plus overview. Keep the current meshes, textures, fixed shark eyes and calm-swim rig. Reuse accepted assets; no source-image/video generation is required. This is an action-observation gallery, not additional fishing/inventory gameplay.

## Domain Language

Tank: one species' bounded swimming volume. Action: selected fish's Swim/Turn/Ascend/Dive behavior. Turn: path-following change of heading plus delayed body bend; rigid carrier yaw alone is insufficient. Overview: observe all four separate tanks. Pause: freeze current showcase timelines; camera stays interactive.

## Functional Requirements

Four species, four visible actions each. Switch selected tank/action, replay, pause/resume, inspect any view and return to originating screen. Other fish remain in their own tanks, with calm swimming. Selecting an action starts an observable safe loop; no wall clipping, abrupt resets or unexplained stops before turns. Ascend/Dive change height and pitch while fins continue. Preserve species-specific body/fin patterns.

## Non-Functional Requirements

One shared3D viewport capped1280×720; hidden gallery does not animate or render. Native pixel materials remain nearest/matte. Tank dimensions allow turning envelope and real-length scale; close camera works for small piranha. No save/schema changes. Reusable motion controller and bounded profiles belong to Foundry resources and a JSON CLI handoff.

## Security Concerns

Local existing assets only, fixed bundled runtime script, bounded declarative configuration, model/profile/runtime hashes frozen. No arbitrary script execution field, credentials, new account integration, paid generation or save access.

## Open Questions

None blocking. User confirmed the four-action scope. Tank layout and camera presets are implementation choices within the stated showcase.

## Success Criteria

All16 species/action combinations have actual Godot evidence. Head follows movement direction, turns bend multiple body bones with tail delay, up/down change height with sensible pitch, fins animate, transitions are continuous, posed fish remain within their tank. Real GUI switches/pause/replay/overview/return work at representative window sizes. Four tanks are distinct. Current shark eye positions and original textures remain unchanged. Runtime/controller and input provenance are independently reviewed and recorded.
