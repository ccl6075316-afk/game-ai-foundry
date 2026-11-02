# 水草与布景生产 SOP

适用新建、重建、返修、扩充和知识维护。代码路径相对 Foundry 根目录；`projects/fishing-2d` 是独立 Git 仓库。先读 [AGENTS](../../../../AGENTS.md) 和 [workflow 合同](../../gamefactory-toolkit/SKILL.md)。本文整理现有制作方法，不新增资产接受、不自动重建旧批次。

## 1. 固定对象、当前目录与影响范围

记录 ID、名称/学名或物件构造、目标尺寸、来源审核/哈希、当前 GLB/图集/目录/材质/动作依赖、修改范围、需保留的外观、旧失败和待查。模型变更后旧哈希报告不再自动有效。布局、绑定、材质和 shader/实例数据也可能在 GLB 不变时影响外观/动作。

当前已记录的组合是 20 种草、30 件静态造景，共 50 件；此数来自 V11 handoff，不含底床/碎石/鱼。核对实际目录后再施工：

| 当前组成 | 资产/入口 | 状态定位 |
|---|---|---|
| 首十种正常叶草 | `game/assets/aquascape-v10/`，骨骼与无骨骼 shader 分支 | 游戏 `plans/reviews/aquascape-natural-v10/validation-report.json` 及 `motion-visibility/` |
| 首批石木与十件小摆件 | `game/assets/aquascape-v9/solids/` | `plans/reviews/aquascape-budget-v9/validation-report.json` |
| 追加十种草、十件静态物件 | `game/assets/aquascape-v11/` | `plans/reviews/aquascape-expansion-v11/production.handoff.json`、`validation-report.json` |
| 实际合并注册表 | `game/assets/aquascape-v5/catalog.json`、`game/assets/aquascape-decor-v1/catalog.json` | 文件名 V5/V1 不表示当前仍是首版；逐项读实际 `model` 和变形分支 |

V11 预览的 `accepted_for_commit` 不代表完整游戏性能或连续碰撞已接受。历史记录里的 E: 绝对路径是来源信息；先按当前根目录、归档索引重定位，检查输入确实存在且不是未下载的 LFS 指针，再运行。

## 2. 准备并审核来源

新生成走冻结 Brief / Production Delta → `workflow context → validate → init → run → status`，所有业务命令 `--json`；运行中只查同一 job，失败按原合同恢复。先看各命令 `--help`，Unix 用仓库解释器或 `bash gamefactory`，Windows 用 `gamefactory.cmd`。作业到 `done/human_review` 后实际看图，记录图像用途和审核范围，才裁切/抠图/建模。已有来源核验原 manifest、assets-manifest、审核和输入 SHA，不补造新生成记录。

水草艺术描述使用“一簇自然生长的【品种】水草”，以叶形、叶宽、颜色、生长方式区分。不规定叶片数量、固定变体、逐叶外张/弯曲角，也不统一安排侧卷/突出翘叶/展开嫩叶。正常叶修复优先从本种已看过的既有原画取源；`normal-leaf-sources.json` 的旧叶片索引是来源定位，不是新图的数量要求。

整簇正/侧/俯参考用于布局，单叶或枝叶簇图用于轮廓与纹理。图上 ROOT/TOP 标签不能证明相机和根区正确。分叉、叶柄/根冠、轮廓、遮挡、对象身份与像素画风分别看；未知背面/深度明确写推断。石木与摆件按 [正交视图方法](../../../aquascape/ORTHOGRAPHIC-METHOD.md)核对同对象三向共同坐标，不非等比拉伸来伪造一致。

源图、风格参照、提示、拒绝原因、原始尺寸、角色用途和 SHA 进入原 handoff。V3 端视 `depth_only`、斜视 TOP 和 V11 辅助视图只在原批准范围使用，不升级为精确空间测绘。

## 3. 水草：布局、原像素、连接与低面构建

先按本种生长方式和已审核整簇标注布局：根茎附生、放射根冠、有茎、匍匐、苔藓等不能只换名称共用角数组。金鱼藻等无根种不补造根束，固定作者基点不等于声称有生物根系。历史计数和固定角仅用于同一来源复现。

两类现有实现按来源选择，不因批量性能自动替换所有植物：

| 分支 | 实现与适用边界 |
|---|---|
| 独立叶片闭合壳、根茎和骨骼 | `build_catalog_models.py`；V7 轮廓/V8 全边颜色处理、V9 低面、V10 正常叶固化。适合来源中可独立审核的完整叶片 |
| 原画枝叶簇薄壳、alpha 间隙、固定基点 shader | `build_expansion_v11.py plants` 与 `expansion_source_layouts.py`；本批细碎枝叶各有独立配置，不是整丛单张广告牌，也不保证新物种可只改 ID |

原分辨率裁切、nearest 采样，检查自由缘 RGB/alpha、背面/封边和白底污染。只扩 alpha 会露白，只有内轮廓一圈去白会漏实际外扩边；参照目录 V6—V8 负例。正反叶壳应有正确朝向、基部连接和自然体积，不把密集拓扑当像素细节；低面可见折线如实记录。

