# 远程鱼资源调查方法与证据

调查时间：2026-11-02。研究源 APK、远程快照和导出模型分别保留，不用相同鱼名证明版本或形态一致。

1. 从已完整校验的小米 APK 读取 `assets/bin/Data/f47775a3a8e034a4f819df69f2824a58`，用 UnityPy 1.25.4 解析其中名为 `update_allplatform` 的 TextAsset。其 XML 保存于本目录 `apk-update-allplatform.xml`，APK SHA 与配置定位保存在 `http-probes.json`。
2. 该配置明确列出 `android-cnformal1/2/3` 三个外部环境。仅请求各根目录下由客户端字符串证实的 `FilesMD5.txt` 和 `FilesMD5_V2.txt.zip`，结果见 `http-probes.json`。1/2 的原始清单 SHA 一致，3 的清单不同；本次保留 cnformal1 的唯一原始文本，其他响应只保留哈希和结果。
3. `FilesMD5.txt` 每行依次为资源相对路径、MD5、字节数和归属标签，以 `|` 分隔。5219 行中，3640 行标记 `__APP`，1579 行归属于其他标签；734 行属于 `bundles/b_fish_*.unity3d` 前缀，含非鱼动物、道具、贴图及变体。派生索引保留清单中的原始路径、期望 MD5、大小和 DLC 标签，URL 由已证实的根地址拼接原路径。
4. 选择 APK ZIP 中确实不存在的 `assets/bundles/b_fish_rainbowtrout.unity3d`，从 cnformal1 同名路径请求。实际 1006146 字节，MD5 与清单一致；独立计算 SHA256，结果见 `rainbowtrout-download.json` 和库内 `assets-manifest.json`。可重复取得资源不表示已取得生产复用许可。
5. 该包含重复的 32 字节 UnityFS 前缀；检查偏移 32 处为 `UnityFS\0` 后，使用 `UnityPy.load(data[32:])`。得到 1 个 Mesh、1 个 SkinnedMeshRenderer、1 个 Animator、3 个 Texture2D。Mesh 导出为 OBJ 后计数 `v ` 与 `f ` 行，得到 1826 顶点、2976 三角面；仅保留原包和解析证据，不重复存放这一未做视觉审核的 OBJ。
6. APK 的 `assets/bundles/b_lua.unity3d` 同样用 UnityPy 读取。`LuaDLC`、`DLCObserver`、`VersionFileManager` 等 TextAsset 是 LuaJIT 字节码，只提取字符串观察下载相关接口，不冒充完整反编译控制流。关键字符串见 `download-logic-observations.json`。其中 `dev_piecemeal` 是开发/回退常量，不作为本次鱼资源的正式来源。

虹鳟资源的 HTTP Last-Modified 为 2025-08-08，早于所保存小米 APK 的 2026-08-14。尚未证明当前游戏实际选择 cnformal1、清单代表最新线上版本、或资源与该 APK 完全配套，故始终独立列来源。

## 325 个基础鱼名的批量补齐

2026-11-02 用户要求“尽量补齐”后，读取已有 325 个基础名的 646 个预制体路径及对应包路径；646 个包均出现在同一份 cnformal1 冻结清单中。另下载 `bundles/BundleDependency.txt` 和 `bundles/InBundleAssetsMap.txt`，先核对清单大小/MD5，再计算 SHA256。对 646 个包递归展开声明依赖，得到 661 个包、822778961 字节，全部校验通过；没有将 APK 内其他版本的包混入依赖闭包。

通过原始 AssetBundle 的 `m_Container` 读取精确预制体路径及根 GameObject，建立以序列化文件名与 PathID 为键的对象索引，按 FileID 指向的 external 文件名跨包解析。沿 Transform 子节点遍历完整预制体层次，从 MeshRenderer/MeshFilter 或 SkinnedMeshRenderer 取得实际网格，再检查指定材质及非空贴图引用。不要只按包名或网格名猜测鱼种，也不要调用会隐式扫描整个仓库查依赖的容器便捷接口。

646 条精确预制体全部找到，325 个基础名均至少有一条可读模型；所引用的 593 个网格对象全部可导出，1858 个贴图对象均实际解码并保存解码像素哈希。导出文件按实际 OBJ 字节 SHA 去重，保留 588 个文件、289542312 字节。OBJ 是网格局部静息坐标，包含该网格的全部原始部件，没有烘焙场景/骨骼变换或重组为已验收整鱼。

