# New eleven fish: retained methods after accepted release, 2026-11-05

用户已接受本批十一鱼，并明确退役实验图片、旧模型、稠密采样与未采用/仅候选阶段的重放脚本。以后从正式成品修改，不从旧修复链重建。

当前可编辑源：`projects/fishing-2d/assets/source/fish/<species>/fish.blend`；正式GLB：`projects/fishing-2d/game/assets/models/fish/<species>.glb`。所有材质已packed，无linked/loose依赖。当前运行表是游戏`game/assets/models/fish/motion/eleven20261105.json`，实际运行依赖已迁入游戏；下列历史参数里的旧实验路径不是当前运行入口。

完整每鱼关键节点、最终面数/骨数/source与GLB SHA、历史SOP SHA及退役语义：`projects/fishing-2d/plans/reviews/eleven-fish-release-20261105/history-new-eleven.md`。PDF及对照结论由正式docs/reviews保留。旧文档中的候选命令、截图和旧SOP绑定仅供理解历史，不承诺仍存在或可重放；不得改旧报告SHA制造新通过。

## 继续适用的方法

- 嘴第一、全部鳍第二；唇完整原画域、开口/上下颌体积与左右/跨缘材质不能由机械清单替代。孔雀鲈18°下颌只能一条生效链，避免重复捕获rest并叠加。
- 鳍根限值须逐鱼读取并明确单位：本批大黄鱼声明outer/embedding各0.5mm，即0.05cm；不是旧缺省0.10/0.60cm。膜根collar与自由面0.02mm判据是另一合同，不混用。共享fin_attachment_limits.py与两个runner保留在公共目录。
- 多surface必须在各自原绑定空间实际pose变换后再合并，triangles按offset；独立原始完整库存+prepared库存+声明三方核对，不能部分prepare后用partial声明绿过。公共portable/export_fin_poses_merged.gd为opt-in实现，base不变。
- 两层有厚度且不穿身体并不保证无self。用有限三角、完整surface、实际矩阵；共享点/边只豁免该接触本身，不能豁免别处真交叉。AABB广相覆盖所有候选，对近共面共享边用有限区间/精确符号，不扩大EPS吞错。
- 巨骨舌鱼32骨是本鱼支持合同；局部中面Jacobian与根混合框/单一父框须一致，不能只靠静态挤出或正反同权重。保留正常幅频/完整根域。其他鱼不继承该骨数或参数。
- 眼必须有相对真实支持体表的浅凸体积，不能用RGBA比例代替；077既验闭体/逐surface不透明供体，又验原完整GLB实际GPU覆盖。保留各物种必要077适配器及实际capture依赖。
- 源material foundry_export_contract_json固化MASK/cutoff0.5/nearest等实际合同；BLEND水体排序问题不能靠改公共水体掩盖。头底补色先看干净供体，不复制侧鳃。材质only-nearest克隆不能改RGB/alpha/emission，灰模来回复原。
- 所有当地库艺术模型仅为形体参考；raw OBJ本次显示注册-Y头向/+Z背面，不冒称历史轴早已登记、生物实测或用户形态接受。对照等长含全部可见部件，不等于鼻/尾柄解剖配准。
- 源/GLB冷导出须关闭旧静态构建链。普通blend编辑与普通GLB独立可用；当前静态已接受冻结，不因历史工具保留重新开启模型。

## 保留工具和小参数（其余候选专用源码退役）

