---
type: debug-knowledge
status: SUCCESS
bug_topic: fish-school route/body coupling and dropped frame time
date: 2026-10-26
---

# Fish-school motion: verified prototype corrections

## Root cause

The prototype advanced the native fish controller, then replaced its carrier transform with an independent school heading. Native body curvature still differentiated the controller's private ellipse. Opposite school trajectories therefore produced identical local bone poses. Separately, interactive `min(delta,0.05)` discarded time before both simulation and animation clocks:8 supplied seconds became6 at15Hz and4 at10Hz. Far-tier5Hz held poses were a separate, explicit quality tradeoff.

## Fix approach

FixA wraps the exact factory-created controller. Its existing native clip, wave, fin constraints, species-specific dispatch and phases remain; delayed heading/pitch history from actual school velocity replaces the unrelated body steering term. Authored Turn bend limits remain engineering clamps. FixB uses a60Hz accumulator, at most8ticks per rendered frame, retains backlog and observes each consumed trajectory tick; the native pose evaluates once per rendered frame when due. Both defects had separate failing tests before implementation and passed on their first valid fix runs. Interactive full-frequency default is a separate presentation choice; explicit tiered mode still holds poses.

## Pattern identification

Advancing animation is insufficient when another layer overrides its world transform. Trace where curvature, velocity and carrier orientation originate. A fixed-step benchmark also does not prove that interactive wall time is preserved. Compare actual supplied/consumed seconds, native phases and pending time rather than reading animation position alone.

## Prevention

Preserve straight/positive/negative trajectory tests at equal native phases. Test8seconds at60/15/10Hz and a stalled frame with bounded backlog draining. Use quaternion relative rotations instead of self-angle comparisons susceptible to float noise. Inspect rendered mesh deformation at matched headings; bone counters alone cannot establish GPU or visual success. Freeze historical benchmark sources and write changed-source measurements to a new review directory.

## Related code and evidence

- `resources/runtime/godot/fish-school/FishSchoolMotionAdapter.gd`: actual delayed steering, native pose recomposition.
- `resources/runtime/godot/fish-school/FishSchoolReview.gd`: fixed clock, native pose cadence and placement; deployed copies are byte-identical.
- `resources/scripts/volume-fish/test_school_motion_v2.gd`, `test_school_clock_backlog_v2.gd`, `test_school_motion_adapter_v2.gd`:12,4,15 checks.
- `projects/fishing-2d/plans/reviews/fish-school-motion-v2/validation-report.json`: final state, source-bound reports, four refreshed benchmarks and visual evidence.

All four debug phase reviews approved; code review approved the isolated prototype. Native production files and species parameters remained unchanged. Actual two-fish Metal capture shows reversed body curvature; this is not biological, full-body collision, continuous fin-root or formal fish-asset acceptance. User visual acceptance remains pending.

One lesson: a fish's world trajectory and delayed body steering must consume the same motion history, and elapsed time must be accounted for explicitly.
