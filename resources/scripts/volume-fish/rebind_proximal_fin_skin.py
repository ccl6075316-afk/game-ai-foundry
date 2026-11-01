"""Rebind explicit proximal median-fin skin to its actual finite body surface.

No geometry/UV/normals/material, skeleton, clip, root-domain, tolerance or motion
amplitude changes. This creates an isolated source candidate, not a gate pass.
"""
import argparse,hashlib,json,sys
from pathlib import Path
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.geometry import barycentric_transform
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(Path(__file__).parent/'portable'))
from source_snapshot import rig_action_snapshot

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text(encoding='utf8'))
def geometry(o):return repr(([tuple(v.co)for v in o.data.vertices],[(tuple(f.vertices),f.material_index)for f in o.data.polygons],[[tuple(u.uv)for u in l.data]for l in o.data.uv_layers],[tuple(n.vector)for n in o.data.corner_normals]))
def weights(o):return [{o.vertex_groups[g.group].name:g.weight for g in v.groups}for v in o.data.vertices]

p=argparse.ArgumentParser(description=__doc__)
for name in ['blend','config','output']:p.add_argument('--'+name,required=True,type=Path)
a=p.parse_args(sys.argv[sys.argv.index('--')+1:]);cfg=read(a.config);out=a.output.resolve();assert out.is_relative_to(ROOT/'projects/fishing-2d/experiments')and not out.exists();assert sha(a.blend)==cfg['input_blend_sha256'];profile=read(ROOT/cfg['profile']);assert sha(ROOT/cfg['profile'])==cfg['profile_sha256']and profile['species']==cfg['species']
assert cfg['fins']and len({r['node']for r in cfg['fins']})==len(cfg['fins'])
for ref in cfg['basis_reports']:assert sha(ROOT/ref['path'])==ref['sha256'],'Stale actual-failure evidence'
bpy.ops.wm.open_mainfile(filepath=str(a.blend.resolve()));rig=rig_action_snapshot();body=bpy.data.objects[cfg['body']];body.data.calc_loop_triangles();vs=[v.co.copy()for v in body.data.vertices];tri=[tuple(t.vertices)for t in body.data.loop_triangles];tree=BVHTree.FromPolygons(vs,tri,all_triangles=True)
frozen={o.name:geometry(o)for o in bpy.data.objects if o.type=='MESH'};old_weights={o.name:weights(o)for o in bpy.data.objects if o.type=='MESH'};records=[];changed_ids={}
for row in cfg['fins']:
 ob=bpy.data.objects[row['node']];fin=next(f for f in profile['fins']if f['name']==row['profile_fin']);assert not fin['paired'],'This branch supports explicitly source-viewed median fins only'
 assert row['projection']in ('dorsal','ventral');vertical=1 if row['projection']=='dorsal'else-1;assert (fin['tip'][1]<fin['anchor'][1])==(vertical==1)
 band=fin['root_attachment']['root_band'];end=row['transition_end_source_t'];assert band<end<.5;changes=[];changed_ids[ob.name]=set()
 for v,t in zip(ob.data.vertices,ob.data.attributes['foundry_fin_source_t'].data):
  if not band+1e-7<t.value<end:continue
  hit,n,face,_=tree.ray_cast(Vector((v.co.x,v.co.y,vertical*2)),Vector((0,0,-vertical)),4);assert hit is not None,'Explicit proximal point has no directional body support'
  ids=tri[face];beta=barycentric_transform(hit,*[vs[i]for i in ids],Vector((1,0,0)),Vector((0,1,0)),Vector((0,0,1)));target={}
  for j,w in zip(ids,beta):
   for g in body.data.vertices[j].groups:
    bone=body.vertex_groups[g.group].name;target[bone]=target.get(bone,0)+max(0,w)*g.weight
  original=old_weights[ob.name][v.index];q=max(0,min(1,(t.value-band)/(end-band)));gain=1-q*q*(3-2*q);mix={bone:original.get(bone,0)*(1-gain)+target.get(bone,0)*gain for bone in set(target)|set(original)};items=sorted(mix.items(),key=lambda z:(-z[1],z[0]))[:4];total=sum(w for _,w in items);assert total>0
  for g in list(v.groups):ob.vertex_groups[g.group].remove([v.index])
  for bone,w in items:(ob.vertex_groups.get(bone)or ob.vertex_groups.new(name=bone)).add([v.index],w/total,'REPLACE')
  changed_ids[ob.name].add(v.index);changes.append({'vertex':v.index,'source_t':t.value,'gain':gain,'actual_body_triangle':ids,'body_barycentric':list(beta),'original':original,'new':{k:w/total for k,w in items}})
 assert changes,'Empty explicitly nominated proximal skin domain'
 records.append({'fin':ob.name,'unchanged_root_threshold':band,'transition_end_source_t':end,'vertices':changes})
assert all(geometry(bpy.data.objects[n])==s for n,s in frozen.items());assert rig_action_snapshot()==rig
for name,old in old_weights.items():
 new=weights(bpy.data.objects[name])
 assert all(new[i]==old[i]for i in range(len(old))if i not in changed_ids.get(name,set())),'Untargeted body/fin/root skin changed'
out.mkdir();bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(out/'fish.blend'))
report={'ok':True,'kind':'actual_body_barycentric_proximal_fin_skin','input_blend_sha256':sha(a.blend),'config_sha256':sha(a.config),'builder_sha256':sha(__file__),'blend_sha256':sha(out/'fish.blend'),'geometry_UV_normals_materials_rig_actions_exact':True,'root_domain_and_root_weights_unchanged':True,'all_untargeted_weights_exact':True,'records':records,'scope':'Only explicit proximal non-basal fin weights changed. Fresh source/cold parity, volume, whole490/072 and actual visual checks remain mandatory.'}
(out/'skin.validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'ok':True,'changes':{r['fin']:len(r['vertices'])for r in records}}))
