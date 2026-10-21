---
module: "volume-fish/Godot source sampling"
date: "2026-10-20"
problem_type: "logic_bug"
severity: "high"
symptoms:
  - "侧图深色轮廓在3D头顶/背腹/下巴变成横梯、套环或额外眼纹。"
  - "全背腹重取色同时改变正常鳞片、色阶和像素分布，被用户拒绝。"
  - "FishSourceInk: Material source differs from frozen decoded source PNG"
root_cause: "侧向源图投影及nearest-opaque扩展将2D墨线或眼纹带入隐藏皮肤；同一鱼还经过friendly眼变换、头部投影、局部供体和alpha回退，原始UV不能代表全部实际取样。Godot导入另改透明RGB并保存未使用mip层，原PNG或全Image存储不等于实际nearest使用base RGBA。"
solution: "逐物种人工冻结确证源墨线/保护域/供体；104实验在最终源图和opaque回退取样处只换RGB、逐采样保留alpha；冻结实际导入base RGBA快照并验证旧opaque来源完全复现，独立RGB探针相对基线的并集约束离散画面改动。部分试修有改善，仍未接受整鱼。"
prevention: "先追实际取色分支与源像素，不通用擦暗色；禁止复用被拒绝的全背腹重映射。关闭必须零差异，候选域外必须零差异，探针不批准语义区域；保留正常皮肤、真实口内/唇/鳃/眼/斑纹。材质变化仍需新鳍身与视觉交付门。"
tags: [fish, pixel-art, shader, source-ink, provenance, regression]
---

## Symptoms

macOS / Godot4.7.1 Compatibility / OpenCV5.0.0。本轮真鲷头顶有粗黑梯条，黑鲷中央有金黑重复眼纹，梭鲈上吻部分暗带由旧去眼纹供体造成。三者不是同一根因。

导入校验先报精确错误`FishSourceInk: Material source differs from frozen decoded source PNG`。Godot填透明边缘RGB影响35185个alpha0像素，非零alpha像素变化0；实际Image还含11,385,332bytes存储，nearest使用的baseRGBA8为8,541,616bytes。不能把失败简单归为sRGB后放宽比对。

## Investigation Attempts

- 100全背腹向内重采样：正常身体也改变，用户明确拒绝；不是可以继续调好的推荐模板。
- 真鲷最初猜额外眼纹：源眼域诊断不命中；查实际头顶轮廓后才冻结3473确证深蓝墨线像素。
- 真鲷只限中央法线域：只填中间，留下两侧粗条；完整同一源域试修减轻粗条，但仍有细暗线和像素拉伸。
- 黑鲷宽横向遮罩：触及真实侧眼，被独立审查否决；改窄中央域仅部分改善。
- GPU UV编码受到显示转换影响，两批trace有失真，明确标无效/近似，不能把这些坐标当精确最终供体。

## Root Cause Analysis

实际采样链可能为`UV → friendly_eye_uv → head_source_uv/局部patch → source_texture → opaque_skin`，还会基于RGB亮度做分支。最终ALBEDO后用原始UV筛颜色，会漏掉或误改其他路径。透明区nearest填充又会把选中轮廓色向外扩展；以算法名称相同代替逐RGBA核对不充分。

104只处理显式`Closed_body/surface0`的已装配材质副本；源图、GLB、UV、几何、绑定、动作、口内与鳍不修改。它是带拒绝条件的实验取样工具，不是墨线自动识别器或全鱼接受工具。

## Solution

### Before

```glsl
vec4 c = texture(source_texture, friendly_eye_uv(UV));
if (c.a < .95) c = texture(opaque_skin, friendly_eye_uv(UV));
// rawUV上的最终颜色过滤无法完整解释所有实际供体路径。
```

### After

```glsl
// 保留既有最终UV表达式；仅在确证源域修改RGB。
vec4 c = ink_source_sample(friendly_eye_uv(UV));
if (c.a < .95) c = ink_opaque_sample(friendly_eye_uv(UV));
// wrapper返回vec4(replacement_rgb, original.a)。
```

- 原source与opaque的二参数texture调用逐token包裹，未知sampler用法如`texelFetch`/别名/LOD拒绝；真实sampler必须唯一、nearest、source_color、repeat_disable，注释不能伪造声明。
- mask与donor RGBA坐标图不做sRGB解码；供体RGB仍走原source_color nearest。
- 冻结GLB/源快照/尺寸/mask/donor/代码；严格比整个baseRGBA8，去掉比较用Image未用mip层，不忽略alpha0 RGB。
- 最近透明扩展使用当前OpenCV `distanceTransformWithLabels(DIST_L2,5,DIST_LABEL_PIXEL)`且alpha阈值243；与实际旧opaque逐RGBA0差后才使用provenance。3473墨线源像素对应126354透明扩展坐标，总mask129827。
- 47帧关闭对独立102基线差异0；实际候选对RGB各探针与独立基线差异并集，域外差异0。单个无关像素改动负例被拒绝。旧100整背部反例在101冻结局部域外改变34279px，被拒绝。

这些只证明本轮离散采样范围保留；可见细暗线、黑鲷残余眼纹、梭鲈白环及多鱼拉伸仍未解决。没有新整鱼接受或正式安装。

## Prevention

每次分别写清观察、实际取色来源、已批准源域、未知、输入哈希和检查范围。不要从“暗”“在包围盒内”“与旧版一样”推导通过。PNG原图、Godot实际导入base快照、opaque扩展三者分别冻结。RGB探针并集仅是影响证据，不能批准大片正常皮肤；候选域外变化应追分支，不扩大mask迎合after。

动作离线捕获须`set_action → step(0) → seek`并断言snapshot；不能信文件名。材质/模型/配置变化后重跑鳍根、全鳍面、身体不透明及游戏视距多视、动作切换门；没有这些门的试修只能归档为候选。

## Cross References

- [鱼验证漏检与限定通过](fish-validation-misses-anatomy-volume-fish-20261015.md)
- [104实验模块与数据格式](../../../resources/runtime/godot/source-ink-104/README.md)
- [口部修订规则](../../../resources/skills/fish-volume-production/references/mouth-repair.md)
- [实际动作捕获契约](../../anvil/knowledge/2026-10-20-102-action-capture-contract.md)
- Fish仓库：`docs/3d-fish/2026-10-20-MOUTH-MATERIAL-REVIEW.md`、`experiments/blender-fish/review-105/README.md`；这是物种试修与原始证据权威入口。
