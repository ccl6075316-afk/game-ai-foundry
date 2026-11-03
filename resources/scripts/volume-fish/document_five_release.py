"""Document the accepted five-fish release and retire its old pending status."""
import json,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];G=ROOT/'projects/fishing-2d';R=G/'plans/reviews/five-fish-release-20261104'
read=lambda p:json.loads(p.read_text(encoding='utf8'))
def write(p,d):p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
manifest=read(R/'manifest.json');assert manifest['status']=='done';table=[]
for row in manifest['records']:
 s=row['species'];d=R/s;freeze=read(G/f'assets/source/fish/{s}/frozen-static.json')['static'];sop=read(d/'sop.validation.json');data=read(d/'production-data.json');assert sop['ok'] and all(v is True for k,v in data['technical_reuse_basis'].items()if k!='statement')
 table.append(f"| {row['name']} | {s} | {freeze['triangles']} | {freeze['bones']} | `{row['model']['sha256']}` |")
 (d/'HANDOFF.md').write_text(f"# {row['name']}：正式成品，2026-11-04\n\n用户已整鱼接受，授权安装、退役旧实验并提交推送。与罗非鱼R5同类，外形、全部鳍、UV/像素材质、蒙皮及骨架静态数据冻结；默认后续仅改动作，重开静态制作须有明确用户要求。\n\n正式GLB：`game/assets/models/fish/{s}.glb`，SHA256 `{row['model']['sha256']}`。可编辑源：`assets/source/fish/{s}/fish.blend`，SHA256 `{row['source']['sha256']}`。静态指纹在同目录 `frozen-static.json`，来源与参数见 `parameters.json`、`references/` 及 Foundry `resources/volume-fish/{s.replace('_','-')}-final-20261104.json`。\n\n{freeze['triangles']}三角面、{freeze['bones']}骨骼。`sop.validation.json` 全部9阶段通过；`production-data.json` 明确同字节历史专项报告的复用依据，原报告没有改写成新跑。新进程从正式源导出与已接受GLB逐字节一致；实际游戏首次/缓存加载与独立冷读数组、RGBA一致，480动作控制相位和360切换相位骨架差值0，四动作画面对照差异像素0。代表图 `canonical-actions.jpg` 已实际复看。\n\n完整交接、清理统计和复现入口见 [批次交接](../HANDOFF.md)。旧实验路径仅用于历史溯源，以 `../retention-manifest.json` 定位保留原件。资料库游戏美术不是生物实测；近似参考和未确定部位的限制没有因成品接受而消失。\n",encoding='utf8')
old=G/'plans/reviews/five-fish-width-detail-20261031';oldm=read(old/'manifest.json');revision=oldm['database_revision_20261103']
revision.update(status='done',next_action='none',formal_acceptance=True,installed=True,user_acceptance=True,static_frozen=True,completion_scope='five_user_accepted_canonical_final_assets',review_entry=str(ROOT/'resources/scripts/volume-fish/open_five_final.py'),completion_report=str(R/'installation.validation.json'),release_handoff=str(R/'HANDOFF.md'),preflight='Historical inputs and complete facts migrated under final release history/references; retired experiments are not current entries.')
for row in revision['candidates_completed']:
 s=row['species'];current=next(x for x in manifest['records']if x['species']==s);row.update(model=current['model']['path'],sha256=current['model']['sha256'],status='done',next_action='none',installed=True,user_acceptance=True,static_frozen=True,handoff=str(R/s/'HANDOFF.md'))
