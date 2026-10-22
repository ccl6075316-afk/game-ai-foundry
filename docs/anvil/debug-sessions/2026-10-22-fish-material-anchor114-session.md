# 114：原材质嘴线与动画中贴图滑转

用户明确：回到未清洗原材质标线，当前材质已经洗掉部分嘴部；新增贴图游动时会跟着转动。旧113“确认当前材质绿线”依赖撤销，不用那份被质疑的图裁模型。

原嘴线使用112保留的source-images原始PNG直接在2D画布显示和标线，不通过clean-source、shader或当前重建UV。原图未修改；标线是候选识别结果，不冒充用户接受或已经完成几何修剪。

## 根因与独立审核

BodyChart112在vertex()中把VERTEX/NORMAL命名为rest坐标，但Godot Compatibility先蒙皮再执行用户vertex，动态坐标使静态截面投影/法线混合域随姿态改变。现有EyeOwnership106/107的导入顶点序号和原UV校验提供可复用模式，新增方法还必须保存原始法线。

`material-anchor-114/production-negative/anchor.validation.json`运行实际生产shader的vertex，固定全细节三角集合、加大cull bounds、只把raster POSITION展成原UV画布。四动作×三相位，旧采样最多改变167481像素；独立静态XYZ/normal oracle全部零变化、零查表故障。非均匀临时供体排除纯色隐藏滑动。原几何、绑定、UV均未修改。

anvil:debug独立审查debug_review：Phase1/2 APPROVED根因和模式，Phase3 APPROVED仅BodyChart修复。FrontSkin、SourceJaw虽然有同样坐标命名，但当前探针前者仅111有效彩色像素、后者0，不能证明有/无漂移。旧front-negative/jaw-negative报告中的ok=true是无有效覆盖造成的无效结论，明确撤销，不作验收。新探针强制1000供体像素，覆盖不足返回失败。它们需要非退化参数或3D对应点验证，当前未改这两个分支。

## 修复

新增通用RestSurface114，直接从实际导入ArrayMesh逐mesh/surface提取XYZ、normal、UV到无mipmap的RGBAF最近邻表；GPU以VERTEX_ID定位并核对原UV、有效位和数量。异常显式洋红显示，不裁身体。BodyChart独立复制材质，避免跨鱼/跨surface覆盖表。固定原始采样坐标，保留实际骨骼变形和动作。

ValidateSurface112仍重建精确授权代码；另核对实际表的全部字节、数量、尺寸、格式、代码/helper/template身份、模型、全部surface数组与LOD摘要。FrontSkin既有outer wrapper通过精确重建继承其下BodyChart修复，不修改自身采样表达式。原PNG、供体、GLB、动作控制器均保持。

## 验证边界

先前chart-fixed对同一负例已零变化，但初版探针未强制coverage，需用最终探针复验。正在运行19条实际chart鱼的四动作、3个距离及真实切换、独立GPU查表故障探针，再重跑完整身体覆盖与逐鱼完整鳍基门。固定UV诊断不替代实际运行LOD，离散姿态不证明连续时间，也不构成背腹美术、嘴部黑点、唇线或用户外观接受。

此前113启动导入与分缸可见性修复保留。尚无新GLB、源图接受或整鱼交付。

## 最终结果与strike记录

Strike1：第一轮完整身体门在validate_lining拒绝black_seabream/zander。新增材质duplicate丢失眼域wrapper未声明的inactive口部投影参数，导致false变null。修复为复制前核对实际false、复制后显式保留false；不改或放宽验证器。最终BodyChart SHA256 `7cfb4bfe069a23792690581d8ae93968c95bd77481eb76ce7c960883dd909be3`。

最终UV诊断遇到piranha网格名不同导致probe空引用；诊断脚本改为按chart profile解析mesh/surface，生产代码未改。已通过的旧probe源码保留inputs/probe-fixed-closed-body.gd，可与报告probe_sha匹配；剩余鱼用新probe继续。该诊断错误不当作模型故障或通过。

- 19鱼456个固定UV样本全部0changed/0fault，最低39401供体像素；独立oracle保持零变化。legacy单变量恢复旧赋值重现167481变化。
- front/jaw分别111/0供体像素，最终按insufficient_probe_coverage失败，明确未知。
- 19鱼实际runtime304动作/距离/中点切换样本，0查表故障，最小213身体像素；不枚举全部LOD或连续时间。
- body-final：23鱼368组实际GPU身体覆盖，无缺块；fin：19鱼各177姿态完整鳍基通过，共3363姿态，不放宽根区或容差。
- gallery：最终1314checks/0fail。
- 本机M4预热120帧p50/p95：黑鲷10.512/13.771ms，梭鲈9.703/11.853ms，巨骨舌鱼13.134/15.037ms。维持113修复量级，不保证零性能回归或其他机器。
- 黑鲷/梭鲈实际生产材质游动GIF已生成，源帧与记录保留swim/。

独立debug_review最终Phase4 APPROVED，仅BodyChart滑转修复。逐一重算body/runtime依赖、fin计划/模型/报告、全部最终生产哈希相符。原图嘴线候选仍供后续几何工作；嘴型、正面黑环、背腹供体美术及FrontSkin/SourceJaw坐标风险不在本次成功范围。未作volume accept，未提交或推送。

知识记录：docs/anvil/knowledge/2026-10-22-fish-rest-material-coordinates.md。正式本轮状态读取Fish material-anchor-114/review.validation.json。
