# 整鱼完成出口与局部制作状态（2026-10-31）

维护源为 Foundry 仓库，入口实现为 `cli/volume_sop.py`、`cli/volume_fish.py` 和 portable 制作脚本。此门不替代实际看图、解剖判断或用户接受。

## 开工与恢复

`volume plan` 自动建立同目录 `<handoff stem>-sop-review.json`，包含完整阶段、逐项证据、物种、task_type=new、当前标准快照。`volume replan` 建新 rebuild 清单，不复制旧审核。`portable/prepare_spec.py` 自动建立同名清单并把 production 引用写进 spec；默认 rebuild，新鱼传 `--task-type new`，局部返修传 repair。缺 species 的技术小样可预览，但不能通过完整出口。`sop-init --task-type new|rebuild|repair|local_godot_static_merge` 可手动建立清单；候选的 production.review 指向它，species/task_type 必须对应。

继续旧 spec 的 `run_source.py` 会补建清单；继续旧 handoff 构建/接受时也会补建。只读 `volume validate` 不创建文件，实时返回完整 production 检查；跨日先 validate 或 sop-check，不信任 manifest 内缓存的 production_status。局部制作不要求未实施项预先通过，保留 pending；“保留部件”同样要求证据，不是豁免。local_godot_static_merge 只说明任务范围，不会在完整出口减免检查。

## 状态与出口

- `volume build/render/validate` 的技术成功保留 done/human_review，明确 `completion_scope=mechanical_preview`，并返回 production.status=blocked 及逐阶段失败。此 done 仅允许局部审阅，不表示整鱼完成。
- `run_source.py` 的成功明确 `completion_scope=source_parity_only`，manifest 和响应同时给出 production_status。语义等价不能证明新模型满足全部制作标准。
- `volume accept` 在机械检查、渲染及实际操作者说明之外，直接调用当前 SOP 检查器，验证清单绑定的当前 GLB、blend、源图和 profile；缺项返回 sop_incomplete，不写接受。已接受候选重新 validate 时也实时复查 SOP。
- `run_delivery_checks.py` 所有专项通过后仍调用同一完整检查器；缺证据为 blocked，specialized_checks_ok=true，formal_acceptance=false。默认退出1。局部工作可加 `--checks-only`：仅允许技术通过退出0，manifest/响应的 ok 仍为 false、整鱼仍 blocked，不能据退出码称整鱼完成。
- 完整清单通过仅到 whole_fish_operator_review/human_review，不自动产生用户接受。自动门不能阻止任意自由 shell 或虚假文字声明。

## 绑定与迁移

candidate_files 的每一项填写实际文件路径和 SHA256。证据 bound_inputs 必须绑定完整候选快照；stage method/reviewer/observations 与全部 checks 不能留空。原有嘴、真实法线厚度/尾截面、源固化和冷读语义门继续运行，不能拿任意 ok=true JSON 或总览图替代专用报告。

普通 handoff 完整出口额外核对 model、editable_source、source_image、species_profile 的实际路径和字节。portable 交付核对 model、species_profile、delivery_config（本次 --config）、final_spec、motion_config（spec.motion.profile）、motion_runtime（spec.motion.runtime）；这些角色也必须加入同一清单及证据绑定。runtime_manifest 等原有必需角色继续保留。共享 production 引用可由 config.production 或 final-spec.production 提供，路径使用绝对路径；不得新建一份仅含技术通过的清单绕过原清单。

标准快照记录标准版本、全部必需 criteria、SOP/鳍型/补皮/导出/嘴检查卡和检查器文件哈希。新增条目或这些文件变化会返回 stale_standard；不得自动升级快照或批量重绑历史证据。应逐项审核差异、补实施/补验证后，显式更新 standard；保留历史报告和接受范围。模型、配置、运行文件或任一证据字节变化会触发 stale_artifact/stale_binding/wrong_current_candidate。无法实现的生成器能力留作 pending/blocked，不用技术构建成功代替。

现有三鱼候选、历史报告和认可宽度档案不作修改。旧清单无 standard/task_type 会在新检查中失败；可在原候选之外建立新清单完成迁移，旧报告保留原状。此标准采用保守失效：标准文件的文字编辑也会要求重新核对，尚不自动推断哪些证据可安全保留。

## 验证与边界

单测使用合成图片/文件与报告，只证明软件门接通，不证明真实鱼外观。负例覆盖缺项但手填 done/passed、伪装专用报告、变更模型/标准/物种、技术专项全通过但整鱼缺证据、已接受后缺项、归档不能继承新制作通过。volume 测试仅模拟昂贵 Blender 进程，接受出口运行真实 SOP 检查；portable 测试直接执行交付实际调用的 finish_delivery，运行真实 SOP 检查，无全局 gate mock。

当前通用报告仍包含操作者声明及部分仅检查 ok 的报告项，软件不能证明所有报告语义真实性，也不自动执行视觉/解剖审核。当前改进封住受支持入口的漏调用和过期证据，不声称防伪签名或阻止绕开 CLI 的自写安装脚本。


本轮验证：`test_volume_sop.py` 29项；`test_volume_fish.py` 38项（1项需外部Blender的既有smoke跳过）；`test_volume_archive.py` 6项归档测试及其导入的同一volume测试均通过；portable 的 prepare_spec 7项、delivery_adapters 4项、species_fin_inventory 3项、guard_regressions 13项通过；`git diff --check` 无错误。未运行真实鱼的昂贵490或图审，不将软件测试当三鱼交付。测试临时目录由TemporaryDirectory收尾；本轮没有生成模型、逐帧图片、录像或长期实验目录，保留代码/测试/本执行记录，未删除其他任务产物，未提交。
