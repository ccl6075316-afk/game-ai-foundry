# 用户接受后的成品维护与历史退休（2026-11-05）

本次用户明确将新11条视为成品，要求“所有的”提交推送至两仓库干净，并删除相关实验图片、旧模型和纯占空间历史，只留有用文字。此授权适用于本次24条成品，覆盖旧SOP关于继续保存这些鱼历史代表图、旧负例模型及旧实验唯一输入的保留要求；不延伸至未接受鱼或其他资产。

当前鱼以游戏 `assets/source/fish/<species>/fish.blend` 和 `game/assets/models/fish/<species>.glb` 为修改基础。24份源文件经只读新进程审计，137个FILE图像均完整packed，21个GENERATED/VIEWER数据块不构成外链；无linked library或其他必需松散依赖。24份GLB无外部image/buffer URI。无需为清理而重导或改变已接受模型。

保留当前成品、可编辑源、实际运行脚本/动作配置、成品内嵌纹理、实际游戏2D原图/图标、共享资料库，以及用户特别要求的完整对照PDF。旧检查点blend/GLB、供体工作副本、截图、录像、逐帧/密集姿态/网格dump、重复报告、日志、回放归档和弃用实验脚本提炼结论后按精确清单删除，不再造大压缩包。非当前依赖的SOP来源图片重复副本也可退休。

文字按三层保存：通用方法留仓库skill/resources；逐鱼参数与最终SHA留发布manifest；具体失败、重要节点、限制和历史核心数值留游戏正式handoff及两份history摘要。保留历史报告的真实时点、哈希和结果；原路径失效须明确说明，不能把退休后的旧SOP称为新检查通过。以后重新修改须用当前源做新的影响验证，不能继承旧图或其他鱼接受。

执行清理前核对解析后的绝对路径、精确文件/字节/SHA、现成品和活依赖keeper，先完成文字提炼与PDF落盘，再清理。清理后核对保护资产SHA、实际删除/剩余字节及两仓库Git/LFS状态。用户说“提交”即两仓库commit+push；“本地清空”指Git工作区干净，不是删除仓库。不重写Git历史，不手工删`.git`对象。

正式入口：Foundry `resources/volume-fish/final-eleven-fish-20261105.json`；游戏 `plans/reviews/eleven-fish-release-20261105/HANDOFF.md`。PDF的参照角色与历史差异文字：`docs/reviews/fish-reference-comparison-20261105/README.md`。资料库艺术模型、近缘厚度参照和非标定历史预览的限制继续生效，不能升级为生物实测或补造主参照。


## 2026-11-08 扩展为28条与补漏规则

用户已接受鲸鲨、旗鱼及两条双髻鲨，以上canonical-only与旧实验退休规则覆盖全部28条。未接受游动观感不构成保留旧静态工程理由。每轮扫Foundry独立projects、游戏output/experiments/reviews及Git/LFS；Git干净不等于实验已清。旧归档的物种接受状态必须对照当前inventory更新，不继续按“四鱼未成品”保留。先分离原始论文/参考模型、提炼方法与失败数值，再按文件SHA清除旧工程/截图/模型/密集数据。当前源/成品、活运行依赖、资料库和PDF前后哈希验证；不手工删Git对象或重写历史。详见游戏static-fish-release-20261108/HANDOFF.md补漏段。
