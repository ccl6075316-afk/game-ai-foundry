> 2026-11-05 历史制作记录退役说明：本批十一鱼已获用户成品接受，旧实验图片、模型、密集数据与候选专用重放链已按授权清理。本页旧路径/命令仅为历史方法记录，不是当前可运行入口或仍存在的图证据。以后从canonical fish.blend修改；当前依赖与保留方法见 `resources/volume-fish/eleven-fish-release-20261105/METHODS.md` 和游戏正式release/history-new-eleven.md。

# 带鱼100cm：采用方法与恢复入口

当前是尚未安装/尚未获用户整鱼接受的冻结候选，最终状态以游戏原 `experiments/hairtail-static-merge/README.md`、`lowpoly-20261104/production-review.json` 和 `sop-final.validation.json` 为准。该profile中的施工时间状态只作参数快照，不能替代最终review。

## 可恢复作者

`build.py --profile profile.json --output <仓库output/work/experiments内新目录> --blender E:/blender/blender.exe` 从本目录全部严格SHA输入重建普通 `fish.blend`/`fish.glb`。用Foundry `.venv/Scripts/python.exe` 调用；输出目录须全新。对已有输出加 `--cold-only` 只作普通源冷导字节比较。作者不读游戏实验目录的旧高模：`inputs/rig.blend` 保67骨/1个Animation的完全相同签名，旧8096顶点已全部清零；空数据块名保留fake-user只是保证普通导出命名。其余输入是原生RGBA、去胸鳍ROI供体、有限参考表及实际原画域/浅眼高度场/口与牙参数。`inputs/generated-head-skin/` 是内置imagegen的限域辅助颜色，非新侧图或生物形态。

真实重放 `resource-replay-r2/method-replay.validation.json` 产生GLB **a5ae53ae77b395b63bfa248142cd859059ab1253b6849ac4b6847d38cb3651ee**，与原候选整字节相同；普通冷导也整字节相同。源blend **0fbfde27751a4a00f90df0c2eced0507e68dc07547d7b5483df3e37523d48b02**。1936面作者中间态加32真实口内扇心/64面后，最终2000面；身体1020、背376、胸64×2、眼144/148、6艺术牙簇184。展示100cm硬限2000、优选1500，未凑面到别档。

`profile.json` 保存完整实际站点/参考归一、mouth/eye/tooth/root域及限域取色参数与输入SHA。`motion.profile.json` 为最终实际四动作/控制/铰链配置的字节相同资源副本，SHA `677ef0f95d112b50b5631437bca789db13282b58e43a1f6a678be7e8b1d3bc01`。原Animation/67骨保留；LowerJaw原生旋转幅度0，不声明新喂食动作。

## 本鱼结构参数与验证

- 原画1869×179；身体42站×10径向，115站本地游戏造型参考按可见吻到尾丝工程轴归一，非TL/SL或生物实测。参考量测/重放由同目录父方法与 `measure_hairtail_library_reference_20261104.py` 保存。
- 嘴先保原开度，1758真口角；连续上/下唇与牙分离，整身体Boolean口内语义面；真实唇完整带两辅助权重0，隐藏外颌原生二维皮肤运输，不把侧轮廓墨绕成腹槽。眼真实接受峰凸高约.227705/.227711cm，不缩颅；眼盖与身体有限三角相交，前后同支持分割。
- FAO PDF SHA87c19068457c3c108678b8b0aee5750d44bcb85d6f985cc876d27dab0de06334，p3715及p3712Fig11支持正确胸根(1624,120)/(1626,128)/(1621,135)，不是旧左上尖根；本地各72tri/10吻合根点作为艺术对应。完整基域5有限支持三角/7点，中心内埋.0008native，根/梢半厚.001/.00025，游离外展20°，近根smoothstep距离/.25混合身体权重，原幅度/控制保留。严格共线点与外包.23源像素耳合并回收预算，不裁原域。
- 背33纵站×3跨度，零跨度端焊合，半厚.0018→.0005，根身体/梢DorsalTip混合。原画鳍条由像素表达，不冒充生物鳍条数量。无尾/腹鳍；尾丝x3..100明确是body_filament_cross_sections，6有限源/GLB截面，.001mm冻结误差门，无假caudal-root。
- `validate_volume.py` 实测所有3壳真正双向有限法线厚度/完整基面接触、源/GLB对应和尾丝；保常厚鳍+半宽尾丝普通负例。厚度是制作代理而非鱼组织测量。
- `validate_fin_self.py` 为采用全3鳍检查器，源码SHA `ff47aaf25210d389eef86771a6cf0ad29cce0f712b5f6eb42b3d83a217d5d724`；相对实际最终核唯一差异是ROOT解析，见resource-validator-method报告。CLI取--model/--source/--compact/--full/--output；先重建完整490普通Godot posed-surface导出后可复放。每surface合并库存、源ID唯一位置+skin/全三角多重集对应、每姿态同源alias位置严格0；sourceID只定义真正共享接触，不能豁免对外交叉。显式doubleAABB；共面微正面积进入精确有限核，合法共享点/边以外交集拒。当前7全链/8exact控制及490都过；离散不保证连续。
- `RuntimeBindings.gd` 只实施正常引擎nearest采样，不改Emission/RGBA/alpha/几何/UV/skin。公共查看器按显式 `engine_materials={"texture_filter":"nearest"}` 消费；gray恢复仍须nearest。原始Godot emission导入filter3并非已审像素状态。鳍源Alpha→GREATER_THAN(.5)产生原生MASK，body/eye/toothOPAQUE；export_contract只补源声明nearest/clamp metadata，BIN数组/PNG不变。

## 精确证据与清理

最终原review的98证据、完整077 16GPU、3鳍490根/全膜/self、8附层支持490、头包络/旧尖头负例、native/四动作/12切换、20秒视频、普通冷源均在原handoff导航。最终完整490矩阵保留；密集posed帧仅留代表，清理收据保全部被删SHA。错误render-index检查器207MB trace保完整1470姿态pair库存/源ID映射及最小反例后退役，非模型失败。没有安装或提交；物种库身份/生物厚度/不可见组织和连续时间未知继续保留。
