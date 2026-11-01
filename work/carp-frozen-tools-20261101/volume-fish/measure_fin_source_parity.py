"""Cold source export diagnostic for finite fin geometry/UV/skin/NORMAL, material bytes and clips.
Always saves actual deviations; this tool never modifies the input blend or GLB.
"""
import argparse,bpy,hashlib,json,math,sys
from pathlib import Path
from itertools import permutations
sys.path.insert(0,str(Path(__file__).resolve().parent))
from patch_existing_fin_meshes import read
from repair_fin_clearance import values
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--model',type=Path,required=True);p.add_argument('--blend',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--supported-export',action='store_true');p.add_argument('--existing-export',type=Path);p.add_argument('--export-proof',type=Path);a=p.parse_args(sys.argv[sys.argv.index('--')+1:]);a.output=a.output.resolve();input_paths={a.model.resolve(),a.blend.resolve()}|({a.existing_export.resolve()}if a.existing_export else set())|({a.export_proof.resolve()}if a.export_proof else set());assert a.output not in input_paths,'Diagnostic output must not overwrite an input';a.output.parent.mkdir(parents=True,exist_ok=True);temp=a.existing_export.resolve()if a.existing_export else a.output.with_suffix('.glb');sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();mh,sh=sha(a.model),sha(a.blend);
if a.existing_export:
 assert a.export_proof;proof=json.loads(a.export_proof.read_text());assert proof['model_sha256']==mh and proof['blend_sha256']==sh and proof['reexport_sha256']==sha(temp),'Stale existing actual export'
else:
 assert temp.resolve()not in input_paths and not temp.exists();bpy.ops.wm.open_mainfile(filepath=str(a.blend.resolve()))
 if a.supported_export:
  from export_source_with_frozen_normals import export_guarded
  export_proof=export_guarded(temp)
 else:bpy.ops.export_scene.gltf(filepath=str(temp),export_format='GLB',export_animations=True,export_yup=True,export_skins=True)
def get(path):
 d,b=read(path);fins={};bindings={}
 for n in d['nodes']:
  if 'mesh'not in n:continue
  name=n.get('name','');bindings[name]=[d['materials'][q['material']]['name']for q in d['meshes'][n['mesh']]['primitives']]
  if name not in ['Dorsal','Anal','Caudal','Pectoral_left','Pectoral_right','Pelvic_left','Pelvic_right']:continue
  jn=[d['nodes'][j]['name']for j in d['skins'][n['skin']]['joints']];tri=[]
  for pr in d['meshes'][n['mesh']]['primitives']:
   at={k:values(d,b,v)for k,v in pr['attributes'].items()};ids=[q[0]for q in values(d,b,pr['indices'])]
   for k in range(0,len(ids),3):tri.append([(at['POSITION'][i],at['TEXCOORD_0'][i],{jn[j]:w for j,w in zip(at['JOINTS_0'][i],at['WEIGHTS_0'][i])if w>1e-7},at['NORMAL'][i])for i in ids[k:k+3]])
  fins[name]=tri
 images={}
 for m in d['materials']:
  t=m.get('pbrMetallicRoughness',{}).get('baseColorTexture')
  if not t:continue
  im=d['images'][d['textures'][t['index']]['source']];view=d['bufferViews'][im['bufferView']];raw=bytes(b[view.get('byteOffset',0):view.get('byteOffset',0)+view['byteLength']]);images[m['name']]={'sha256':hashlib.sha256(raw).hexdigest(),'bytes':raw}
 clips={}
 for anim in d.get('animations',[]):
  channels={}
  for c in anim['channels']:
   s=anim['samplers'][c['sampler']];key=d['nodes'][c['target']['node']]['name']+'/'+c['target']['path'];channels[key]={'times':values(d,b,s['input']),'values':values(d,b,s['output']),'interpolation':s.get('interpolation','LINEAR')}
  clips[anim.get('name','unnamed')]=channels
 return fins,images,clips,bindings
old,oi,oc,ob=get(a.model);new,ni,nc,nb=get(temp)
def error(x,y):
 if set(x[2])!=set(y[2]):return float('inf')
 return max([abs(u-v)for u,v in zip(x[0]+x[1],y[0]+y[1])]+[abs(x[2][k]-y[2][k])for k in x[2]])
