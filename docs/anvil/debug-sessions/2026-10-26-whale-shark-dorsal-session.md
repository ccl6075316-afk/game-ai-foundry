# Whale shark dorsal material investigation

Mode: Normal. Date: 2026-10-26 (Asia/Shanghai).

User: Continue fixing the whale shark's back spots/material; current appearance remains unsatisfactory. User has not yet specified a single priority from the optional question. Previous accepted direction requires original centreline and aligned longitudinal rows, not staggered/random spots.

## Evidence and initial scope

- Actual configured model159: `8a10d9ba17defee7c1e72ebe8bf31e2485aa2c433606e42ef7d863edfe24e261`; material body158: `11f6ee4d33e4475cc299497812f92a9b0f0d26dbe968282e56d1771af3829bf1`.
- Current FinalizedFish157 loads the static GLB and this body resource. Main game resources have not been modified.
- Archived159 views and original151/152r2 top artwork inspected directly. Current fresh GPU views: `work/whale-shark-spots/baseline-r2/`. Isolated actual resource rendering, not the complete game or action certification.
- Native154 skin1152×576 is retained; it contains 24 aligned columns, a thin centreline and approximately oval pixel clusters. Its own native shape is not asserted to be a perfect circle.
- Existing flat shader maps a scalar arc-distance field from153 through immutable transported reference positions. Shape158 changed actual geometry without replacing these reference positions, intentionally preserving old appearance. That is appropriate for feature ownership but not automatically for physical metric calculations.
- Export `work/whale-shark-spots/surface.json`: 12,772 current vertices and corresponding material reference positions. For posterior trunk x∈(-.30,.20), |reference.z|>.01, actual/reference lateral scale ranges0.823–1.302; median0.969. The field cannot represent current surface distances throughout the revised body. Maximum |x difference|.0257 occurs elsewhere in the head; posterior x differences need separate exclusion.
- Artist-only first candidate changes longitudinal/width scale with an integrated phase. Tail size transition improves, but oblique elongation remains. This is a local experiment, not a successful bug fix or final asset. Its compiled GPU version uses the existing arc texture's spare channels; a first17-sampler attempt failed the Mac Compatibility16-sampler limit and was discarded.

## Phase1 root-cause hypothesis

The obsolete physical arc metric contributes to visible distortion on revised body158/159. Preserve feature/ownership reference coordinates and native raster, but evaluate dorsal-only surface distance using the actual current body mapped into that reference chart. Confirm independently by reconstructing actual transverse section lengths and comparing old field values on held-out body vertices/triangles. This does not assert that all aesthetic defects are caused by the metric, or that correcting it automatically earns user acceptance.

Current report/state: `work/whale-shark-spots/migration.validation.json`, material/GPU validation reports. All complete159 physical/body/SOP gates remain pending as before.

Phase1 confirmation: history inspected (Foundry4f5f0bf / Fish358bedb7 retain159 and its158 dependencies). The actual155×64 rings still exist; posterior x is unchanged. `old-metric.validation.json` records630 independent current-ring probes: obsolete distance relative error median8.74%, P9519.06%, max19.87%. Independent reviewer reproduced the old LUT hash and showed it matches the old reference-ring metric to<4e-7. Phase1 approved for this specific metric mismatch, not all appearance issues.

## Phase2 pattern comparison

Read in full: `projects/whale-shark-153/prepare_arc153.py`, `measure_distortion153.py`, `resources/scripts/volume-fish/build_surface_distance_skin.gd`, `LowPolyFishTransport.gd`, actual `FinalizedFish157.gd` and `MouthRepair139.gd`.

Working numerical example153: original64-point polygonal transverse rings, cumulative real YZ distances from crown, float LUT sampled linearly, original raster sampled nearest. Independent153 triangle Jacobian diagnosis separates metric distortion from artwork quality; its rejected staggered raster is not reused. Working feature-transport example139/158: immutable original material coordinates preserve mouth/eye/gill/colour ownership even when geometry moves. These two mechanisms have different purposes; transporting old feature coordinates is correct, reusing their old physical metric is not.

Differences: actual158 ring YZ changed; reference coordinates and153 R-channel arc did not; X and original ring correspondence remain unchanged in the posterior domain. Topology/indexing, source raster, rig, UV, features, belly and head masking remain the same. Head remodel has X changes outside the affected posterior range; it must stay outside metric reconstruction. There are155 recoverable64-point rings across x[-.337414,.334620]. Current material uses16 fragment samplers on Mac, so reuse the existing scalar arc texture and do not add a sampler. Godot4.7.1 local resource renderer uses the production FinalizedFish157 loader, but raw GLTF import and static views do not replace formal imported-LOD/action verification.

Intended single correction: reconstruct the scalar arc LUT from current physical rings while retaining the old reference-theta lookup. No new feature coordinates, no additional texture, no native raster edits, no art taper in this isolating candidate. Test the correction independently of the earlier artist-only candidate.

Phase2 independent review APPROVED. Reviewer emphasized actual GPU texel-centre filtering and separate head/shoulder seam inspection.

## Phase3 hypothesis and failing test

Falsifiable hypothesis: replacing only the obsolete scalar arc metric with current physical distances will make the existing dorsal lookup measure the revised body's transverse surface to within1% on held-out cuts. It may reduce a contributor to elongated dots; raster shape, projection foreshortening, two-dimensional shear and artistic density remain alternative explanations for other visual defects.

