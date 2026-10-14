# 巨骨舌鱼头部观感排查（2026-10-14）

## 入口与证据

- 模式：Degraded（用户描述和实机/三视静帧可用；无崩溃日志或错误堆栈）。以下判断均标注置信度。
- 用户反馈：「巨骨蛇鱼的头还是有点怪」（按项目鱼种理解为巨骨舌鱼）。已异步询问主要是正面轮廓、侧面嘴吻还是眼/贴图，答复待定。
- 可复现：打开 `044-arapaima-v11.handoff-artifacts/review/front.png` 与 `oblique.png`，对照已接受的正面 `char_arapaima_front044_nobg.png` 和侧面 `char_ac510a4e97_nobg.png`；正面头的外轮廓接近圆桶，侧斜面吻部偏尖，鱼脸从身体形成连续管状截面。
- 运行时资料：`output/arapaima-volume-qa/` 的 v11 转身/上浮/下潜帧；v11 handoff 当前 `status=done`、`style_visual_review=accepted`，但用户新反馈优先于既有验收记录。
- 变更背景：v10、v11 的 front/oblique 图像视觉近似；v11 主要解决前贴图接缝与背面遮挡，并未更改头部几何比例。

## Phase 1：根因调查

- 首轮推断被独立审查 **REJECTED**：只凭 u≈0.865 的头部截面近圆就将外环归因于头本身，忽略了正面正交投影中头后方的躯干。未据此修改模型。
- [高置信度] `resources/volume-fish/arapaima.profile.json` 的 `body.sections` 同时控制侧面 top/bottom 和横向 depth；构建器 `build_fish.py:224-245` 用椭圆环生成封闭身体。量化显示最大身体半宽 0.092（u≈0.579）、最大正视高度约0.161（u≈0.499），而头部 u≈0.865 半宽0.052、高约0.116。前视投影中更粗的后躯必然围在小脸外，形成当前正面图所见的大圆环；独立审查确认 Blender 与 Godot 都出现，非游戏镜头独有。
- [高置信度] 已接受正面原图中后躯向上收束，没有形成环绕脸的圆盘；前额/下颌有层次。现模型从宽躯干单调收窄到尖吻，投影外廓在脸四周成为圆环，与原画前视关系不符。这是主因。侧面吻尖与眼口贴图是否也需改动尚未确认，不能合并为同一根因。
- [中置信度] `head_projection` 只在原封闭体表面投射前图；它改变眼口图案但无法消除后躯外圆。`model_depth_range=[-0.08,0.08]` 与前部较窄截面可能压缩面部图案；需独立测试，不能直接调整。
- 最小鉴别：基于构建器的几何公式做前视投影，分别比较完整 body.sections 与只保留 u≥0.74 头段时的外轮廓宽高；若大圆宽度降到头段上限，即证明后躯投影来源。当前无 Blender 可执行文件，数学投影可作无改动诊断，正式产物仍需规范 build/render。
- 已执行只读投影试验（112 环×48 顶点、与构建器同一线性截面插值）：全部环的前视最大宽/高=0.1838/0.1610，最大宽来自 u=0.5823；隐藏 u<0.74 的躯干环后降至0.1615/0.1459；只留 u≥0.865 的前头段后降至0.1021/0.1138。证实圆外环的横向极值来自后躯，前头明显更窄。试验不证明最终应该把头放宽多少。
- 尚未实施修复。

## Phase 2：工作模式对照

- 第一轮独立复核 **REJECTED**：误把 Foundry `resources/volume-fish/blacktip-reef-shark.profile.json` 草稿当成已接受模型的 profile。已更正来源；未实施修复。
- [高置信度] 实际已批准的黑鳍礁鲨 `projects/fishing-2d/experiments/blender-fish/models/blacktip_reef_shark/041-eye.profile.json` 使用同一 `build_fish.py` 椭圆环。其横向最大半宽在 u≈0.812–0.872 头附近（0.078），而不是后躯；该物种正视本身仍偏圆，只用来证明同一构建器允许不同截面分布，不能当巨骨舌鱼解剖标尺。
- [高置信度] 体形更接近的银龙鱼已批准 profile `resources/volume-fish/silver-arowana.profile.json` 在 u≈0.702 半宽0.058，到 u≈0.854 仍保留0.042（约72%）；巨骨舌鱼从最大0.092（u≈0.579）到0.052（u≈0.865）只剩约57%。银龙没有相同的已批准前图，因此也不能用来确定目标正视比例。
- [高置信度] 巨骨舌鱼侧面 top/bottom 与横向 depth 是 profile 中可分开的维度。已接受侧图能锁定 top/bottom；已接受前图只约束可见宽度趋势和层次，不是标定的正交相机，无法唯一反推出每个 u 的 depth。前肩至头部延长横向体积是待测假设，不是已确定修复。
- 依赖：profile 修改会改变哈希；需新 v12 双来源 `volume plan → build → validate → render`，检查四张图和 Godot 实景，再 `volume accept`，并确保游戏 GLB 与 handoff 哈希一致。当前 `doctor` 与本机路径查询均未发现 Blender 可执行文件，正式 build/render 会被阻断；当前 arapaima profile 未跟踪、builder 有此前未提交改动，必须保护 v11 基线。尚未修改现有模型。