normals={};geometry={}
for name,tri in old.items():
 remaining=list(new[name]);maximum=angle=0.;ge=0.;assert len(tri)==len(remaining)
 for row in tri:
  match=None
  for i,other in enumerate(remaining):
   for order in [other[k:]+other[:k]for k in range(3)]:
    err=max(error(x,y)for x,y in zip(row,order))
    if err<=1e-6:
     normal_error=max(abs(u-v)for x,y in zip(row,order)for u,v in zip(x[3],y[3]))
     if match is None or normal_error<match[3]:match=(i,order,err,normal_error)
   if match and match[3]<=1e-6:break
  assert match,(name,'Geometry/UV/skin mismatch');i,order,err,_=match;remaining.pop(i);ge=max(ge,err)
  for x,y in zip(row,order):
   maximum=max(maximum,max(abs(u-v)for u,v in zip(x[3],y[3])));dot=sum(u*v for u,v in zip(x[3],y[3]));den=math.sqrt(sum(u*u for u in x[3])*sum(v*v for v in y[3]));angle=max(angle,math.degrees(math.acos(max(-1,min(1,dot/den)))))
 normals[name]={'max_component_error':maximum,'max_angle_degrees':angle,'passes_historical_0.001':maximum<=.001,'passes_1e_6':maximum<=1e-6};geometry[name]={'triangles':len(tri),'max_component_error':ge}
image_report={}
for name in set(oi)|set(ni):
 same=name in oi and name in ni and oi[name]['sha256']==ni[name]['sha256'];image_report[name]={'embedded_bytes_equal':same,'model_sha256':oi.get(name,{}).get('sha256'),'source_export_sha256':ni.get(name,{}).get('sha256')}
 if not same and name in oi and name in ni:
  index=len(image_report);paths=[]
  for label,lookup in [('model',oi),('source',ni)]:path=a.output.parent/(a.output.stem+f'-image-{index}-{label}.png');path.write_bytes(lookup[name]['bytes']);paths.append(str(path))
  image_report[name]['decode_compare_paths']=paths
clip_report={}
for name in set(oc)|set(nc):
 ok=name in oc and name in nc and set(oc[name])==set(nc[name]);max_value=max_time=0.;issues=[]
 if ok:
  for key in oc[name]:
   x,y=oc[name][key],nc[name][key]
   if len(x['times'])!=len(y['times'])or len(x['values'])!=len(y['values'])or x['interpolation']!=y['interpolation']:ok=False;issues.append(key+' count/interpolation');continue
   max_time=max(max_time,max(abs(u[0]-v[0])for u,v in zip(x['times'],y['times'])));max_value=max(max_value,max(abs(u-v)for aa,bb in zip(x['values'],y['values'])for u,v in zip(aa,bb)))
 else:issues.append('clip/channel inventory')
 clip_report[name]={'same_channel_sampling':ok,'max_time_error':max_time,'max_value_component_error':max_value,'passes_1e_6':ok and max_time<=1e-6 and max_value<=1e-6,'issues':issues}
assert sha(a.model)==mh and sha(a.blend)==sh
r={'ok':ob==nb and all(v['passes_historical_0.001']for v in normals.values())and all(v['embedded_bytes_equal']for v in image_report.values())and all(v['passes_1e_6']for v in clip_report.values()),'model_sha256':mh,'blend_sha256':sh,'verifier_sha256':sha(__file__),'reexport_model':str(temp),'reexport_sha256':sha(temp),'fin_normals':normals,'fin_geometry_UV_skin':geometry,'winding_preserved':True,'materials':image_report,'mesh_material_bindings_equal':ob==nb,'clips':clip_report,'inputs_unchanged':True,'supported_float_normal_export':a.supported_export,'export_procedure':'Guarded source FLOAT_VECTOR corner attribute exported with Blender; only NORMAL accessor binding uses its own emitted attribute stream'if a.supported_export else'Ordinary Blender File Export','scope':'Actual source cold re-export comparison. Normals measured per matched triangle loop after POSITION/UV/joint-name skin correspondence. Embedded image byte equality proves pixel identity; differing compressed images require decoded pixel check. No source or validated model changed.'};a.output.write_text(json.dumps(r,indent=2));print(json.dumps({k:r[k]for k in ['ok','fin_normals','mesh_material_bindings_equal','clips']}))
