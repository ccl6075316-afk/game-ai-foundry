---
type: debug-knowledge
status: SUCCESS
bug_topic: shark-eye-placement
date: 2026-10-13
---

# Knowledge: shark eye placement

## Root Cause Summary

The front planar UV projection overwrote the lateral eye region. Source eye centers nearly aligned, but front pigment sheared and spread over the tapered curved head; only70/804 side-eye dark pixels remained. The model and Godot hashes matched, so import scaling was not the cause. Overall source/style review and topology tests had not measured eye correspondence.

## Fix Approach & Why It Works

Represent each eye as one bounded native-side-textured patch aligned to the nearest head surface. Move competing side/front pigment to native skin donor UVs without changing source pixels. Use whole-face front donor islands: mixing shifted and unshifted UV corners can interpolate across the removed pigment. Keep body geometry and skin weights fixed. Default profiles preserve their prior behavior.

## Pattern Identification

An eye can look coherent head-on while distorting from the side because a frontal projection ignores axial position. Matching source rectangle bounds is not landmark correspondence. Protecting the side eye alone proved the cause but caused frontal eyebrow streaks; it was rejected as a final fix.

## Prevention Strategy

Check full eye support across every mesh, not a named eye mesh or a single ROI score. Require corresponding anchors, compact footprint, both sides and a real frontal/oblique review. Preserve baseline failure evidence. Guard derived eye geometry dimensions as well as input scalar bounds; a finite subnormal UV width can still yield infinite height. Mechanical texture/topology checks do not approve art quality.

## Verified Outcome

Formal041 GLB:5190f78e2cc6dfc37ca1d2b708102f46be6a38d5c65f37dd45582c0f63810929. Both eyes retain804/804 source dark pixels, side support approximately44.5×39.9 pixels and anchor error<0.59 pixels; original front eye pigment mappings0. Ten original meshes/weights unchanged, two thin closed eyes added. Native Godot checks66/66. CLI676 total:674 pass,2 existing skips. All four independent debug phase gates approved; Foundry acceptance and post-accept validation complete. No new image/video API calls.

## Related Code Locations

- `resources/scripts/volume-fish/build_fish.py`: head donor islands and optional surface-eye branch.
- `cli/volume_fish.py`: bounded declarative profile and derived eye-height checks.
- `cli/test_volume_fish.py`: compatibility and malformed eye/donor input tests.
- Game `041-eye.profile.json` and `041-eye-landmark-check.py` in `experiments/blender-fish/models/blacktip_reef_shark/`.
- `docs/anvil/debug-sessions/2026-10-13-shark-eye-placement-session.md` and `.ai/anvil/reviews/2026-10-13-shark-eye-placement-review.md`.

## Key Takeaway

Use one shared bounded eye surface across views; two independently projected painted eyes are not a coherent three-dimensional eye.
