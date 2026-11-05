> 2026-11-05 历史制作记录退役说明：本批十一鱼已获用户成品接受，旧实验图片、模型、密集数据与候选专用重放链已按授权清理。本页旧路径/命令仅为历史方法记录，不是当前可运行入口或仍存在的图证据。以后从canonical fish.blend修改；当前依赖与保留方法见 `resources/volume-fish/eleven-fish-release-20261105/METHODS.md` 和游戏正式release/history-new-eleven.md。

# 非洲鲶鱼身体077与真实附属部件登记

`validate_registered_body.py`与`capture_registered_body.gd`是本鱼独立适配，不修改公共portable检查器。上游Python SHA256为`1a73badcd756005eb10e5e70530ea3bcc084c5db2f084d0cb16843cb65ab4fd7`，Godot捕获为`ac77115bcc72afc23e039f21e2c4ddcaa8f52ed2e783b3c2c7ec6a69902cdb8c`。

本鱼完整网格清单包括身体、七鳍、八条活体须及两个浅眼盖。须登记在`living_auxiliaries`，不能改称鱼鳍或装饰眼；每条须是20三角面、焊接封闭、有向边一致的管体，实际权重为刚性`body_00`。须的12个作者控制点因硬法线导出为40个实际渲染顶点，必须核真实流而非漏掉重复法线点。浅眼保留两份已审源结构：历史每侧25点/36面/12边界，有限身体支持修正后每侧23点/32面/12边界；均为`body_00/body_01`混合蒙皮，不能冒称闭合刚性透镜。每份仍须精确匹配自己的新源登记；拓扑签名本身不授予眼部可见性或外观接受，未来结构变化须重新审查适配范围。

`auxiliary_geometry_reference`绑定`inspect_auxiliary_inventory.py`从当前冷导出模型与源blend取得的清单，并加入`frozen_inputs`。清单绑定模型SHA、各附属部件完整POSITION/NORMAL/UV/JOINTS/WEIGHTS数组、有向三角索引、RGBA及实际骨权；节点不能通过额外TRS藏入位移。所有点必须被有限面引用，法线、骨权、面面积、内部边绕向和实际UV包围区alpha255均须通过。模型变化后必须重新生成实际清单，不能仅替换旧清单的模型SHA。

身体内核保持原规则：逐surface验证完整属性、单位法线及面绕向、归一骨权、不透明材质和整张身体供体alpha255；焊接身体必须封闭且有向边一致。GPU捕获隐藏附属部件，独立验证身体在两姿态×八视、同姿态同相机下相对双面不透明参考缺像素为0，同时零alpha负例必须检出。计划启动前须冻结`maximum_amplitude=2.5`、有限`pose_time`、真实展示缩放及所有输入SHA。

从Foundry根运行，输出使用新的本鱼实验子目录：

`--game`使用含`project.godot`的`projects/fishing-2d/game`目录；不要传不含项目文件的仓库父目录。

```powershell
.venv/Scripts/python.exe resources/scripts/volume-fish/african-catfish-20261104/test_registered_body.py -v
.venv/Scripts/python.exe resources/scripts/volume-fish/african-catfish-20261104/inspect_auxiliary_inventory.py --help
.venv/Scripts/python.exe resources/scripts/volume-fish/african-catfish-20261104/validate_registered_body.py --game <绝对游戏目录> --godot <Godot控制台exe> --plan <冻结plan.json> --output <新的本鱼实验目录>
```

测试默认使用稳定的`fixed-yz-material-r1/standalone.plan.json`，可通过`CATFISH_BODY077_TEST_PLAN`选择另一份真实计划；八项测试覆盖正例、遗漏须、伪装成鳍、假闭合眼、错误骨权、登记哈希变化、有限须点位移及节点位移。

历史与当前诊断证据均在游戏`experiments/four-fish-current-standard-20261101/african_catfish/`。`body077-barbel-material-r2-preflight/completion.validation.json`保留浅眼内部边绕向错误的失败；修正后`body077-eye-winding-r1-registered-gpu/completion.validation.json`对1830面候选通过。集中诊断快照`rebudget-r1/body077.plan.json`及`rebudget-r1/body077-diagnostic/completion.validation.json`绑定1998面模型`f3416cc92a922fb3b58bfdde7ad84538558fadff68d47a9e7008b347879a37c6`，身体三个surface、八须和两眼登记通过；16组缺像素均为0，透明负例检出22137px。

上述通过只覆盖指定快照的077，不证明鳍安全、须/眼全动作接触、连续全时段或用户整鱼接受。修订状态和最终冻结入口以原manifest、handoff及sop-review为准；批量修正期间不为未改变的身体重复跑GPU，最终候选再执行统一验证。

当前新身体/眼及固定YZ材质的077为`fixed-yz-material-r1/body077-final-gpu/completion.validation.json`，模型SHA`b70261163625d9eb72dd5895a61de2368e23a46556d6e63c242bfa91dd2904dd`、2000三角面、身体三个surface；16组缺像素均0，透明负例22137px，当前八项正反测试通过。报告SHA`62d5dbdfdc07e5f20665a8551321503b06e3fb24647781de4e3548d076371941`。作者为眼下三个有限身体facet新增同X支持行（8控制/+16面），旧身体077已失效，不能拿旧BODY精确相同来结转。新模型身体836面，两个23/32/12浅眼的新源登记SHA为`385b582e865be06e751398a1e1f9e40d33213f9c0b8c6dce90454dce1c373b79`。

E01眼部完整原像素域、金虹膜/瞳高光前盖支持和外围/LOD由本鱼独立证据检查，077捕获隐藏眼盖不能替代它。M01材质归属的只读数值和方法在原实验`m01-readonly-20261105/`；可复用的本鱼诊断`inspect_original_front_projection.py`接受`--source --model --config --output`，检查当前实际atlas与旧`Y/W(u)`作者公式，输出209个有限前视采样。它仅诊断旧投射来源，不是修复后材质或眼部验收门。实际修复为本鱼私有作者固定物理YZ span、从真实语义UV输入重烘并精确转移chart RGB；完整嘴缘、真侧眼/鳃和几何/蒙皮保留，不能把已烘焙atlas坐标当原始source UV。
