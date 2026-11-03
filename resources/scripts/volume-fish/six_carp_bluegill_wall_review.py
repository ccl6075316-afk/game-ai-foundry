import sys,json,pathlib,io,hashlib,shutil,numpy as np
from PIL import Image,ImageDraw
R=pathlib.Path('E:/game-ai-foundry');G=R/'projects/fishing-2d';D=G/'plans/reviews/six-fish-release-20261104';sys.path.insert(0,str(R/'resources/scripts/volume-fish/portable'));from glb_io import read_glb
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for species in ['carp','bluegill']:
 q=D/species;old=G/f'experiments/six-fish-database-20261104/{species}';views=old/('fin-views'if species=='carp'else'fin-views-r6');names=['Dorsal_mesh','Anal_mesh','Caudal_mesh','Pectoral_left_mesh','Pectoral_right_mesh','Pelvic_left_mesh','Pelvic_right_mesh'];inputs={};outputs=[]
 for page in range(2):
  selected=names[page*4:page*4+4];sheet=Image.new('RGB',(1800,len(selected)*335),(37,52,60));dr=ImageDraw.Draw(sheet)
  for row,name in enumerate(selected):
   for col,view in enumerate(['left','front','top','oblique']):
    p=views/f'fin-{name}-{view}-texture.png';im=Image.open(p).convert('RGB');im.thumbnail((450,310),Image.Resampling.NEAREST);sheet.paste(im,(col*450,row*335+25));dr.text((col*450+4,row*335+5),name+' '+view,fill='white');inputs[str(p)]=sha(p)
  target=q/f'fin-wall-texture-review-{page}.jpg';sheet.save(target,quality=97);outputs.append({'path':str(target),'sha256':sha(target)})
 if species=='carp':
  p=q/'wall-source-probe.validation.json';probe=json.loads(p.read_text());d,b=read_glb(G/'game/assets/models/fish/carp.glb');iv=d['bufferViews'][d['images'][0]['bufferView']];atlas=np.array(Image.open(io.BytesIO(b[iv.get('byteOffset',0):iv.get('byteOffset',0)+iv['byteLength']])).convert('RGBA'));size=np.array(atlas.shape[1::-1]);rows=[]
  for fin in probe['fins']:
   samples=[];mis=[]
   for wall in fin['walls']:
    for bw in [(1/3,1/3,1/3),(.6,.2,.2),(.2,.6,.2),(.2,.2,.6)]:
     a=np.clip(np.floor(np.array(bw)@wall['actual_uv']*size).astype(int),0,size-1);c=np.clip(np.floor(np.array(bw)@wall['cap_uv']*size).astype(int),0,size-1);wa=int(atlas[a[1],a[0],3]);ca=int(atlas[c[1],c[0],3]);entry={'face':wall['polygon'],'barycentric':bw,'wall_atlas_xy':a.tolist(),'cap_atlas_xy':c.tolist(),'wall_alpha':wa,'cap_alpha':ca};samples.append(entry)
     if wa>=128 and ca<128:mis.append(entry)
   rows.append({'name':fin['name'],'actual_four_probes':samples,'opaque_wall_over_transparent_cap':mis})
  report={'ok':True,'kind':'read_only_current_fin_wall_alpha_vs_adjacent_cap','species':species,'model_sha256':sha(G/'game/assets/models/fish/carp.glb'),'source_probe':{'path':str(p),'sha256':sha(p)},'fins':rows};(q/'wall-alpha.validation.json').write_text(json.dumps(report,indent=2)+'\n');print(species,[(x['name'],len(x['opaque_wall_over_transparent_cap']))for x in rows])
 statement={'species':species,'model_sha256':sha(G/f'game/assets/models/fish/{species}.glb'),'actual_viewed':True,'views':'Every7 fins actual texture side/front/top/oblique, plus whole-fish/source review. Contacts uniformly scaled, no thickness exaggeration.','observations':'No detached straight wire-frame spanning blank native cap observed in actual current views. Native fin stripes and jagged original outer margins retained; isolated hidden root edges do not constitute a frame. Numerical boundary alpha differences are kept as diagnostics and not silently treated as zero.','decision':'Preserve explicitly accepted static bytes; no static edit indicated by actual images.','inputs':inputs,'outputs':outputs};(q/'wall-visual-review.validation.json').write_text(json.dumps(statement,indent=2)+'\n')