- `resources/volume-fish/arapaima-lowpoly-20261104/basal-support-fit.json` — Small adopted object parameters or species evidence; historical paths are not current live dependencies
- `resources/volume-fish/arapaima-lowpoly-20261104/posterior-red-skin.json` — Small adopted object parameters or species evidence; historical paths are not current live dependencies
- `resources/volume-fish/arapaima-lowpoly-20261104/posterior-ventral-skin.json` — Small adopted object parameters or species evidence; historical paths are not current live dependencies
- `resources/volume-fish/mahi-mahi-20261104/basal-domains-r29.json` — Small adopted object parameters or species evidence; historical paths are not current live dependencies
- `resources/volume-fish/mahi-mahi-20261104/construction.json` — Small adopted object parameters or species evidence; historical paths are not current live dependencies
- `resources/volume-fish/mahi-mahi-20261104/fin-volume.config.json` — Small adopted object parameters or species evidence; historical paths are not current live dependencies
- `resources/volume-fish/pacific-bluefin-tuna-lowpoly-20261104/mouth-r4.config.json` — Small adopted object parameters or species evidence; historical paths are not current live dependencies
- `resources/volume-fish/pacific-bluefin-tuna-lowpoly-20261104/native-fin-cutouts.json` — Small adopted object parameters or species evidence; historical paths are not current live dependencies
- `resources/volume-fish/pacific-bluefin-tuna-lowpoly-20261104/production-parameters.json` — Small adopted object parameters or species evidence; historical paths are not current live dependencies
- `resources/volume-fish/pacific-bluefin-tuna-lowpoly-20261104/README.md` — Retain useful method/provenance prose; historical commands are explicitly retired by current batch METHODS notice
- `resources/volume-fish/peacock-production-20261104/head-envelope.json` — Small adopted object parameters or species evidence; historical paths are not current live dependencies
- `resources/volume-fish/peacock-production-20261104/integrated-eye-parameters.json` — Small adopted object parameters or species evidence; historical paths are not current live dependencies
- `resources/volume-fish/peacock-production-20261104/production-parameters.json` — Small adopted object parameters or species evidence; historical paths are not current live dependencies
- `resources/volume-fish/peacock-production-20261104/README.md` — Retain useful method/provenance prose; historical commands are explicitly retired by current batch METHODS notice
- `resources/volume-fish/peacock-production-20261104/right-root-wall-r6.parameters.json` — Small adopted object parameters or species evidence; historical paths are not current live dependencies
- `resources/volume-fish/silver-arowana-20261105/adopted-methods.json` — Small adopted object parameters or species evidence; historical paths are not current live dependencies
- `resources/volume-fish/silver-arowana-20261105/README.md` — Retain useful method/provenance prose; historical commands are explicitly retired by current batch METHODS notice
- `resources/volume-fish/yellow-croaker-20261104/complete-body-material-r46.config.json` — Small adopted object parameters or species evidence; historical paths are not current live dependencies
- `resources/volume-fish/yellow-croaker-20261104/head-envelope-r48.plan.json` — Small adopted object parameters or species evidence; historical paths are not current live dependencies
- `resources/volume-fish/yellow-croaker-20261104/METHODS.md` — Retain useful method/provenance prose; historical commands are explicitly retired by current batch METHODS notice
- `resources/volume-fish/yellow-croaker-20261104/root-fin-thickness-r48.config.json` — Small adopted object parameters or species evidence; historical paths are not current live dependencies
- `resources/volume-fish/yellow-croaker-20261104/species-review-facts-20261105.json` — Small adopted object parameters or species evidence; historical paths are not current live dependencies
- `resources/volume-fish/zander-lowpoly-20261104/accepted-uv-chart.config.json` — Small adopted object parameters or species evidence; historical paths are not current live dependencies
- `resources/volume-fish/zander-lowpoly-20261104/adopted-method.json` — Small adopted object parameters or species evidence; historical paths are not current live dependencies
- `resources/volume-fish/zander-lowpoly-20261104/fin-volume-final.config.json` — Small adopted object parameters or species evidence; historical paths are not current live dependencies
- `resources/scripts/volume-fish/african-catfish-20261104/AUTHORING.md` — Retain useful method/provenance prose; historical commands are explicitly retired by current batch METHODS notice
- `resources/scripts/volume-fish/african-catfish-20261104/BODY077.md` — Retain useful method/provenance prose; historical commands are explicitly retired by current batch METHODS notice
- `resources/scripts/volume-fish/african-catfish-20261104/capture_registered_body.gd` — Actual GPU capture dependency of retained077 adapter
- `resources/scripts/volume-fish/african-catfish-20261104/validate_registered_body.py` — Reusable species-specific body077/auxiliary adapter
- `resources/scripts/volume-fish/arapaima_20261104/ArapaimaBasalSupportMotion.gd` — Adopted normal motion:32-bone relative basal support, canonical game copy is authoritative
- `resources/scripts/volume-fish/arapaima_20261104/eye_binding_guard.py` — Finite body-supported eye verification dependency
- `resources/scripts/volume-fish/arapaima_20261104/validate_body_supported_eyes.py` — Reusable species-specific body077/eye support adapter
- `resources/scripts/volume-fish/blacktip-20261105/finite_edge_kernel.py` — Reusable finite triangle/coplanar interval kernel with near-coplanar correction
- `resources/scripts/volume-fish/hairtail_20261104/AUTHORING.md` — Retain useful method/provenance prose; historical commands are explicitly retired by current batch METHODS notice
- `resources/scripts/volume-fish/hairtail_20261104/capture_standalone_body.gd` — Actual GPU capture dependency of retained077 adapter
- `resources/scripts/volume-fish/hairtail_20261104/exact_finite_contact.py` — Generic exact binary-rational finite-contact predicate; not whole-fish acceptance
- `resources/scripts/volume-fish/hairtail_20261104/export_contract.py` — Reusable ordinary multi-surface cold export/material contract
- `resources/scripts/volume-fish/hairtail_20261104/lip_protection.py` — Adopted source bake native-lip scalar protection method
- `resources/scripts/volume-fish/hairtail_20261104/README.md` — Retain useful method/provenance prose; historical commands are explicitly retired by current batch METHODS notice
- `resources/scripts/volume-fish/hairtail_20261104/RuntimeBindings.gd` — Nearest-only clone of active material; normal engine binding
- `resources/scripts/volume-fish/hairtail_20261104/validate_body.py` — Reusable body077 with actual emissive donor and closed mixed eyes/teeth
- `resources/scripts/volume-fish/mahi-mahi-20261104/BODY077.md` — Retain useful method/provenance prose; historical commands are explicitly retired by current batch METHODS notice
- `resources/scripts/volume-fish/mahi-mahi-20261104/capture_mixed_eye_body.gd` — Actual GPU capture dependency of retained077 adapter
- `resources/scripts/volume-fish/mahi-mahi-20261104/compact_membrane_kernel.py` — Reusable compact actual-pose membrane measurement implementation
- `resources/scripts/volume-fish/mahi-mahi-20261104/README.md` — Retain useful method/provenance prose; historical commands are explicitly retired by current batch METHODS notice
- `resources/scripts/volume-fish/mahi-mahi-20261104/validate_mixed_eye_body.py` — Reusable077 mixed eye patch adapter
- `resources/scripts/volume-fish/pacific_bluefin_tuna_20261104/eye_binding_guard.py` — Finite supported-eye verification dependency
- `resources/scripts/volume-fish/pacific_bluefin_tuna_20261104/validate_body_supported_eyes.py` — Reusable077 closed body-supported eye adapter
- `resources/scripts/volume-fish/piranha-20261104/README.md` — Retain useful method/provenance prose; historical commands are explicitly retired by current batch METHODS notice
- `resources/scripts/volume-fish/piranha-20261104/validate_body_eye_caps.py` — Reusable077 projection adapter retaining original full GPU inventory
- `resources/scripts/volume-fish/silver_arowana/validate_body.py` — Reusable077 closed mixed-eye/barbel adapter
- `resources/scripts/volume-fish/yellow-croaker-20261104/capture_mixed_eye_body.gd` — Actual GPU capture dependency of retained077 adapter
- `resources/scripts/volume-fish/yellow-croaker-20261104/validate_mixed_eye_body.py` — Reusable077 mixed eye patch adapter
- `resources/scripts/volume-fish/zander/exact_shared_halfspace.py` — Generic exact/high-precision finite shared-seam predicate
- `resources/scripts/volume-fish/zander/recovery_contract.py` — Reusable complete referenced-accessor and embedded-PNG digest
- `resources/scripts/volume-fish/zander/validate_body.py` — Reusable077 closed mixed-eye adapter
- `resources/runtime/godot/mouth-zander-110/README.md` — Retain useful method/provenance prose; historical commands are explicitly retired by current batch METHODS notice
- `resources/runtime/godot/peacock-final-20261104/PeacockMotion.gd` — Adopted single-chain normal jaw+body motion; canonical game copy authoritative