Before fix implementation, `work/whale-shark-spots/test_arc_metric.py` independently intersects actual indexed triangles at31 non-ring X coordinates, computes53 crown-to-flank arc probes per cut, and samples the candidate exactly as GPU normalized linear texture lookup (including half-texel positions/clamping). Frozen numerical limit: max relative1%, denominator floor.005 native; crown zero1e-5; signed monotonicity. No source ring self-comparison and no artistic parameter changes.

Old LUT fails1,643 probes: median10.13%, P9520.70%, max22.53%, max absolute.01519 native. Centreline and monotonicity already pass, ruling out a flipped sign/crown offset as this numerical defect. Existing154 raster unchanged from the configured material and uniform-raster artistic trial considered separately; no attribution of all elongation to this single metric. Negative report: `old-triangle-metric.validation.json`.

Phase3 independent review APPROVED. Reference test uses piecewise angle interpolation on triangle cuts; it is not an exact analytic theta intersection, and the limitation remains explicit.

## Phase4 single metric correction and verification

Implemented `resources/scripts/volume-fish/remeasure_transported_arc.py`: current polygon YZ lengths, reference-chart ray intersections, GPU texel-centre LUT placement, centreline signed distances. It rejects incomplete rings/nonfinite data and active-domain X transport. The existing shader is zero beyond reference X=.30; altered head X starts.3128, so guard explicitly applies to the active domain while the LUT still covers its original range. Initial input guard rejected the inactive head portion; this was an explicit scope correction, not a relaxed physical tolerance.

`bind_current_arc.gd` saves `metric-candidate/body.res`, changing only skin153_arc. Shader code, every other uniform/texture byte, geometry, UV, weights and LOD arrays compare equal. Material resource reads and GPU captures are new processes. Current metric test:1,643 probes PASS, median0.00243%, P950.04375%, maximum0.21622%, centreline0, monotonic. Numerical tolerance unchanged. Matched top/side/oblique/bottom views actually inspected; candidate still has artistic density/shape issues, so this metric success is not user acceptance.

Regression: all143 existing `test_volume_*.py` tests pass from the correct cli working directory. An initial root-directory run hit the repository gamefactory module-name collision; no source fix was made for that invocation problem. Initial preview camera and17-sampler failures are experiments to be summarized and cleaned; final matched baseline/metric/combined GPU logs have no ERROR/SCRIPT ERROR and completed capture.

Independent artistic trial remains separate: original raster sampled with a smoothly varying scale and integrated longitudinal phase; full1152px ordered field is repeated longitudinally, no small-patch quilting. It preserves the centreline/row phases, reduces tail dots and decreases shoulder size before the original small head dots. The combined review candidate adds this explicitly declared art change to the corrected metric. It is not included in the numerical single-change success claim and has no final fish certification.

Full177/490/body/action/SOP remain pending on the159 baseline and new material candidates. Nothing has replaced the main game binding; this round delivers a reviewable local material revision, not an accepted whole fish.

Phase4 independent review APPROVED for the single-metric correction. Scope constraints: regular star-shaped rings, six-decimal native-coordinate grouping, no active longitudinal transport, and interpolation support outside the active boundary must be checked on reuse. Current.30/.3128 boundary separation is adequate. Separate artistic/combined candidate remains unapproved by that review.

## Round handoff and cleanup

Review: `work/whale-shark-spots/review.html`; source parameters: `resources/volume-fish/whale-shark-dorsal-20261026.json`. Saved metric/combined engine resources retain actual current geometry and all existing body data; these are frozen local material candidates, not main-game installation. Existing GLB/source geometry is unchanged, so this material-only experiment does not require an artificial GLB re-export. Formal cold-import/actions/fin/body/finalization gates remain pending and `sop-check` correctly blocks final completion. No historical pass was rebound to the new candidate.

Cleanup receipt `cleanup.validation.json`: removed38,643,939 bytes of failed camera/missing-body/17-sampler views, obsolete art-only resource and duplicate exported textures. Kept approximately73.6MB of current resources, source metrics, reproduction tools, negative evidence and twelve matched images. Restored original artwork/source files remain hash-verified against the checkpoint archive. Final Git/LFS status checked in both repositories; unrelated concurrent fish-school work is left untouched. No commit/push requested or performed.

## 2026-10-26 提交收尾

用户明确要求提交、清理实验垃圾并沉淀SOP/知识库。后续原生背图获得局部认可，侧图v3获认可，但v3模型被拒绝；v4实际视频辅助模型已保存，仍为未验收候选。完整结果与失败边界见知识条目 `2026-10-26-whale-shark-video-model.md`。当前177/490鳍根通过，490鳍面超时、唇缘局部接触和正式场景等仍待完成。提交检查通过148个单元测试、4个Godot脚本解析与旧距离场负例；没有把SOP blocked改成通过。当前身体字段计算逐字节保持原导出。

原完整稠密压缩包经31个动作/极值代表样本逐项校验后精简，回收约4.43GB，490来源哈希与根报告、冻结检查代码保留。正式保留包迁入 fishing-2d 的 `plans/reviews/whale-shark-20261026/`，本地工作目录只作恢复/预览缓存。两个仓库中另一活动任务的梭鲈/鱼群/性能改动不混入本轮提交；最终提交与推送以Git实际结果为准。
