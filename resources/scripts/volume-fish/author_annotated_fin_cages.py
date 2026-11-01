"""Build sparse independent fin cages from reviewed native source domains.

Uses the current newly authored fish only to transfer its source-to-3D placement
and skin. Every native source coordinate persists for subsequent full-root and
thickness work. It does not claim anatomy or physical validation.
"""
import argparse,hashlib,json,sys
from pathlib import Path
import bpy,bmesh,numpy as np
from mathutils import Vector
from mathutils.geometry import delaunay_2d_cdt
ROOT=Path(__file__).resolve().parents[3]
sys.path[:0]=[str(ROOT/'cli'),str(Path(__file__).parent/'portable')]
from volume_shape import fin_baseline_parameter
from source_snapshot import rig_action_snapshot
from fish_budget import check_triangle_budget

def read(p):return json.loads(Path(p).read_text(encoding='utf8'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def mesh_snapshot(ob):
 return repr(([(tuple(v.co),[(g.group,g.weight)for g in v.groups])for v in ob.data.vertices],[tuple(f.vertices)for f in ob.data.polygons],[[tuple(u.uv)for u in l.data]for l in ob.data.uv_layers]))

def layer_samplers(ob,source_crop):
 ob.data.calc_loop_triangles();vertices=np.array([v.co[:]for v in ob.data.vertices]);uv=[None]*len(vertices)
 for loop,item in zip(ob.data.loops,ob.data.uv_layers.active.data):uv[loop.vertex_index]=tuple(item.uv)
 image=next(n.image for n in ob.data.materials[0].node_tree.nodes if n.type=='TEX_IMAGE')
 require_size=[source_crop[2]-source_crop[0],source_crop[3]-source_crop[1]];assert list(image.size)==require_size
 q=np.array(uv)*[require_size[0],-require_size[1]]+[source_crop[0],source_crop[3]]
 faces=np.array([tuple(t.vertices)for t in ob.data.loop_triangles]);a=q[faces[:,0]];m=np.stack([q[faces[:,1]]-a,q[faces[:,2]]-a],axis=2);det=np.linalg.det(m)
 groups=[]
 for sign in [1,-1]:
  ids=np.flatnonzero(det*sign>1e-5);assert len(ids);tri=faces[ids];start=a[ids];inv=np.linalg.inv(m[ids])
  def sample(point,tri=tri,start=start,inv=inv):
   p=np.asarray(point);v=np.einsum('nij,nj->ni',inv,p-start);bc=np.c_[1-v.sum(1),v];cl=np.maximum(bc,0);cl/=cl.sum(1)[:,None];proj=np.einsum('ni,nij->nj',cl,q[tri]);dist=((proj-p)**2).sum(1);dist[(bc>=-1e-6).all(1)]=0;k=int(np.argmin(dist));vs=tri[k];mix={}
   for i,gain in zip(vs,cl[k]):
    for g in ob.data.vertices[int(i)].groups:
     name=ob.vertex_groups[g.group].name;mix[name]=mix.get(name,0)+gain*g.weight
   items=sorted(mix.items(),key=lambda v:-v[1])[:4];total=sum(w for _,w in items);assert total>0
   return bc[k]@vertices[vs],{n:float(w/total)for n,w in items if w>1e-8}
  groups.append(sample)
 return groups

p=argparse.ArgumentParser(description=__doc__)
for name in ['config','output']:p.add_argument('--'+name,type=Path,required=True)
a=p.parse_args(sys.argv[sys.argv.index('--')+1:]);cfg=read(a.config);out=a.output.resolve();assert out.is_relative_to(ROOT/'projects/fishing-2d/experiments')and not out.exists()
source=ROOT/cfg['blend'];assert sha(source)==cfg['blend_sha256'];maskfile=ROOT/cfg['masks'];assert sha(maskfile)==cfg['masks_sha256'];masks=read(maskfile);profile=read(ROOT/cfg['profile']);W,H=masks['source_size'] if 'source_size'in masks else cfg['source_size'];aspect=H/W
bpy.ops.wm.open_mainfile(filepath=str(source));bpy.context.scene.frame_set(0);frozen_rig=rig_action_snapshot()
logical_names=[f['name']+s for f in profile['fins']for s in(['_left','_right']if f['paired']else[''])]
object_names=cfg.get('object_names',{});assert not set(object_names)-set(logical_names)
resolved_names={n:object_names.get(n,n+'_mesh')for n in logical_names}
assert len(set(resolved_names.values()))==len(logical_names) and all(n in bpy.data.objects and bpy.data.objects[n].type=='MESH'for n in resolved_names.values()),'Explicit one-to-one fin mesh mapping required'
replace=set(resolved_names.values());protected={o.name:mesh_snapshot(o)for o in bpy.data.objects if o.type=='MESH'and o.name not in replace};records=[]
oldcuts=read(ROOT/cfg['initial_validation'])['metrics']['native_fin_cutouts']
for fin in profile['fins']:
 rec=next(r for r in masks['fins']if r['name']==fin['name']);imagefile=Path(rec['image']);assert sha(imagefile)==rec['image_sha256'];image=bpy.data.images.load(str(imagefile),check_existing=False);image.pack()
 polygon=np.asarray(cfg['source_polygons_px'][fin['name']],float);root=np.asarray(rec['root_px'])+np.array(rec['crop'][:2]);center=polygon.mean(0)
 extra=[*root]
 # Three source-local support points retain a controllable finite root band.
 for q in root[np.linspace(0,len(root)-1,min(3,len(root))).round().astype(int)]:
  direction=center-q;extra.append(q+direction/max(np.linalg.norm(direction),1e-9)*8)
 seeds=np.r_[polygon,np.array(extra)];vs=[Vector(q/[W,H])for q in seeds];npoly=len(polygon)
 dv,de,df,*_=delaunay_2d_cdt(vs,[(i,(i+1)%npoly)for i in range(npoly)],[list(range(npoly))],1,1e-8)
 # CDT returns isolated input seeds outside a concave domain as well. They
 # have no source-face UV and must not become unreferenced mesh vertices.
 used=sorted({i for f in df for i in f});remap={old:new for new,old in enumerate(used)}
 unused_seed_count=len(dv)-len(used);dv=[dv[i]for i in used];df=[tuple(remap[i]for i in f)for f in df]
 q=np.array(dv)*[W,H];N=len(q);assert len(df)>0
 fin['source_baseline']=(root/[W,H]).tolist();fin['polygon']=(polygon/[W,H]).tolist()
 span=max(fin_baseline_parameter(v,fin['source_baseline'],fin['polygon'],aspect)for v in dv);assert span>0
 # This conversion is the frozen physical source-distance definition used by the checker.
 def root_distance(point):
  best=float('inf')
  for aa,bb in zip(root,root[1:]):
   delta=bb-aa;t=np.clip(np.dot(point-aa,delta)/np.dot(delta,delta),0,1);best=min(best,float(np.linalg.norm(point-aa-t*delta)))
  return best
 maximum=max(root_distance(v)for v in polygon);fin['root_attachment']['root_band']=rec['root_band_px']/maximum
 ts=[fin_baseline_parameter(v,fin['source_baseline'],fin['polygon'],aspect)for v in dv]
 for suffix in(['_left','_right']if fin['paired']else['']):
  ob=bpy.data.objects[resolved_names[fin['name']+suffix]];functions=layer_samplers(ob,oldcuts[fin['name']]['native_crop_top_left']);positions=[];weights=[]
  for fn in functions:
   for point in q:
    co,skin=fn(point);positions.append(co);weights.append(skin)
  positions=np.array(positions);direction=np.mean(positions[:N]-positions[N:],axis=0);faces=[]
  for f in df:
   ids=list(f);aa,bb,cc=positions[ids]
   if np.dot(np.cross(bb-aa,cc-aa),direction)<0:ids.reverse()
   faces.append(tuple(ids))
  cap=list(faces);faces +=[tuple(i+N for i in reversed(f))for f in cap];edges={}
  for f in cap:
   for i,j in zip(f,f[1:]+f[:1]):edges.setdefault(tuple(sorted([i,j])),[]).append((i,j))
  for e in edges.values():
   if len(e)==1:
    i,j=e[0];faces.append((j,i,i+N,j+N))
  old=ob.data;mesh=bpy.data.meshes.new(ob.name+'_native_sparse_cage');mesh.from_pydata(positions,[],faces);mesh.update();mat=old.materials[0].copy();mat.name=ob.name+'_native_source';next(n for n in mat.node_tree.nodes if n.type=='TEX_IMAGE').image=image;mesh.materials.append(mat)
  uv=mesh.uv_layers.new(name='UVMap');points=(q-rec['crop'][:2])/rec['size']
  for f in mesh.polygons:
   f.use_smooth=True
   for li in f.loop_indices:
    u,v=points[mesh.loops[li].vertex_index%N];uv.data[li].uv=(u,1-v)
  for name,values in [('foundry_fin_source_t',ts),('foundry_fin_source_u',[v[0]for v in dv]),('foundry_fin_source_v',[v[1]for v in dv])]:
   attr=mesh.attributes.new(name,'FLOAT','POINT')
   for i,v in enumerate(values*2):attr.data[i].value=v
  ob.data=mesh
  for i,mix in enumerate(weights):
   for bone,w in mix.items():(ob.vertex_groups.get(bone)or ob.vertex_groups.new(name=bone)).add([i],w,'REPLACE')
  ob['foundry_native_source_crop']=rec['crop'];bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));assert all(e.is_manifold for e in bm.edges);bm.to_mesh(mesh);bm.free();mesh.calc_loop_triangles()
  records.append({'name':ob.name,'layer_vertices':N,'triangles':len(mesh.loop_triangles),'unreferenced_CDT_seeds_removed':unused_seed_count,'native_source_crop':rec['crop'],'source_t_max':fin['root_attachment']['root_band'],'native_mask_sha256':rec['image_sha256'],'physical_review':'pending'})
