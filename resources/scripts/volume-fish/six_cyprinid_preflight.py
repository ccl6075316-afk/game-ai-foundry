"""Six-fish batch: inspect crucian/grass actual accepted baseline and local library."""
import json,sys,hashlib
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2];sys.path[:0]=[str(HERE),str(HERE/'portable')]
from compare_database_fish import read_obj,split_components,normalized,widths
from glb_io import read_glb,arrays
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p,d):p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
rows=json.loads((ROOT/'projects/fishing-2d/experiments/three-fish-fin-detail-20261031/manifest.json').read_text(encoding='utf8'))['species']
catalog=[json.loads(x)for x in(ROOT/'resources/fish-database/catalogs/fishing-master-cdn-cnformal1-20261102/collection-status.jsonl').read_text(encoding='utf8').splitlines()]
for s,base in [('crucian','CrucianCarp'),('grass_carp','GrassCarp')]:
 out=ROOT/f'projects/fishing-2d/experiments/six-fish-database-20261104/{s}';out.mkdir(parents=True,exist_ok=True);r=next(x for x in rows if x['species']==s);model=Path(r['model']);blend=Path(r['editable_blend']);assert sha(model)==r['model_sha256']and sha(blend)==r['editable_blend_sha256']
 ref=ROOT/'resources/fish-database'/next(x for x in catalog if x['source_name']==base)['preferred_mesh_exports'][0];rv,groups=read_obj(ref);components={k:split_components(rv,f)for k,f in groups.items()};bodygroup=max(components,key=lambda k:len(components[k][0][0]));rf=components[bodygroup][0][0];partition_note='Largest welded body excludes separate eye components.'
 if s=='grass_carp':
  from scipy.sparse import coo_matrix
  from scipy.sparse.csgraph import connected_components
  ff=groups[bodygroup];edges=np.concatenate([ff[:,[0,1]],ff[:,[1,2]],ff[:,[2,0]]]);_,labels=connected_components(coo_matrix((np.ones(len(edges)),(edges[:,0],edges[:,1])),shape=(len(rv),len(rv))),directed=False);ids=np.unique(labels[ff[:,0]]);counts={int(i):int((labels[ff[:,0]]==i).sum())for i in ids};excluded=[i for i in ids if counts[int(i)]in[96,30,50]];assert len(excluded)==5;rf=ff[~np.isin(labels[ff[:,0]],excluded)];partition_note='Raw-index material islands inspected: exclude left pectoral96 faces and two eye sets30+50 each. Welded positional connectivity incorrectly joins fin/eyes to body at shared contacts; keep actual body, jaw and fin-base caps1950 faces.'
 rn,rmeta=normalized(rv,rf,[1,2,0],False)
 d,b=read_glb(model);pr=d['meshes'][0]['primitives'][0];v=arrays(d,b,pr['attributes']['POSITION']);n=arrays(d,b,pr['attributes']['NORMAL']);idx=arrays(d,b,pr['indices']);bi=np.concatenate([idx[p['index_start']:p['index_start']+p['index_count']]for p in d['extras']['geometry_parts']if p['role']in['body_skin','mouth']]);f=bi.reshape(-1,3);vn,vmeta=normalized(v,f,[0,1,2]);fn=np.cross(v[f[:,1]]-v[f[:,0]],v[f[:,2]]-v[f[:,0]]);dot=(fn*n[f].mean(1)).sum(1);bad=np.flatnonzero(dot<=0)
 record={'species':s,'baseline':{'model':str(model),'sha256':sha(model),'blend':str(blend),'blend_sha256':sha(blend),'candidate_directory':r['candidate']},'reference':{'path':str(ref),'sha256':sha(ref),'base_name':base,'group':bodygroup,'partition_note':partition_note,'body_faces':len(rf),'components':{k:[q[1]for q in cs]for k,cs in components.items()},'normalization':rmeta},'game_normalization':vmeta,'sections':{'reference':widths(rn,rf),'baseline':widths(vn,f)},'normal_failures':{'count':len(bad),'triangles_body_order':bad.tolist(),'minimum_dot':float(dot.min())},'limits':['Third-party game art, identity/age/biological dimensions unverified.','Body/eyes/fin partition independently inspected; do not reuse welded largest-component heuristic without review.','Finite body nose-to-peduncle axis normalized; source XY/style remains project-owned.'],'user_acceptance':False}
 write(out/'database-preflight.validation.json',record)
 im=Image.new('RGB',(1400,650),'white');dr=ImageDraw.Draw(im)
 for j,(axis,title)in enumerate([(2,'TOP'),(1,'SIDE')]):
  dr.text((20,15+j*320),s+' '+title+' orange library / blue current',fill='black')
  for vv,ff,col in [(rn,rf,'#e49b38'),(vn,f,'#2878bd')]:
   for tri in vv[ff][:,:,[0,axis]]:dr.line([(700+float(q[0])*1150,175+j*320-float(q[1])*1150)for q in np.vstack([tri,tri[0]])],fill=col,width=1)
 im.save(out/'database-body-comparison.png')
 write(out/'manifest.json',{'species':s,'status':'running','next_action':'library_visual_review_then_mouth_first_revision','user_acceptance':False,'installed':False,'baseline':record['baseline'],'known_gaps':['Library transverse comparison','Inherited body normal/winding disagreement','Full current production ledger and relevant final gates'],'normal_failures':record['normal_failures']})
 (out/'HANDOFF.md').write_text('# '+s+'：资料库与完整生产补齐\n\n采用三鱼最新已认可局部外观，不采用旧游戏高模。先审库内实际身体/眼/鳍归属及Unity变换、归一化；身体法线负例必须修复。嘴优先，保留原唇域、口腔、眼与完整鳍；二维去鳍底图/真实描边色相/头底鳃纹/像素密度/头身灰模和正式入口冷读均为适用风险。新源/GLB冻结后重新跑完整490/072/077、头嘴正负例、实际鳍厚/尾柄、动作与SOP；旧通过不迁移。\n',encoding='utf8')
 print(json.dumps({'species':s,'body_group':bodygroup,'body_component_faces':len(rf),'normal_bad':len(bad),'reference_width_max':max(x['width_over_body_axis']for x in record['sections']['reference']),'current_width_max':max(x['width_over_body_axis']for x in record['sections']['baseline'])}))
