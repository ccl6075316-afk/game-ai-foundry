> 2026-11-05 历史制作记录退役说明：本批十一鱼已获用户成品接受，旧实验图片、模型、密集数据与候选专用重放链已按授权清理。本页旧路径/命令仅为历史方法记录，不是当前可运行入口或仍存在的图证据。以后从canonical fish.blend修改；当前依赖与保留方法见 `resources/volume-fish/eleven-fish-release-20261105/METHODS.md` 和游戏正式release/history-new-eleven.md。

# 食人鱼开放浅眼盖的077局部适配

仅用于本轮1940面、19骨、原身体支持面重心蒙皮的两片浅眼盖，不改公共077，也不将其标成刚性闭合眼镜片。

`validate_body_eye_caps.py`固定公共基类 `portable/validate_standalone_body.py` 的SHA为 `1a73badcd756005eb10e5e70530ea3bcc084c5db2f084d0cb16843cb65ab4fd7`；基类变化先停下来审差异。

最小行为差异：

1. 从真实完整GLB和已核分区检查身体、全部八鳍及恰好两片显式眼盖，完整1940面计数独立阻断。缺眼角色、多部件、漏声明直接失败。
2. 对这两片眼盖逐顶点核对当前完整原眼UV、源ROI逐像素RGBA、真实四重心蒙皮；支持三索引必须组成当前body的一枚真实有限三角。核对同模型/同490实际动作时序的有限前面接触报告、检查代码SHA，以及实际controller/profile的当前路径和SHA。不允许陈旧/其他模型/缺姿态报告，也不允许将开放非刚性盖填成rigid/closed。
3. 只对独立身体拓扑分析投影移除已声明眼盖，调用公共`inspect_model`原函数。身体所有原三角/上下颌、UV、法线/绕序、权重、闭合/非流形、逐surface不透明供体断言不改。投影中仍包括完整八鳍，另行加回294眼面到全鱼计数。
4. 真实077 GPU采集继续由公共`validate`原函数执行，读取完整当前GLB，不使用投影文件替代实际模型。16组同姿态/相机实际身体与不透明参考比较零缺像素，透明负例必须实际失败；原始断言和实现没有复制/删除/改阈值。

这是局部验证适配，不是新通用鱼生产入口。眼盖自身490有限面与支持关系已经另行检查；不借body077替代眼部几何、鳍根/鳍面、实际多视、完整SOP或用户整鱼接受。

正式实验记录在游戏 `plans/reviews/four-fish-current-standard-20261101/piranha-release-20261102/HANDOFF.md` 的“后续眼体积审计与恢复”。当前实际模型和输入计划在 `experiments/four-fish-current-standard-20261101/piranha/eye-volume-20261104/`。

运行：仓库`.venv/Scripts/python.exe resources/scripts/volume-fish/piranha-20261104/validate_body_eye_caps.py --game <游戏> --godot <真实Godot> --plan <body-eye-current.plan.json> --output <新实验输出目录>`。

`test_private_caps.py`对真实当前候选执行正例，以及错误模型、陈旧/错误模型/缺姿态眼报告、缺眼/多overlay/篡改角色、假rigid/closed、身体材质alpha0和一像素透明供体负例。身体同姿态GPU及透明负例引用刚刚实际执行的完整077报告。报告不补造用户接受，也不把源导出语义通过当成完整成品。

当前R5入口为上述实验下的 `fin-collar-r5/operator-finish.manifest.json`；可用 `test_private_caps.py --candidate fin-collar-r5` 重建15项真实正反例，新增假支持三角、错controller/profile负例。大负例模型已按完整哈希清单删除，方法、原输入与完整拒绝结果保留。当前GLB SHA `40bcab889088894369296eabc96060e1d41fbe101e225fa8d7b7f6050edede89`，当前所有正式物理计划使用0.5mm根领/.02mm自由面；最初0.6mm结论只保留为明确失效历史。

根领修复的原参数、完整问题清单、源固化与数值在同一handoff顶部；`trial_restore_root_collar.py`保留本轮局部几何重建过程，`finalize_root_collar_source.py -- --candidate <新名字>`用于已核几何固化（已有目标拒绝覆盖），不能把几何试验返回成功视作通过。当前需要复验时优先从R5可编辑源冷导出。全部原根选区/基线、UV/权重和动作保持；同名surface通过共享opt-in `portable/export_fin_poses_merged.gd`完整累积，实际自交通用方法引用版本库 `references/fin-shell-self-intersection.md`，不复制其他鱼参数或接受。
