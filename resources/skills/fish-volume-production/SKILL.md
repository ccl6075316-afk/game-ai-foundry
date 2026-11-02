---
name: fish-volume-production
description: Build or repair rigged, source-art-based 3D fish in Game AI Foundry, including species evidence, mouths, complete fins, rooted motion, source finalization and Godot review. Use for fish production and its SOP maintenance; use aquascape-production for plants and scenery.
---

# 原画驱动的 3D 鱼

定位实际 Foundry 根目录和目标游戏，读根 `AGENTS.md`、[工具箱合同](../gamefactory-toolkit/SKILL.md)。代码路径相对 Foundry 根目录；不把旧报告绝对路径或本机技能安装位置当工作区。仓库技能是维护源，本机链接/副本不能承载独有经验。

## 开工入口

新建、重建、返修和批量推广都先读[生产 SOP](references/production-sop.md)及[真鲷跨鱼执行表](references/red-seabream-lowpoly-trial-lessons-20261101.md#跨鱼执行表开工先读)。在原 handoff / 逐鱼清单记录本鱼适用风险、保留区与拟用验证画面，不能只写“已阅读”。SOP 0—10 节是执行顺序；后半日期案例保留历史，不按编号递增试错。

首次用 `volume sop-init` 建逐鱼清单，之后更新原清单。按当前实际功能/运行依赖和本鱼库存选方法，核验源图/归档/接受，不补造生成记录；新鱼先审核二维去鳍底图、实际色相描边、头底鳃纹、像素密度、头身灰模接口及整眼比例。既有动画/生成作业遵循工具箱状态合同。

基础检查后 **嘴 → 全部适用鱼鳍 → 其余**。嘴须有下唇线、真实开口、上下颌体积与两侧原画/跨口缘接续；嘴未完成不推进下一鱼或整鱼完成流程。依[嘴执行卡](references/mouth-execution.md)选择完整方法链，先预检原生二维完整唇域，再局部冷读，不能用横缝、闭体、独立装饰唇带或整块抹色代替。

## 按问题选知识

完整参考路由、物种实例、已替代路线见[知识索引](references/knowledge-index.md)。只读本次需要的专题；[部位质量守卫](references/component-quality-rules.md)保留原入口16条规则与有效负例。

| 本次问题 | 优先执行卡 |
|---|---|
| 头厚/体厚、俯视头吻、连续头身比例 | [宽度依据](references/width-evidence-workflow.md)、[黑鲷近缘厚度与两侧覆盖](references/black-seabream-production-lessons-20261102.md) |
| 嘴几何、唇材质、口内供体 | [嘴执行](references/mouth-execution.md)、[嘴优先证据](references/mouth-first-review.md)、[二维唇色接续](references/mouth-material-continuity.md) |
| 原画整鳍边界、余边/白边、实际蒙皮根带 | [完整源鳍](references/fin-source-shape.md)、[精确切鳍](references/precise-native-fin-cutouts.md)、[有限根带](references/native-fin-detail-lessons-20261031.md) |
| 鳍厚、尾柄、有限自由鳍面穿体 | [鳍型/厚度/尾柄](references/fin-types-thickness-tail.md)、[有限接触返修](references/finite-fin-contact-repair.md) |
| 眼、中央额部、背腹/头底、贴图滑动 | [眼睛](references/eye-volume.md)、[部位供体](references/source-zone-review.md)、[源表面返修](references/source-surface-repair.md) |
| 控制笼低面 B 新建、无聊天重建交接 | [控制笼](references/reference-cage-body.md)、[完整重建 SOP](references/reference-cage-rebuild-sop.md) |
| 配置驱动源/部位/冷导出或单 surface | [通用工具及 capabilities](references/portable-finalization-tools.md)、[单材质源固化](references/single-material-source-finalization.md) |
| 鲨鱼、同族双髻鲨与项目原画来源 | [鲨鱼主线](references/shark-production-lessons.md)、[双髻鲨边界](references/hammerhead-family.md) |
| 旧 Godot 静态装配回源的本地检查点 | SOP 0.2 与[次级模型卡](references/static-merge-secondary-model.md)，不用于新鱼、主动修鳍或正式交付 |
| 实际游戏替换、缓存冷读与性能测量 | [正式替换防遗漏](references/five-fish-width-release-lessons-20261101.md)、[性能审计](references/performance-audit.md) |

部位或验证方法不清，按游戏 `docs/3d-fish/ANATOMY-RESEARCH.md` 查证后转成约束。先核同口径长度/最大体宽及峰位，再核头吻各站与连续轮廓；直接测最终有限网格。2026-11-02允许同属/同科或已审模型作近缘厚度参考，用户指定定稿样板优先；记录物种、来源SHA、部位映射、长度归一化和未知，不冒充同种实测或继承接受。项目已审原画约束主体/鳍形，外部模型用于批准的结构与量测角色，不直接挪扫描轮廓再拉伸皮肤迁就。

[整鱼预算](references/display-length-budget.md)按2026-11-02用户再次确认的展示体长分档：普通≤120cm为1500/2000，>120—300cm为3500/4000，>300—600cm为5500/6000，>600cm为7500/8000（优选/硬上限）；鲨鱼以3000～4000为最低起步预算范围（当前实现3500优选/4000本档上限），>300cm继续升到5500/6000，>600cm升到7500/8000，不能统一封顶4000。正好边界归前档，统计身体/嘴口内/全部鳍两面厚度封边及附层，不凑数加面，不以预算牺牲嘴/原眼/画风/连接/动作。

## 验证与完成

局部嘴、全部鳍、其余多视与代表动作稳定，收齐一轮问题后再冻结集中跑完整门；相同适配两次失败先定位最小反例。候选/失败/暂停即时更新原记录，不连续盲调、不重复开生成作业或为“放心”重跑有效门。旧报告不批量换SHA冒充新候选通过。

- 每鱼检查完整鳍基，对同姿态实际蒙皮身体面测有符号距离；按源图冻结各鳍根区，不套鳍数/选点/骨名，漏鳍/空区/旧哈希须失败。`validate_fin_completion.py` 与 `validate_fin_membrane_clearance.py` 分别覆盖完整根、整片自由鳍面及适用动作，根带许可不适用于自由面，不事后缩根区或放宽容差。
- `validate_body_integrity.py` 检查闭合身体、逐surface不透明供体与GPU同姿态覆盖，正常口腔外不得缺块；透明装饰叠层与下层实体分别核验。`check_head_form.py` 和正/俯/斜灰模独立验吻型，不为取色压尖头。
- 原生循环、Godot四动作/真实切换、独立幅频/零幅度/支点、全部实际LOD与材质归属均按当前候选验。离散177/490等覆盖不证明全连续时间安全，也不证明原图/解剖或用户外观已通过。专项入口/参数见 SOP 与游戏 `docs/3d-fish/VALIDATION.md`。
- 原像素/nearest、两侧同光照侧腹覆盖、隐藏活动鳍后的身体残影、实际唇/眼/鳃区域与背腹接头都要看。技术计数、源RGB一致、UV未变或旧profile approved不能代替视觉审核。

准备本轮交付主动执行[最终源固化与导出](references/final-asset-export.md)：静态几何/UV/权重/纹理进可编辑源与最终GLB，保存引擎资源；新进程关闭实验静态造型链直接读最终入口并检查真实动作/缓存。完整门和实际图审后跑 `volume sop-check --review <清单> --output <报告> --json`，再按来源/接受合同使用 `volume accept`；这是操作者审核，不等于用户接受。完整门未通过仍按[工作流状态规则](references/production-workflow-gates.md)保留候选/局部结果。

## 知识与产物收尾

每轮按[知识收尾卡](../../../docs/3D-ASSET-KNOWLEDGE.md#每轮修改后的知识收尾卡)回写三层：通用SOP/方法，本鱼profile/标注，本次handoff/验证/实际图审与用户反馈。没有新方法就引用原卡和参数差异；新分支明确替代关系并接入知识索引。逐鱼数值、鳍数、原图坐标和接受不跨鱼继承。

先确定保留/归档恢复范围，再逐清单清理可重建帧、稠密样本、重复图和临时工程/缓存，保存唯一输入/证据及剩余体积。用户要求提交时核对 Foundry 与独立游戏仓库，commit + push；提交不是验收。安装副本须与仓库逐文件一致，或链接仓库维护源。
