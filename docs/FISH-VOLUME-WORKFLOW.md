# 单图鱼类实体建模与游戏展示

**增补皮肤排除二维描边：** 原侧图的轮廓墨线用于识别形状，不能经UV延展、最近不透明扩展或供体混合进入背、腹、吻端、下巴等增补表面形成黑环/条纹/杂色。制作前标出描边与正常皮肤，取色时排除描边；真实斑纹、口裂、鳃线和合理明暗分别保留，不能按亮度一概删除。修补须锁定正常身体的像素分布与配色，不能用整片背腹重采样去污染。按项目[二维描边与增补皮肤规则](../projects/fishing-2d/docs/3d-fish/MOTION-AND-SURFACES.md#二维描边不得进入三维增补皮肤)核对供体及无光照/游戏多视、动作；明确污染未解决不得接受整鱼材质，不能用技术门通过代替。该规则已记录；未声明所有现用鱼或自动描边识别均已完成。

085口部材质补充：按目标物种分别定义中央吻端外皮、上下唇、口腔内衬和深处阴影，不能为缺少正面供体而收尖几何，也不能给所有口内面统一近黑色。当前13条模型共用的近黑口腔是旧制作默认，尚非逐种生物学证据。大黄鱼口内白/口缘粉是已查到的反例；其他物种色素未知保留未知。源侧图边缘描线不得横向拉成正面皮肤，连续过渡不能用硬法线切换。具体来源、全21鱼研究卡与修订验收见目标项目 [ORAL-JAWS.md](../projects/fishing-2d/docs/3d-fish/ORAL-JAWS.md) 的085节。本轮是研究，不是模型修复接受。

本流程覆盖像素鱼源图、物种专用实体建模、骨骼动作和 Godot 展厅验收。通用 CLI、构建器和物种 profile 保存在 Foundry；正式 GLB、选定原生模型和游戏集成报告保存在目标游戏。旧 Fisher（`fishing-2d`）实验脚本保留为历史参考，后续生产入口统一为 Foundry。视频是预览证据，游戏运行的是网格、蒙皮和骨骼动画。

**每条鱼完成后固定执行鳍根绝对连接门（072起）**：新建、局部修改、材质整理或重新导出均检查全部适用鱼鳍；冻结完整鳍基而非单个锚点，静止、原生循环、实际Godot四动作与动作切换均检查。通用入口 `resources/scripts/volume-fish/validate_fin_completion.py --plan <冻结模型与根区清单> --game <游戏目录> --godot <可执行文件> --blender <可执行文件> --output <报告目录> [--species <鱼>]`。同姿态蒙皮身体三角面BVH测正负距离；漏鳍、空根区、模型哈希过期或距离失败返回非零。不能以保持旧坐标或处于鱼缸包围盒内代替连接检查；无可靠根区时先补资料与选择器。机械通过后仍复核源图、灰模/贴图多视和完整动作。游戏侧简化入口与本批失败基线、修订证据见 [VALIDATION.md](../projects/fishing-2d/docs/3d-fish/VALIDATION.md)。

## 建模前先查物种尺寸与部件结构

### 073：知识与技能入口、完整鳍基配置

可复用技能为 `resources/skills/fish-volume-production/SKILL.md`，物种研究与失败经验继续维护在游戏 `docs/3d-fish/`；不再为每轮制作重新发现069d源图吻部和072鳍根检查的结论。

嘴部返修的结构/材质诊断见该技能 `references/mouth-repair.md`。091海鲈的有效经验是：先看同种真实口部，固定原画坐标，分别对齐额头、口裂和下巴；不可只抬口线而保留错误下颌。侧面轮廓、横向厚度推断、真实三维唇缘取色及正面口内面分别审核。用户认可改善并授权提交后保存当前版本，同时保留尚未解决的外观边界；单鱼参数不自动推广。

新建鱼鳍可声明 `source_baseline: [[u,v], ...]`，2–128个源图左上原点归一化点。参数按点到完整基线的源图物理X/Z距离、除以鳍面远端跨度计算，基线上各点均为t=0；与只用anchor→tip点积不同，倾斜或曲折鳍基不会丢掉另一端。构建时细分基线，投影前保留 `foundry_fin_source_t`，根带继承身体权重，向远端平滑回到鳍骨。该字段供新建模型使用；保留原生修订不能从投影坐标重猜源参数。

`root_attachment.surface_region` 可省略为 `nearest`，或显式为 `posterior`。后者仅用于适合的尾柄后端连接，限制到后端朝后的身体面，避免薄片点分投左右侧后使根带横穿身体。073褐鳟旧候选曾被既定6mm埋入门拦截；修投影目标后通过，没有放宽门槛。蓝鳃太阳鱼旧臀鳍轮廓产生非流形，构建门同样阻断，保留失败报告。

`freeze_authored_fin_roots.py -- <output.plan.json> <handoff.json> [...]`（Blender运行）从本次原生POINT参数冻结每个鳍的完整根区，再运行固定完成门。073验证蓝鳃7鳍、褐鳟8鳍；不能据此宣布任意未定义鳍型自动支持。嘴部方法选择见知识库 `ORAL-JAWS.md`：单一侧面皮肤的小静态口裂允许连续原UV；侧/正面多来源仍要求连续头部图集。

**部位判断不清或制作后无法验证时，必须回查形态资料。** 按游戏知识库的 [部位查证规则](../projects/fishing-2d/docs/3d-fish/ANATOMY-RESEARCH.md)定位疑点，查询中英文术语和目标物种在该位置的原始描述/实拍，再转成位置、形状、连接、尺寸或动作约束与有效检查。此分支贯穿准备、建模及验收，用户指出形态问题也触发；不因技术全通过就跳过。查不到的保留未知，区分资料不足、模型错误与验证能力不足；不继续盲调该部位，不把未经验证的模板推广给其他鱼。通用方法沉淀到部件指南，物种参数与证据留在物种卡；研究、实现、验收状态分别报告。

先读 fish 知识库的 [建模前准备](https://github.com/ccl6075316-afk/fishing-2d/blob/main/docs/3d-fish/PREPARATION.md) 与 [验证与交付](https://github.com/ccl6075316-afk/fishing-2d/blob/main/docs/3d-fish/VALIDATION.md)（本地 `projects/fishing-2d/docs/3d-fish/`）。准备时冻结物种、测位、资料类别和会失败的基线；交付分别报告技术、同测位资料、连接、源图轮廓、真实蒙皮动作、整体视觉。不得只对齐一个宽度或以包络通过代替其余项目。

验收先覆盖前期研究的头、吻、眼、各鳍等适用部位，再复核整鱼长宽高、指定背部宽度及关联比例，最后评整体视觉与动作。操作者须对照最初资料主动判断尺寸偏差是否合理，允许有依据的制作容差，不要求完全一致；关键比例明显失真应修正。各项接受区间及理由在制作前记录，不以统一百分比或事后放宽区间代替判断；具体清单、偏差示例及报告格式见上述验证指南。

共用制作知识库在独立 fish 仓库的 [`docs/3d-fish/README.md`](https://github.com/ccl6075316-afk/fishing-2d/blob/main/docs/3d-fish/README.md)，本地路径为 `projects/fishing-2d/docs/3d-fish/`。新增或重建真实鱼类时，先按其中尺寸规范查同种形态测量，填写物种参考卡；巨骨舌鱼已有原始宽高、头部比例和当前模型尺寸示例。缺少数据须记录检索与推断，不能仅依据生成三视图估计全部厚度。

先区分 TL/SL、裸鱼体与含鳍包围盒、局部与最大宽高。英语生物测量 `body depth` 是背腹体高，当前 profile 的 `half_depth` 是左右半宽；两者不可互换。按相同解剖测位约束灰模后，再对齐多视图和划分 UV。头/嘴/眼、背鳍/臀鳍、尾柄/尾鳍、成对鳍须分别核对；环绕视频与五视检查共同评价整体，不能只凭正脸静图判整鱼优劣。

## 当前生产入口：先像素源图，后实体模型（040）

原游戏是像素画风，增加三维体积不改变这项风格要求。新鱼先使用 Foundry 的生图流程，并把已有已接受的鱼图作为风格参考；明确整侧面、独立鱼体、轮廓可拆分的鱼鳍、有限色阶及清晰像素块。检查源图形态、轮廓、配色、像素密度和鳞片/鳍条表现，再按现有 `assets review` 接受源图。不要先做光滑程序色模型，再用 nearest 或后处理宣称风格已统一。

已有鱼种可复用已经生成并接受的源图，仍须提供资产清单、生成来源和审核记录，不因变为 3D 就强制重复生图。源图 `image.raw` 阶段须完成，资产审核须接受；canonical 透明源图必须真实存在，Brief/profile 中必须明确 `pixel_art` 与 `style.reference_image`。缺失来源、审核或风格契约时，`volume plan` 返回阻塞/修输入；不能跳过 CLI 直接运行内部 Blender 脚本。

先执行 `volume --help` 及所需子命令 `--help`。为本次鱼种准备 profile：

1. 将 `resources/volume-fish/profile.schema.example.json` 复制到该项目的制作资料目录，例如 `volume/blacktip-reef-shark.profile.json`。模板是 `draft`，不是已接受鱼形；已有物种 profile 也须对照本次实际源图检查。
2. 将已接受的游戏风格参考图原样复制到 profile 同目录，命名为 `style-reference.png`，保留示例的 `style.reference_image: "style-reference.png"`；也可显式改为绝对路径，或 `repo://` 开头的 Foundry 根相对路径。普通相对路径按 profile 所在目录解析，禁止 `../` 向父目录跳转。不要移动或改写原参考素材。
3. 根据已接受的 canonical PNG 校准 `source_aspect_ratio`、body 横截面、脊柱、鱼鳍、眼睛、须和动作参数。坐标契约为 `normalized_source_top_left`；厚度和隐藏部位须说明推断。确认 `style.pixel_art=true`、`texture_filter="nearest"`、`roughness=1.0`。校准与输入审核通过后才把 `profile_review_status` 设为 `approved`，不能只改状态跳过检查。
4. 调用下面的 `volume plan` 冻结输入。profile 输入接受与产物美术接受是不同审核：profile 已批准，输出仍须三视和实际游戏风格审核。

CLI 输入如下，Windows 使用仓库 launcher；Unix 使用对应 launcher 或已配置的仓库 Python 环境：

```bash
.\gamefactory.cmd volume plan --brief <brief.json> --assets-manifest <assets-manifest.json> --asset <asset-name> --profile <species.profile.json> --output <handoff.json> --json
.\gamefactory.cmd volume build --handoff <handoff.json> --blender <blender-executable> --json
.\gamefactory.cmd volume validate --handoff <handoff.json> --json
.\gamefactory.cmd volume render --handoff <handoff.json> --blender <blender-executable> --json
```

上述四步之后，操作者或外部 Agent 逐张检查侧面、正面、斜视、源图/风格参考对照图，并完成目标游戏画面审核；通过后执行第五条命令收口：

```bash
.\gamefactory.cmd volume accept --handoff <handoff.json> --note "Agent visual review: inspected side/front/oblique/style comparison and game views; record concrete findings and image paths here" --json
```

`--note` 必填，应写实际审查者身份、所看图及具体结论，不能照抄示例占位文字。外部 Agent 的检查只记录为 Agent 视觉审核，不能写成用户本人已接受。发现缺陷先修源图/profile/模型，再构建、渲染和复核，不能直接修改 handoff 的接受字段。

`plan` 只创建待执行的 handoff；`build` 使用固定构建器生成实体、绑定、动作和导出；`validate` 读取产物检查技术条件；`render` 生成侧面、正面、斜视及源图/风格参考对照；`accept` 在视觉审查之后检查构建、渲染及四张审核图仍对应当前输入与产物，记录接受结果。产物目录为 handoff 同目录的 `<handoff-stem>-artifacts`，渲染检查另存 `render.json`。按每次 JSON 的 `ok/status/next_action/failures` 决定下一步，不把命令退出或文件存在当作完成。Blender 路径可由 `--blender` 临时指定，未提供时查找 PATH 中的 Blender。构建和渲染不自行触发生图；付费生图仍走已有 image/workflow 入口和资产账本。

通用入口为 `resources/scripts/volume-fish/build_fish.py`，物种 profile 位于 `resources/volume-fish/`。profile 描述物种自己的轮廓、厚度、鱼鳍和动作，不用同一条鱼任意拉伸替代解剖。handoff 冻结源图与风格参考的 SHA256，记录 native 图片尺寸、产物路径及像素材质契约；输入改变后重做计划与相应审核。仅把 handoff、资产清单和 validation report 作为状态，不另建生产队列。

### 已接受源图随原生模型归档后的复用

旧生图工程不在当前机器、但完整的模型接受证据仍在时，可使用 `volume replan --archive-inputs <archive-inputs.json> --profile <profile> --output <new.handoff.json> --json`。先读 `volume replan --help`。这是同物种、同展示体长、同源像素的历史接受复用，不重建或伪造已丢失的 frozen Brief、raw、pipeline 或 image.raw 状态。

输入映射必填 `accepted_handoff`、原始 `profile`、`blend`、`glb`、`source`、`reference` 和 `review_images`；有辅助源图时提供 `front_source/top_source/bottom_source`。路径显式定位当前本机文件，相对路径以映射文件目录解析。`review_images` 的键和值须覆盖旧接受记录的全部审核图。CLI检查旧handoff确为done/accepted、有操作者说明与历史生成/源图接受记录，并核对原profile、模型、全部源图、风格图和审核图的接受哈希。只有profile文本允许Git CRLF→LF规范化比较，图片和模型要求逐字节一致。

生成的handoff冻结当前映射及所有证据哈希，仍为pending/run、视觉pending，随后走同一个 `build → validate → render → 实际审核 → accept`。每一步重新检查归档证据，禁止覆盖接受输入。`accepted_archive.scope` 明确记录上游原文件没有重新验证；旧Brief字段仅保留历史身份，不冒称本次重新运行了缺失的workflow。缺少这些接受证据时不得使用该入口，应恢复原工程或按正常workflow重新制作源图。输入映射只是文件定位，不是第二套接受状态。

055黑鳍礁鲨复核采用此入口：源图像素与041接受一致，改进胸腹鳍连接并试验第二背鳍高度。部位标准见游戏 `docs/3d-fish/species/blacktip-reef-shark.md`；实验通过与最终整鱼接受分别记录。

### 可选正面辅助原画：双来源头部投影

侧面图无法提供可靠的正面头部纹理。需要补全这部分时，先为正面辅助原画建立独立的 frozen Brief，设置 `project.view="front"`，通过已有 Foundry workflow 生图，再完成透明 canonical 图和 `assets review` 接受。提示硬锁为正对观众、居中对称，禁止侧面和三分之四角度。它使用与侧面图一致的像素风格参考；不是把侧面像素强行拉到整个正脸，也不是生成后的图像后处理。

侧面原图继续用于身体和鱼鳍；可选正面原图只投射到 profile 指定的头部朝前表面。两张图都以原始分辨率打包，各自检查 Foundry `image.raw` 完成、接受状态、冻结 Brief、生成来源与哈希。正面资产的 Brief 从其资产清单读取，不能拿普通本地图片绕过来源审核。

```bash
.\gamefactory.cmd volume plan --brief <side-brief.json> --assets-manifest <side-assets-manifest.json> --asset <side-asset-name> --profile <dual-source.profile.json> --front-assets-manifest <front-assets-manifest.json> --front-asset <front-asset-name> --output <handoff.json> --json
```

`--front-assets-manifest` 与 `--front-asset` 必须成对提供，而且 profile 必须包含 `head_projection`；反过来，包含 `head_projection` 的 profile 也必须提供正面源图。随后仍执行相同的 `build → validate → render → 视觉审查 → accept`。不要仅靠新增字段将未审核的 profile 设为接受。

`head_projection` 的必填字段如下。数值是说明结构的示例，必须按实际侧面几何与已接受正面图校准后才可使用：

```json
{
  "head_projection": {
    "start_u": 0.86,
    "end_u": 0.98,
    "normal_threshold": 0.35,
    "side_limit": 0.65,
    "source_rect": [0.25, 0.2, 0.75, 0.8],
    "model_depth_range": [-0.05, 0.05],
    "model_v_range": [0.3, 0.65]
  }
}
```

| 字段 | 含义与边界 |
|---|---|
| `start_u`、`end_u` | 侧面源图归一化横坐标中允许投射的头部区间，均为 0–1 且不相等；允许逆序，实际按最小/最大值取区间。 |
| `normal_threshold` | 表面法线沿鱼头方向的分量必须大于此值，范围 0–0.95，避免覆盖侧腹。 |
| `side_limit` | 表面法线左右分量绝对值必须小于此值，范围 0.1–1。 |
| `source_rect` | 正面原图中的 `[左, 上, 右, 下]` 归一化矩形；各项 0–1，左小于右、上小于下。 |
| `model_depth_range` | 模型左右厚度方向映射到正面矩形宽度的区间，按鱼头朝向统一左右；以侧面原图整幅宽度为 1 的模型单位表示，各项 −0.5–0.5 且递增。 |
| `model_v_range` | 模型上下位置对应侧面源图的归一化高度区间，0–1 且递增，映射到正面矩形高度。 |

`head_projection` 还可提供 `uv_patches`，用于在已接受正面原图中借用邻近像素修正重复眼纹等局部投影。它是最多 16 项的数组，每项只允许 `polygon` 与 `offset`：`polygon` 为 3–128 个归一化 `[u,v]` 顶点（各项 0–1），`offset` 为两个 −1–1 的有限数。每个顶点加上 offset 后的 donor 坐标也必须留在 0–1，不能靠截断或纹理重复掩盖越界。省略表示不修补；只改变模型 UV，不修改源 PNG。

眼睛需要贴合头部表面时，可使用 `eyes.mode="surface_patch"`。原有 `center`、`radius`、`depth` 仍必填，并增加 `source_rect`（归一化 `[左,上,右,下]`，各项 0–1 且宽高为正）、`thickness`（0.0001–0.01）和 `surface_offset`（0–0.003）。`center` 和 `source_rect` 都取侧面原图左上原点的归一化坐标；半径、深度、厚度和表面偏移使用“侧面原图整幅宽度为 1”的模型单位，矩形的原生像素纵横比决定眼部贴片高度。派生半高 `radius × (矩形归一化高度 / 矩形归一化宽度) / source_aspect_ratio` 也必须为有限正数且不大于 0.05；CLI 按 profile 宽高比检查，构建器再按实际原图宽高检查，拒绝极窄矩形导致的溢出或过大几何。所有数值必须有限，拒绝 NaN/Infinity。未提供 `mode` 时维持原有眼睛行为，且禁止携带这三个 patch 字段；显式 mode 只接受 `surface_patch`，未知字段或模式均拒绝。这些参数须按实际头部和原画眼位校准，不能通过增加眼球体积掩盖眼位错误。

投影只为符合区间和法线条件的身体表面选择正面材质及 UV，鱼鳍和其余身体继续使用侧面图。它不自动确定真实头部厚度，几何仍需单独校准。渲染对照包含侧面源图、正面源图、风格参考和模型，检查接缝、眼口位置、色阶及像素密度；有双来源文件不代表观感已通过。

该接口描述 Foundry 支持的可选能力。040 本次正面辅助原画的实际生成/接受和双来源模型完成情况须读取对应资产清单、handoff 与报告；接口或自动测试通过不能写成本次双来源美术已经完成。

### 风格审核不能由机械检查替代

对照板至少同时提供源图、已有风格参考和模型三视；实际 Godot 中再检查默认距离、近看、正侧面和斜视。审核项目包括像素块尺度、有限色阶、轮廓节奏、鳞片/鳍条笔触、体积遮挡和原图已画明暗是否被物理光照重压。新旧鱼放在同一灯光和相机条件下比较。发现风格不一致，应修源图或材质并复核，不能把“32 项 GUI/骨骼检查通过”写成美术通过。

自动构建和首次验证只确认网格、蒙皮、动作、原尺寸纹理、nearest 和粗糙材质等条件，保持 `style_visual_review=pending`、`next_action=human_review`，不能自动接受风格。`volume accept` 检查报告、输入、blend/GLB 以及四张渲染图的新鲜度并冻结相关哈希，通过后写入 `handoff.style_visual_review=accepted`、时间、审核说明及哈希，返回 `next_action=none`。这些机械门禁只防止接受陈旧或缺失产物，不会判断图中内容；实际视觉审查必须由调用者完成并据实记录。用户随后指出观感差异时，仍需继续修正和重新审核。

每次重新构建或重新渲染都会清除上一轮 `style_review` 并把接受状态恢复为 `pending`；新的四张图需要重新视觉审核和 `accept`。接受记录绑定侧面源、可选正面源、风格参考、profile、blend、GLB 与四张审核图的哈希；后续 `validate` 也会核对已接受记录是否仍匹配当前产物，不能沿用旧注释给新模型背书。

### 像素材质与实际引擎

保留源图 native 分辨率并嵌入模型，大小由运行时真实体长控制。鱼的颜色贴图使用 nearest，最终 3D 视口展示也使用 nearest，避免两次平滑。过滤器保留已有像素，不能创造不存在的像素美术。远处斜视可能出现高频闪烁；若需要 nearest mipmap，须以同场景对比确认，不能静默改为线性过滤或把原图缩成屏幕尺寸。

像素图已经画了光照，新增金属/镜面高光容易变成塑料或写实效果。当前展厅复制鱼材质后设 `metallic=0`、`metallic_specular=0`、`roughness=1`，保留既有柔和漫反射和源材质少量自发光，使三维体积仍可辨认；不统一切成完全无光照。身体不透明，独立鱼鳍保留原 alpha。相机、动画、鱼体尺寸和原图像素不因此改变。

## 单张侧面图能确定什么

原图的 alpha 轮廓可确定头尾长度、高度、侧面形状和鱼鳍边界。正面厚度、左右差异、口腔及隐藏表面需要额外参考或人工推断。生成闭合体积网格后，分别看侧面、正面和斜视；侧面正确不能证明体积正确。

保留原图分辨率和画风，按 UV 投影到两侧。原图已画明暗，过强物理光照会重复压暗。材质以原图颜色为主，适当弱化光照；不要称为完整 PBR 重建。食人鱼原图 1492×844，带鱼 1869×179，本次导入没有按屏幕大小降采样。

## 网格、鱼鳍与骨骼

Blender 坐标为 X 头尾、Y 厚度、Z 高度。普通摆尾左右摆动，绕世界 Z；用骨骼静止矩阵逆变换换算到局部轴，不能给所有骨骼直接设置同一局部轴。用四元数处理多轴姿态。

鱼鳍独立建模和绑定，鳍根与鳍尖分开控制，鳍尖滞后。连续长背鳍分段波动。几何边界匹配原图，凹轮廓采用约束三角剖分，检查翻面及权重。运动鱼鳍分离后，从体表局部清除重复画鳍，否则出现两片胸鳍；保留其他原图像素。

转向将头部路径、整体朝向和沿身曲率分开，身体按沿身距离滞后，不绕躯干中心刚性旋转。Blender 保持体积蒙皮不能假定会原样移植到 glTF/Godot；强弯曲需要在目标引擎重新检查塌陷、自交和边界。

相近体形可复用基础网格再修轮廓、厚度和鳍。食人鱼与带鱼差异大，直接拉长旧网格会保留错误的头、尾和鳍；重建物种专用网格和绑定，复用程序、动作接口、材质和验证流程更合适。统一接口不等于共用几何。

## 真实运动与相机

完成每条鱼动作后，按游动、悬停、转向、进食、受力挣扎分别查资料和录像。优先水族馆、研究机构及直接观察，记录物种、URL、实际阅读/观看范围、支持的事实和未知参数。游动通过不代表进食、挣扎也真实。

带鱼基本运动以长背鳍波动为主，普通躯干摆幅小；头朝上悬停、后退游动、主动前进掉头分别制作。本次参考包括[葛西臨海水族園观察](https://www.tokyo-zoo.net/topics/news/kasai/6012_20074_2011-09-23.html)、[饲养员访谈](https://tachiuo.net/archives/177)和[水族馆实拍](https://www.youtube.com/watch?v=SJSVHeYMtxM)。皇带鱼/粗鳍鱼研究和仿生机器人不能作为普通带鱼动作的直接实测依据。

没有提取可标定的完整 180° 活体带鱼掉头，半径、时长及传播速度仍是艺术性参数。用户认可的是视觉原型，不能升级为生物力学真实性结论。

较高斜视可能把水平回转投影成向下回环。用同一动作输出平视正侧面和斜视，只改相机，分辨弯曲、朝向镜头造成的缩短和自身遮挡。换视角不能修复真实厚度或错误动作。

## Blender 到 Godot

1. 保存原生 `.blend`、独立动作和必要输入；导出副本，不覆盖验收源文件。
2. 只导出鱼的骨骼、体积网格、鱼鳍和眼睛，排除摄影机、灯光、食物、钓线等预览道具。
3. 采样骨骼游动循环，剥离根位置及旋转动画，交给场景控制位置。首尾匹配骨骼姿态，并在导入后检查实际循环时长和衔接。
4. glTF 不支持任意 Blender 程序材质。将局部去鳍等颜色混合烘焙到原尺寸颜色图，再建立可导出的基础材质；不把灯光一并烘焙，鱼鳍透明边界单独保留。
5. 导出名称不一定保留 Blender 动作名。本次 `ACTIVE_ACTIONS` 实际导出为 `Animation`；检查 GLB 和 Godot 实际片段列表，不能仅凭预期 `Swim` 名称断言有动画。
6. Godot glTF 导入为 Y 向上；世界轴、局部轴、根变换和单位分别校准。聚合模型空间 AABB，按真实体长缩放并居中，不凭预览估计比例。
7. 骨骼和 AnimationPlayer 存在不等于播放成功。采样运行时四元数，确认身体和独立鱼鳍变化，并看实际渲染。

本次食人鱼 15 根骨骼、体长 0.1775 m；带鱼 67 根骨骼、体长 1.0 m。导出采样为 24 FPS/1 秒和 24 FPS/2 秒。Godot 当前片段时长约 1.0417/2.0417 秒，应保留实际测量，不能以源时间替代导入后的长度。

## 原大厅展示缸与验收（036 历史阶段）

大厅保留现有 2D UI，通过拥有独立 World3D 的 SubViewport 放入 3D 缸体、底砂、石头、灯光、摄像机及蒙皮鱼。缩略图和放大观察共用同一视口，不复制动画；轻量屏幕后处理添加水光。内尺寸约 2.8×1.05×1.2 m，当前仅展示，不写入鱼库存或饲养系统。

现有点击路由先命中新展示缸，再命中旧缸；缩放、平移使用大厅本地坐标。放大支持正面、斜视、暂停/继续和返回。保护宽高比，避免拉伸视口后误判鱼形；旧缸继续按原系统显示。

验收包括构建、资源导入、实际大厅启动、正面/斜视录像、骨骼变化、暂停时间轴、返回/重新打开。通用 `godot validate` 只启动 main，没进入大厅时可能漏掉惰性加载的 GDScript 解析错误；捕获有文件不代表日志无错。对目标场景同时检查日志和画面。

本次四组捕获共 180 帧，运行日志零错误，身体/背鳍/胸鳍骨骼变化，观察按钮通过，161 项游戏测试通过。本机缺少 .NET 8 系统测试运行时，测试使用 `DOTNET_ROLL_FORWARD=Major` 跑在已有 .NET 上；设置只用于本轮测试，不等于修改目标框架或验证所有部署环境。

只把平缓循环游动接入缸内；头朝上悬停、主动掉头、进食和挂线挣扎保留在 Blender，尚未接成游戏行为。小幅位置漂移是展示控制，不是路径跟随转向验收。

## 独立 3D 展厅（038）

后续用户要求单独的 3D 展厅与自由视角。游戏现在从海岸枢纽和各水族馆展厅的「3D 展厅」按钮进入独立场景；普通大厅不再挂载实时 3D 缩略缸。切换场景销毁旧视口，避免把两套场景同时留在后台。新增空白展厅仍按玩家设置创建，3D 展示不依赖当前展厅编号，也不改鱼库存或存档结构。

复用已验收的食人鱼、带鱼 GLB 与骨骼游动，保留原纹理和真实相对体长。独立场景采用透视相机、玻璃缸与展台，支持拖动环绕、Shift 拖动或中键平移、滚轮及触控板缩放，并提供正面、斜视、复位、暂停和返回。全周观察时不能沿用遮挡背面的实心缸背板；俯仰、距离和平移应有边界，避免相机进入地板。

SubViewport 按可见画面的实际宽高比生成，渲染尺寸上限 1280×720；这只限制最终屏幕渲染，不缩小原始鱼纹理。隐藏时停用视口和鱼动画。Mac 性能调查要分别记录场景创建耗时、持续帧耗时、纹理内存和视口渲染成本，不能凭「有 3D」判定全部卡顿由 GPU 引起。该项目已测到 2D 转身亮度分析重复执行和轮廓循环中频繁跨引擎读取属性的 CPU 成本，具体前后数值以 Fisher 本次验证报告为准。

独立展厅需测试真实 GUI 输入路由、骨骼变化、暂停恢复、返回再进入、窗口宽高比变化与旧视口销毁。直接调用按钮回调不能代替鼠标命中测试；无窗口的 dummy renderer 也不能证明 Mac 上的显示帧率。038 的范围仍是展示与观察，未把 Blender 的其他动作接成完整 3D 饲养行为。

## 两种新实体鱼（039 历史原型）

新增黑鳍礁鲨使用物种专用网格和原生顶点色；现有银龙鱼使用原生 1838×515 侧面图重建，图像像素保持原样。各自保存构建器、打包 `.blend`、正式 GLB 与验证报告，目录为 Fisher 的 `experiments/blender-fish/models/{blacktip_reef_shark,silver_arowana}`。骨骼分别为 15 / 35 根，源游动循环 2 秒，Godot 导入实际片段为 `Animation`、约 2.041667 秒。体长 1.5 / 0.7 m 由运行时设定。

本轮导入教训：GLB 有 `COLOR_0` 不代表 Godot 已使用它。黑鳍礁鲨首轮通体白色，读取导入网格确认颜色非白，但材质 `vertex_color_use_as_albedo=false`；复制运行材质后，只对含 `Mesh.ARRAY_FORMAT_COLOR` 的 surface 启用该属性，灰背、白腹和黑尖才正常。银龙鱼的独立鱼鳍必须连接原图 alpha，否则被轮廓略微包住的透明像素会变成黑色三角；身体材质仍保持不透明。两项均以目标引擎画面复核，不能只检查 Blender 或导出文件存在。

展示分为黑鳍礁鲨、银龙鱼、原食人鱼与带鱼三组。切换复用房间/缸体，立即释放旧模型，保留暂停状态；近看仅调相机，不改体长。32 项真实 GUI、材质、骨骼和生命周期检查通过，另有 173 项游戏回归测试；最终报告为 `plans/reviews/2026-10-13-shark-arowana-3d-validation.json`。检查正侧面、另一侧、头部正面与斜视，保存两张最终引擎图，其余临时图和探针移出工程。

形态参考分别为 [Smithsonian 黑鳍礁鲨条目](https://biogeodb.stri.si.edu/sftep/en/thefishes/species/4821)与[国家动物园银龙鱼条目](https://nationalzoo.si.edu/animals/silver-arowana)。资料支持形态特征；未知厚度、鳍弧度和运动幅度仍是制作推断。当前只有循环游动和轻微展示位移，不将其称为完整 3D 饲养或转向行为。039 这一轮历史记录中，生图、生视频 API 调用均为 0；这不是后续生产的零付费限制。用户随后要求新鱼先 Foundry 生图统一像素画风，执行范围由 040 覆盖。

## 已接受模型的四动作展缸（042，046 扩展为五鱼）

当任务只为当前黑鳍礁鲨、银龙鱼、食人鱼和带鱼增加 `Swim/Turn/Ascend/Dive` 展示动作时，复用正式 GLB 的网格、贴图、蒙皮和基础循环，不重新生成原画，也不伪造新的 `image.raw` 阶段。该入口与上面的新原画/新几何生产分开；模型本身改变后，应先完成相应模型审核，再重新计划动作。

固定控制器位于 `resources/runtime/godot/VolumeFishMotion.gd`，声明式配置位于 `resources/volume-fish/motion/<species>.json`。使用三条命令：

```bash
.\gamefactory.cmd volume motion-plan --profile resources/volume-fish/motion/blacktip_reef_shark.json --profile resources/volume-fish/motion/silver_arowana.json --profile resources/volume-fish/motion/piranha.json --profile resources/volume-fish/motion/hairtail.json --models-dir <game/assets/models/fish> --reviews-dir <plans/reviews/042-input-models> --output <motion.handoff.json> --json
.\gamefactory.cmd volume motion-build --handoff <motion.handoff.json> --json
.\gamefactory.cmd volume motion-validate --handoff <motion.handoff.json> --json
```

`motion-plan` 要求完整物种集合；当前集合为黑鳍礁鲨、路氏双髻鲨、银龙鱼、食人鱼和带鱼，同时保留旧四鱼 handoff 的只读兼容。从目录读取 `<species>.glb` 和 `<species>.validation.json`，验证真实网格、skin、基础 `Animation` 循环及头到尾骨骼映射，再冻结 profile、模型、控制器和审核来源的 SHA256，写 `pending/run` handoff。基础循环须有实际骨骼旋转，变化的位移/缩放不在当前 rest/skin 包络范围内；四元数正负号变化不算真实动作。配置只有受限数值和骨名，不接受脚本、命令或插件字段。

每鱼复用验证报告使用 `kind="existing_volume_model_review"`，至少包含 `schema_version:1`、`species`、实际 `model_sha256`、`review_status:"accepted"`、`reviewer:"command_operator"`、具体 `note` 和 1–8 项 `evidence` 文件路径。可同时保留标准 JSON 命令合同字段。evidence 引用既有 JSON 验收报告与 PNG/JPEG 实际画面；已有 Foundry volume handoff 必须仍通过验证、处于视觉接受状态，且指向同一 GLB。旧鱼的 operator 复用审核说明沿用的模型身份和历史证据，不把空的旧生图账本补写成新生成记录。

| profile 范围 | 校验约束 |
|---|---|
| `real_length_cm`、`head_sign`、`base_clip` | 0.1–1000 cm；方向只接受 −1 或 1；基础片段为实际存在的 `Animation`。 |
| `body_bones` | 4–32 个唯一 skin 骨名，按实际父子层级从头到尾排列。 |
| `tank_size_m`、`path_radii_m` | 三维缸内尺寸各 0.1–100 m；水平两轴路径半径各 0.01–50 m。 |
| `vertical_amplitude_m`、`envelope_radius_m` | 0–20 m 和 0.01–50 m；安全包络半径 E 至少为实际体长 L 的 2 倍。 |
| 时间与基础游动 | `period_seconds` 4–60 s、`transition_seconds` 0.2–3 s、`body_delay_seconds` 0–2 s、`base_body_gain` 0–1。 |
| 四个 `actions` | 每项只有 `radius_scale` 0.3–1、总 `bend_radians` 0–1、`vertical_sign` 和 `clip_speed` 0.2–2。Swim/Turn 不改变高度方向；Ascend 为 +1、Dive 为 −1。 |

Swim 使用完整路径半径，Turn 的半径系数不大于 0.8 且总弯曲量至少比 Swim 多 0.1 rad；弯曲量沿骨链分配，不是每根骨骼都转同一大角度。所有数值须有限，未知字段拒绝。缸体各半尺寸必须容纳对应路径半径或垂直幅度，加上 E 与 0.02 L 余量。运行时还须按实际 Godot 骨架 rest 链和 skin 杠杆距离再次核算姿态包络，不能仅相信声明的 E。该保守空间不是物种实测的转弯半径。

可选 `body_wave_radians`（0–1）为尾端相对头部的游动航向摆幅，`body_wave_cycles`（0.25–2）为沿身体的波周期，`bend_bias`（0–2，默认0.65）控制转弯分布向尾部集中程度。省略波幅时不添加身体波动。波相位跟随连续基础动画时间，沿真实rest骨链距离传播；各关节施加相邻绝对航向的差值，避免骨骼数量累加放大。基础循环用 `base_body_gain` 混合，独立鱼鳍仍播放原动画。`max_bend_rad`包含转弯与波动的合成关节偏转；包络仍依据任意旋转下的完整蒙皮杠杆上界。

`motion-build` 仅将固定控制器和校准配置写到 handoff 同级的 `<stem>-artifacts/FoundryFishMotion.gd`、`motion.json` 和 `validation.json`；`motion.json` 为 `{schema_version:1, profiles:{species:profile}}`。游戏接入可复制到 `res://scripts/aquarium/FoundryFishMotion.gd` 与 `res://assets/models/fish/motion/motion.json`，已有 GLB 原样保留。输出位置固定在 handoff 范围内，拒绝符号链接和改写输出路径；重放前检查模型、profile、helper、复用报告及其证据是否变化。

技术构建与只读验证保持 `human_review`，不自动认证动作质量。最终操作者报告须绑定实际使用的全部 GLB、生成配置及控制器哈希，记录每鱼四动作的真实 Godot 骨骼、路径、连续性、缸内包含性和 GUI 证据，再记录实际画面审核。该报告继续作为验收状态，不新增任务数据库或通用动作插件系统。

### 046 宽头鲨生产经验（2026-10-14）

路氏双髻鲨最终使用独立的侧面、正面、俯视和仰视图。每个 frozen Brief 必须放在不同项目根，不能只靠子目录名区分，否则 workflow 状态文件会互相覆盖。侧图负责身体、鳍、尾和侧面轮廓，正面图负责头部厚度与宽度，俯视和仰视图分别提供头锤与颈部的背面、腹面颜色；四图都先走 Foundry 生图和资产接受，再进入同一个 volume handoff。

宽头不能只把普通鲨鱼头部贴图横向拉宽。profile 的 `head_projection` 同时定义前向几何宽度和纹理供体区域；供体 crop 必须完全落在不透明像素内。若 crop 包含透明角，导出到不透明 body 材质后会形成大块黑斑，即使法线阈值和投射方向正确也无法补救。进入 Blender 前先对 front source 的 alpha 做轮廓采样，确认 crop 的四角和插值路径均不穿透明区；眼睛可用单独小网格定位在头翼末端，避免被正面投射拉成黑椭圆。

侧面图也不能提供真实的头顶与腹面。把侧面眼睛、鳃和轮廓阴影沿环形截面包裹，会在头颈形成黑色项圈；把整张俯视或仰视透明图矩形投射到不透明网格，同样会把轮廓外透明像素显示成黑块。`dorsal_projection` 和 `ventral_projection` 因此只选择真正朝上或朝下的面，并用扩大后的 `model_depth_range` 将几何映射到供体图连续不透明的中央区域。每条鱼须独立校准 crop、深度范围和法线阈值。

Blender 5 在本地化界面中会翻译节点显示名。构建器查找 Principled BSDF 和 Background 时使用稳定的 `node.type`，不依赖英文显示名。`head_projection.normal_threshold` 允许到 −1，用于确实需要覆盖整个前向头部的物种；这不是默认值，每条鱼仍应以最小覆盖范围为准。侧、正、斜视、俯视、仰视和源图风格对比全部目视通过后，才执行 `volume accept`。俯视和仰视专门检查头顶、腹面、头颈接缝及成对鱼鳍，不能由斜视代替。

路氏双髻鲨动作没有复制黑鳍礁鲨 profile。常规游动沿后体传播保守波形；转身半径与弯曲参考同科鲨鱼研究，升降则把头翼视为可主动控制的前置舵面。文献支持方向，不足以给出当前展缸所有关节角，因此绝对幅度仍是明确标注的制作推断。046 的 Godot 验收覆盖五鱼二十种动作、二十五组动作过渡和二十八次真实鼠标检查。

## 成本与保存范围

### 047 锤头与鱼鳍重建（2026-10-14）

046 的宽头由纵向身体截面逐渐加宽，俯视成为楔形；双髻鲨不能用这个结构验收。新增可选 `cephalofoil.sections`，每行独立定义横向位置、后缘、前缘和半厚度，以横向扫掠构造闭合头翼，中央凹口和前缘浅凹槽由几何定义。它连接窄颈、眼位位于两端、口部位于腹面。它仍是制作重建，不是测量扫描。

侧面鳍图的垂直长度不能同时充当三维胸鳍的垂直长度和横向展长。可选 `vertical_scale` 控制相对鳍根的垂直量，横向展长仍由独立 depth 定义。`opaque` 与 `source_rect` 让闭合几何决定鳍缘，颜色从经过审核的原图不透明供体矩形取样；只把顶点 UV 挪到不透明像素还不够，三角形内部可能穿越透明背景。背腹供体同样应避开原画里已画出的鳍和阴影，以免形成拉长条带。

含 `cephalofoil` 的验收强制提供 `clay_side/clay_front/clay_top/clay_oblique` 四个灰模视图，连同五个带材质视图和源图风格对照绑定哈希。Godot 腹面诊断须用独立相机绕过展厅交互 pitch 限制，核对真正腹面且完整入镜。灰模证明结构，材质图证明贴图，运行测试证明动作连续性，三者不能互相代替。

### 043 身体柔韧性与转向修正（2026-10-13）

用户反馈鲨鱼与银龙身体僵硬。固定控制器增加沿真实骨链距离传播的身体波，分别校准两鱼摆幅与转向分布；Turn路径半径系数由0.65改为鲨鱼0.45、银龙0.38。保留身体正在跟随的历史路径，系数使用加速度连续的五次过渡，短窗平均转向速率，修复切换时迟滞身体突然折转。四鱼GLB、贴图和眼位保持原哈希。

当前权威输入为游戏 `plans/volume-motion/043-flexible-fish-v3.handoff.json`，操作者报告为 `plans/reviews/2026-10-13-flexible-volume-fish-validation.json`；Foundry技术报告仍保持human_review，实际Agent画面审查单独记录。Windows Godot 4.6.1/RTX 5080实际展厅16组动作、20次动作切换以及23项真实鼠标路由检查通过；对照动画与16组画面位于游戏 `output/043-flexible-fish-qa/`。可复跑 `game/tests/VolumeFishMotionQA.gd`，使用游戏工程作为Godot的path。由于本地新鱼导入缓存缺失，QA通过Godot GLTFDocument读取相同GLB并进入现有展厅；未重测完整C#主场景导航或macOS性能。CLI十项测试通过，两项符号链接安全测试受Windows账户权限限制未能执行。

### 044 单鱼默认镜头可见性修正（2026-10-13）

用户指出正常3D场馆看不到鲨鱼和银龙。复现确认模型实际存在，但单鱼镜头错误使用技术安全包络鱼缸尺寸：鲨鱼镜头距离17.87米、银龙8.34米，两鱼缩成几十像素，鲨鱼还会被相邻鱼缸结构遮挡。单鱼页面现按真实鱼长2.6倍取景并跟随当前carrier；正面、斜视和复位均保持单鱼聚焦，只有总览显示完整鱼缸布局。正式standalone场景在Windows Godot 4.6.1/RTX 5080下复核；修复后距离分别为3.9米和1.82米。前后画面及报告位于游戏 `output/044-fish-visibility-qa/` 与 `plans/reviews/2026-10-13-volume-fish-visibility-validation.json`。173项游戏单元测试、16组动作、20次动作切换、23项鼠标路由和10项CLI动作测试通过。

### 045 现实运动学文献校准（2026-10-14）

用户认为043的摆幅过强。黑鳍鲨巡游波改按野外 `Carcharhinus limbatus` 实测校准：后段屈曲均值12.21°，本控制器尾端程序波由0.55降至0.21 rad；前体保持更稳，转弯总弯曲由0.95降至0.58 rad，Turn半径系数由0.45增至0.65。银龙依据同种研究确认为亚鲹形BCF游姿，约后2/3身体参与波动；程序波由0.78降至0.31 rad、沿身周期0.67，转弯总弯曲由1.0降至0.68 rad，半径系数由0.38增至0.60。银龙论文没有给关节角，其绝对幅值明确作为保守制作推断。

资料与参数映射见游戏 `plans/research/045-fish-motion-literature.md`，权威动作 handoff 为 `plans/volume-motion/045-literature-calibrated-motion.handoff.json`，操作者验证报告为 `plans/reviews/2026-10-14-literature-calibrated-volume-fish-validation.json`。Windows Godot 4.6.1/RTX 5080实际场馆16组动作、20次转场、23项真实鼠标路由和全部包络检查通过；匹配机位对照位于 `output/045-literature-fish-qa/`。该校准针对常规巡游与偏航转向，不代表逃逸急转。

复用验收模型后，增加动作主要是骨骼参数、关键帧和验证成本，不需要每个动作重复生视频；换鱼种仍有轮廓、厚度、鱼鳍、绑定及真实动作研究成本。先用代表动作验证，再扩展动作库。

本次导出、游戏展示和录像没有调用生视频 API；早期局部修鳍曾使用生图，不能称整个流程零 API 成本。机器时间、人工时间、供应商费用分别记录，没有账单不编造价格。

保存代码、正式 GLB、选定原生模型、必要局部材质与轮廓输入、资料记录和紧凑报告。缓存、密集逐帧图、旧视频和存档备份留本机。制作记录不是第二套状态；状态仍读取 manifest、progress、handoff、assets-manifest 和 validation report。

## 040 双原画制作完成（2026-10-13）

黑鳍礁鲨侧面主图与正面辅图均通过 Foundry workflow 和 assets review；本轮成功生成 2 张静图、0 次视频。源图尺寸分别为 1834×618 和 891×654，原像素嵌入模型，nearest、非金属、粗糙度 1。正式五步通过，接受后的再次 validate 返回 accepted/none。

制作 profile 与权威 handoff 位于游戏 `experiments/blender-fish/models/blacktip_reef_shark/040-blacktip.profile.json`、`040-foundry.handoff.json`；原生 blend、GLB、机械验证、四张三视/风格对照图位于 `040-foundry.handoff-artifacts/`。实际游戏 GLB 与接受记录哈希一致。游戏中为 18 骨骼、2 秒循环、1.5 米展示体长；银龙鱼继续使用已有原生像素源图。

实际 Mac Apple M4 Godot 检查 64/64 通过，游戏测试 173/173；游戏证据见 `output/040-foundry-pixel-volume-qa/validation.json` 和同目录两张 `*-final.png`。源图、正面、两侧及斜面已目视核查；修复侧面矩形接缝与重复眼。斜面眼形略长、鼻顶仍有窄纹理带，厚度与游动参数为艺术性估计。本次只接入展示游动，不表示已实现鲨鱼的转身、进食、挣扎。

## 041 眼位修正（2026-10-13）

用户指出040眼位观感异常。原因是前图覆盖侧眼并沿弯曲头部拉长；041改为左右各一个固定的原生侧图眼片，与头表面法线对齐，移除body两种投射中的重复眼色。原PNG不变，十个原网格及其权重不变。正式输入/权威状态为游戏制作目录 `041-eye.profile.json`、`041-eye.handoff.json`，原040资料保留为历史。

新版双侧眼像素完整率100%，侧投影约44.5×39.9原图像素，落点误差小于0.59像素；旧前图眼残影映射为0。实际Mac Godot五视和66项检查通过，独立审查通过，Foundry接受及再次validate完成。当前游戏结果见 `output/041-shark-eye-qa/` 和 `plans/reviews/2026-10-13-shark-eye-placement-validation.json`。040所记录的斜视长眼限制已在041修正；本次没有额外生图或视频生成。

## 051：主图 B 驱动的路氏双髻鲨重建

先选定 049B 主图，再经 Foundry 图生图生成并审核侧面 050r3、俯视 050r2、正面 050、腹面 050r4；腹面引用已审核的俯视图，保持 B 的来源链。生成视图仍是近似参考，不是精确正交测量。

通用建模器支持 dorsal/ventral projection 的 `sections`：每行 `[model_u, source_u, donor_low_v, donor_high_v, model_half_depth]`，沿躯干插值对应关系，保留原尺寸纵向色泽与像素细节。横向头翼独立扫掠，头部贴图按每行透明轮廓取有效区域；前缘描边不能铺成整个正面的黑带。俯视和腹面中烘焙的眼睛要避开，由末端眼睛表面贴片承担。鱼鳍从原图轮廓校准几何与原尺寸 UV，不能用小块灰色 donor 替代整片鳍的细节。

Windows 图生图命令的来源核验必须保留参数中的反斜杠；用禁用转义的词法解析器读取历史 argv，不执行历史命令。主图对照 `master-comparison.png` 与侧、正、斜、俯、腹和四张灰模图一起纳入接受哈希。机械校验不承担视觉验收；最终还需 Godot 实际四动作和场馆画面。051 仍简化腹面嘴部细节，不能宣称逐像素复刻主图或用户亲自验收。

### Godot/.NET 验证与交付

主项目 SDK 与测试项目 GodotSharp 依赖必须使用同一版本。本轮 Godot 4.6.1 使用 `SpriteFrames.SetAnimationLoop(name, bool)`；4.7 的 `LoopMode` / `SetAnimationLoopMode` 不能直接用于 4.6.1。测试项目通过不代表主项目可编译：交付前同时执行主项目 `dotnet build` 与测试项目 `dotnet test`，再核对真实引擎画面。Windows 仅安装 .NET 10 时，net8 测试可临时设置 `DOTNET_ROLL_FORWARD=Major`，不要把这个本机环境需求写入产品配置。

正式交付保留最终 GLB、打包贴图的原生 blend、选定主图及四视图、生成与接受来源记录、物种 profile、动作研究和紧凑验收证据。旧失败模型与逐帧视频截图不进入提交。Foundry 通用工具与独立游戏仓库分别提交；历史 handoff 保持原哈希和路径，不为迁移档案伪造一次新的接受。新机器按归档源图重新初始化 workflow/handoff 后复验。

## 052：基于已接受原生模型的横向宽度调整

已有模型只需调整左右宽度时，profile 可增加 `rest_shape_revision`，继续走 `volume plan → build → validate → render → accept`（全部 `--json`）。该分支打开已接受的原生 `.blend`，只调整静止网格与骨骼的 Blender Y 坐标，保留 X 长度和 Z 高度；不重新生成拓扑、UV、材质或动作。它不能替代需要改嘴部结构、背腹弧度或鱼鳍轮廓的建模。

`rest_shape_revision` 必须提供 `source_handoff`、`source_blend`、`source_glb` 三条路径及对应的 `source_handoff_sha256`、`blend_sha256`、`glb_sha256`，另加 `stations`。相对路径以当前 profile 所在目录为基准。历史 handoff 必须为 `done` 且具有操作者视觉接受记录；模型哈希须对应接受记录，侧/正/俯/腹源图及画风契约须与新计划一致。plan 与后续 freshness 检查都会重验，输出不得覆盖接受源模型。历史接受只证明来源，不会自动接受新形状。

每个 station 为 `[u, source_half_width, target_half_width]`。`u = Blender X + 0.5`，对应原源图横向归一化位置，按原图朝向读取，不自动转换成鼻尖起算的 TL 百分比。两个半宽均使用 Blender 原生模型单位，等于源图宽度归一化尺度；不是厘米，也不是源图高度比例。先在相同解剖站位测量原模型左右半宽，再把资料中的目标全宽按模型实际 `cm_per_unit` 转为半宽。局部鳃盖宽不能直接替代全身体最大宽。目标/原半宽比在站位间以 C1 smoothstep 插值，端外沿用最近端点比；因此修改区外要设置比值为 1 的保护站位。源半宽不由构建器自动测量，资料、定位及比例推断须在物种研究卡中记录。

成对鱼鳍以原鳍根的宽度变化做整体 Y 平移，鳍骨同步平移，以保留自身展长与鳍面形状；独立 `Textured_eye_*` 眼片以中心做整体平移，避免随头部横向缩放而压扁。其他网格按站位比例缩放 Y。技术报告记录 `native_revision`、`width_only`、`topology_uv_unchanged`、鳍根平移、骨骼数、顶点数与八项技术检查。计数和活动 UV 不变的断言不等同所有原生数据的完整差分；验收仍检查实际整鱼环绕与游动、眼片贴合和鳍根连接。

052 的巨骨舌鱼与路氏双髻鲨构建、渲染已完成，八项技术检查均通过；该事实不代替新的运行画面与视觉接受。权威结果分别位于游戏 `experiments/blender-fish/models/arapaima/052-knowledge-width.handoff-artifacts/validation.json` 与 `experiments/blender-fish/models/scalloped_hammerhead/052-knowledge-width.handoff-artifacts/validation.json`。

## 053：头部高度、鱼鳍连接与独立解剖验证

052 的 `width_only=true` 只保证当次不改变 Z；它没有验证眼位头高、闭嘴形状、全身厚度或鱼鳍接触。八项技术检查以及 Godot 的 `inside_envelope=true` 均不能作为整鱼解剖正确的结论。后续必须分别报告技术条件、同解剖站位资料比较、实际连接与视觉审核。

### 原生模型的可选高度场

`rest_shape_revision` 可增加 `vertical_stations`；没有此字段时继续保持 Z 不变。示例仅说明字段，不是某条鱼的生物学目标：

```json
"vertical_stations": [
  [0.60, 0.30, 0.70, 0.30, 0.70],
  [0.80, 0.30, 0.70, 0.35, 0.65]
]
```

每行 `[u, source_top_v, source_bottom_v, target_top_v, target_bottom_v]`，v 使用原源图高度归一化、从上向下的坐标。u 递增，top 必须小于 bottom，要求 2–128 个站位、有限数值和 0.25–4 的正高度比例。构建器在站位间平滑插值 Z 仿射映射，源图高宽比参与 v→Z 换算；端外延伸最近的映射，修改区外须提供恒等保护站位。

身体与原生头部覆盖层使用相同的场；独立眼片、成对及中线鱼鳍按自身中心/鳍根整体平移以保留形状，对应骨骼根尾同步移动，其他骨骼按相同场调整静止位置。X、拓扑、UV、权重及动作曲线继续保留。它改变静止骨骼方向，因此仍须检查原生游动与 Godot 四动作；不能仅凭曲线没有变化断言动态外形正确。

横向 `stations` 的目标/源半宽比允许 0.25–12，同时两种绝对半宽仍限制在源图宽度的 0.0001–0.5。较高比例仅提供窄端环的局部宽嘴实验能力，不提供任何物种嘴宽依据；零宽端点也不能通过乘法扩展。嘴宽、躯干最大宽缺乏匹配资料时必须标为推断或未测量，并检查正、侧、俯、腹及斜面灰模/纹理外形。

`resources/scripts/volume-fish/audit_native_revision.py` 是只读原生保留审计：比较接受原生模型与候选的拓扑、UV、权重、动作、贴图和骨骼层级；X 必须不变，Z 只允许声明的 `vertical_stations` 映射，并逐网格报告实际变化与映射误差。无高度场时要求 Z 不变。它不能用于声称程序化重建的尾鳍仍保留旧拓扑；有意重建的部件须单独记录与审核。

### 程序化鱼鳍的可选身体表面附着

需要修复悬空鳍根时，在相应 `fins[]` 增加：

```json
"root_attachment": {
  "mode": "body_surface",
  "root_band": 0.05,
  "blend_end": 0.35,
  "inset": 0.001
}
```

`root_band` 和 `blend_end` 使用原始源图 anchor→tip 投影参数 t，要求 `0 <= root_band < blend_end <= 1`；`inset` 使用源图宽度归一化原生单位，范围 0–0.005，不是厘米。根区内每个实际三角化顶点查询身体表面，沿向外法线向内缩进；位移平滑减至 blend_end 处为零。正常程序化构建中鳍骨根部同步附着，根区完全使用身体脊柱权重，外侧平滑恢复鱼鳍骨骼权重。

058起，`rest_shape_revision`也允许**明确的成对鳍**设置相同`root_attachment`，未提供时保留原行为。先在修形前的原生静止坐标记录`foundry_fin_source_t`，再对修改后的实际`Closed_body`投射根区；查询必须临时使用骨架REST姿势，不能把第0帧已弯曲的评估身体当作静止表面。保留拓扑、UV、贴图和旧动画；只改声明的近端几何与权重，t≥blend_end的鳍面不变，原有鳍骨旋转轴/枢轴保留，近端改用身体权重。非成对鳍仍拒绝此原生选项，不能套用不合适的t选区。默认原生权重不变的审计不适用于这项显式修复，必须单列实际变化、原生根区距离、远端保留及Godot实际蒙皮证据；058的只读审计见`scripts/audit_arapaima_native_058.py`。

构建后的原生鱼鳍保存 POINT FLOAT 属性 `foundry_fin_source_t`，使 Solidify 双层顶点仍能追溯原始 t。不能根据投影后的 XYZ 或修补过的 donor UV 猜测根区。连接检查覆盖完整附着边界和根区，报告最大/最小间隙、穿入量及采样覆盖；不能用一个穿入身体的顶点证明整条根部相连。接触容差属于制作准则，不能写成文献生物学范围。

尾鳍源图轮廓保留率、真实物种尾叶/尾柄形状与动画连接分别验证。源图 alpha 的区域、阈值、源图/profile/模型哈希须随验证报告记录；较高面积保留率仍可能形成错误的宽面板，需实际灰模与纹理审核。只修鱼鳍轮廓时不更换已接受源图，重建的拓扑及权重按实际结果报告。

### 解剖与实际动作证据

解剖诊断脚本输出只读 validation report，绑定当前模型与 profile 哈希，不代替 handoff 或资产接受。报告区分：发表测量/比例、跨研究换算场景、艺术推断、缺失测量及不可比较项；分别列出文献均值与实际观测范围、模型值、偏差和站位/生长阶段不确定性。局部鳃盖宽不能与全身体最大宽直接比较，体高不能与宽度混用，围度换算宽度必须声明截面假设。

鱼鳍连接至少检查静止姿势、原生 Swim 的明确采样及真实 Godot `Swim/Turn/Ascend/Dive`。四动作须测量实际蒙皮后的身体和附着边界位置；包络通过只说明没有越界。数值场景满足、技术通过、视觉接受分别报告。闭嘴轮廓、眼睛归属、尾柄连接及未知目标仍需整鱼环绕视频、灰模和真实资料对照，不能自动汇总成“解剖全部通过”。


## 059：显式成对鳍连接与埋入验收

`check_fin_attachment.py` 的 `--require-paired-contact` 将所有已定义的成对鳍根带纳入总体判定，包括没有 root_attachment 的旧 profile；默认保持历史诊断语义，未启用不代表全部成对鳍已通过。原生与真实 Godot 的 `check_runtime_fin_attachment.py` 均支持 `--max-penetration-cm`，同时限制过深埋入；缺省时仍仅检查正间隙。两项阈值必须按鱼种、尺寸和预先冻结的制作准则设置。059孔雀鲈使用 gap<=0.12cm、embedding<=0.18cm，不可照搬为其他鱼种生物学标准。完整鳍基解剖选择器、非成对鳍与连续时间仍分别验收。

## 060：参数化闭口颌部原型

可选 `oral_jaws` 由 `cli/volume_mouth.py` 校验、`resources/scripts/volume-fish/oral_jaws.py` 构建，示例为 `peacock-bass-oral-jaws-060b.profile.json`。适用头朝右的新纵向鱼体、continuous_atlas；拒绝原生保留修形和横扫头型。corner/front 为源图归一化坐标；gap、upper_retraction、lower_projection、lip_bevel 为源图宽度原生单位，front_pigment_band 为正面图 v 区间。通过真实口腔切面与唇缘倒圆表达闭口结构，仍无独立颌骨/张口动画。

前端和头部图集共同使用声明的 `front-skin.png` 派生供体；验证其路径、原图哈希、参数、分辨率、文件哈希和 GLB 实际像素，继续保留真实可见额部的原图材质。旧源图保持不变。render 增加 oral_side/front/oblique 及对应灰模近景。`audit_oral_jaws.py --blend ... --profile ... --output ...` 以五组横向射线区分真实嘴裂与贴图线；059k 负例确实失败。技术/静态射线通过不能替代嘴宽、唇褶形态、实际动作和视觉接受。物种依据与复用边界见 fishing-2d/docs/3d-fish/ORAL-JAWS.md；其他物种须重新查证和验收。

062可选 `oral_jaws.slit_path`（首尾匹配corner/front的3–16个递增u/v地标）支持单调Hermite曲线与末端下转；`lip_roll`的radius/height（源图宽度原生单位）和lower_ratio（无量纲）控制局部厚唇，先膨起再切口。有内部格网的前盖和平滑颌位移避免扇形端盖撕皱，曲线使用MANIFOLD布尔求解（本机Blender5.0.1验证），实际原生/GLB流形检查仍必须通过。旧双点配置默认不变。曲线射线检查增加末端0.95/0.97测位；`render_oral_pair.py --baseline <blend> --candidate <blend> --output <absolute-dir>` 用同相机/灯光/帧只读对照，不能把曲线或体积存在等同于鱼唇自然。详见游戏口部指南062及062e profile；当前形态仍pending。

063可选 `oral_jaws.separate_lower` 改走 `separate_jaw.py`：实际移除头部原下吻，构建独立封闭浅兜下颌和卷唇缘，原身体链赋权；仍无独立颌骨开合。字段及坐标单位见游戏 `ORAL-JAWS.md` 的063节和063c profile，配置与原壳lip_roll/非零lip_bevel互斥。检查必须改用 `audit_separate_jaw.py` 的结构归属/旧体积移除/中央口腔间隙/后根埋入，不能沿用全宽空嘴裂测试；后根四动作实际蒙皮另用 `check_runtime_jaw_root.py`，装配容差和埋入与鳍根限制分别记录。固定相机对照可加 `--inspect-separate-jaw` 生成独立件/拆解图，仅渲染中临时移位、不修改模型。实际视觉仍单独验收，不能因分件实现成功就宣布形态自然。

## 067：先验参考一致性，再验局部厚度和运动

真实资料、侧面设计稿、独立生成的辅助视图分别承担解剖约束、设计目标和未定深度提示，不默认三者可由同一网格精确重现。源图张口时，必须先建立对应的相机与开口参考姿态；闭口或任意张角模型不能直接与其计算轮廓误差。头颌包络、眼心、口角、上下颌尖、下颌外缘等地标及同姿态投影需先通过视觉审核，再进行闭合、唇厚、口内/嘴角组织与动作制作。浮点权重、闭合网格、接触/包络通过不能替代该审核。

当用户指出“与原图也不符”，应停止在既有局部形状上连续调参，制作真实/原图/模型三方对照并明确参考冲突。分件是编辑方法，不应把独立几何基元外轮廓作为目标形态。孔雀鲈066c对照及GitHub DeepShapeKit/Idea23D/TRELLIS代码查证见游戏ORAL-JAWS.md的067节：可借鉴关键点/轮廓拟合和实际网格多视渲染选择，但生成器演示或二维草图评估不等于已验证该物种可开合唇缘。任何自动形态误差须限定同姿态、可信对应区域。


### 069：原图同姿态轮廓必须实际比较

用户要求嘴形接近原图时，不能只验证闭合网格、朝向或某个局部曲率。源图不变，先冻结头颌ROI、上下颌尖、口角/嘴缝边界、alpha阈值、相机和对应参考姿态，再修改整个不符的头颌包络。比较图必须使用相同像素坐标及共同缩放，不允许分别平移、拉伸来隐藏前端偏差。报告交并比、排除裁切伪边界的轮廓距离、端点误差和嘴缝两侧误差；高面积重合也可能掩盖嘴缝被填死，因此需要分开检查开口。该检查不能推断未知深度或闭口咬合。

通用构建分支为`oral_jaws.separate_lower.reference_shape`：每行`[u,top_v,bottom_v,half_width]`沿下颌纵向布站，`open_degrees`与控制器最大角度一致；`web_end_u`指定嘴角组织终点，`side_projection_start_u`限定原侧图头部供体。开口参考形状经逆LBS反算闭口静止网格，嘴角上侧保留身体影响、下侧跟随下颌。此分支不同时接受旧`lip_path/lip_sections/root_surface_inset`。保留原字段的兼容性不意味着旧椭圆片模板适合该鱼。

新增只读工具：`render_reference_pose.py --blend ... --profile ... --source ... --output ...`用Blender执行，产生原图尺寸、宽1、原点对齐的侧正交0°/参考角灰模和贴图，并绑定模型、profile、源图及渲染哈希；`check_source_contour.py --source ... --render ... --target ... --output ...`用仓库Python执行；`audit_reference_jaw.py --blend ... --profile ... --output ...`用Blender执行，逐点核查原始影响权重及参考投影重建。仍先走正式plan/build/validate/render，不以附加检查代替视觉审核或自动accept。

比较target属于物种和具体图像，须提供源图哈希、参考角、ROI、端点、预定阈值；其他鱼应明确填写`upper_tip_region/lower_tip_region`矩形和`mouth_columns`区间，省略时仅兼容069孔雀鲈旧target，禁止当跨鱼种默认。姿态、原图朝向或相机不对应时先修对应关系，不凭数值称通过。用错位端点、填死嘴缝的反例验证检查能拒绝错误。眼位不属于本轮用户要求，不调整眼睛参数。

069曾发现Blender在新增deform group时重新分配CustomData，持有的属性RNA引用会误读其他层；在创建/清空顶点组前，先把`reference_source_u/reference_jaw_weight`拷成数值数组。必须逐点检查实际权重，而非仅检查权重和等于1。GLB闭口顶点已经逆变形，不能再用静止X当原图u选嘴根或嘴尖；本分支用未变的源图UV.x作运行时选区。


### 071：存量模型的小幅修形与材质整理

用户要求逐条稍微改善时，先冻结当前游戏GLB、原图、原始投影坐标和既有检查画面；每条独立决定最小修改，不对已接近的轮廓强行改几何。复用当前导出物也要保留其原有源图/接受记录；旧版食人鱼、带鱼和银龙鱼有明确的legacy导出来源，不能伪造新volume接受。新鱼仍走正式volume来源和审核门。存量修补以版本化plan、baseline与candidate、原生/实际引擎validation report保存，不覆盖历史接受证据。

本轮通用工具`resources/scripts/volume-fish/polish_existing_export.py`读取冻结plan，支持有界head_affine、tail_affine、独立鳍远端小角度展向、局部源侧图UV，以及pixel_material_only。具体力度、坐标和源图哈希存于`resources/volume-fish/polish-071/*.json`，物种参数不是跨鱼种默认。原输入GLB和原像素保留，拓扑、骨骼静止层级与权重单列精确检查；输出重新做同坐标原图/旧版/新版及斜视对照，再检查实际游戏。

071验证出的边界：头部截面仿射只适合壳体，眼球、眼圈、高光及细触须应保持独立形状，用锚点位移跟随，不能一起拉成长椭圆或厚三角片。重新投射侧头UV时应保留原侧供体的材质光照/自发光设置，避免新建不同材质带来明暗接缝。源图上保留眼睛时，旧的整块辅助眼贴片与去眼供体不能同时叠用；必须选一种明确表示，并核查是否双眼、裁半或出现矩形背景。071鬼头刀选择侧图原眼、抑制冗余不透明辅助贴片，前/背供体及胸鳍附近残留仍另列，不称全部贴图已修好。

只改材质/采样时优先直接修GLB JSON的sampler/PBR参数，原BIN逐字节保留，避免为微小显示整理重新采样长骨骼链。071食人鱼和带鱼的几何、蒙皮及动画二进制完全保留；游戏此前本身已覆盖nearest/粗糙参数，因此游戏内变化小，不能包装成形状改善。

实际引擎要比较改前改后：按物种配置的头骨名定位，不假设都叫body_00；legacy食人鱼叫Head，带鱼叫Body_00。导出重排和浮点量化会影响顶点索引和哈希格边界，近端点按同鳍空间对应检查，不能把索引变化当脱离。区分变换分量的数值容差和实际接触容差。刚性整片绑定的legacy带鱼没有零自鳍权重根区，本轮以整个保留胸鳍作形状/动作保留见证，不冒称新测了完整解剖附着边。071每鱼四动作各8姿态，共256样本，另含孔雀鲈开合/下颌点；两个实际展厅64个动作入口检查。仅证明离散采样及保留，不替代全时刻碰撞和生物动作研究。


## 074：可控范围与活动鳍贴图归属

每鱼交付新增零幅度/大小幅度/快慢频率/独立身体与鳍/参数转换检查，完整鳍根实际运行时检查现177姿态。通用实现与验收工具为 `resources/runtime/godot/FishSurfaceOwnership.*`、`VolumeFishMotion.gd`、`freeze_surface_ownership.py`、`validate_motion_controls.gd`、`validate_surface_ownership.gd`。物种参数在 `resources/volume-fish/surface-ownership-074.json`，不得硬编码到通用算法。隐藏独立胸腹鳍后必须实看身体上是否还画着鳍；再确认原纹理和描边随活动鳍运动、透明背景不变黑框。运行时供体推断与边线不会自动进入原GLB，外部GLB交付需另行烘焙。详见游戏知识库 `docs/3d-fish/MOTION-AND-SURFACES.md`，原图/模型SHA与实际GPU截图一起归档。


## 075：鳍面穿体独立门

每条鱼交付既验完整鳍根，也验整片鳍面摆动时不进入身体；连接通过不能替代此项。`validate_fin_membrane_clearance.py`按冻结plan检查原生/运行时490姿态的完整根带和全鳍面，微小根缝豁免及自由面穿入容差须在候选前确定。修复工具 `repair_fin_clearance.py`可追加POSITION/NORMAL保持原GLB其他流，并重冻浅根/后端尾基。安全中立和外展幅度在运行时逐鱼配置，约束必须匹配实际导入骨名，缺配应失败。详见游戏知识库 `MOTION-AND-SURFACES.md` 的075节；目前只有蓝鳃太阳鱼完成此新门。


## 076：将全鳍面检查提前到新鱼构建

2026-10-19，大西洋鲑和红皇帝鱼复用已有源图正式构建。相关物种的体色偏差、旧资产中文名与学名的区别，以及未知体宽保留在物种卡，不从原画反推生物实测。

`root_attachment.surface_clearance` 为可选原生坐标距离（0–0.02，有限数，非布尔）；未设置时沿用原路径。它给自由鳍面留体表间隙，不能代替蒙皮范围检查。胸/腹鳍沿左右方向查询实际体表，背/臀等中位鳍沿背腹方向投影；尾鳍仍显式连接后端面。任取最近面会把深埋的背鳍基误投到侧腹，造成折叠。

顶点在外不代表三角面在外。076b红皇帝鱼背鳍面内部穿入约5.21mm；定向投影修复后，076c臀鳍曲面根边仍穿入约0.73mm。076e细分中位鳍完整基线（步长0.001原生单位），缩短曲面上的弦。不要缩根区、放宽0.5mm根缝/0.02mm自由面容差、删鳍或锁鳍来通过。二维加密原型076d导致GLB焊接后非流形而被拒绝，不能推荐所有鳍无条件铺密集网格。

检查器也需要真实负例与已知体外例：最近三角面法线在棱/顶点附近不能判内外。076鲑鱼尾鳍完全位于鱼体包围盒后方，但旧法线点积误报约77mm穿入。现用闭合体有向射线与AABB先判内外，再用最近点距离量深度；身体面绕序由有符号体积统一。完整冻结根面（含内部点）只能在同一根缝深度以内豁免，不能掩盖深埋根面。更新检查器后，076b真实穿入负例仍失败，最终候选须重新检查。

每条新鱼依旧检查490姿态：静止、原生25相位、四动作和切换、五种范围和切换、中间幅度/独立频率混合及参数变化。保存实际GLB、完整鳍基、导出器、检查器、控制器、动作配置与plan的哈希。原生间隙不是按毫米通用模板；身体缩放后再检查游戏单位。离散表面与时间采样不是连续碰撞证明。

源画布轮廓、游戏内隐藏胸腹鳍后的皮肤、自由边描线、五视与20秒以上环绕仍分别查看。头部高重合不证明开口相同；源图末端张口而模型为简化静态口时，开度差异须明确保留，不声称完整摄食机制通过。


077新增每鱼身体完整性阻断门：`freeze_body_opacity.py`冻结派生不透明皮肤供体；`validate_body_integrity.py`检查闭合身体、供体清单与实际GPU同姿态覆盖。正常口腔之外不接受任何身体镂空，鳍透明轮廓不得影响身体。详见项目 `docs/3d-fish/BODY-INTEGRITY.md`。


079头吻横向修订见项目 `docs/3d-fish/HEAD-TRANSVERSE.md`。可用 `revise_head_width.py` 追加局部POSITION/NORMAL，保留原UV/骨骼/动画流；先冻结物种自己的截面站，禁止受影响区含鳍，正/俯/斜与原侧面分别对照，之后重冻运行时材质/身体供体并跑身体与完整鳍面门。


## 083：头型优先于贴图便利

纺锤身体、口位、吻端俯视形状、口裂宽和眼前头宽独立查证。旧profile approved及鳍/身体技术门不能代替灰模正/俯/斜视的同种吻型审核。使用 `check_head_form.py` 对预先冻结的物种宽度包络作检查，并以旧尖头作负例；该门不替代生物学证据。材质不适配应修UV/供体，而不是擅自压尖头部。083b四鱼规则、可复用范围与失败候选详见目标游戏 `docs/3d-fish/HEAD-TRANSVERSE.md`。087补充：批量问题列出全部现用鱼逐项决定；邻色补口缝仍须保留上下唇体积，禁止固定高度假横线。`revise_lip_rim.py`沿真实公共边滚边并记录副UV，参见知识库087节与 `mouth-pigment-087.json`，不能将086失败外观当推荐模板。
