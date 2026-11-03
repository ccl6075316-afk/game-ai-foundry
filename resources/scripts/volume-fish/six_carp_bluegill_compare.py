"""Audit the two assigned current low-poly candidates against local named art bodies."""
import sys,json,hashlib
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2];sys.path[:0]=[str(HERE),str(HERE/'portable')]
from compare_database_fish import read_obj,split_components,normalized,widths
from glb_io import read_glb,arrays
G=ROOT/'projects/fishing-2d';OUT=G/'experiments/six-fish-database-20261104'
read=lambda p:json.loads(p.read_text(encoding='utf8'));sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
c=read(G/'experiments/carp-lowpoly-sop-20261031/manifest.json');b=next(x for x in read(G/'experiments/three-fish-fin-detail-20261031/manifest.json')['species']if x['species']=='bluegill')
for s,base,h,model,blend in [('carp','CommonCarp','48c098bbd5d687edeebd2f0e75d5e8d4e8fc25ba7c7ac66eb1ac7d0cbdba0b27',c['model'],c['editable_source']),('bluegill','Bluegill','49bec05884b3c9ebff4e4e18690707b4c2f480abcf0c6316c779bd3bca7e1d5f',b['model'],b['editable_blend'])]:
 out=OUT/s;out.mkdir(parents=True,exist_ok=True);ref=ROOT/f'resources/fish-database/artifacts/fishing-master-cdn-cnformal1-20261102/mesh-exports/{h}.obj';rv,groups=read_obj(ref);group=base+'_0';components=split_components(rv,groups[group]);rf=components[0][0];rn,rmeta=normalized(rv,rf,[1,2,0],False)
 model=Path(model);blend=Path(blend);d,buf=read_glb(model);pr=d['meshes'][0]['primitives'][0];v=arrays(d,buf,pr['attributes']['POSITION']);idx=arrays(d,buf,pr['indices']).reshape(-1);f=np.concatenate([idx[p['index_start']:p['index_start']+p['index_count']]for p in d['extras']['geometry_parts']if p['role']in ['body_skin','mouth']]).reshape(-1,3);vn,vmeta=normalized(v,f,[0,1,2]);rr=widths(rn,rf);vr=widths(vn,f)
 canvas=Image.new('RGBA',(1500,700),'white');draw=ImageDraw.Draw(canvas)
 for row,(a1,a2,title)in enumerate([(0,2,'TOP / thickness'),(0,1,'SIDE / source silhouette')]):
  top=row*350;draw.text((20,top+10),s+' '+title+'  Orange: library body / Blue: current candidate',fill='black')
  for vv,ff,color in [(rn,rf,(224,151,51,100)),(vn,f,(34,117,190,100))]:
   layer=Image.new('RGBA',canvas.size);ld=ImageDraw.Draw(layer)
   for tri in vv[ff][:,:,[a1,a2]]:ld.polygon([(750+float(p[0])*1200,top+190-float(p[1])*650)for p in tri],fill=color)
   canvas=Image.alpha_composite(canvas,layer)
  draw=ImageDraw.Draw(canvas)
 canvas.convert('RGB').save(out/'library-body-comparison.jpg',quality=95)
 report={'species':s,'reference_kind':'Named third-party game art, not biological measurement; identity/age/sex unverified','reference':{'base_name':base,'path':str(ref.relative_to(ROOT)),'sha256':sha(ref),'group':group,'components':[x[1]for x in components],'normalization':rmeta},'installed':{'path':str(model.relative_to(ROOT)),'sha256':sha(model)},'editable_source':{'path':str(blend),'sha256':sha(blend)},'game_normalization':vmeta,'sections':{'reference':rr,'installed':vr},'limits':['Model body group checked for detached components; project source XY is independent and preserved.','Nose-to-body-peduncle mesh extent is engineering length, not biological SL/TL.','Reference snout topology/end cap does not define target mouth shape.'],'formal_acceptance':False}
 (out/'reference-comparison.validation.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf8');(out/'manifest.json').write_text(json.dumps({'species':s,'status':'running','next_action':'inspect_reference_and_mouth','user_acceptance':False,'installed':False,'baseline_model':report['installed'],'baseline_source':report['editable_source'],'reference':report['reference']},indent=2)+'\n',encoding='utf8')
 print(s, 'reference W/L',max(r['width_over_body_axis']for r in rr),'candidate W/L',max(r['width_over_body_axis']for r in vr),flush=True)
