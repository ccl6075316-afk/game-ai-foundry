"""Declare actual Bluegill parts and cameras for the portable pilot."""
import hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'projects/fishing-2d/experiments/bluegill-portable-trial-20261030'
sys.path.insert(0,str(Path(__file__).parent/'portable'))
from glb_io import read_glb as read, arrays as values
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
report=json.loads((OUT/'packing-unique/packing.validation.json').read_text(encoding='utf8'))
assert report['triangles']<=2000
parts=[]
for row in report['parts']:
    role='body_skin' if row['node']=='Closed_body' and row['surface']==0 else 'mouth' if row['node']=='Closed_body' else 'fin'
    parts.append({'name':row['node']+'_'+str(row['surface']),'logical_name':row['node'],'role':role,'source_node':row['node'],'source_surface':row['surface']})
profile=json.loads((ROOT/'projects/fishing-2d/game/assets/models/fish/motion/motion.json').read_text(encoding='utf8'))['profiles']['bluegill']
profile_path=ROOT/'resources/volume-fish/bluegill-reference-cage-native-motion-20261030.json'
runtime=ROOT/'projects/fishing-2d/game/scripts/aquarium/FoundryFishMotion.gd'
doc,binary=read(OUT/'packing-unique/merged-mask.glb')
assert len(doc['animations'])==1
clip=doc['animations'][0]['name']
profile['base_clip']=clip
joint_names={doc['nodes'][i]['name']for i in doc['skins'][0]['joints']}
constraints=profile.get('fin_motion_constraints',{})
profile['fin_motion_constraints']={(k if k in joint_names else k.removesuffix('_2')):v for k,v in constraints.items()}
assert set(profile['fin_motion_constraints'])<=joint_names
write(profile_path,profile)
positions=values(doc,binary,doc['meshes'][0]['primitives'][0]['attributes']['POSITION'])
scale=float(.191/(max(v[0]for v in positions)-min(v[0]for v in positions)))
plan={'species':'bluegill','game':'projects/fishing-2d/game','parts':parts,'motion':{'api':'foundry_motion_v1','runtime':{'path':str(runtime.relative_to(ROOT)),'sha256':sha(runtime)},'profile':{'path':str(profile_path.relative_to(ROOT)),'sha256':sha(profile_path)},'action':'Swim'},'viewer':{'model_scale':scale,'native_clip':clip,'focuses':{'head':{'mode':'bbox_relative','position':[.88,.47,.5]}},'captures':[{'name':'side','yaw_degrees':0,'pitch_degrees':0,'time_seconds':0},{'name':'oblique','yaw_degrees':35,'pitch_degrees':15,'time_seconds':0},{'name':'front','yaw_degrees':90,'pitch_degrees':0,'time_seconds':0},{'name':'top','yaw_degrees':0,'pitch_degrees':85,'time_seconds':0},{'name':'reverse','yaw_degrees':180,'pitch_degrees':0,'time_seconds':0},{'name':'bottom','yaw_degrees':0,'pitch_degrees':-85,'time_seconds':0}]}}
write(OUT/'parts-and-view.json',plan)
print(json.dumps({'ok':True,'parts':len(parts),'triangles':report['triangles'],'scale':scale}))
