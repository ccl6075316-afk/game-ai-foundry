# 巨骨舌鱼物种网格与头部复核（2026-10-15）

状态：**实验，未验收，未替换游戏资产**。以已接受的侧图及 `resources/volume-fish/arapaima.profile.json` 为轮廓输入，对比游戏中旧 GLB、物种化白模、旧鳍混合版。实验脚本归档在 `resources/volume-fish/experiments/arapaima-species/`；大体积 `.blend`、`.glb` 和全角度临时渲染保留在本地游戏实验目录，未提交。

## 鳍的“鼓包”与连接

- 新物种白模的鳍实际很薄，但鳍膜和薄侧壁共用平滑法线；胸鳍又增加了根部厚度、向外弯曲，源图多边形还经过 Catmull 圆滑。斜视时光照把薄鳍表现为鼓起的肉片。
- v4 保留源图鳍轮廓、减小胸鳍弯曲与根部厚度，并把薄侧壁设为硬边：[斜视灰模](../evidence/arapaima-species/v4-flat-fin-oblique.png)。鼓包消失，但鳍像平纸片，不能作为完成版。
- v5 保留新躯干/头，移植已接受游戏模型第 0 帧求值后的七片旧鳍：[斜视材质图](../evidence/arapaima-species/v5-old-fins-textured-oblique.png)。旧鳍有内部顶点与轻微折面，比 v4 更自然；仍需单独解决鳍根穿插与动画绑定。此版本只是对照，移植鳍未保留骨骼。

## 头部的失败原因与试验

- v5 的[正视灰模](../evidence/arapaima-species/v5-head-front-clay.png)暴露悬在脸前的梯形下颌；侧面虽然能读出嘴，正面不符合已接受的鱼脸参考。
- v6–v8 用连续头壳替代独立上下颌，并加宽吻端。悬空下颌消失，但[正视口线](../evidence/arapaima-species/v7-mouth-front-clay.png)成了横杠和两条胡须状侧线；口线建模假设失败。
- v9–v10 将躯干与头合为一个闭合外壳，移除头肩的圆形端盖接缝，并按照新表面深度重新定位眼与鳃线。[斜视灰模](../evidence/arapaima-species/v10-oblique-clay.png)的外轮廓连续，但[正视灰模](../evidence/arapaima-species/v10-front-clay.png)仍是圆脸加突出的横唇，未达到物种形态验收。
- 单侧图直接投到整个外壳，[正视贴图](../evidence/arapaima-species/v11-side-uv-front.png)成为同心条纹。把旧版已接受的正面贴图承载面移植过来，[结果](../evidence/arapaima-species/v12-front-overlay.png)与新头相互穿插，出现尖形遮挡；旧 UV/贴片不能直接套到新几何。

目前最值得继续的是 v10 的连续头身形体方向与 v5 的旧鳍结构，但**组合仍未通过正视头形和贴图视觉审核**。原 `front044` 正面图带强透视，不能当作与侧图同尺度的正交前视数据。下一轮应先依据可信的正/侧/俯参考定吻宽、眼位、口裂与鳃盖边界，在灰模中同时验收三个视角；随后为新头重建 UV 与正面、头顶过渡贴图。不能继续靠额头投射条纹或旧贴片遮盖几何问题。

脚本是隔离实验代码，不是正式 `volume plan → build → validate → render → accept` 的产物。旧游戏 GLB、已接受源图与运行时资产都未在本轮替换。
