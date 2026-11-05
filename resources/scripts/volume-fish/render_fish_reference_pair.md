# 完整鱼正交参考对照

2026-11-05收尾：本次24鱼已获用户成品接受，用户要求旧实验图片、模型和重放数据退休。完整交付为 `docs/reviews/fish-reference-comparison-20261105.pdf`，来源角色、差异和SHA文字在同名文档目录。此渲染器及通用材质提取方法可供新任务使用；带日期的本轮prepare/batch/gallery/PDF编排脚本只是方法实现记录，其旧output/实验输入已退休，不能当作当前成品入口或声称一键重放仍可用。新对照请基于当前canonical GLB与明确来源重新建立输入，不恢复历史候选。

运行Blender后台，只读原文件，输出四张灰模：ours/reference各side/top。选加--native则另出四张原材质图（原游戏CustomShader不复现）。不批跑，不做PCA，不找最大连通块，不隐藏鳍，不改网格，不拉直尾巴；OBJ所有g组均保留。blend按所有MESH对象原mesh data/节点world读bind/rest，不烘焙Subdivision等modifier、不采样动画；请优先提供唯一完整鱼GLB，含其它辅助mesh的blend不应冒充整鱼来源。

## 命令

E:/blender/blender.exe --background --factory-startup --python resources/scripts/volume-fish/render_fish_reference_pair.py -- --pair <绝对pair.json> --output <仓库output内新目录>

renderer在异常时写ok=false结构化report（不会覆盖预先存在的输出目录）。Blender可能返回0，调用者须检查Traceback及report.ok/source_files_unchanged；正式渲染还需四张或八张文件存在。

## 输入

顶层id、resolution=[1280,800]、ours、reference。每个asset必填：

- path与sha256：明确实际OBJ/GLB/blend。GLB必须自包含。
- canonical_from_source_axes：[带符号轴名三项]，依次是canonical X鼻向、Y向上、Z已声明横向，例如我们的file-native GLB为["+X","+Y","+Z"]；旧五鱼已观察库OBJ可为["-Y","+Z","+X"]。每条鱼均须独立核准，不自动继承。
- uniform_scale：大于0的明确等比因子；不支持非等比缩放。
- pose：固定"bind_rest"，不采样动画。原文件mesh data、完整静态节点world保留；GLB会显式撤回Blender固定glTF上轴转换，再应用输入signed axes，并将原始GLB节点层次TRS/matrix的bounds与实际导入source-world bounds核对。OBJ直接读取v坐标、逐角vt，无OBJ importer默认换轴。
- alpha_policy：GLB/blend为"preserve_embedded"；OBJ精确材质表为"explicit_obj_recipe"；无法恢复OBJ alpha时须显式"raw_mesh_unverified"，渲染图上红字标明卡片边不等于可见鳍外缘。

每个asset各自按全部有面顶点的canonical X span归一为1、完整bbox居中，仅用等比scale与平移。长轴span是工程几何口径，不是生物TL/SL；尾弯与开口等原始rest差异保留。pair两资产、side/top共同一份ORTHO scale和宽高，包含双方所有鳍；camera projection实际验证两视每单位X像素数一致。PNG内标归一口径、姿态与alpha边界，render.validation.json保留完整数值、节点world、输入/输出SHA。该图只用于比较，不构成物种身份、生物实测或形态接受。

## OBJ显式材质表

obj_materials是list，每个实际有面的g组恰好一项：group/name/texture_path/alpha_mode(OPAQUE|MASK|BLEND)/alpha_cutoff(MASK必填)/base_color(RGBA)/uv_scale/uv_offset/double_sided/source_material_key。texture_sha256可加并阻断核对；flip_v默认false，只在原OBJ vt上先翻V，再scale/offset；interpolation默认Closest、extension默认REPEAT，须按真实source recipe给定。若UV不能确认，保留未知而不猜纹理方向。

OPAQUE忽略纹理alpha；MASK按真实cutoff；BLEND保留连续alpha。matte只断开BSDF RGB/光照输入，Alpha上游、mode/threshold与backface策略保持，before/after alpha图签名相等。无可解析Principled alpha的native shader会失败，不猜一个alpha。OBJ recipe仅为标准diffuse＋原alpha诊断，不声称重现Unity custom shader。alpha恢复来源、纹理SHA/材质key/UV参数进入报告。

旧compare_database_fish.py只选body组最大连通块并画投影，不作为此完整鱼入口；body-only若后续需要，须另给明确原始面组/三角范围，不推断largest component。


## 集中预检与清洁RGBA

加--preflight-only时复用完全相同的导入、源SHA、GLB静态节点world bbox核对、完整mesh/group库存、alpha图保留及两视共用camera流程，只跳过渲染；preflight.validation.json的rendered=false、files={}。不导出模型，不制作另一套gate。unsupported alpha/GLB输入会明确ok=false，不能以Blender退出码0放行。

加--clean-rgba时背景透明，完全不创建文字/标签节点，仍输出同名四张或加--native八张PNG，便于root直接使用alpha叠加；report记clean_rgba=true、相同camera/原bounds/center/归一factor。可与--preflight-only合用；此模式是默认有标签probe之后按root要求加入，未为它重复渲染probe，正式批次须实际看图。

Blender glTF importer可能创建Icosphere骨骼custom_shape。只排除具备明确bone.custom_shape引用且不属于原GLB mesh node的导入辅助对象，在报告逐名记录。所有真正原GLB mesh均保留，OBJ全部g组均保留；.blend不凭这一GLB辅助规则去除自身mesh。GLB importer up轴撤回为source=(blender.X,blender.Z,-blender.Y)，并以原GLB静态节点层次world bbox核验。顶视camera从+Y、screen right=+X/up=-Z；侧视从+Z、right=+X/up=+Y。除XY framing，所有有面顶点还须处于camera前方深度范围，防止空白反向相机漏判。