644 条预制体的蒙皮骨骼引用全部可解析；小丑鱼、火焰神仙鱼使用 MeshRenderer，源预制体没有蒙皮骨骼绑定，但保留其原有 Animator 资源，不推断为没有动画。全部 Animator 的非空控制器/Avatar 引用可解析，尚未运行播放验收。`DogtoothTuna`、`Dolphinfish`、`Manta` 在目标索引中只有带后缀的预制体，逐鱼表保留实际首选名称，不伪造无后缀基础模型。

证据分别为 `collection-report.json`、`bundle-inventory.jsonl`、`prefab-inventory.jsonl`、`mesh-inventory.jsonl` 和 `texture-inventory.jsonl`。当前逐鱼表在 `catalogs/fishing-master-cdn-cnformal1-20261102/collection-status.*`，历史 APK 浏览表保持原字节。

可复用的本次调查脚本保存在 `collection-scripts/acquire.py`、`collection-scripts/resolve_prefabs.py` 和 `collection-scripts/validate_collection.py`，脚本哈希见 `collection-report.json`。从仓库解释器安装固定 UnityPy 1.25.4、jsonschema 4.26.0 至 `work/fish-database-complete-20261102/deps` 后，先运行 acquire，再运行 resolve_prefabs；脚本仅访问固定官方根地址及源清单列出的资源，已有文件先校验，不覆盖不同字节的原始资料。acquire 从已保存的目录与依赖表重建目标集合，可重复核验或续取；resolve_prefabs 更新技术证据和 `progress.json`。完成来源/资产登记和逐鱼目录更新后运行 validate_collection，校验全部资产哈希、LFS 规则、OBJ 坐标/索引、记录引用及历史迁移字节；最后仍须清理临时产物并收尾 progress/validation report。临时依赖下载遇到上游 TLS 失败后使用清华 PyPI 镜像取得相同固定版本，未修改项目正式依赖。

进一步测量须先核准真实物种、场景/骨骼变换和静息姿态，实际划分身体与鱼鳍，定义长度及截面测位，再记录 `Wmax/L` 与 `W(t)/Wmax`；本次解析的整鱼包围盒不能直接成为厚度依据。

## UV、蒙皮和动作的后续核查

读取 `mesh-inventory.jsonl` 定位的原始 Mesh，用 MeshHandler 读取 UV0 和绑定姿态；从原始 `m_CompressedMesh.m_Weights/m_BoneIndices` 独立展开顶点权重，保留完整流消费、权重和、非负有限值及索引范围检查。UnityPy 1.25.4 的压缩第 4 权重分支误用 `1 - integer_sum`，独立解码器改用 `(31 - integer_sum) / 31.0`，不对原数据做事后任意归一化；算法与 [AssetStudio 原始实现](https://github.com/Perfare/AssetStudio/blob/master/AssetStudio/Classes/Mesh.cs#L1030) 的余权重处理一致，所查源码的 SHA、取得时间和关键表达式留在审计报告。原包和既有几何导出没有改动。

从 AnimatorController 的 `m_TOS`、状态机数组、动画引用与 AnimationClip 的时间/循环/采样设置读取动作结构，按 FileID/external 文件名和 PathID 对应到片段；不以名称相同判断引用相同，也不把所有依赖内的 757 个片段都当作某一条鱼的动作数量。所有目标预制体共引用 605 个控制器，均已读取且片段引用完整。动作元数据、原始关键帧流、骨骼权重和材质均保存在原始包中，目前未做完整带骨骼 GLB 导出或实时播放验收。

鲫鱼示例的颜色、法线、金属度贴图分别是 `CrucianCarp_D`、`CrucianCarp_N`、`CrucianCarp_M`，材质槽及源对象引用保存在 `rig-animation-report.json`。目前 OBJ 自身只有几何/UV/法线，不含骨骼、权重、动画与引擎材质装配。原地摆尾与其他姿态有现成动作片段；整鱼位置路径、转弯、触发条件及是否叠加程序/Shader 变形仍须另查运行时代码。
