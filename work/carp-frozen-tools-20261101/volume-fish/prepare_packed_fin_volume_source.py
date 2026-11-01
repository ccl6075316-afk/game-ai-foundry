"""Extract actual editable packed parts for existing per-fin normal-ray checks.

No static geometry correction or acceptance. Positions come from the saved
source, checked bidirectionally against its cold model; the original rig stays.
The finite baseline width is the current frozen native-source domain, never a
nearest-body subset. Retained tail source parameters use exact old identities.
"""
import argparse,json,sys
from pathlib import Path
import bpy,numpy as np
from mathutils.kdtree import KDTree
from mathutils import Vector
HERE=Path(__file__).resolve().parent;sys.path[:0]=[str(HERE),str(HERE/'portable')]
from glb_io import read_glb,arrays,sha
from source_snapshot import rig_action_snapshot
from export_packed_fish_source import EXACT_UV,SOURCE_VERTEX
def read(p):return json.loads(Path(p).read_text(encoding='utf8'))
def distances(points,line):
 a=line[:-1];v=np.diff(line,axis=0);t=np.clip(((points[:,None,:]-a)*v).sum(2)/np.maximum((v*v).sum(1),1e-12),0,1);return np.linalg.norm(points[:,None,:]-a-t[:,:,None]*v,axis=2).min(1)
def main():
 p=argparse.ArgumentParser(description=__doc__)
 for k in ['candidate','tail-source','output']:p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args(sys.argv[sys.argv.index('--')+1:]);C=a.candidate.resolve();out=a.output.resolve();assert not out.exists()and out.is_relative_to(HERE.parents[2]/'projects/fishing-2d/experiments');out.mkdir(parents=True)
 bpy.ops.wm.open_mainfile(filepath=str(a.tail_source.resolve()));tail=bpy.data.objects['Caudal_mesh'];oldtail=np.array([v.co[:]for v in tail.data.vertices]);oldts=np.array([v.value for v in tail.data.attributes['foundry_fin_source_t'].data]);kd=KDTree(len(oldtail))
 for i,v in enumerate(oldtail):kd.insert(Vector(v),i)
 kd.balance();source=C/'source-run/source/fish.blend';model=C/'source-run/fish.glb';bpy.ops.wm.open_mainfile(filepath=str(source));ob=next(o for o in bpy.data.objects if o.type=='MESH');rig=next(o for o in bpy.data.objects if o.type=='ARMATURE');rig_before=rig_action_snapshot();mesh=ob.data;d,b=read_glb(model);pr=d['meshes'][0]['primitives'][0];pos=arrays(d,b,pr['attributes']['POSITION']);uv=arrays(d,b,pr['attributes']['TEXCOORD_0']);idx=arrays(d,b,pr['indices']).reshape(-1,3);native=np.array([v.co[:]for v in mesh.vertices]);expected=pos[:,[0,2,1]]*np.array([1,-1,1]);assert np.max(abs(native-expected))<1e-7
 for v in mesh.vertices:assert int(round(mesh.attributes[SOURCE_VERTEX].data[v.index].value))==v.index
 material=mesh.materials[0];skin=[{ob.vertex_groups[g.group].name:g.weight for g in v.groups}for v in mesh.vertices];packing=read(C/'conformed/packing.validation.json');auth=read(C/'conformed/author.validation.json');fins={r['name']:r for r in auth['fins']};masks=read(auth['input_masks']['path']);records=[]
 for old in list(bpy.data.objects):
  if old.type=='MESH':bpy.data.objects.remove(old,do_unlink=True)
 groups={}
 for part in d['extras']['geometry_parts']:groups.setdefault(part['source_node'],[]).append(part)
 for name,parts in groups.items():
  if bpy.data.objects.get(name):assert bpy.data.objects[name].type=='EMPTY';bpy.data.objects.remove(bpy.data.objects[name],do_unlink=True)
  tris=np.concatenate([idx[p['index_start']//3:(p['index_start']+p['index_count'])//3]for p in parts]);ids=np.unique(tris);lookup={int(j):i for i,j in enumerate(ids)};faces=np.array([[lookup[int(j)]for j in t]for t in tris]);m=bpy.data.meshes.new(name+'_finite_volume_check');m.from_pydata(native[ids].tolist(),[],faces.tolist());m.materials.append(material);m.update();new=bpy.data.objects.new(name,m);bpy.context.scene.collection.objects.link(new);new.parent=rig;mod=new.modifiers.new('Original armature','ARMATURE');mod.object=rig
  for i,j in enumerate(ids):
   for bone,w in skin[int(j)].items():(new.vertex_groups.get(bone)or new.vertex_groups.new(name=bone)).add([i],w,'REPLACE')
  layer=m.uv_layers.new(name='UVMap')
  for loop in m.loops:
   q=uv[ids[loop.vertex_index]];layer.data[loop.index].uv=(q[0],1-q[1])
  if parts[0]['role']=='fin':
   if name=='Caudal_mesh':
    match=[kd.find(Vector(q))for q in native[ids]];error=max(q[2]for q in match);assert error<2e-6;ts=np.array([oldts[q[1]]for q in match]);domain='Original retained tail, exact geometric source-point identity';band=None
   else:
    row=fins[name];packed=next(r for r in packing['parts']if r['node']==name);px=uv[ids]*packing['atlas']['size']-packed['atlas_placement']+packed['virtual_crop_origin'];root=np.array(row['root_px']);dist=distances(px,root);band=row['root_band_px'];maximum=max(float(dist.max()),band*2);fraction=row['source_band_fraction'];ts=np.where(dist<=band,fraction*dist/band,fraction+(1-fraction)*(dist-band)/(maximum-band));ts=np.clip(ts,0,1);domain='Complete independently frozen native root curve, unchanged source-band fraction; native width at least original full band; both finite layers and all closing faces included'
   attr=m.attributes.new('foundry_fin_source_t','FLOAT','POINT')
   for i,t in enumerate(ts):attr.data[i].value=float(t)
   records.append({'name':name,'vertices':len(ids),'root_band_px':band,'parameter_basis':domain})
 assert rig_before==rig_action_snapshot();bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(out/'fish.blend'),check_existing=False)
 report={'ok':True,'kind':'actual_packed_source_extracted_for_fin_volume','canonical_source':str(source),'canonical_source_sha256':sha(source),'model':str(model),'model_sha256':sha(model),'source_positions_vs_cold_max_error':float(np.max(abs(native-expected))),'rig_actions_exact':True,'tail_source':str(a.tail_source.resolve()),'tail_source_sha256':sha(a.tail_source),'derived_volume_source':str(out/'fish.blend'),'derived_volume_source_sha256':sha(out/'fish.blend'),'fins':records,'formal_acceptance':False,'scope':'Lossless static logical-part extraction for existing normal-ray/contact test only. It does not replace canonical editable source or any full fish gate.'};(out/'validation.json').write_bytes((json.dumps(report,indent=2)+'\n').encode());print(json.dumps({'ok':True,'fins':len(records)}))
if __name__=='__main__':main()
