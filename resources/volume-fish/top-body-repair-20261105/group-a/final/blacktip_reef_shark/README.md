# 黑鳍礁鲨：鳍位、尺寸及真实有限支持收尾

当前冻结源 SHA `c663b9a4347c5327ad01c561d9cbe5da93d93ba292855712b28c1cdb863217bd`，GLB `f9ffc6f9c71155cdf126cd82bf3b1c88d634d61963b64896796fd59e88428e43`；完整3930三角面、展示150cm，实际完整GLB X跨度及scale在numeric-evidence.json。所有operator物理门及正式SOP9阶段60证据已通过，已同字节安装canonical；全9鱼真实游戏入口276检查全过（errors=[]、新进程、无ERROR），含Display/Fishing/真实口缘与hook/四动作。两仓提交由root收口，本记录尚不冒称已commit。

今后只从canonical `projects/fishing-2d/assets/source/fish/blacktip_reef_shark/fish.blend`、`projects/fishing-2d/game/assets/models/fish/blacktip_reef_shark.glb`及本目录source-domain.json继续。旧候选、媒体和密集姿态按用户授权退休，旧路径/SHA仅作溯源，不能称可重放或新验证通过。原PNG、共享鱼资料库及29页对照PDF保留。

source-domain.json直接读取最终源，保留8鳍所有完整root IDs、原完整3D cap descendants、实际root位置/全部UV loop集合/named skin及跨根自由边。Caudal104点/144面是完整三维尾柄/末cap footprint，不是一个平面或UV中面；不能用当前法线、接触距离或UV阈值重新缩根。原域仅作有向边/面细分新增41个必要有限支持点，82tri，不增加自由叶密度。

本轮最有用的方法与负例：

- 最近四个cap点的无拓扑delta混合把尾的上下叶/前后域混到一起，造成24个毫米级自由叶折叠。用原真实网格邻接连接完整cap与保持的远自由叶，再只修实际首层残余；保完整104cap与46远叶固定。单做Float64 nearest bary、去掉补偿或仅harmonic场都没有自动通过。
- 薄cap投影必须保原参数与两层身份。Nearest把不同原source点压到同一body脊会倒序、折层乃至零面。胸鳍保原X/Z参数，再在实际body侧向交面求Y与原层序；背/臀保原signed lateral身份。最终Anal0/36仅恢复其原侧向间距，全部9mesh exact zero-area为0。不得把三维cap整体压平。
- `for g in list(v.groups): remove(...)`保存的是会随成员数组删除而移动的RNA引用，会留下旧body组。本轮87根点曾有总权>1，归一化导出后造成厘米级动态错位。必须先快照整数group IDs，清空并实际读回，再写所需named weights。保原own-fin gain，只修证实不符合原期望的点；源拥有导出器正确归一化了错误源，不能冤称GLB凭空改权重。
- `LBS(point, bary(weights))`不等于三体表顶点各自LBS后再bary。静态贴合不是动态证明。通过维护CPU导出取得真实全490骨变换/权重响应，完整根顶点、7分边及4面点构造有界小量约束，保原.5mm阈值/完整域/幅度。只7根点≤.16mm物理偏移；单点会跨薄cap时对真实连续patch加共同运输约束，不追任意无限加面。所有UV aliases须同源身份。
- SecondDorsal只有真实free73产生全部5598坏有限descriptor；按完整490实测响应，只上移它1.248236mm物理，未改完整28根/远端/原轴，随后全8鳍490根与整膜均0失败。
- 法线厚度、完整cap signed接触和自交分别实核。复用`validate_explicit_shark_fin_volume.py`数学及当前显式域；尾截面按同一真实body rear X平面切实际有限body与完整tail cap，不能混所有不同X的根宽。所有8鳍实际constant-free负控保持完整cap而因taper拒绝；当前证明见最终正式数值。

本次保留明确限制：尾还有11个actual body平面的点/线接触，没有正面积重叠，10个≤11nm native、最长12.09µm，body signed≤1.562e-6mm；没有新的暴露自由叶折叠。不能写generic self0，也不能把此个案变成通用豁免或放宽正常volume/根/膜门。原88面口内是已接受的opaque常量暗腔材质，非本轮新涂色；外皮与104面原生唇过渡仍用原内嵌图片，严格身份保存单独验证。

numeric-evidence.json保完整核心数值、候选与报告SHA、失败原因、参考限制和清理字节。当前资料库参考BlacktipShark OBJ `ef7b01b1…dcda86c3`仅为获准艺术近似，精确Carcharhinus物种未经确认，不冒称生物实测。新改动按影响重新复验。

严格原生保存现已通过全部1730面/1215语义点/完整28边口缘。原constant oral216/242draw rows无损归59点，保单模型实际named FLOAT精确身份；跨模型按Godot同commit的原slot float32顺序归一化、float32乘65535后截断比较实际UNORM16，不能直接截断raw FLOAT或用Python double加法猜运行时身份。独立near-unit负例与47测试保留于父级debug知识记录，候选几何无为此改动。