oldm.update(status='done',next_action='none',formal_acceptance=True,user_acceptance=True,current_release=str(R/'manifest.json'),current_catalog=str(ROOT/'resources/scripts/volume-fish/open_five_final.py'),interactive_catalog=str(ROOT/'resources/scripts/volume-fish/open_five_final.py'));write(old/'manifest.json',oldm)
p=old/'handoff.md';text=p.read_text(encoding='utf8');marker='## 2026-11-04：五鱼接受、正式安装与静态冻结'
if marker not in text:p.write_text(marker+'\n\n用户已整鱼接受虹鳟、褐鳟、大西洋鲑、海鲈、红皇帝鱼；正式GLB及源已安装，默认只改动作。旧实验已按SHA清单退役。当前入口为 `plans/reviews/five-fish-release-20261104/HANDOFF.md` 和 Foundry `resources/volume-fish/final-five-fish-20261104.json`。以下旧路径、未接受或待安装状态仅保留为历史记录，以新入口为准。\n\n'+text,encoding='utf8')
cleanup=read(R/'cleanup-execution.json');supp=read(R/'verification-cleanup.json');total=cleanup['deleted_bytes']+supp['deleted_bytes'];retained=read(R/'retained-size.json')
handoff='''# 五鱼正式成品交接 · 2026-11-04

虹鳟、褐鳟、大西洋鲑、海鲈、红皇帝鱼已获用户整鱼接受，已替换游戏正式角色。用户原话：“非常好，完美，把它们直接归类到跟罗飞鱼一样，就是彻底把它定下来……把它们也导出来，替换游戏里的角色……实验都可以去掉了，这个就可以作为成品了。然后把它提交上去就行了。”

五鱼与罗非鱼R5同类：**静态成品冻结，默认后续只改动作。** 外形、完整鳍、UV/像素材质、蒙皮和骨架静态数据不得在新聊天中自动重做；需要明确用户要求才重开。动作改动按实际影响重新验证全部适用鳍根/鳍面、身体和四动作切换。罗非鱼本次未改，六鱼静态指纹均通过。

## 当前入口与资产

Foundry 索引 `resources/volume-fish/final-five-fish-20261104.json`，逐鱼 `<species-hyphen>-final-20261104.json`；形态参数仍在 `resources/volume-fish/database-revision-20261103/<species>.profile.json`，未跨鱼继承外观验收。

游戏 `game/assets/models/fish/<species>.glb`；源 `assets/source/fish/<species>/fish.blend`，包含当前材质和蒙皮。相邻 `source.png`、`atlas.png`、`body-generated.png` 是原图、图集和生成供体，`validation-source.blend` 仅供原模板坐标验证，不能替换交付源。`frozen-static.json` 独立锁定几何/UV/蒙皮、材质像素及骨架静态数据，动作轨道不在该锁定范围。

| 鱼 | species | 三角面 | 骨骼 | GLB SHA256 |
|---|---|---:|---:|---|
'''+ '\n'.join(table)+'''

## 方法与逐鱼参数

先用本地库可核对的模型与Unity变换审计选择横向包络，再按本鱼原画、嘴和全鳍约束调整。保留库原始SHA、部位对应、长度归一化和未知；库内模型是美术参考，不能称生物实测。红皇帝鱼使用明确记录的相近体型 ShortTailRedSnapper 参考，同种吻型和外观仍独立审核。每鱼完整参数、修正及失败结论在 `<species>/parameters.json`、`references/`、`history/`。海鲈与红皇帝鱼根区蒙皮修正是已接受静态资产的一部分。

通用方法见 Foundry `resources/skills/fish-volume-production/references/five-fish-width-release-lessons-20261101.md`；制作工具在 `resources/scripts/volume-fish/`。此目录 `methods/` 的旧绑定脚本只是历史方法快照，不再进入游戏静态装配链。

## 固化与实际游戏验证

从正式 `fish.blend` 以Blender新进程导出，五鱼GLB均与用户接受的SHA逐字节一致。游戏仅加载完整GLB，旧静态造型、材质补丁、旧动画替换和LOD导入钩子已退役，五鱼导入关闭自动LOD。当前冻结入口对不符SHA的模型明确报错，避免静默落回旧装配。

清理和运行链改动后，逐鱼重新运行实际 `VolumeFishExhibit._add_fish` 首次加载、缓存加载，与独立GLTFDocument冷读比较：所有位置/法线/UV/权重/骨骼/索引和RGBA一致；首次加载材质覆盖0；缓存复制材质句柄，但实际像素和材质属性相同。每鱼480控制相位及360切换相位实际骨架最大差0，四动作GPU对照每对差异像素0。五张 `canonical-actions.jpg` 已实际复看，完整鱼体和鳍在四个代表姿态中保持已接受外观。

逐鱼 `source-cold-export.validation.json`、`canonical-load.validation.json`、`canonical-pixels.validation.json` 是本轮正式路径的新测量。9阶段、54项证据的 `production-review.json` 与 `sop.validation.json` 均通过。历史完整490姿态鳍根/鳍面、072、077GPU、嘴、头型负例和鳍厚专项原报告保留原字节；本轮物理模型、可编辑源、形态配置、动作控制器与参数字节一致，复用依据明列于 `production-data.json`。这些报告不冒充本轮重新执行，也不证明全连续时间。`recheck-fin.plan.json` 仅重定位到正式路径，未来复验要重新运行，不能沿用旧plan SHA的通过。

`retention-manifest.json` 将原路径映射到保留字节及SHA；历史报告内部路径保持原貌，旧路径不是当前依赖。`production-review.json` 的当前证据指向保留后的实际文件，正式候选角色全部绑定当前资产SHA。新进程验证关闭实验静态构建，运行时静态构建调用为0。

## 复现入口

在 Foundry 根目录，用 `.venv/Scripts/python.exe resources/scripts/volume-fish/open_five_final.py --godot <Godot路径>` 打开只读五鱼成品列表，可切换四动作、灰模、侧/正/俯视；`--smoke` 检查列表。`viewer-smoke.validation.json` 的62项技术检查全部通过，此项不代替用户接受。查看器所有输出写入 Foundry `output/five-final-viewer/`。

正式路径复验用 `run_five_final_verification.py --blender <路径> --godot <路径>`，额外输出仅在 `output/five-fish-release-20261104/`，临时GLB和帧需按清单收尾；工具保留最终报告与代表图。交付SOP：`gamefactory.cmd volume sop-check --review projects/fishing-2d/plans/reviews/five-fish-release-20261104/<species>/production-review.json --output <允许的报告路径> --json`。

## 清理与保留

'''+f'''本次删除 **{cleanup['deleted_files']+supp['deleted_files']:,} 文件、{total:,} 字节**。其中旧实验及其重复源、候选、帧、GPU稠密采样、旧模型子目录、退役绑定/导入钩子共 {cleanup['deleted_bytes']:,} 字节，临时正式路径复验产物 {supp['deleted_bytes']:,} 字节。逐文件绝对路径、SHA和大小在 `cleanup-files.json.gz`、`verification-cleanup.json`；原实验删除前逐项核对保留映射与运行引用。没有新建资产压缩包，`.json.gz` 只是小型删除清单。

当前保留资产和记录实际 {retained['total_bytes']:,} 字节（统计时点，包含正式源/GLB、逐鱼来源配置和本目录证据；随后增加的少量交接文字另计）。保留完整数值报告、关键负例源、原画与供体、代表图/视频。原图、库输入和与其他鱼共享的历史归档保留；未因体积删除不明引用资产。Git历史中原已跟踪实验可从父提交恢复，见 `cleanup-plan.json`；新源与唯一必要输入已有明确保留地址。

提交范围为 Foundry 方法/参数/冻结入口和 fishing-2d 正式资产/证据及实验退役；用户要求提交包含两个仓库commit与push，实际提交号在交付消息报告。
'''
(R/'HANDOFF.md').write_text(handoff,encoding='utf8')
print(json.dumps({'ok':True,'documented':5,'deleted_bytes':total,'retained_bytes':retained['total_bytes']}))
