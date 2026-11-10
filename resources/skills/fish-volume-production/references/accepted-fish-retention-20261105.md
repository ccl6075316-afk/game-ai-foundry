# 用户接受后的成品维护与历史退休（2026-11-05）

本次用户明确将新11条视为成品，要求“所有的”提交推送至两仓库干净，并删除相关实验图片、旧模型和纯占空间历史，只留有用文字。此授权适用于本次24条成品，覆盖旧SOP关于继续保存这些鱼历史代表图、旧负例模型及旧实验唯一输入的保留要求；不延伸至未接受鱼或其他资产。

当前鱼以游戏 `assets/source/fish/<species>/fish.blend` 和 `game/assets/models/fish/<species>.glb` 为修改基础。24份源文件经只读新进程审计，137个FILE图像均完整packed，21个GENERATED/VIEWER数据块不构成外链；无linked library或其他必需松散依赖。24份GLB无外部image/buffer URI。无需为清理而重导或改变已接受模型。

保留当前成品、可编辑源、实际运行脚本/动作配置、成品内嵌纹理、实际游戏2D原图/图标、共享资料库，以及用户特别要求的完整对照PDF。旧检查点blend/GLB、供体工作副本、截图、录像、逐帧/密集姿态/网格dump、重复报告、日志、回放归档和弃用实验脚本提炼结论后按精确清单删除，不再造大压缩包。非当前依赖的SOP来源图片重复副本也可退休。

文字按三层保存：通用方法留仓库skill/resources；逐鱼参数与最终SHA留发布manifest；具体失败、重要节点、限制和历史核心数值留游戏正式handoff及两份history摘要。保留历史报告的真实时点、哈希和结果；原路径失效须明确说明，不能把退休后的旧SOP称为新检查通过。以后重新修改须用当前源做新的影响验证，不能继承旧图或其他鱼接受。

执行清理前核对解析后的绝对路径、精确文件/字节/SHA、现成品和活依赖keeper，先完成文字提炼与PDF落盘，再清理。清理后核对保护资产SHA、实际删除/剩余字节及两仓库Git/LFS状态。用户说“提交”即两仓库commit+push；“本地清空”指Git工作区干净，不是删除仓库。不重写Git历史，不手工删`.git`对象。

正式入口：Foundry `resources/volume-fish/final-eleven-fish-20261105.json`；游戏 `plans/reviews/eleven-fish-release-20261105/HANDOFF.md`。PDF的参照角色与历史差异文字：`docs/reviews/fish-reference-comparison-20261105/README.md`。资料库艺术模型、近缘厚度参照和非标定历史预览的限制继续生效，不能升级为生物实测或补造主参照。


## 2026-11-08 扩展为28条与补漏规则

用户已接受鲸鲨、旗鱼及两条双髻鲨，以上canonical-only与旧实验退休规则覆盖全部28条。未接受游动观感不构成保留旧静态工程理由。每轮扫Foundry独立projects、游戏output/experiments/reviews及Git/LFS；Git干净不等于实验已清。旧归档的物种接受状态必须对照当前inventory更新，不继续按“四鱼未成品”保留。先分离原始论文/参考模型、提炼方法与失败数值，再按文件SHA清除旧工程/截图/模型/密集数据。当前源/成品、活运行依赖、资料库和PDF前后哈希验证；不手工删Git对象或重写历史。详见游戏static-fish-release-20261108/HANDOFF.md补漏段。

第二轮缓存规则：Git/LFS缓存与工作区载荷分开统计。2026-11-10 Mac 实测发现，百度 standalone adapter 下 `prune --verify-remote` 会把从未上传的负例误判为 verified，不能再据此直接清真实缓存。先保护当前 index/HEAD、全部 ref tip、stash/父树、未推送提交、其他工作树和现存载荷；远端核对只能在隔离硬链接镜像中，命令级禁用 standalone、使用实际存储端点，并要求未上传负例确实保留。核对成功后才按精确 SHA 清真实旧对象，不对真实缓存用 `--force`。详见 `docs/storage/lfs-history-cleanup-mac-20261110/README.md`。Godot只删无有效源import且无代码/场景/序列化资源引用的缓存；当前资产前后SHA核对。旧版本号不代表无依赖，造景重建/预算验证和鱼兼容链仍使用的资源先保留。

## 2026-11-10 本机全目录收尾

跨机器同步不会删除被 Git 忽略的旧实验。不能沿用另一台机器的“已清理”结论，也不能只看 Git 状态或上轮删除清单：每次在当前机器盘点 Foundry 的 work/output/独立 projects、游戏 output/experiments/reviews、两仓库 Git/LFS 与导入缓存，记录未跟踪和被忽略文件。历史退休清单只有路径和 SHA 同时匹配才可复用。先查活动任务、当前引用及原始输入，再提炼方法和完整核心数值、按精确清单删除；重复证据要留下现存同 SHA keeper 映射。下载残片单独确认无活动传输，未知且未确认副本的 LFS 对象明确列入保留项，不当垃圾盲删。收尾报告须给出实际剩余体积、保护资产 SHA 复核与保留原因。Mac 实际回执在游戏 `plans/reviews/static-fish-release-20261108/mac-full-cleanup-20261110/`。
