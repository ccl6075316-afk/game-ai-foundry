# Fish school motion debug — 2026-10-26

Mode: Normal. Runtime v1 logs, code and user observation available. No fix attempted. Strike count: 0.

User evidence: In the fish-school scene, sailfish and whale shark appear almost motionless and turn rigidly, described as an aircraft carrier turning.

Scope: Investigate isolated prototype locomotion/animation coupling and timing. Preserve existing production GLBs, materials, skeletons, native controller and v1 benchmark evidence. No fish anatomy/appearance acceptance inferred. Per-phase independent adversarial review required before progressing.

Evidence inventory: v1 reports under projects/fishing-2d/plans/reviews/fish-school-v1; baseline byte snapshots under fish-school-motion-v2/baseline-v1; diagnostic probe assigned, no fixes authorized before root-cause gate. Code paths: FishSchoolReview._process/_place, FishSchoolSimulation.configure/_decide/step, FoundryFishMotion.step/_capture_base_and_pose/_path.

Initial unconfirmed hypotheses: native phases may be advancing but low amplitude plus held poses reduce visible movement; school heading replaces carrier orientation while native body curvature follows old ellipse; shared world-speed and small point-radius ignore species body length; interactive min(delta,0.05) may slow simulation under low FPS. Each must be tested separately. Uniform speed, native conservative profiles and fixed cohorts are known prototype assumptions, not established biological behavior.

Recent-change correlation: these prototype files were introduced uncommitted in the preceding user-authorized experiment; no older committed implementation. Production controller/profile files predate the prototype. Existing whale-shark dorsal work is concurrent and outside this task.

## Phase 1 — root cause evidence

Actual factory-loaded sailfish/whale shark/bluegill/tuna, 480 controlled ticks, diagnostic.validation.json: clips, local body joints and fins have nonzero changes. At identical native phases, opposite and reversing carrier paths produce exactly identical bone quaternions (maximum component difference 0). Native body steering differentiates its private ellipse; FishSchoolReview._place subsequently replaces the carrier transform using independent school velocity. Actual trajectory curvature is never supplied to body posing. This establishes a transform/steering data-flow bug; local bone motion alone does not establish rendered tail displacement or subjective visual acceptance.

Independent clock reproduction: 8 seconds supplied as 60/15/10 FPS advances 8/6/4 simulated seconds because _process uses min(delta,0.05). Native animation clocks inherit the same loss. Far tier holds 440/480 frames with only 40 pose updates; carrier still changes between updates. This is an explicit quality tradeoff in V1, not evidence of a stopped clip.

Independent 20-second point simulation: whale shark center median ~1.61m/s (0.20 current full lengths/s), sailfish ~1.43m/s. Its authored native whale path spans ~0.98–1.57m/s, so absolute speed being too low is not established. Uniform world-speed/turn parameters and point radius are prototype limitations, not an excuse to raise species amplitude/speed arbitrarily. Kinematics report records actual projection/truncation events separately.

Baseline code/asset bindings unchanged (755 runtime sources). Exact V1 code snapshot preserved. Diagnostic exited cleanly; only narrowly identified macOS CA warning. Reproduction and units in motion-v2/diagnostic.validation.json, kinematics/findings.md and the two external probes. No fixes attempted, strike 0. Pending independent Phase 1 gate.

Phase 1 gate APPROVED: phase1-review.md, Q1–Q5 yes. GPU skinning/subjective quality remain independent validation requirements.

## Phase 2 — pattern comparison

Full native Exhibit + FoundryFishMotion form the first working reference: one private path controls carrier/head anchor and delayed body steering; real delta advances clocks, manual AnimationPlayer preserves native fin constraints. The second reference, full IntermittentFishGait.gd plus body_swim_gait132.gd/trial_swim_gait132.gd, explicitly separates travel and oscillation clocks and reapplies delayed steering independent of coasting amplitude; it is an opt-in experimental example, not a cross-species approved gait. Its own .25s cap is explicit dropped_seconds policy, unsuitable for silently discarding school elapsed time.

Differences and dependencies are recorded exhaustively for the affected boundary in kinematics/findings.md: school replaces native carrier/head-anchor output; actual yaw/curvature/speed has no return path to skeleton; uniform world speed/turn/radius; 60/15/5 held pose groups; interactive .05s clamp; benchmark fixed tick rather than wall time; no speed-to-beat coupling; no full-body collision. Native private path derivatives, .30s smoothing, body-delay history, normalized body distances, head_sign, rest yaw/pitch axes, action limits and paired-fin constraints must stay coherent. Viewer must retain factory guards, asset/material bindings and current source snapshots. Actual native body and fin amplitudes are nonzero; GPU visual outcome remains unproven until capture.

Dependency/environment checks: .NET Godot4.7.1/M4 Metal, existing imported production resources, source meshes unchanged, Apple GL sampler limit requires Metal, 3 hammerheads remain excluded by original import source gate; no guard bypass. Native fin constraints must not be replaced by general symmetric flap. Do not reuse bluegill132 numerical parameters or claim all movement anatomy validated. Pending Phase2 independent gate; no implementation attempted.

Phase2 gate APPROVED in phase2-review.md, Q1–Q4 yes. Proceeding to two independent minimal failing tests, with production source unchanged.

