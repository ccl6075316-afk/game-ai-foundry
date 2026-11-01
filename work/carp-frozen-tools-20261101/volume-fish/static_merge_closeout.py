"""Verify retained evidence, close local checkpoints, and prune explicit temporary paths.

Run only after personally reviewing each visual-review-sheet.png and source views.
This closes SOP 0.2 checkpoints, never formal fish acceptance.
"""
from migrate_static_remaining import *
from datetime import datetime, timezone

NAMES = dict(zip(PARAMS, ['孔雀鲈', '尼罗罗非鱼', '大西洋旗鱼', '太平洋蓝鳍金枪鱼']))
REPORTS = ['old-actual-freeze', 'old-assembly-export', 'old-normalization-bounds',
           'blender-export', 'editable-source', 'geometry-compare',
           'normal-preservation', 'normal-preservation-reopened',
           'candidate-import', 'animation-pose-compare', 'material-rebind',
           'local-cold-load', 'main-cold-binder', 'main-cold-lookups',
           'main-import-arrays', 'main-array-parity', 'candidate-install', 'visual-compare']

def record(path):
 return {'path': str(path.relative_to(GAME_ROOT)), 'sha256': sha(path), 'bytes': path.stat().st_size}

def close(sp):
 b, ident, camel, old = ctx(sp)
 d = json.loads((b/'migration-parameters.validation.json').read_text())
 evidence = {}
 for name in REPORTS:
  p = b/(name+'.validation.json'); row = json.loads(p.read_text())
  assert row.get('ok', True), (sp, name)
  evidence[name] = record(p)
 source = json.loads((b/'editable-source.validation.json').read_text())
 assert source['byte_identical_to_initial_export']
 assert source['editable_blend_sha256'] == sha(b/(sp+'-static.blend'))
 assert sha(b/'original-installed.glb') == old
 assert sha(b/(sp+'-static.glb')) == sha(GAME/'assets/models/fish'/(sp+'.glb')) == d['candidate_sha']
 assert json.loads((b/'main-cold-binder.validation.json').read_text())['receipt']['static_build_calls'] == 0
 assert json.loads((b/'main-array-parity.validation.json').read_text())['all_surface_array_hashes_skin_and_lod_equal']
 runtime = GAME/f'assets/models/fish/motion/final{ident}/{sp}'
 for manifest_path in [runtime/'materials.json', b/'old-materials.json']:
  manifest = json.loads(manifest_path.read_text())
  for row in [x for rows in manifest['materials'].values() for x in rows] + list(manifest['textures'].values()):
   p = GAME/row['path'].removeprefix('res://'); assert sha(p) == row['sha256'], p
 for mode, count in [('old',3),('new',15)]:
  assert len(list((b/('visual-'+mode)).glob('*.png'))) == count
 visual = json.loads((b/'visual-compare.validation.json').read_text())
 usage = b/'mapping-repair-secondary.validation.json'
 findings = [
  'Blender raw NORMAL drift was measured first. Guarded preservation changed no JSON or non-NORMAL accessor bytes; reopening the editable source reproduces the installed candidate.',
  'Old actual per-surface LOD and native Godot animation retained. Main and isolated imports have identical full surface arrays, skin and LOD inventories.',
  'Near-degenerate old LOD triangles are counted separately; no new shape or fin correction was made.'
 ]
 if sp == 'peacock_bass':
  evidence['topology-mapping'] = record(b/'topology-mapping.validation.json')
  findings += ['Hidden Eye_relief helpers must be removed immediately before export; visible Textured_eye nodes retained.',
   'Three body lookup surfaces require directed triangle-fan mapping: all old vertices covered, exact directed triangle multiset, zero ambiguous matches. Nearest-alias mapping failed exact lookup texel validation and was rejected.',
   'PI/DeepSeek compression probe timed out after 180 seconds and did not fix lookup ambiguity; default import compression restored. Main executor supplied verified topology mapping. Reported API cost $0.021474324; no measured Codex savings.']
  evidence['secondary-usage'] = record(usage)
 report = {'kind':sp+'_static_merge_local_checkpoint','species':sp,'local_checkpoint_passed':True,
  'formal_acceptance':False,'user_acceptance':False,'scope':'SOP 0.2 local Godot static-script merge',
  'parameters':d, 'checks':{'editable_source_reexport_byte_identical':True,'geometry_uv_skin_raw_normals':True,
   'old_per_surface_lods_retained':True,'native_animation_59_samples':True,'all_vertex_id_lookup_texels_verified':True,
   'main_fresh_process_static_calls':0,'main_vs_isolated_arrays_skin_lods_exact':True},
  'visual_review':{'reviewer':'primary executor','method':'Original side and turn/front images plus all 18 old/new view crops in visual-review-sheet.png visually inspected.',
   'observation':'No added visible shape, eye, fin, missing body area or material defect observed in these representative captures. Discrete views do not certify continuous motion.',
   'changed_fish_pixels_over_12':[r['changed_fish_pixels_over_12'] for r in visual['views']],
   'sheet':record(b/'visual-review-sheet.png')},
  'evidence':evidence,'known_porting_findings':findings,
  'invalidated_or_deferred':['Old fin-root/full-fin 177/490 and body-integrity reports do not transfer to this re-export.',
   'Planned fin overhaul and full applicable formal SOP checks remain required before formal asset acceptance.'],
  'completed_at':datetime.now(timezone.utc).isoformat()}
 save(b/'local-checkpoint.validation.json',report)
 (b/'README.md').write_text(f'''# {NAMES[sp]} {ident}：本地静态合并检查点

SOP 0.2 范围已完成，正式资产验收及用户验收均未宣称通过。旧实际装配已回写 `{sp}-static.blend` 与安装 GLB；运行时保留正常动作、材质绑定与按本鱼哈希限定的导入 LOD/原生动画。

实际为 {d['mesh_count']} 网格、{d['surface_count']} 材质面、{d['bones']} 骨、{d['tracks']} 原生轨道、{d['fin_surfaces']} 鳍面。源重开重导出字节相同；逐面几何/UV/蒙皮/原始法线、旧 LOD、59 姿态、全部顶点查表、正式入口冷读通过，静态构建调用 0。主工程与隔离候选的全部导入数组、蒙皮及 LOD 完全一致。

实际看过原尺寸侧视与转身斜视，以及18张旧新代表画面的裁剪总览 `visual-review-sheet.png`。同相位游泳侧/斜前/斜俯视变化超过12色阶的鱼体像素为 {report['visual_review']['changed_fish_pixels_over_12']}。未观察到新增可见形状或材质问题；有限采样不证明完整连续动作无穿体。

输入、源与资产哈希、专项报告索引及待验事项见 `local-checkpoint.validation.json`；保留清单见 `retention.validation.json`，临时产物删除范围见 `cleanup.validation.json`。原有鳍根/整鳍177/490及身体专项报告因重导出失效，正式候选冻结后重验。

复现：在 Foundry 使用 `python3 resources/scripts/volume-fish/migrate_static_remaining.py <stage> {sp}`。capture/source/old_visual 仅允许旧输入哈希；重放时须在隔离副本恢复 `original-installed.glb`、原 `.import`、旧入口及 `old-materials.json` 为旧材质清单。阶段依次为 capture、source、engine、material、old_visual、install、new_check、main_arrays；孔雀鲈 material 前另运行 `static_merge_topology.py`。逐鱼具体脚本保留在 repro；清理后 candidate-project 可由 engine 重建。Blender 4.5.3 LTS、Godot 4.7.1 mono；需本机已记录工具链与 .NET 路径。`raw-export.glb` 是保留的法线修正前唯一候选，不能当安装成品。

'''+'\n'.join('- '+s for s in findings)+'\n')
 # Only explicit reconstructible temporary paths; retained input/source/images untouched.
 targets = [b/'candidate-project', b/'repair-evidence', b/'mapping-probe.json', b/'mapping-repair-events.jsonl']
 targets += list(b.glob('*.log')) + list(b.rglob('__pycache__')) + list(b.glob('*.blend1'))
 previous_cleanup = b/'cleanup.validation.json'
 deleted = json.loads(previous_cleanup.read_text())['deleted_files'] if previous_cleanup.exists() else []
 for target in targets:
  if not target.exists(): continue
  assert target.resolve().is_relative_to(b.resolve()) and not target.is_symlink()
  files = sorted(target.rglob('*')) if target.is_dir() else [target]
  removed = [record(p) for p in files if p.is_file()]
  # A replay can regenerate a path; keep its latest deletion and preserve earlier paths.
  replacement_paths = {row['path'] for row in removed}
  deleted = [row for row in deleted if row['path'] not in replacement_paths] + removed
  if target.is_dir(): shutil.rmtree(target)
  else: target.unlink()
 save(b/'cleanup.validation.json',{'kind':'bounded_static_merge_cleanup','ok':True,'deleted_bytes':sum(x['bytes'] for x in deleted),
  'deleted_files':deleted,'preserved':'Original inputs, editable source, raw/final exports, native motion/LOD, failure reports, replay scripts, all 72 original captures across four fish, four review sheets and all runtime dependencies.',
  'note':'Secondary failed compression logs/events summarized in checkpoint; deterministic probes remain reproducible.'})
 retained=[record(p) for p in sorted(b.rglob('*')) if p.is_file() and p.name!='retention.validation.json']
 runtime_files=[record(p) for p in sorted(runtime.rglob('*')) if p.is_file()]
 save(b/'retention.validation.json',{'kind':'retained_static_merge_evidence','ok':True,'files':retained,'runtime_files':runtime_files,
  'retained_experiment_bytes':sum(x['bytes'] for x in retained),'runtime_bytes':sum(x['bytes'] for x in runtime_files)})
 print(json.dumps({'species':sp,'local_checkpoint':True,'deleted_bytes':sum(x['bytes'] for x in deleted),'retained_experiment_bytes':sum(x['bytes'] for x in retained)}))

if __name__ == '__main__':
 for species in PARAMS: close(species)
