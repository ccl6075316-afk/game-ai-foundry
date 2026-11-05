"""Fit a continuous upper side envelope; existing XY and mouth remain fixed.

The plan binds the current actual finite envelope and its two endpoint heights.
Its quintic curve is an artistic continuity target, not animal measurements.
"""
import bpy,bmesh,json,sys,hashlib,shutil,math
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).parent/'portable'))
from source_snapshot import rig_action_snapshot
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def smooth(x):
 x=np.clip(x,0,1);return x*x*x*(10+x*(-15+6*x))
def main():
 base,plan_path,out=map(lambda s:Path(s).resolve(),sys.argv[sys.argv.index('--')+1:]);c=json.loads(plan_path.read_text());src=base/c['baseline'];L=c['L']
 assert not out.exists()and'/experiments/'in str(out)and sha(src/'fish.glb')==c['baseline_model_sha256']
 bpy.ops.wm.open_mainfile(filepath=str(src/'fish.blend'));body=bpy.data.objects['Reference_head_body'];me=body.data;me.calc_loop_triangles()
 before=np.array([v.co[:]for v in me.vertices]);uv=np.array([l.uv[:]for l in me.uv_layers.active.data]);faces=[tuple(p.vertices)for p in me.polygons];weights=[[(g.group,g.weight)for g in v.groups]for v in me.vertices];actions=rig_action_snapshot()
 others={o.name:np.array([v.co[:]for v in o.data.vertices])for o in bpy.context.scene.objects if o.type=='MESH'and o!=body}
 protected={v for p in me.polygons if me.materials[p.material_index].name=='Actual finite oral lining'for v in p.vertices}
 native=np.load(base/'skin-r2/native-lip-pixel-map.npz')['map'];points=np.c_[native[:,0]+.5,4096-native[:,1]-.5]
 for tri in me.loop_triangles:
  q=uv[list(tri.loops)]*[2048,4096];sel=(points>=q.min(0)-1).all(1)&(points<=q.max(0)+1).all(1)
  if not sel.any():continue
  matrix=np.column_stack([q[1]-q[0],q[2]-q[0]])
  if abs(np.linalg.det(matrix))<1e-9:continue
  beta=(points[sel]-q[0])@np.linalg.inv(matrix).T
  if ((beta>=-1e-5).all(1)&(beta.sum(1)<=1.00001)).any():protected.update(tri.vertices)
 protected=sorted(protected);t=(c['nose']-before[:,0])/L;a,b=c['interval'];s=np.clip((t-a)/(b-a),0,1)
 target=sum(math.comb(5,k)*(1-s)**(5-k)*s**k*v for k,v in enumerate(c['bernstein_coefficients']))*L
 top=np.interp(t,c['samples_t'],c['original_top'])*L;bottom=np.interp(t,c['samples_t'],c['original_bottom'])*L;mid=(top+bottom)/2
 active=(t>a)&(t<b);assert np.all(target[active]>mid[active]+L*.0001),'Upper-envelope target crosses the jaw midplane'
 # Actual upper half is mapped affinely, so the highest current vertex gets
 # the entire correction. Reusing pre-repair height normalization attenuates
 # that correction and leaves the original side kink in place.
 height=np.clip((before[:,2]-mid)/np.maximum(top-mid,1e-8),0,1);lateral=1-smooth((abs(before[:,1])/L-.045)/.030)
 dz=(target-top)*height*lateral;dz[~active]=0;dz[protected]=0;new=before.copy();new[:,2]+=dz
 for v,p in zip(me.vertices,new):v.co=p
 me.update();me.normals_split_custom_set([(0,0,0)]*len(me.loops));bm=bmesh.new();bm.from_mesh(me);assert all(e.is_manifold for e in bm.edges)and bm.calc_volume()>0;bm.free()
 assert np.array_equal(before[:,:2],new[:,:2])and np.array_equal(before[protected],new[protected])and np.array_equal(before[~active],new[~active])
 assert faces==[tuple(p.vertices)for p in me.polygons]and np.array_equal(uv,np.array([l.uv[:]for l in me.uv_layers.active.data]))
 assert weights==[[(g.group,g.weight)for g in v.groups]for v in me.vertices]and actions==rig_action_snapshot()
 assert all(np.array_equal(v,np.array([p.co[:]for p in bpy.data.objects[n].data.vertices]))for n,v in others.items())
 out.mkdir();bpy.context.preferences.filepaths.save_version=0;bpy.ops.object.select_all(action='DESELECT')
 for ob in bpy.context.scene.objects:
  if ob.type in ['MESH','ARMATURE']:ob.select_set(True)
 bpy.context.view_layer.objects.active=body;bpy.ops.wm.save_as_mainfile(filepath=str(out/'fish.blend'));bpy.ops.export_scene.gltf(filepath=str(out/'fish.glb'),export_format='GLB',use_selection=True,export_animations=True,export_yup=True,export_def_bones=False)
 for name in ['fin-authoring.json','body-color-mask.npz']:shutil.copyfile(src/name,out/name)
 changed=np.where(abs(dz)>1e-9)[0];report=dict(ok=True,kind='continuous_hammerhead_upper_side_flow',species=c['species'],baseline_sha256=sha(src/'fish.glb'),model_sha256=sha(out/'fish.glb'),plan_path=str(plan_path),plan_sha256=sha(plan_path),XY_exact=True,complete_oral_and_native_lip_vertices_exact=True,all_eye_fin_vertices_exact=True,protected_vertices=protected,topology_UV_weights_rig_actions_images_unchanged=True,maximum_displacement_m=float(abs(dz).max()),changed_vertices=[dict(index=int(i),before=before[i].tolist(),after=new[i].tolist())for i in changed],scope='Current head/neck side upper flow only. XY, closed mouth geometry, original native lips, fins and materials retained. Continuous target is fitted on finite low-poly geometry, not exact analytic surface or biological measurement.',visual_review='pending',formal_acceptance=False)
 (out/'neck-authoring.validation.json').write_text(json.dumps(report,indent=2)+'\n');print('SIDE_FLOW_CANDIDATE',base.name,len(changed),report['maximum_displacement_m'])
if __name__=='__main__':main()