## Phase3 — hypotheses and pre-fix test design

H1: school trajectory does not drive body steering because native posing differentiates its unrelated ellipse. At identical native phase, controlled straight/positive/negative school yaw inputs should produce opposite nonzero residual steering (subtract straight to isolate steering from clip/wave); current implementation predicts exactly zero difference. Test actual sailfish and whale shark, real imported skeleton rotations and native yaw axes, not a missing hypothetical API.

H2: interactive .05s clamp is the source of slow motion under long frames. For supplied8seconds at60/15/10FPS, elapsed and correctly scaled controller/body/fin clocks should all account for8seconds; current predicts8/6/4. Test independently with fresh contexts, no GPU FPS assertion. Alternative stopped-clip/zero-fin-track explanations were rejected by rawclip and native-step probes; whale absolute speed being too low remains unsupported; GPU appearance remains separate.

Executed faithful actual-viewer contexts via _build_world and await _populate, normal factory/controller configuration and source guards (not a manually invented adapter API). Regression script test_school_motion_v2.gd frozen before runtime edits; baseline report regression-baseline/regression.validation.json (16,818B). Both fish A responses are exactly0 and fail; B60Hz passes8seconds,15Hz yields6,10Hz yields4, school-full10Hz also yields4. Controller initial phase offsets subtracted, clip/body/fin rates read and expected clocks derived.12checks,8expected failures, setup and755source bindings stable; exit1 as expected, no non-environmental errors or shutdown leaks. No fixes attempted. Pending Phase3 gate.

Phase3 gate APPROVED in phase3-review.md, Q1–Q5 yes. Frozen regression hash verified. Phase4 must implement/verify steering and clock defects separately; GPU visuals not yet accepted.

## Phase4 — implementation

FixA delegated after gates: isolated adapter wrapping the exact factory-created controller, retain native clip/wave/fins and model bindings, feed actual school yaw/pitch history to delayed body steering. Existing species Turn bend is an engineering clamp, no new biology tuning or native asset edits. Verify A passes while unfixed B remains baseline before proceeding to FixB. Strike count0.

FixA first valid run: sailfish positive/inverse steering residuals −/+0.1925rad summed local joints; whale shark −/+0.16rad (authored clamp). Both A assertions pass; unfixed B remains8/6/4seconds. Initial launch omitted Forward+ and was rejected before fish setup; preserved as setup failure, not a tested fix failure. External adapter contract15checks pass: seam, stationary/vertical orientation, unchanged native base/wave and local fin poses, one native step, delayed reversal, pitch, bounded history, invalid-input rejection. Float self-angle noise in the test oracle was replaced by normalized relative-quaternion atan2 without runtime changes. Production preservation report:754 original bound files unchanged, excluding only prototype Viewer; one new adapter allowed, no unexpected changes. Strike0.

FixB independently tested before implementation: .5s stall+60×1/120s inputs =1s, old clock consumed only.55s including native/adapter clocks. Implemented fixed60Hz accumulator, max8ticks per frame, retained backlog, per-tick trajectory observation and one due native pose per render. Frozen regression12/12passes: all60/15/10Hz inputs advance8s; focused backlog4/4passes:1s supplied/consumed, first frame8ticks=.133333s. No fix failures. Separate presentation decision: interactive default full-frequency so quality review is visible; explicit tiered performance mode remains held poses and is labelled. Benchmark clock remains exactly1tick/render, independent of wall time.

Final source freeze, GPU comparison, refreshed benchmark, independent Phase4/code review and cleanup pending. Do not claim subjective or biological acceptance from these numerical checks.

Final verification: actual Metal frozenV1/current videos each192frames/8.000s, native phases matched after1s straight pre-roll. Primary and independent reviewer inspected close top/oblique images: bodies reverse curvature at matched carrier heading, so rendered mesh changes were verified beyond bone counters. All four refreshed25-species benchmarks passed source/settings checks;50full/tier median17.247/8.266ms,200full/tier55.959/33.127ms. Benchmark150ticks/2.5s total and120sampleticks/2s; native posecounts6000/1900/24000/7600. No realtime capacity or old/new speedup claim. Tiered still holds poses.

Phase4 Q1–Q6 APPROVED and mandatory code review APPROVED, no findings. Review at .ai/anvil/reviews/2026-10-26-fish-school-motion-review.md with byte-identical code-review.md copy. Final12+4+15+25+10 automated checks pass. Strikecount0; only invalid setup/test-oracle issues occurred before valid verification, with no runtime retry changes.

Knowledge saved to docs/anvil/knowledge/2026-10-26-fish-school-motion.md; reusable method appended to performance-audit.md, per-fish unchanged parameters/actual evidence in motion-review.md.384generatedPNGframes/139,881,230B removed after encoding/integrity validation; representative stills, videos, frozenbaseline, unique failure/final reports and engine logs retained. Cleanup report lists duplicate removals. Current production assets/other whale-shark chat work were preserved. Updated50fish/full-frequency interactive preview opened and deliberately left running. Existing red-seabream source-image export warnings were recorded; no game packaging was attempted.

Terminal result: two identified prototype bugs verified fixed; all debug gates passed; user visual acceptance and formal fish/body/fin/anatomy gates remain pending outside this experiment. No commit/push requested or performed.