## Phase 3：单因素假设与试验

- 第一轮独立复核 **REJECTED**：单一0.80宽度阈值由候选参数几乎直接保证，尚未检验视觉圆环和固定 UV 的作用。以下补充了前视面积与 UV 样点的独立诊断；仍未修改正式资产。
- 假设 [中置信度]：仅把前肩至前头（u≈0.72–0.98）的 `body.sections[*][3]` 横向 depth 曲线放宽，就能使正视脸宽与后躯接近，减少「小脸套在后躯圆盘中」的印象；侧面 top/bottom、源图、UV、骨骼、相机保持原样。
- 预先设定的数学鉴别：u≈0.865 脸部宽度 / 最大身体宽度至少0.80，同时整鱼最大宽增加不超过5%，侧面 top/bottom 完全不变。它只检验方向，不能代替图像审核或自动宣布观感通过。
- 只读临时候选函数：原 depth + `0.025 × smoothstep((u−0.72)/0.10) × (1−smoothstep((u−0.90)/0.08))`。未写入正式 profile。v11 基线最大宽0.184、u=.865 脸宽0.1042、比例0.566；候选最大宽0.186（+1.1%）、脸宽0.1542、比例0.829；侧影 top/bottom 数值完全相同。基线不满足目标，候选数学目标通过。
- [中置信度] 这支持 depth 分布可改善前视比例，仍无法验证眼口贴图映射、正面实际轮廓、斜视头型、动作蒙皮。必须用同一相机正式构建渲染并在 Godot 对照；当前无 Blender 可执行文件，不能据此改游戏 GLB 或称问题已解决。
- 补充同相机二维正交投影（`/private/tmp/arapaima_head_projection_probe.png`；灰色=后躯露出的环，米色=u≥0.74 的头，红点=固定 UV 的眼睛横向位置）：v11 后躯外环可见面积17009像素，占鱼体20.3%；只变 depth 曲线的候选为9515像素，占11.3%。候选使侧边圆环显著缩窄，但上下仍有后躯可见；它并没有把全鱼变成前图的锥形，也没有验证真实贴图。
- 固定 `head_projection.model_depth_range=[-0.08,0.08]` 下，正面原画约 x=0.354/0.644 的双眼映射到模型横向约±0.046。其物理眼距在单变量试验中不变；相对 u≈0.865 头宽从基线约0.88降到候选约0.60。接受的前图脸部双眼相对宽度目测更接近后者，但 source_rect、深度、视角均非严格标定，因此仅作监测值，不能据此自动通过。

## Phase 4：候选实现与当前门禁

- 已创建独立 `resources/volume-fish/arapaima-head-v12.profile.json`，与 v11 canonical profile 比较仅六行 `body.sections[*][3]` depth 值不同；侧面 top/bottom、前图投影参数、骨骼/鳍/动作均相同。旧 `resources/volume-fish/arapaima.profile.json` 和游戏 GLB 未改。
- `volume plan --json` 已生成 `projects/fishing-2d/experiments/blender-fish/models/arapaima/044-arapaima-v12.handoff.json`，返回 `status=pending/next_action=run`，仍为视觉待审核。
- 正式 `volume build --json` 返回 `ok=false,status=blocked,next_action=fix_input`，失败 `dependency_missing`，明确提示 Blender executable missing。未绕过 Foundry 门禁导出 GLB，未替换 v11，也未调用 accept。
- 本机 `doctor`、PATH 和常见应用路径检查均未发现 Blender；安装要使用网络，仓库 `AGENTS.md` 要求明确确认。已向用户询问是否允许安装或提供已有可执行路径；答案待定。诊断仍为中置信度，不能记为修复完成。

## 后续：找回便携版并恢复构建

- 进一步搜索发现 `/private/tmp/fish-blender-toolchain/mounted/Blender.app/Contents/MacOS/Blender`。该目录是仍在挂载的 `blender-4.5.3-macos-arm64.dmg`；本地 SHA256 与保存的校验清单一致，程序报告 Blender 4.5.3 LTS。此前只查 PATH 和常见应用目录，漏查了这个挂载目录；上节的「未发现 Blender」是当时搜索范围内的结论，不代表机器上没有。
- 沙盒内 Blender 在 Metal 后端初始化阶段崩溃（`/var/folders/jq/3bbydr_519nb8gp9l75frkww0000gn/T/blender.crash.txt`）；在沙盒外 `bpy` 启动正常。使用现有便携版和 `--blender` 显式路径完成 v12 `volume build` 与 `volume render`，机械检查全部通过，四张审核图已生成。
- v12 正面双眼比 v11 明显，侧面仍保持源图轮廓；正面后躯圆环仍可见，尚不能认定用户反馈已解决。`style_visual_review=pending`，没有执行 `volume accept` 或替换游戏 GLB。

## v13 单因素试验（2026-10-14）

