# 104：显式源墨线 RGB 排除试验

**实验候选，未安装到游戏，不代表任何鱼已验收。** 这不是自动描边分类器。
制作方必须逐物种确认哪些源图像素是二维描边、哪些是正常皮肤、真实斑纹、口裂或鳃线，再冻结 mask 和供体图。

## 使用边界

- 在现有 friendly/head-source/口部材质 helper 装配完成之后调用 `FishSourceInk.gd.apply(model, species, mode)`。
- 仅修改指定 `Closed_body` 的 `surface 0` 材质副本。模型实例必须直接来自配置指定 GLB；唯一同名网格、材质、尺寸和原始源图必须匹配。
- 不修改源图、GLB、UV、法线、绑定、动作、口内、鳍或 overlay；原材质参数与 shader 分支保留。
- 展开原 shader 的 `FishHeadSource.gdshaderinc`（绝对 `res://` 或相对于原 shader 的路径）。只接受这个已知 include，未知 include 失败。
- 把原 shader 中的所有二参数 `texture(source_texture, UV表达式)` 与 `texture(opaque_skin, UV表达式)` 包装成 RGB 取色函数。最终 UV 表达式原样保留，包括 `friendly_eye_uv` 之后、头部投影之后和现有局部供体取色之后的坐标。
- 包装函数**总是返回原采样 alpha**，包括透明源区及 opaque fallback；查 alpha 的循环、提前返回、覆盖规则不改。下游原有颜色混合、色调、眼睛处理和 `ALBEDO` 写入不改。
- 不支持额外 LOD/bias 参数、其他源 sampler 操作、未知 include 或不满足 nearest/source_color/repeat_disable 的原 sampler。拒绝后不装材质。

## 冻结配置

默认读取 `res://assets/models/fish/motion/source-ink.json`。调用第四参数可指定另一配置路径。

```json
{
  "schema_version": 1,
  "profiles": {
    "species_id": {
      "model_path": "res://assets/models/fish/species_id.glb",
      "model_sha256": "实际 GLB 的 64 位 SHA256",
      "mesh": "Closed_body",
      "surface": 0,
      "source_size": [1024, 1024],
      "shader_origin": "res://scripts/aquarium/FishBodyOpaque.gdshader",
      "source": {"path": "res://assets/models/fish/motion/ink/species-source.png", "sha256": "实际 PNG SHA256"},
      "mask": {"path": "res://assets/models/fish/motion/ink/species-mask.png", "sha256": "实际 PNG SHA256"},
      "donors": {"path": "res://assets/models/fish/motion/ink/species-donors.png", "sha256": "实际 PNG SHA256"}
    }
  }
}
```

`shader_origin` 仅在现有 helper 已生成无 `resource_path` 的临时 shader、且其中有相对 include 时用于解析。它不是替换 shader 的模板。所有配置应随本次 validation report 冻结哈希。

三个 PNG 尺寸必须等于原 source 贴图。这里 `source.path` 指**冻结的实际 Godot imported `source_texture.get_image()` 解码 RGBA8 base-level 快照**。helper 校验 PNG 文件 SHA、尺寸，并对实际材质与快照做**base level 全图、全通道、全部字节相等**校验，不做 sRGB→linear 转换，也不放宽为仅不透明像素比较。`Image.get_data()` 可能包含额外 mipmap 层，而 PNG 仅保存 base level；由于本模块只接受不使用 mipmap 的 `filter_nearest` sampler，比较前仅对临时 Image 清除未使用的 mip 层，并在 receipt 记录此事，不改变实际 Texture。Godot 的 `fix_alpha_border` 可能修改 alpha=0 区域的 RGB，因而该快照不一定与 GLB 内嵌原图逐字节相等。

制作报告必须同时保留 GLB 内嵌原图的来源 SHA，以及“内嵌原图与 imported 快照的不透明像素相等”报告（注明选区 alpha 阈值、比较像素数、差异数和两张图的 SHA）。这些是来源追溯证据；不能代替 helper 对实际材质与冻结 imported 快照的严格全字节比较。实际内嵌 GLB 图另由 GLB 哈希绑定。

### Mask 与供体编码

- mask 红通道必须为 `0` 或 `255`；`255` 才替换 RGB。透明区如会触发 nearest-opaque fallback，制作方须将对应 ink 来源的排除区域扩展到这些透明坐标；helper 不自行分类或扩展。
- donors 是 **RGBA8 数据**，每个命中 texel 的四字节按 `[x高, x低, y高, y低]` 编码冻结 source 的整数像素坐标，原点在左上。未命中位置不读取。
- donor 必须在尺寸内、source alpha ≥ `243/255`、且不在 mask 内。此技术检查不能判断 donor 是否有真实鳞纹、是否来自同一身体部位，仍需实际审核。
- mask/donors 从原始 PNG 用 `ImageTexture` 建立，不依赖 import 配置；shader 不给它们 `source_color` hint，避免把坐标元数据当色图解码。source/donor RGB 则通过原 `source_texture : source_color, filter_nearest` sampler 读取，保留正常色彩转换。
- source 和 opaque fallback 都用各自最终传入的**相同源坐标**查询 mask。替换 opaque fallback 时 RGB 也取冻结 source donor，alpha 仍为该 fallback 原 alpha。

## 模式与证据

`apply` 的 mode 默认为 `0`；合法值：`0` 原色原 alpha，`1` donor RGB，`2` 红探针，`3` 绿探针，`4` 蓝探针。探针同样只换命中 RGB，保留原 alpha。下游 shader 仍可能混色或覆盖探针，因此不能把最终屏幕未显色直接解释成“没有采到墨线”。

`apply` 返回安装数量 `0/1`；`last_error` 表示失败原因，`last_receipt` 记录本次模式、采样替换数量、命中 texel 数和输入哈希。物种未配置返回 `0` 且无错误。重复安装明确失败。模式切换可在已安装副本上设置 `ink_mode`，无需再次 apply。

最小 headless parser 检查只证明 GDScript 可解析。交付仍需：mode0 与基线逐像素对照；三色探针及其并集；原图/无光照/灰模/贴图多视；身体变化区外不变；口内与 alpha 不变；真实四动作及切换；当前鳍根、身体完整性和吻型门。任何 donor/配置/模型变化使对应旧报告失效。

`check_source_ink_contract.gd` 可用 Godot `--headless --path <现有游戏目录> --script <该脚本绝对路径>` 运行。它检查真实两种源 shader 的展开、包装、alpha/ALBEDO 表达式保留，以及 `texelFetch`/别名/第三参数漏包和注释伪造 nearest 声明等反例；不建立任何模型或接受记录。

本模块不解决自动分类、眼部重复投影、错误嘴型、头部尖化、纹理拉伸或脏色来源尚不明确的问题，也不把“变亮”当成修复通过。
