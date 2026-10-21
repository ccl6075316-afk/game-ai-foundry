# 黑鲷106：眼睛归属与皮肤取样分离

日期2026-10-21；Normal mode（102/103实际GPU画面和47帧记录，当前源图/GLB/代码可读）。用户授权只试黑鲷，保留现有眼位大小，不替换正式游戏。

## Phase1：证据与根因

- 源图SHA162e96afe723addb52a5675ac7308a3bd172491b82f975db6855d7073760d924，与082已接受source文件一致；workflow context done/human_review、validate ok。模型3643445f为未接受083预览，不能继承整鱼接受。
- 103对同一friendly_eye_uv眼域再乘窄中央法线mask，只去掉中央小桥。头顶正中也采到眼圈；实际Closed_body至少11个abs(normal.z)<.2顶点命中旧源眼域，真正两侧源眼中心则在z≈±.0233、normal.z≈±.858。没有独立左/右眼的3D归属。
- 原因已追至源纹理RGB→friendly_eye_uv→skin_sample（source/opaque分支）→ALBEDO。头顶使用同一侧图眼纹，跨面重复。源图眼位是否应更低没有证据，本轮不移动原画眼睛。
- 新查看发现旧source_eye椭圆中心(.9056,.4364)不能罩全下方眼圈，不能直接扩大旧遮罩当作完整眼分离。已人工圈定完整原生像素眼圈polygon，source-eye-proposal.png；瞳孔连通分量质心约(1793.87,447.62)像素。polygon包含完整金/黑眼圈及窄周边，避开右侧另一个天然黑斑；仍需独立域审核。
- 按实际friendly UV寻找当前真正侧眼瞳孔最近顶点为(0.4047123,0.0240310,±0.0261424)，normal.z约±.903；这是映射锚点，非物种实测位置。
- git历史：103窄桥清理、104对全部实际source/opaque采样封装并保留alpha；二者代码已归档。当前正式game没改。

## Phase2：待审核的模式比较

- 103仅在最终ALBEDO按raw/friendly UV与中央法线过滤；既没有完整眼圈域，也没有正向定义两个侧眼区。
- 主FishHeadSource现有眼清理用source_eye_keep(rest_position)+局部横宽；黑鲷真实眼位置与宽头比例不同，不能照抄旧across阈值。
- 104已验证每次source_texture/opaque_skin取样包装、原alpha不变，且用独立RGB探针并集检查影响区；可复用语法验证，不复用真鲷源墨线域。
- 新试验将人工眼域在皮肤供体副本补干净，原source/GLB保持不变，再用独立左右3D区域保留原眼色。为了避免动态位移使遮罩滑动，拟将静态3D归属权重写到运行时复制Closed_body的未使用UV2；原UV0/positions/normals/indices/colors/bones/weights及所有鳍必须逐字节保持。任何原UV2或未知mesh格式先拒绝。

## Phase3：待裁决的最小提案

先做未着色的归属诊断，不批准大改颜色：
- 源眼polygon像素点：(1761,385),(1818,385),(1843,399),(1858,424),(1858,466),(1838,492),(1810,504),(1761,504),(1738,480),(1733,446),(1740,411)。
- 3D中心：(0.4047123,0.0240310,±0.0261424)；半轴(.045,.070,.015)，椭球距离q≤.95为1，q≥1.05为0，中间连续过渡。是为本鱼现有源眼定义的工程试验域，不做跨种参数。
- 当前156个源眼polygon内abs(normal.z)≥.75侧位顶点q最大.9419，均保留权重1；正中域z≈0不在任一眼区。不能以此代替片元和真实画面。
- donor沿用已检查干净灰皮肤rect(.85,.36,.88,.39)，按原生像素镜像延续，只改眼域内RGB，alpha完全保持原采样。新皮肤副本在眼域外应每RGBA像素相等。
- mode0与独立原始材质同景47帧必须完全相等；左右眼分色诊断不允许中线相接或多余眼；候选需侧眼中心/轮廓对照，离散动作及切换无滑动；原允许域以外零变化，不能用after反推扩大mask。
- 旧鳍面失败继续保留；任何候选交付仍需新鳍根/鳍面/身体门，不以几何未变跳过。


### Phase2设计收敛：保持网格原样的逐顶点归属表

