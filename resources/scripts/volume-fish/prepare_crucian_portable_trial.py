"""Species-specific recipe; reusable execution is in portable/, no installed writes."""
import copy,json,hashlib
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[3];OUT=ROOT/'projects/fishing-2d/experiments/crucian-portable-trial-20261030'
OLD=ROOT/'projects/fishing-2d/experiments/blender-fish/models/crucian'
def read(p):return json.loads(p.read_text(encoding='utf8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,d):p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
assert not OUT.exists();OUT.mkdir()
p=copy.deepcopy(read(ROOT/'resources/volume-fish/crucian-082g.profile.json'));h=read(OLD/'082g.handoff.json')
source=OLD/'082-source-inputs/char_crucian_082_nobg.png';assert sha(source)==h['source']['sha256']
profile=ROOT/'resources/volume-fish/crucian-reference-cage-20261030.profile.json';assert not profile.exists()
head=next(x for x in read(ROOT/'resources/volume-fish/snout-083b.plan.json')['items']if x['species']=='crucian');envelope=head['target_half_width_envelope']
sections=p['body']['sections'];positions=sorted({s[0]for s in sections}|{r[0]for r in envelope}|{u for u,v in p['oral_jaws']['slit_path']})
new=[]
for u in positions:
    row=[u]+[float(np.interp(u,[s[0]for s in sections],[s[i]for s in sections]))for i in [1,2,3]]
    if u>=envelope[0][0]:row[3]=float(np.interp(u,[s[0]for s in envelope],[s[1]for s in envelope]))
    new.append(row)
p['body'].update(sections=new,rings=len(positions),ring_positions=positions,radial=12);p['oral_jaws']['lip_bevel']=0;p['native_fin_cutouts']=True
for fin in p['fins']:
    fin['interior_grid']=[2,1];fin['root_attachment']['baseline_spacing']=.02
p['notes'].append('2026-10-30 second portable trial after bluegill consolidation: source-driven sparse cage, original crucian fins/roots and mouth; own083b transverse target integrated as an artistic hypothesis. No old-body decimation, no bluegill shape or clearance values. All appearance/physical acceptance pending.')
write(profile,p)
reference=ROOT/p['style']['reference_image'].removeprefix('repo://')
archive={'accepted_handoff':str(OLD/'082g.handoff.json'),'profile':str(ROOT/'resources/volume-fish/crucian-082g.profile.json'),'blend':str(OLD/'082g.handoff-artifacts/fish.blend'),'glb':str(OLD/'082g.handoff-artifacts/fish.glb'),'source':str(source),'reference':str(reference),'review_images':{k:str(OLD/'082g.handoff-artifacts/review'/({'style_comparison':'style-comparison.png','master_comparison':'master-comparison.png'}.get(k,k+'.png')))for k in h['style_review']['hashes']['review_images']}}
write(OUT/'archive-inputs.json',archive)
write(OUT/'manifest.json',{'kind':'fish_portable_second_trial','species':'crucian','status':'pending','next_action':'run','source_sha256':sha(source),'accepted_source_receipt_sha256':sha(OLD/'082g.handoff.json'),'profile_sha256':sha(profile),'installed_baseline_sha256':sha(ROOT/'projects/fishing-2d/game/assets/models/fish/crucian.glb'),'budget':{'preferred_triangles':1500,'hard_triangles':2000},'accepted_archive_scope':'Existing historical source/style/model review verified by volume replan. Missing upstream raw is explicitly historical, not reconstructed or re-generated.','user_acceptance':False,'installed':False})
print(json.dumps({'ok':True,'rings':len(positions),'radial':12,'profile':str(profile)}))
