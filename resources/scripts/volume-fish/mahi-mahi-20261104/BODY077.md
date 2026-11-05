> 2026-11-05 历史制作记录退役说明：本批十一鱼已获用户成品接受，旧实验图片、模型、密集数据与候选专用重放链已按授权清理。本页旧路径/命令仅为历史方法记录，不是当前可运行入口或仍存在的图证据。以后从canonical fish.blend修改；当前依赖与保留方法见 `resources/volume-fish/eleven-fish-release-20261105/METHODS.md` 和游戏正式release/history-new-eleven.md。

# 鲯鳅开口浅眼盖的独立身体077适配

本目录`validate_mixed_eye_body.py`和`capture_mixed_eye_body.gd`派生自portable同名身体检查链，公共文件未改。上游Python SHA为`1a73badcd756005eb10e5e70530ea3bcc084c5db2f084d0cb16843cb65ab4fd7`，Godot捕获SHA为`ac77115bcc72afc23e039f21e2c4ddcaa8f52ed2e783b3c2c7ec6a69902cdb8c`。

采用差异仅为登记本鱼两个25点/36面、12条边界的开口浅眼盖，真实骨权为body_00/body_01混合，不能声明closed rigid lens。计划必须绑定`eye_geometry_reference`的路径/SHA并把它加入frozen_inputs；其中记录独立源的POSITION/NORMAL/UV/JOINTS/WEIGHTS/有向索引/图像RGBA及node变换哈希。负例验证有限眼平移、node平移、错误骨权和假闭合声明均拒绝。该登记不等于眼部全动作接触或外观接受。

身体仍逐surface检查原数组、正常法线/面绕向、归一骨权、不透明材质及整张身体供体alpha255，焊接后全身封闭且有向边一致。GPU逻辑保持两姿态×八视、同姿态/同相机原材质与双面不透明参考零缺像素，并必须拒绝零alpha材质负例。计划在启动Godot前还须显式给出`maximum_amplitude=2.5`及有限`pose_time`，避免错误计划在GPU进程内挂起。

从Foundry根运行：

`--game`必须是含`project.godot`的`projects/fishing-2d/game`，不能传其仓库父目录。使用错误项目上下文可改变GLTF导入结果，不能把随后名称断言当模型缺件。

```powershell
.venv/Scripts/python.exe resources/scripts/volume-fish/mahi-mahi-20261104/test_mixed_eye_body.py -v
.venv/Scripts/python.exe resources/scripts/volume-fish/mahi-mahi-20261104/register_eye_reference.py --model <源冷导出GLB> --comparison <实际旧眼对照报告> --output <新的本鱼眼登记json>
.venv/Scripts/python.exe resources/scripts/volume-fish/mahi-mahi-20261104/validate_mixed_eye_body.py --game <绝对游戏目录> --godot <Godot控制台exe> --plan <本鱼冻结plan.json> --output <新的本鱼实验目录>
```

本轮原始输入/计划/报告在游戏原实验`experiments/four-fish-current-standard-20261101/mahi_mahi/`。R33/R34为历史独立通过快照；R36恢复旧浅眼实际凸高后重新登记`body077-eye-r36-reference.json`，绑定`eye150-r36-comparison.validation.json`。`r36-body077-max-controls.plan.json`与`body077-r36-gpu-max-controls/completion.validation.json`对该快照通过。后续`r39-body077-max-controls.plan.json`与`body077-r39-gpu-max-controls/completion.validation.json`绑定R39模型`ef3c36a1bff4fd0e9aa284ab7c64ad3fda250d2420566b66d804da8aba1a4309`，眼登记仍与R36逐属性相同；另冻结`normal-cone-r39/fin-only.validation.json`说明改动范围。真实展示缩放1.1998139550683433、Turn@3.75s和2.5幅度下16组缺像素全为0，透明负例检出23407px。仅离散两姿态，不证明连续全时段、鳍安全或用户接受。后续候选状态以原handoff和逐鱼清单为准，最终冻结后统一复验。

R31身体供体包含透明像素，原失败报告保留；修订R33静态身体派生供体后通过，几何/UV/蒙皮/动画数组未改。早期额外“12个实际UV采样透明”的诊断错误使用了Y翻转，已撤回，不能作实际GLTF采样证据。首次GPU计划缺最大幅度字段的失败日志保留，随后增加启动前预检并以完整计划通过。当前采用的源/派生图、plan和全部数字归原handoff；重复部分捕获按`body077-root-cleanup.validation.json`逐SHA清理。

冻结R51的最终077计划为`r51-body077-max-controls.plan.json`，正确项目下报告为`body077-r51-final-project-gpu/completion.validation.json`：模型`3fc100704119caf59ce4f15450f52527e663c2f9d5541d8a6dcf5db3ddcb763b`，1970三角面、身体三个surface、16组缺像素均为0，透明负例23407px。第一次误传仓库根目录的启动失败单独保留在`body077-r51-final-gpu/launch-failure.validation.json`，未改模型或验证内核；只做了正确项目上下文的重跑。最终整鱼结果仍归原清单。
