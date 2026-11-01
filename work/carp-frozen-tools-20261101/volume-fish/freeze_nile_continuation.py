"""Freeze the user's unaccepted pause, documentation and successful replay evidence.

Run only for the explicitly requested 2026-10-30 documentation checkpoint.
"""
from pathlib import Path
import json,hashlib,shutil,subprocess,datetime
repo=Path(__file__).resolve().parents[3];game=repo/'projects/fishing-2d';trial=game/'experiments/nile-dorsal-route-trial';r7=trial/'round7-upper-lip-continuity';r6=trial/'round6-reference-repair';proof=trial/'replay-20261030';workspace=repo/'work/nile-b-replay-20261030'
read=lambda p:json.loads(p.read_text(encoding='utf8'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
def bound(p):return {'path':p.relative_to(repo).as_posix(),'sha256':sha(p),'bytes':p.stat().st_size}
statefile=trial/'next-round-plan.validation.json';state=read(statefile)
assert sha(r7/'B-artifacts/fish.glb')=='ca4241a271584c80c09553a3e21a12a52bfc70e143ad1a91d4deb24f0dc45f09'
assert sha(game/'game/assets/models/fish/nile_tilapia.glb')=='4ee2c552939b682463120b52e40f2f98e996c2dad8f91f9144ab7d6de51ad25a'
case=game/'docs/3d-fish/NILE-B-REBUILD-20261030.md';text=case.read_text(encoding='utf8');marker='<!-- FROZEN_NUMERIC_TABLES -->'
plan=read(r6/'repair.plan.validation.json')
if marker in text:
 lines=['| 环 | u | top | bottom | width |','|---:|---:|---:|---:|---:|']
 for i,row in enumerate(plan['body_sections']):lines.append('| '+str(i)+' | '+' | '.join(format(v,'.17g') for v in row)+' |')
 lines+=['','| 切口u | 下边界Z | 上边界Z |','|---:|---:|---:|']
 for row in plan['cut_profile_native']:lines.append('| '+' | '.join(format(v,'.17g') for v in row)+' |')
 case.write_text(text.replace(marker,'\n'.join(lines)),encoding='utf8')

banner='''> **当前续做入口（2026-10-30暂停）**：用户明确“今天这个没到我的想要的标准”，没有接受当前外观。先读[NILE-B完整重建与续做SOP](NILE-B-REBUILD-20261030.md)，核对续做assets-manifest，再打开当前A(round6)/B(round7)。B1476、A1492三角面；旧轮次下方的“当前/完成/就绪”只描述当轮历史，不能覆盖此断点。今天不再继续造型；下一次由用户恢复。\n\n'''
p=game/'docs/3d-fish/HANDOFF-20261029-NILE-B.md';s=p.read_text(encoding='utf8')
if '**当前续做入口（2026-10-30暂停）**' not in s:
 first,rest=s.split('\n',1);p.write_text(first+'\n\n'+banner+rest,encoding='utf8')
p=game/'docs/3d-fish/species/nile-tilapia.md';s=p.read_text(encoding='utf8')
if '**当前续做入口（2026-10-30暂停）**' not in s:
 first,rest=s.split('\n',1);p.write_text(first+'\n\n'+banner.replace('(NILE-B-REBUILD-20261030.md)','(../NILE-B-REBUILD-20261030.md)')+rest,encoding='utf8')
p=trial/'handoff.md';s=p.read_text(encoding='utf8')
if '**当前续做入口（2026-10-30暂停）**' not in s:p.write_text(banner.replace('(NILE-B-REBUILD-20261030.md)','(../../docs/3d-fish/NILE-B-REBUILD-20261030.md)')+s,encoding='utf8')
p=trial/'round4-ab-textured/README.md';s=p.read_text(encoding='utf8')
warning='> 本页为round4历史对照，非当前断点。当前A在round6、B在round7；用户明确未达标准。先读游戏docs/3d-fish/NILE-B-REBUILD-20261030.md，不运行B.json通用build。\n\n'
if '本页为round4历史对照' not in s:p.write_text(warning+s,encoding='utf8')

route='''\n\n## 低面B重建与无聊天交接\n\n按视频/原图先塑身体再独立鳍，或用户要求明天无重要信息丢失续做时，读[参考图低面鱼完整重建SOP](references/reference-cage-rebuild-sop.md)。罗非鱼当前完整逐步记录位于游戏docs/3d-fish/NILE-B-REBUILD-20261030.md；现有状态以next-round-plan.validation.json和当前review为准。保存来源、完整数值、真实方法、每个严重问题/失败及未接受状态，不把打开/另存现有B称从零重建。必要时只在全新work目录执行隔离复现，核对几何/UV/权重及贴图；模型可复现不代表用户接受或正式验收。\n'''
skill=repo/'resources/skills/fish-volume-production/SKILL.md';s=skill.read_text(encoding='utf8')
if '## 低面B重建与无聊天交接' not in s:skill.write_text(s+route,encoding='utf8')
for base in [repo/'resources/skills/fish-volume-production/references',Path.home()/'.codex/skills/fish-volume-production/references']:
 base.mkdir(parents=True,exist_ok=True)
 if base!=repo/'resources/skills/fish-volume-production/references':shutil.copy2(repo/'resources/skills/fish-volume-production/references/reference-cage-rebuild-sop.md',base/'reference-cage-rebuild-sop.md')
 for name in ['production-sop.md','reference-cage-body.md']:
  p=base/name;s=p.read_text(encoding='utf8');link='\n\n> **需要完整重建与跨日交接时**：另读[参考图低面鱼重建SOP](reference-cage-rebuild-sop.md)，以及游戏 `docs/3d-fish/NILE-B-REBUILD-20261030.md` 的实际逐步案例。它保存材料、控制点/鳍/嘴/补色/导出/验证全链、严重问题和已实测复现命令；罗非鱼当前仍被用户明确认为未达标准，不能视作成功外观模板。\n'
  if '**需要完整重建与跨日交接时**' not in s:
   first,rest=s.split('\n',1);p.write_text(first+'\n'+link+rest,encoding='utf8')
local=Path.home()/'.codex/skills/fish-volume-production/SKILL.md';s=local.read_text(encoding='utf8')
if '## 低面B重建与无聊天交接' not in s:local.write_text(s+route,encoding='utf8')

review=read(r7/'review.validation.json');review.update(status='paused_by_user_for_documented_continuation',user_visual_acceptance='not_accepted_user_explicitly_below_standard',user_pause={'instruction':'今天就先这样；逐步记录，明天能无重要信息丢失继续或从零重建B。今天没到想要的标准。','model_work_paused':True,'documentation_complete':True,'case_sop':case.relative_to(repo).as_posix(),'important_problem_ids':['P%02d'%i for i in range(1,11)]});write(r7/'review.validation.json',review)
sop=read(r7/'sop-review.json');sop['candidate_files']['runtime_manifest']['sha256']=sha(r7/'review.validation.json');write(r7/'sop-review.json',sop)
run=subprocess.run([str(repo/'.venv/Scripts/python.exe'),'cli/gamefactory.py','volume','sop-check','--review',str(r7/'sop-review.json'),'--output',str(r7/'sop-check.validation.json'),'--json'],cwd=repo,capture_output=True,text=True,encoding='utf8');assert not json.loads(run.stdout)['ok']
paramsfile=repo/'resources/volume-fish/nile-tilapia-review-fixes-20261030.json';params=read(paramsfile);params['current_upper_lip']['user_visual_acceptance']='not_accepted_user_explicitly_below_standard';params['continuation_sop']=case.relative_to(repo).as_posix();params['model_work_paused']=True;write(paramsfile,params)
state.update(status='paused',next_action='resume',next_round_status='paused_20261030_below_user_standard_documented',user_visual_acceptance='not_accepted_user_explicitly_below_standard',resume_scope='User resumes later; first read case SOP and verify checkpoint. Do not automatically resume generic B.json/build or old rejected round5.',continuation_sop=case.relative_to(repo).as_posix(),continuation_assets_manifest=(trial/'continuation-20261030.assets-manifest.json').relative_to(repo).as_posix());state['current_AB']['user_visual_acceptance']=state['user_visual_acceptance'];state['plan_document_hashes']={k:sha(repo/k) for k in state['plan_document_hashes']};write(statefile,state)
state['latest_user_authorization']='Pause model changes below requested appearance standard; preserve complete stepwise SOP and independently reproducible B checkpoint for later continuation; commit AND push both repositories and clean local temporary outputs.';write(statefile,state)

# Preserve small actual replay evidence before removing the checked workspace.
proof.mkdir(exist_ok=True)
if workspace.exists():
 replay=read(workspace/'replay.validation.json');assert replay['ok'] and replay['equivalence']['all_geometry_uv_weights_equal'] and replay['equivalence']['all_material_image_pixels_equal']
 logs=[]
 for command in replay['commands']:
  source=repo/command['log'];assert sha(source)==command['log_sha256'];dest=proof/source.name;shutil.copy2(source,dest);logs.append(bound(dest))
 shutil.copy2(workspace/'rebuild-equivalence.validation.json',proof/'rebuild-equivalence.validation.json');shutil.copy2(workspace/'compare_exports.py',proof/'compare_exports.py')
 replay['retained_log_evidence']=logs;replay['temporary_workspace_removed']=True;write(proof/'replay.validation.json',replay)
 files=sorted(p for p in workspace.rglob('*') if p.is_file());rows=[bound(p) for p in files]
 receipt={'ok':False,'status':'prepared','scope':'Only independent successful replay workspace after extracting equivalence and all stage logs; current candidate/source files outside this directory are never deleted.','workspace':workspace.relative_to(repo).as_posix(),'deleted':rows}
 write(proof/'cleanup.validation.json',receipt)
 for p,row in zip(files,rows):assert p.resolve().is_relative_to(workspace.resolve()) and sha(p)==row['sha256'];p.unlink()
 for p in sorted((p for p in workspace.rglob('*') if p.is_dir()),key=lambda x:len(x.parts),reverse=True):p.rmdir()
 workspace.rmdir();receipt.update(ok=True,status='done',deleted_bytes=sum(r['bytes'] for r in rows),retained=[bound(p) for p in proof.iterdir() if p.is_file() and p.name!='cleanup.validation.json']);write(proof/'cleanup.validation.json',receipt)

# Record post-review documentation changes in existing retention receipt.
cleanup=read(r7/'cleanup.validation.json');cleanup['continuation_update']='User explicitly below standard and paused; only records/SOP refreshed, model/texture hashes unchanged.';cleanup['retained']=[bound(p) for p in sorted(r7.rglob('*')) if p.is_file() and p.name not in ['cleanup.validation.json','three-navigation.validation.json']];cleanup['retained_bytes']=sum(r['bytes'] for r in cleanup['retained']);write(r7/'cleanup.validation.json',cleanup)

manifestfile=trial/'continuation-20261030.assets-manifest.json';manifest=read(manifestfile);seed={r['path'] for r in manifest['files'] if r.get('rebuild_seed')};paths={repo/r['path'] for r in manifest['files']}
paths.update(p for d in [trial/'round2',trial/'round3-whole-budget-probe',trial/'round4-ab-textured',trial/'round5-user-review-fixes',trial/'method-reference',r6,r7,proof] for p in d.rglob('*') if p.is_file() and p.name!='three-navigation.validation.json')
paths.add(game/'.gitattributes')
# The actual original material viewer loads this frozen asset directory.
paths.update(p for p in (game/'game/assets/models/fish/motion/final178/nile_tilapia').rglob('*') if p.is_file())
paths.update(p for p in (repo/'resources/scripts/volume-fish').glob('*nile*') if p.is_file())
paths.update([repo/'resources/scripts/volume-fish/reference_fin_cages.py',repo/'resources/scripts/volume-fish/oral_jaws.py',repo/'resources/scripts/volume-fish/LowPolyFishTransport.gd',game/'game/project.godot',game/'game/scripts/aquarium/FinalizedNileTilapia178.gd',game/'game/scripts/aquarium/FoundryFishMotion.gd',game/'game/assets/models/fish/nile_tilapia.glb',game/'experiments/grass-carp-static-merge/repro/vertex_map.gd',repo/'resources/volume-fish/motion/nile_tilapia-082.json',repo/'resources/volume-fish/nile-tilapia-review-fixes-20261030.json',case,game/'docs/3d-fish/HANDOFF-20261029-NILE-B.md',game/'docs/3d-fish/species/nile-tilapia.md',statefile,trial/'handoff.md',skill])
paths.update(p for p in (repo/'resources/skills/fish-volume-production/references').glob('*.md') if p.name in ['production-sop.md','reference-cage-body.md','reference-cage-rebuild-sop.md','source-surface-repair.md','fin-types-thickness-tail.md','fin-source-shape.md','mouth-execution.md','final-asset-export.md'])
text_suffixes={'.py','.gd','.json','.md','.tres','.gdshader','.godot'};rows=[]
for p in sorted(paths):
 assert p.is_file(),str(p)
 row=bound(p);row['rebuild_seed']=row['path'] in seed
 if p.suffix in text_suffixes:row['lf_sha256']=hashlib.sha256(p.read_bytes().replace(b'\r\n',b'\n')).hexdigest()
 rows.append(row)
manifest.update(captured_at=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat(),files=rows,user_visual_acceptance='not_accepted_user_explicitly_below_standard',model_work_paused=True,case_sop=case.relative_to(repo).as_posix(),replay_report=(proof/'replay.validation.json').relative_to(repo).as_posix(),scope='Hash-bound continuation inputs/code/candidates/evidence; next-round-plan and current review remain authoritative state. Not an appearance approval.',volatile_excluded=['round7-upper-lip-continuity/three-navigation.validation.json: live user camera navigation only'])
write(manifestfile,manifest)
print(json.dumps({'ok':True,'files':len(rows),'seed_files':len(seed),'replay_proof':str(proof.relative_to(repo)),'user_visual_acceptance':manifest['user_visual_acceptance'],'model_bytes_unchanged':True}))