Phase1独立审查已APPROVED（根因/源polygon成立，不批准颜色）。进一步检查ArrayMesh重建会涉及导入LOD保留，决定不用UV2重建网格：从实际surface0静态顶点计算左右归属，存入无sRGB的浮点ImageTexture，在vertex()按VERTEX_ID查表，再随三角形插值给fragment。原mesh所有数组/LOD/蒙皮/骨骼一字节不动。Godot4.7文档明确VERTEX_ID是当前顶点在缓冲中的索引；仍须实际GPU诊断拒绝索引偏移/空命中，不能只信文档。https://docs.godotengine.org/en/4.7/tutorials/shaders/shader_reference/spatial_shader.html

原皮肤材质先装配；106只复制surface0材质，复用104已验证的源采样token包裹逻辑（不改104），注入新skin/eye/mask纹理与静态归属表。不用Godot Decal节点，不新增漂浮眼片、不增加透明鱼身。材质RGBA的alpha仍每次返回original.a，只改眼域RGB。

106独立baseline取原105单鱼fixture、103helper强制mode0；新候选不再叠103桥遮罩。两工程相同Hall/机位/动画，先捕基线，再检106off逐帧相等。


### Phase3失败基线与实际导入元数据

已读取Godot实际surface0：11552顶点、22750三角形、6级原生LOD；序列hash9db28483c443f64298d25994f9e64709a53ff166eaf80a7001f253fbcc84c8df绑定positions+normals+UV0+indices原始packed bytes。ownership-proposal.validation.json包含逐级三角统计。原始材质有33个中央(abs(z)<.005)且命中完整源眼域的顶点；验收条件“中央眼归属=0”在原始映射下明确失败。提案两眼域对这33点均为0，对156个源眼域内侧位(normal.z≥.75)点均为1；基础及所有6LOD都没有同时含左/右正权重的三角形。不能替代实际片元验收。

为进一步避免任何粗LOD插值把眼权重连成带，查表内容改为原静态顶点rest坐标xyz，fragment用插值后的原坐标分别计算左右椭球；不直接插值权重。两椭球扩至q1.05仍有约.0208原生单位中线间隙。原mesh仍完全不改。数据表只在vertex用VERTEX_ID查，越界必须出现明确诊断失败，而不是当无眼通过。

拟允许实施后的第一步只跑mode0身份和mode2归属诊断；未人工看过两侧/头顶分区前，不把mode1修色当通过。独立baseline捕获已完成，需看实际GPU输出再确认。

### 分阶段独立审核结论

独立审查 `material_repair_review` 已分别批准Phase1根因、Phase2收敛方案、Phase3最小失败基线。Phase4授权范围暂限mode0原样输出、mode2左右归属诊断：须先通过47帧与独立基线逐RGBA像素相等，再查看两侧完整眼圈、正/俯/斜视与LOD压力视图。颜色修复mode1仍未批准。CPU全6级LOD检查不等同于已实测GPU逐级选择。

实现委派 `source_ink_sampler_doer`，只新增Foundry106专用helper、冻结工具和本鱼profile，并装入独立候选工程。正式游戏、原图、GLB、UV和骨骼均不改。当前为未完成试验，不是整鱼验收。

### Phase4：首次GPU诊断（修色仍未启用）

- 首次装配因JSON数字数组与整数数组的严格比较误拒绝，已修输入类型校验。Godot另不允许helper函数直接赋varying，改为返回值后在vertex stage赋值。这是实现调试，未生成修色候选。失败进程已结束，不能使用其输出作为证据。
- 真实GPU mode0与独立原始fixture47张截图逐RGBA像素相等，零变化。`mode0-identity.validation.json`保存逐图统计。
- mode2的47张标准图与48张近远/LOD压力图已捕获。排除会替换106材质的clay和口腔ownership视图后，85张有效着色诊断图无lookup-error magenta。粗细压力的aggregate primitive counts确实不同，但未证明6级LOD逐一选择。
- 发现原域不能立即进入修色：固定侧眼ROI中约5303个金色候选像素，有381个不在纯侧眼owner内，位于上眼缘。这个阈值只是预警，不能替代原图眼圈识别；已交独立审查判断是否误伤完整眼圈。见`eye-rim-warning.validation.json`。CPU只保护normal.z≥.75的156顶点并不充分。
- 原生灰皮肤候选供体rect [.85,.36,.88,.39]实际整数区域[1688,356,1747,386]均不透明，已实际查看，有原生灰像素变化且无眼纹。尚未生成修色副本。
- helper随后仅加入null模型拒绝guard；模板未变，但最终候选仍须重新捕获绑定最终文件哈希，不能把旧回执冒充最终版本。