正常叶修正由 `normalize_plant_leaves.py` 将源叶形/朝向、根连接、rest 与 inverse bind 一起固化到 GLB；不能在游戏临时掰叶作为完成结果。新来源使旧供体审核失效。植物基点取实际作者根基，透明载体角/包围盒最低点可能在根下，不能据此放置整丛导致悬浮。

## 4. 石木、人工摆件、底床与完整预算

[预算 JSON](../../../aquascape/geometry-budgets.json)按一个完整摆放实例合计所有三角面，包括叶片/根茎、两面/封边、子网格及附层：

| 分类 | 优选 / 硬上限 |
|---|---:|
| 碎石代理 | 150 / 300 |
| 普通石 | 400 / 600 |
| 明确分类的大主景石 | 700 / 1000 |
| 沉木 | 800 / 1200 |
| 带状草整丛 | 400 / 600 |
| 宽叶草整丛 | 700 / 1000 |
| 复杂人工摆件 | 1200 / 2000 |

分类写进本物件配置，不能静默升档、按单叶拆预算或为凑数增加面。鱼预算读鱼专用说明：11月2日用户已确认普通鱼继续按展示体长分档、鲨鱼保留例外；本JSON的fish行只对应普通≤120cm档，不能覆盖更长普通鱼或鲨鱼。

石木先对齐分叉/断头/根足/阶台等结构点，再共同约束体积和供体。三向外轮廓交集可能削枝、形成板状或断开；总跨度接近/IoU 高只证明对应投影的一部分。低面 QEM 保留拓扑、轮廓与连接，浅色斑点误追成微孔、非流形和分离木根须单独识别。

人工摆件先明确是真贯通、盲孔、开放底还是有底容器；建壁厚、内壁、底面及洞口射线/连通检查。罐口不能硬交成方口；顶/侧供体不能把黑色开口投到实体屋顶或封闭背面形成假洞。`build_decor_ten.py` 的语义检查与 V11 新物件分支都属于本批适配；离散射线通过不保证任意尺寸的鱼可以穿过。

底床用分区网格与材质，碎石用代理和实例化，不把每粒沙做独立高面物件。分别参考游戏 `AQUASCAPE-SUBSTRATES-V2.md` / `AQUASCAPE-SAND-TRIAL-V1.md`；当前 JSON 的碎石预算是单代理，不能把全部底床默认为一个 300 面实例。

**部署门**：旧高面构建路径末端使用 `optimize_scenery.py --deploy`，其内部先跑预算/结构验证再更新指定目录。V11 从预算内直接构建，`deploy` 同样先调用 `validate_scenery_budget.py` 才合并目录；不为机械重复优化损坏已低面的壳。最终对实际合并目录运行预算门，保留优选是否达到、模型 SHA、几何/根/洞口报告及实际图审。硬上限内不等于外观通过。

## 5. 水流：两条分支分别验

**骨骼**：按 [PLANT-CURRENT-METHOD](../../../aquascape/PLANT-CURRENT-METHOD.md)读取原生 `WaterSway`、骨架、Skin、权重。五节骨/前 8% 固定/十秒/30Hz 是当前已实测实现参数，不是植物生物标准或所有新草必须复制的值。本物件根茎/基部固定，叶尖有真实小幅位移；实际导出 CPU 与 Godot 原生绑定分别验 rest、固定点、位移与首尾循环，确认暂停恢复。81/41 等离散相位不证明全连续时间无互穿。

**shader/实例化**：V9/V10 的无骨骼分支用图集、UV2/顶点色编码根至尖/相位和作者附着点，V11 使用其枝叶簇配置。不要混用格式。根部固定、默认/最大水流包络、首尾一致、四分之一周期变化，须对实际 shader 与 MultiMesh 验证。

V10 已发生的负例：时钟和水面变化，实际叶片像素零变化。Compatibility 路径需要 `use_colors=true` 并逐实例设置 `Color.WHITE`，否则依赖 COLOR 的权重可失效。必须在实际连续时间只对叶片区域比较，排除水面变化；暂停两图逐像素一致，恢复继续运动。单个 MeshInstance 相位特写不能替代真实实例群证据。入口为 `validate_live_plant_motion.py`、`validate_shader_plants.py` 及对应实际引擎捕获。

海葵/软珊瑚有独立柔性部位，不能直接套阔叶权重或统一静止；仅在 Brief 明确包含时扩展。新研究先记未知，不声称已有草的检查覆盖了它们。

## 6. 冻结、实际引擎与性能

局部来源/灰模/材质/根/运动看稳后再冻结候选与全部运行依赖，集中验证：完整实例预算、有限坐标/闭合/非流形、真实根基/绑定/循环、适用洞口/底面、原像素与材质归属。已有脚本检查范围从实现和报告读取，不套用鱼的 072/077 或虚构造景总门。

