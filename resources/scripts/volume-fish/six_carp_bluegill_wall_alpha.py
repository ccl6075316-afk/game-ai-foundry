"""Read-only current fin wall-alpha probes using actual original author wall IDs."""
import sys,json,hashlib,io
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw
R=Path(__file__).resolve().parents[3];sys.path.insert(0,str(R/'resources/scripts/volume-fish/portable'));from glb_io import read_glb,arrays
G=R/'projects/fishing-2d';q=G/'plans/reviews/six-fish-release-20261104/bluegill';model=G/'game/assets/models/fish/bluegill.glb';author=G/'experiments/three-fish-fin-detail-20261031/bluegill/tail-root-skin-r2/author/tail-donors.validation.json';record=json.loads(author.read_text(encoding='utf8'));d,b=read_glb(model);pr=d['meshes'][0]['primitives'][0];v=arrays(d,b,pr['attributes']['POSITION']);uv=arrays(d,b,pr['attributes']['TEXCOORD_0']);ix=arrays(d,b,pr['indices']);ib=d['bufferViews'][d['images'][0]['bufferView']];image=np.array(Image.open(io.BytesIO(b[ib.get('byteOffset',0):ib.get('byteOffset',0)+ib['byteLength']])).convert('RGBA'));size=np.array(image.shape[1::-1]);rows=[]
for part in d['extras']['geometry_parts']:
 if part['role']!='fin':continue
 name=part['source_node'];r=next(x for x in record['records']if x['name']==name);walls={x['triangle']for x in r['wall_donors']};faces=ix[part['index_start']:part['index_start']+part['index_count']].reshape(-1,3);caps=np.array([f for i,f in enumerate(faces)if i not in walls]);capids=np.unique(caps);probes=[];mismatch=[];ambiguous=[]
 for i in sorted(walls):
  tri=faces[i];donors=[]
  for k in tri:
   candidates=capids[np.max(abs(v[capids]-v[k]),axis=1)<=2e-6];options=uv[candidates]
   if not len(candidates):ambiguous.append({'face':i,'vertex':int(k),'reason':'no same-position cap endpoint'});break
   assert np.max(abs(options-options[0]))<1e-6,(name,i,k,'ambiguous cap UV');donors.append(options[0])
  if len(donors)!=3:continue
  for bw in [(1/3,1/3,1/3),(.6,.2,.2),(.2,.6,.2),(.2,.2,.6)]:
   a=np.clip(np.floor(np.array(bw)@uv[tri]*size).astype(int),0,size-1);c=np.clip(np.floor(np.array(bw)@donors*size).astype(int),0,size-1);wa=int(image[a[1],a[0],3]);ca=int(image[c[1],c[0],3]);entry={'face':i,'barycentric':list(bw),'wall_atlas_xy':a.tolist(),'cap_atlas_xy':c.tolist(),'wall_alpha':wa,'cap_alpha':ca,'point_native':(np.array(bw)@v[tri]).tolist()};probes.append(entry)
   if wa>=128 and ca<128:mismatch.append(entry)
 rows.append({'name':name,'original_wall_triangles':len(walls),'actual_cap_triangles':len(caps),'ambiguous':ambiguous,'actual_four_probes':probes,'opaque_wall_over_transparent_cap':mismatch})
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();out={'ok':all(not x['ambiguous']for x in rows),'kind':'read_only_current_fin_wall_alpha_vs_adjacent_cap','species':'bluegill','model_sha256':sha(model),'original_author_wall_inventory':{'path':str(author),'sha256':sha(author)},'mapping':'Original author lists exact closing triangles, retained current indices/UV identical. Current wall duplicates matched against actual non-wall cap endpoints within2e-6 native; no inferred anatomy or source classification from donor UV.','fins':rows,'scope':'Four actual alpha probes per original wall; numerical mismatch is diagnostic only. Natural fin rim/stripes and hidden root walls must be distinguished by actual same-model end/side/oblique texture views before any repair.'};(q/'wall-alpha.validation.json').write_text(json.dumps(out,indent=2)+'\n',encoding='utf8');print([(x['name'],len(x['ambiguous']),len(x['opaque_wall_over_transparent_cap']))for x in rows])