assert rig_action_snapshot()==frozen_rig
assert all(mesh_snapshot(bpy.data.objects[n])==v for n,v in protected.items()),'Protected body/mouth/barbels changed'
triangles=0
for ob in bpy.data.objects:
 if ob.type=='MESH':ob.data.calc_loop_triangles();triangles+=len(ob.data.loop_triangles)
budget=check_triangle_budget(triangles,profile['real_length_cm']);out.mkdir(parents=True);bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(out/'fish.blend'))
bpy.ops.export_scene.gltf(filepath=str(out/'fish.glb'),export_format='GLB',export_animations=True,export_yup=True,export_skins=True)
(out/'profile.json').write_text(json.dumps(profile,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
report={'ok':True,'kind':'native_annotated_sparse_fin_cages','input_blend':str(source),'input_blend_sha256':sha(source),'config_sha256':sha(a.config),'mask_report':str(maskfile),'mask_report_sha256':sha(maskfile),'body_mouth_barbels_geometry_UV_weights_preserved':True,'rig_actions_preserved':True,'triangle_budget':budget,'fins':records,'model_sha256':sha(out/'fish.glb'),'blend_sha256':sha(out/'fish.blend'),'scope':'New source-domain cages, no decimation or old highpoly input. Thickness, native source coverage, complete roots, tail junction and posed validation remain pending.'}
(out/'author.validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8');print(json.dumps({'ok':True,'triangles':triangles,'fins':len(records)}))