- 提案：仅放宽 u≈0.865/0.911/0.945 三个前头截面的横向半宽，保持肩部、躯干、上下侧影与贴图参数固定。独立 Phase 3 复核 APPROVED 为可证伪试验。
- 前视截面归属简化试验：可见肩部像素 26556→19834（约−25.3%），说明预期侧环收缩；该指标不代表视觉合格。
- 已经 `plan→build→render`，机械检查全部通过。实际同机位正面肩带变窄，但侧视与斜视眼鳃区域出现明显拉伸和红色纹理带，视觉试验失败；未执行 `accept`，未替换游戏 GLB。
- 记录为第二次候选失败（v12 第一，v13 第二）。下一步返回根因调查：当前 front overlay 选择阈值 `normal_threshold=0`、`side_limit=.99`，会将正面源图扩展至头侧面，可能是侧视纹理扭曲的重要原因；需先区分几何和投影贡献。

## v14 投影范围隔离试验与三次失败停止

- 独立复核批准只改一个变量：在 v12 几何和其他投影参数不变的条件下，将 `head_projection.side_limit` 从 0.99 收紧到 0.65，见 `resources/volume-fish/arapaima-head-v14.profile.json`。
- `volume plan → build → render` 均成功，机械检查全通过。同机位侧面与斜视的原生眼、鳃和嘴线比 v12、v13 更接近侧面源图，说明正面辅助图覆盖侧腹是纹理扭曲的重要贡献因素（高置信度）。
- 正面图却出现两套眼睛及交叉脸纹：收紧后的前贴图没有覆盖侧面源图上的眼，左右侧面眼从正视投影露出；正面辅助图的脸纹只在中央。这是 v14 视觉失败，不能接受或替换游戏 GLB。
- 累计 v12/v13/v14 三个候选视觉失败。依 `anvil:debug` 的三次失败规则停止继续调数值，转为架构审查：当前单个椭圆环身体、原生侧图覆盖全封闭体、表层前图按面法线淡入，无法同时可靠处理正视轮廓、侧视原生眼鳃和双图交界。需要设计明确的头部独立几何与纹理分区/遮挡，先获得用户关注的主视角，再重新开验证任务。旧 v11 游戏 GLB 保持不变；三个候选 handoff 均未 `accept`。

## 后续结构试验（v15–v17）

- v15 试用前向可见面的 UV donor 擦掉侧图眼睛；该组面在侧视仍可见，导致侧视眼睛丢失、正面眼睛也变弱。视觉审核 BLOCKED，专用构建器代码已撤回；诊断产物保留。
- v16 试用独立弧形前脸薄壳；正侧斜三视显示明显矩形边、黑色条纹，无法与头体表面连续过渡。视觉审核 BLOCKED，薄壳代码已撤回；诊断产物保留。
- v17 使用现有 `body_uv_patches` 与 `surface_patch` 眼睛机制，尝试让原生眼睛独立于躯干贴图。Foundry `plan→build→render` 与机械检查通过，但前视圆桶轮廓没有改善，眼睛上方有黑色碎纹，侧视眼睛重影。视觉审核 BLOCKED，未 accept / 未替换游戏 GLB。
- 这三项试验证明纹理遮挡与轮廓是两个独立问题。原正面源图带有透视化的后躯和正面鱼脸，当前由侧图椭圆截面形成的头/肩连续管状外廓无法靠局部覆盖贴图变为该形状；需按用户最在意的视角重新设计头肩三维轮廓，并为双视图纹理制作有明确边界的 UV 展开，再做正式候选。不得将 v15–v17 仅凭机械验证升级为验收。
- 用户进一步指出「正面甚至有两个眼睛」。复核 profile/构建器后确认：银龙鱼只有单张侧源图，没有 `head_projection`，显式眼睛沿同一侧图取样；巨骨舌鱼有侧图原生眼、正面辅助图的眼和 `Frontal_head_overlay` 三者叠在一个椭圆环头上。v17 又加了 `Textured_eye_±1` 显式眼面，造成额外重影。这是我们的纹理归属设计错误，不是该物种本身无法建模。已验收 v11 未加显式眼面，但前视仍可见侧图眼/正图眼的不一致；v17 未进入游戏。下一版必须保证每个物理眼只由一个 UV 区域/对象绘制，不能再叠加眼面补丁。

## v18 单侧图鉴别试验

- 按用户提议，从 v12 几何创建 `arapaima-head-v18-single-source.profile.json`，移除 `head_projection`，眼睛保持 `null`，没有正面辅图或额外眼面；只复用已接受侧图。Foundry `plan→build→validate→render` 全部成功，机械检查通过。
- 视觉审核失败：[正面](../evidence/arapaima-head/v18-single-source-front.png)只有一对眼睛，但额头呈大面积黑色同心条纹，嘴部像被拉成圆靶；[侧面](../evidence/arapaima-head/v18-single-source-side.png)鱼头背缘也有黑纹；[斜视](../evidence/arapaima-head/v18-single-source-oblique.png)更明显。单侧图消除了叠图重眼，却暴露侧面像素沿椭圆环绕到额头/正面的 UV 拉伸。当前通用单侧 UV 路径不能直接作为巨骨舌鱼成品；`style_visual_review=pending`，不 accept、不替换游戏 GLB。
