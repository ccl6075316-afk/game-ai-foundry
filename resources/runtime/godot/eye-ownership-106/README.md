# 黑鲷106：独立眼层与局部皮肤试修

当前是**未接受的候选试修**，支持mode0原色、mode1修色、mode2诊断。独立域审核只批准继续试修，不代表整鱼、鳍面、身体、吻型或动作已经通过。正式游戏和原baseline未安装106。

## 当前设置与数据

- 实际pupil锚点：restXY `(0.4034926681664948, 0.02486993356463753)`；源centroid像素 `(1793.8714,447.6234)`。
- 独立眼层使用restXY投影，`pixelNative=.9/1986`，锚点只下移22个物理像素。旧sourceUV/friendly采样继续用于皮肤，不参与新眼定位。
- 完整眼层alpha mask为独立审核的9819像素，包含金/黑/白rim，排除右侧天然黑点。
- 旧清理mask修订为12747原polygon与9819眼层的精确union，共12752像素；旧revision与5个新增左眼缘像素证据保留。source与opaque分别绑定自己的清理mask。
- 保留的base及LOD0..4有共同可行域，完整pixel中心/cell四角/边中点的连续下界为21.9334146物理像素，上取整22。共享边上的同3D点合并后，每侧样本唯一；中央禁区absZ≤.005，完整owner从absZ≥.0055开始。样本检查不是全连续曲率证明。

`pixelNative`只使旧pupil局部X/Y尺寸近似保持。实际base三角测量的gold bbox约为旧值96.54%X/94.34%Y，outer-rim约92.90%X/93.44%Y；旧图部分rim原本没有base预像，报告另列。**不能说整眼大小完全没变。** profile中centers/radii是旧r017诊断的历史元数据，当前shader不用它们定义owner。

## 冻结与RGB副本

```sh
.venv/bin/python resources/scripts/volume-fish/freeze_eye_features.py \
  --input resources/volume-fish/eye-black-seabream-106.json \
  --output projects/fish-106-black-eye/game/assets/models/fish/motion/eye-106
```

命令先验证全部输入，再冻结source、mask、配置与副本证明。配置 `eye-ownership-106.json` 放在候选 `assets/models/fish/motion/`；PNG路径仍指 `eye-106/`。输入、source、embedded来源、实际fallback、mask、每张clean副本都有独立SHA。

source是实际imported RGBA8 base-level快照。运行时对原 `source_texture.get_image()` 解码，只清除未使用mip层，随后全图全部RGBA字节与快照严格相等（包括alpha0 RGB）。fallback也与冻结原PNG全RGBA严格对照。不做sRGB转换或仅不透明像素放宽。

mode1分别从原source和原opaque生成clean副本，只替换12752旧眼域内的RGB；全图alpha、域外全部RGBA必须逐字节相等。供体为已检查灰皮rect `(.85,.36,.88,.39)`，实际整数边界 `[1688,356,1748,387)`。按原生60×31像素的X/Y镜像周期重复，以供体左上角作相位；不缩放、不平滑、不用灰常量整块填充。原source、GLB和fallback文件不改。副本合同同时在Python冻结和Godot安装时检查。

## shader与材质边界

`FishEyeOwnership.gd.apply(model,species,mode=0,config_path=DEFAULT_CONFIG,probe=0)`只复制已装配的 `Closed_body surface0` 材质。候选装配移除旧103桥遮罩后安装106，不叠加两次清理。原source/opaque每次二参texture取样经过白名单包装，最终source坐标及alpha保留；未知取样操作、伪nearest声明、重复安装直接拒绝。

- mode0：每个包装返回原RGBA，新眼层函数返回原RGB。实际GPU须对独立原baseline逐像素证明身份。
- mode1：旧域RGB取对应clean副本；新眼层在原最终色末端读**original source RGB**，混合权重为`原source alpha × 9819眼mask × owner`。保留原`tint*COLOR`及光照。不从透明RGB造眼睛。
- mode2/probe0：旧域green；独立负Z眼red、正Z眼blue；缺owner眼域orange标失败。
- mode2/probe1/2/3：分别用red/green/blue代替旧清域和新眼层的实际RGB路径，全部alpha仍原值。三探针相对独立baseline的并集用于预先限定mode1影响区。
- 非mode2禁止非零probe。越界/空lookup项/原UV与参考UV错位显示magenta。

原restXYZ与UV参考存RGBAF ImageTexture，无source_color、无mip；vertex按VERTEX_ID查表，fragment用插值rest计算投影。源色/clean色sampler使用source_color+nearest；mask/lookup不按色图解码。shader不输出ALPHA/discard，口内、鳍、动作和骨骼不受此材质层修改。

通用helper默认mode0。**只有106候选装配缺省为mode1/probe0**，环境 `FISH_EYE_MODE/FISH_EYE_PROBE` 或capture显式参数可覆盖；LOD-only reference固定原103 mode0。

## 明确退休一个坏LOD的候选例外

原生LOD5（402三角）破坏头部上半，完整眼位无可行解，**它已被拒绝，不能称通过**。`FishEyeLod106.gd`只对冻结GLB的`Closed_body surface0`退休这个LOD，其edge与index-data SHA绑定。

实现用原生ArrayMesh `_surfaces` packed序列复制，删除唯一LOD项，不解码重编码几何。所有其余packed vertex/normal/UV/skin/index/format/primitive/AABB/boneAABB/material/name、全部surface数组、surface1全部LOD严格相等。resource属性、metadata、shadow_mesh引用、skin对象和skeleton路径保持。新ArrayMesh有新运行时identity/path；原资源与GLB不改，不接管旧resource缓存路径。未知存储属性/格式、脚本mesh、非零blend shape拒绝。这依赖当前Godot可读存储合同，不默认跨版本兼容。

候选同时安装LOD helper与eye helper。ignored `fish-106-black-eye-lod-reference/game`只装LOD helper，旧103固定mode0，不装106eye。原47帧候选mode0对原baseline；粗LOD压力另对LOD-only reference，分开判断头部恢复与shader影响。

## 检查与捕获

- `check_eye_contract.gd`：真实headless装配0/1/2和mode2三probe，检查源/fallback身份、clean副本域外RGBA与全图alpha、mesh/LOD/binding保持；拒绝无效mode/probe及未知采样。输出参数 `-- --output=/tmp/fish106-mode1-install.validation.json`。
- `capture_trial.gd`：同原102 Hall/region/camera的47张多视和四动作采样，参数 `-- <output> --eye-mode=0|1|2 --eye-probe=0|1|2|3 [black_seabream]`。
- `capture_eye_diagnostics.gd`：同样参数，额外48张：两真侧/前/顶/双斜、近远、细节/粗LOD压力、lit/unlit。记录请求阈值、lod_bias和aggregate primitive count，不冒充逐级GPU选择证明。
- `--lod-only-reference`仅允许mode0/probe0，要求真实LODreceipt且eyeReceipt为空；普通候选必须两个receipt都有，不能漏装106却靠LODreceipt宣称通过。

安装数0/1、`last_error`和`last_receipt`提供结果；模型metadata分别为`eye_ownership_106_receipt`、`eye_lod_106_receipt`。PNG通过 `FileAccess.get_file_as_bytes + Image.load_png_from_buffer`读取并先校验文件SHA，避免Image.load_from_file对已import资源的旧WARNING。**导出包仍未验证**，rawPNG必须列入export include filter，改buffer读取不会自动打包它们。

任何模型、配置、mask、clean图、helper变化会使旧报告失效。交付仍需当前鳍根/鳍面/身体/吻型、实际四动作及切换门；不得把本次局部视觉审核当整鱼接受。
