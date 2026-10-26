---
type: debug-knowledge
status: FAILURE
bug_topic: zander posterior mouth fill
date: 2026-10-26
---

# 梭鲈后口填补：三次尝试后停止

## Bug Description

用户要将后方口缝及黑线直接填成实体皮肤，前端仅留小开口，下巴完整连续。实际运行身体来自fin143/zander/body-base.res，原GLB只是部分来源。旧正式模型完整保留，本轮未安装。

## Attempted Hypotheses

### Attempt 1

- Hypothesis：有界下巴填充加后口角纯X前推可以缩口。
- Fix tried：U下部位移与C前推组合，保留口缘YZ及UV/index。
- Why it failed：实际灰模出现竖缝/平台；不同Y衰减让上口缘X顺序倒转，纹理随强剪切拉伸。
- Learned：正Jacobian及范围缩短不证明口缘自然；离散同高源像素不应强制逐段零斜率。

### Attempt 2

- Hypothesis：压小原口腔即可满足填补。
- Fix tried：后部3%名义残隙、前部约1/3开度，填连续下巴。
- Why it failed：用户明确拒绝残留细线，要求直接填上一部分。
- Learned：代理自加拓扑保护导致用压细代替真填，不能把保留黑线当用户接受。

### Attempt 3

- Hypothesis：裁掉X<.470后口腔/唇面，沿旧口缘缝皮肤并封短前腔可以完成。
- Fix tried：520片skin填面、104片后盖；24个旧空腔点outside变inside，闭体方向/边/有限面积通过。后线取邻近原生cream皮肤。
- Why it failed：首轮误把原图UV写到76×121局部atlas而采黑；定位后唯一材质修正扩为97×121，旧像素及25600旧record采样均0差，新donor正确，几何/shader未动。但最终材质仍有贴片/灰边，统一灰模也有棱纹/接缝，最终REJECTED。
- Learned：真占体积、闭壳及取色正确不等于连续外皮。几何/法线/附层的具体贡献尚未隔离，不编造单因。

## Architectural Concerns Raised

沿旧裂口保形缝补继承了旧边界关系，没有从同一完整外皮建立表面连续性与材质相位。三次失败后停止，需用户架构复核，不自动第四次造型。

## Recommendations

先用只读分层显示隔离几何、法线及附层，再复核局部整体外皮的边界、连续性和原生材质映射。建议尚不是可用实现，不借返修改眼睛、头宽或其他鱼。

## What We Learned

最近有限面法向可能在共享折边误签内外；完整闭体绕数与正负对照已证伪一次接触假失败，原深度门未放宽。机械PASS不能替GPU看图。关键失败输入/图/记录/复现工具保留，临时工具与重复输出按清单清理。正式身体/唇/GLB/源图哈希与基线一致。