### 归属假设被否定：上眼圈与旧中央禁区有交集

独立审查拒绝r015：屏幕(593,267)、(609,280)原金圈被归为纯绿。仅z半轴改为.017的诊断也未解决；(593,267)已恢复，(609,280)仍在蓝绿过渡，金色预警381降到260但不能以减少数量当通过。

为停止逐档猜半轴，导出同Hall/零幅度Swim0/相同侧视机位下的实际蒙皮world顶点、原rest/UV、base与6LOD索引及像素中心射线，以最近正射线三角交点的重心权重反推原rest和最终源UV。`pixel-trace.validation.json`保存全部结果；争议点回查source RGBA与基线实际像素一致。

| 屏幕像素 | 原图像素 | rest Z | r017椭球q | 含义 |
|---|---|---:|---:|---|
| 593,267 | 1811,411 | .010821 | .95264 | r017大致恢复原金圈 |
| 609,280 | 1826,424 | .010278 | .99926 | 仍被混入清理区 |
| 600,270 | 1818,417 | .008760 | 1.07588 | 可见上金圈仍会清除 |
| 580,250 | 1799,402 | .004428 | 1.33350 | 上眼圈已经处于旧abs(Z)<.005中央禁区 |

最后一项意味着“原侧视完整眼圈一像素不动”和“旧中央禁区完全无眼纹”并非已证明可同时成立；不能继续以扩大椭球碰运气，也不能未经证据直接移动眼图。回到Phase2/3，独立审核重新裁定可见眼圈与真正头顶的分界及是否需要最小局部映射调整。修色仍未实施，正式游戏仍未改。

### 两种足迹与旧UV的限制

独立审查已批准分离两个mask：旧12747像素polygon用于清理旧取样；新的9819像素完整眼层mask用于保留金圈、瞳孔、白反光与完整外黑圈，排除周围灰padding和右侧天然黑点。新mask是本次人工视觉审核的数据，颜色连通/凸包只用于提出选区，不是通用自动眼睛分类器。新mask有5像素超出旧polygon（2黑、3灰边），旧眼清理最终须冻结并集，不得漏清。

已精确复刻原透明供体延展：nearest标签来源落旧眼polygon的missing像素为0，重建opaque供体与实际PNG逐RGBA完全相同，见`fallback-eye-provenance.validation.json`。本鱼可共用旧source/fallback眼域；其他鱼须独立追踪。

原设想 `eyeUV=friendly_eye_uv(UV0-shift_v)` 在UV域解析求完整mask最小位移，已采源像素中心、cell角与边中点，并逐左右/base+6LOD报告：旧宽polygon包含灰padding，base需40源像素；紧眼层base需20，至LOD4需26，但LOD5正侧仍无公共解。报告保留，未跳过无解LOD、未实施此runtime。

进一步反求原瞳孔UV：source质心(1793.8714,447.6234)经逆friendly，在base恰有左右两份rest锚点(.403492668,.024869934,±.026227320)；LOD0..4有近似相同XY，LOD5连原UV瞳孔中心都无preimage。旧UV位移仍依赖已经丢失眼域的简化UV，不能作为跨LOD独立眼层。

正在审核的下一方案：眼层改为rest XY平面投影，原图、身体UV、mesh/LOD/rig完全不改；以当前瞳孔rest锚点为基准保持X，源像素物理尺寸从原friendly scale校准，按实际左右曲面与全部LOD求最小向下Y位移。RGB层保持原色彩转换/tint/COLOR与光照，中央禁眼带仍保留。尚未授权实施修色。

### 最终方案：独立restXY眼层，明确退休坏LOD

restXY也不能在原LOD5上找到完整眼域。实际GPU粗压力显示其上半头缺失；该档面积约从base .437808降到.160536，maxY从.15817降到.03159。独立审查批准的例外是只退休Closed_body surface0的LOD5（402三角），原GLB、全部surface数组/base/LOD0–4、surface1和鳍LOD、Skin/骨骼保持。不能继续声称运行时LOD集合一字节没变，也不能把原LOD5写成通过。

