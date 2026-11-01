"""Freeze a source-driven Bluegill low-poly trial; never overwrite installed fish."""
import copy,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'projects/fishing-2d/experiments/bluegill-portable-trial-20261030'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text(encoding='utf8'))
def write(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
assert OUT.resolve().is_relative_to(ROOT/'projects/fishing-2d/experiments')
assert not OUT.exists(),'Fresh trial required'
accepted=ROOT/'projects/fishing-2d/experiments/blender-fish/models/bluegill/073b.handoff.json'
h=read(accepted);source=Path(h['source_image']);profile_path=ROOT/'resources/volume-fish/bluegill-073b.profile.json'
assert h['style_visual_review']=='accepted' and h['source_review']['status']=='accepted'
assert sha(source)==h['source']['sha256']
profile=copy.deepcopy(read(profile_path))
positions=sorted(set([r[0]for r in profile['body']['sections']]+[0.93,0.96,0.982,0.992]))
profile['body'].update(rings=len(positions),radial=12,ring_positions=positions)
profile['oral_jaws']['lip_bevel']=0
for fin in profile['fins']:
    fin['interior_grid']=[2,1]
    fin['root_attachment']['baseline_spacing']=0.02
profile['native_fin_cutouts']=True
profile['notes'].append('2026-10-30 isolated B/portable pilot: direct nonuniform reference cage, original species landmarks/fin contours, no old body mesh or decimation. Transverse widths are inherited artistic hypotheses, not biological measurements. Whole fish preferred1500/hard2000; source skin/fin volume/root/077/head/visual remain unaccepted until tested.')
new_profile=ROOT/'resources/volume-fish/bluegill-reference-cage-20261030.profile.json'
assert not new_profile.exists()
write(new_profile,profile)
OUT.mkdir()
write(OUT/'manifest.json',{'kind':'fish_portable_next_species_trial','species':'bluegill','status':'pending','next_action':'run','method':'New image-driven body cage and independent native fin contours; no old-body simplification. Final static source/export/parts/view/evidence use portable tools.','source':{'path':str(source.relative_to(ROOT)),'sha256':sha(source)},'source_acceptance':{'path':str(accepted.relative_to(ROOT)),'sha256':sha(accepted)},'profile':{'path':str(new_profile.relative_to(ROOT)),'sha256':sha(new_profile)},'baseline_installed_model_sha256':sha(ROOT/'projects/fishing-2d/game/assets/models/fish/bluegill.glb'),'budget':{'preferred_triangles':1500,'hard_triangles':2000},'trial_stages':{'source_gate':'accepted existing073b; workflow context/validate checked','construction':'pending','single_material_source':'pending','cold_reexport':'pending','actual_import':'pending','visual':'pending','full_physical':'not_run'},'unknown':['Exact biological transverse head/body widths and tissue thickness','Unseen skin and new fin surface quality'],'user_visual_acceptance':False,'canonical_bluegill_installation':False})
print(json.dumps({'ok':True,'output':str(OUT),'profile':str(new_profile),'rings':len(positions),'radial':16}))