静态结果先固化到构建输入、GLB/纹理及必要源文件，保存引擎材质/shader。显式重导入，新进程直接读最终资源与真实合并目录，关闭临时静态造型链；看正/侧/背/俯/斜/灰模、绕转、水下和代表相位。摆放类还要实际选择、放置、保存/回读；检查锚点与缸边界。用户原认可的尺寸/画风/轮廓、连接、洞口与正常动作继续保留。

性能只在请求/测量问题需要时测：冻结 GPU/引擎/后端、分辨率、垂直同步、实例数、模型面数和动画路径。区分资产真实面数、MultiMesh 提交量、draw call、GPU 时间、引擎内存计数和进程内存。旧 V9 修复前“千丛 shader 性能”不能当有效动画结论；V11 独立千丛结果也不能保证加鱼、水体和阴影后的整缸帧率。退出 ERROR 与当前行为分开记录，不能声称已解决。

## 7. 每轮回写、交接、清理与提交

使用[共通知识收尾卡](../../../../docs/3D-ASSET-KNOWLEDGE.md#每轮修改后的知识收尾卡)，在原 handoff / validation report 更新：通用方法进入对应 SOP/专题，本种/物件的尺寸、布局、来源/根/供体/运动与分类回到配置，本次输入输出 SHA、技术覆盖、实际图审、失败/未知和用户接受范围回到证据。

没有新方法只需链接已采用卡与参数差异；新方法写清替代了哪条旧路线并接入入口。暂停也记录实际进度和下一步。造景当前没有自动汇总全部来源、图审、源固化和冷读的 SOP 检查器；`validate_scenery_budget.py` 只覆盖其实现的技术子集，不能冒充整套完成。

先核验原始来源、当前资产、唯一对照/动作证据与归档恢复路径，再逐路径/SHA删除可再建高模、重复图、逐帧/稠密样本、临时工程/日志/缓存，记录剩余体积。不要直接重放历史清理名单。用户要求“提交”时在两个独立 Git 仓库完成 commit + push 并确认结果，避免纳入其他工作的现场；本轮只是梳理时不为此重导出模型或重授接受。

## 8. 工具与旧版本的使用边界

先查所用脚本 `--help` 和输入依赖。现有脚本并不都可只换配置重用：

| 入口 | 适配边界 |
|---|---|
| `produce_catalog.py`、`produce_decor_ten.py` | 历史二十件/十摆件整批生产器，含 `.venv/Scripts/python.exe` 和固定版本链；不能直接覆盖已扩充的当前注册表 |
| `build_expansion_v11.py extract → plants → solids → registry → deploy` | 本批固定配置和目录；`deploy` 验证后合并，不删除旧资产；新批次先明确适配，不把 V11 文件名当通用参数 |
| `finish_expansion_v11.py` | 本批技术收尾/清理器，会写 pending 的 handoff；不可对已接受记录盲目重跑覆盖用户状态 |
| `normalize_plant_leaves.py` | 使用同种已实际审核供体和 V10 rest 重绑定证明；新源先重新审核 |
| `optimize_scenery.py` | 显式 `--input`、`--output`、`--report`、`--root`；不传 input 的历史默认不代表当前全部目录 |
| `validate_scenery_budget.py` | `--input` 可传多个实际 catalog，`--root`、`--output`、`--json`；读取本地模型和所需基线/语义证明，缺输入先恢复，不删守卫 |

报告路径必须在仓库明确的 `work/`、`output/` 或项目实验/审核目录，先解析绝对路径。文档中的 `<...>` 必须替换真实路径，不能原样执行：

```text
<repo-python> resources/scripts/aquascape/optimize_scenery.py --root <foundry> --input <candidate-catalog> --output <game/assets/candidate-dir> --report <review/build.validation.json> --deploy
<repo-python> resources/scripts/aquascape/validate_scenery_budget.py --root <foundry> --input <actual-catalog-1> <actual-catalog-2> --output <review/budget.validation.json> --json
```

Unix `<repo-python>` 使用 `.venv/bin/python`，Windows 使用 `.venv/Scripts/python.exe`。顶层 workflow 可用 `bash gamefactory ...`（当前 Unix launcher 未设可执行位）；不要为了读帮助触发生产器、网络生图或完整重建。

历史知识定位：V2 单图鼓包的限制见游戏 `AQUASCAPE-ART-V2.md`；V3 相机/深度冲突见 `AQUASCAPE-THREE-VIEWS-V3.md`；V4 骨骼见 `AQUASCAPE-PLANT-CURRENT-V4.md`；V5—V11 轮廓/白边/低面/正常叶/实例化见 `AQUASCAPE-CATALOG-V5.md`；摆件构造见 `AQUASCAPE-DECOR-V1.md`。主题海缸与大厅见 `AQUASCAPE-MARINE-V1.md` / `AQUARIUM-HALL-3D-V1.md`，不因模型任务扩展大厅玩法。