实际原瞳孔锚点XY为(.4034926681664948,.02486993356463753)，独立眼层使用`.9/1986`原生单位/源像素，下移22个物理像素；保留各LOD的像素单元边界计算下界约21.9334。中央absZ≤.005无眼，absZ≥.0055完整归属。瞳孔尺寸约原100%，金圈bbox约96.54%X/94.34%Y，外黑圈约92.90%X/93.44%Y。上述是本模型工程测量，不能当物种实测或跨鱼种默认。

独立审核分别批准新mask、restXY方案与mode1局部RGB试修。原12747清理polygon补入独立眼mask超出的5像素，冻结12752像素并集；完整眼层9819像素。source/opaque分别用已检查原生灰皮肤镜像供体补RGB，全alpha及域外RGBA严格保留。新眼从未改source取金/黑/白，保持原调色与光照。最终视觉审查看两侧、顶/前/斜视、粗压力与动作切换，允许展示和保留眼睛试修；旧前额/吻端条纹拉伸不属于本轮已解决项。

### 最终真实GPU和代码合同检查

- 最终代码冻结后重新捕获10批。47张原baseline与mode0逐RGBA零差异；mode1在独立RGB三基色探针并集外零变化，全图alpha零变化。48张近远/LOD压力mode0与只修LOD、不安装106眼shader的独立参考零差异。
- 有效37张标准与48张额外owner诊断没有lookup magenta或无归属orange。诊断会替换材质的clay/口腔ownership图不冒充有效眼shader检查。
- 永久`capture_eye_transitions.gd`实际采Swim→Turn→Ascend→Dive→Swim，各.25/.75/1.01T、侧/顶共24图。先`set_action(target,false)`后step0消费pending并断言真实transition；restart=true会seek/reset，不能验证过渡。
- 当前安装绑定helper SHA `d72311bf83db2028078df639ce7adaa616239276e6fbfba6fb3063d9a4c3416b`，template `dbe418371b1f2244264c849037994f997fe476e429a1a53b1bb0d368c9d49a33`，runtime config `b9da4bdc23ffecb7199c106d8d59fd32ca648d3ae015dbb94ae5e4e2c73eaf85`。

### 身体检查器兼容失败与修复

首次body门因动态shader的resource_path为空而报Unexpected body shader；不是发现实际透明洞。不能伪造固定路径绕过。现在仅对实际黑鲷Closed_body surface0核验安装时generated-code SHA、完整当前template、model/helper/config/LOD回执与实际opaque RGBA，去注释后拒ALPHA、ALPHA_*、discard；其他未知shader继续拒绝。实际headless正例及15项破坏回执/代码/模板/alpha负例通过。只在单鱼106且实际未使用head/mouth时允许其缺失，并在回执列出。

修复后重新运行原`validate_body_integrity.py`，闭合壳/不透明供体和16个同姿态GPU覆盖通过，missing_body_pixels全部0。覆盖算法、容差和Python validator未改。失败前证据与修复后当前报告分别保留。

### 当前完成边界

当前177姿态鳍根通过；更密490姿态根区也通过，但全鳍面仍有原有左胸鳍35姿态穿体，最深约0.024176mm，超过冻结0.02mm。保留失败，不为本轮眼睛而调阈值。眼睛试修可以展示，整鱼未接受、未替换正式游戏、未调用volume accept；导出包尚未验证。最终报告与标注图保存在Fish仓库`experiments/blender-fish/eye-separation-106/`。

最终独立`material_repair_review` Phase4代码门APPROVED，限定106眼睛试修和身体检查兼容适配。未发现新的阻断；整鱼膜面失败保留。主线程完成最终文件复核、Python编译及两仓库diff空白检查，记录见`.ai/anvil/reviews/2026-10-21-106-eye-ownership-review.md`。本轮没有提交/推送或正式资产替换。

107推广时共享身体检查器增加严格梭鲈分支，106专有函数及helper/template/config/model未改。106原负例合同重跑通过，16视图身体门也重新GPU通过，current-gates及completion中的身体证据SHA已更新，旧报告存before107前缀。原左胸鳍失败和106其余证据/接受边界保持。
