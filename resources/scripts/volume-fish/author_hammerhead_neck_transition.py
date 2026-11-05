"""Local neck relief on an ordinary source, retaining the mouth and full fins.

Own independent per-species artistic offsets follow the observed library
transition, not measured animal proportions. No remesh or texture repaint.
"""
import bpy,bmesh,json,sys,hashlib,shutil
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).parent/'portable'))
from source_snapshot import rig_action_snapshot
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def smooth(x):
 x=np.clip(x,0,1);return x*x*x*(10+x*(-15+6*x))
def hermite(x,knots,values):
 # Zero derivatives at the compact support endpoints, monotone local segments.
 x=np.asarray(x);out=np.zeros_like(x,dtype=float)
 for a,b,va,vb in zip(knots,knots[1:],values,values[1:]):
  k=(x>=a)&(x<=b);out[k]=va+(vb-va)*smooth((x[k]-a)/(b-a))
 return out
def main():
 base,out=map(lambda s:Path(s).resolve(),sys.argv[sys.argv.index('--')+1:]);src=base/'candidate-r25'
 assert not out.exists()and'/experiments/'in str(out)
 c=json.loads((base/'preparation-r2/config.json').read_text());L=c['display_length_m'];great=base.name=='great'
 bpy.ops.wm.open_mainfile(filepath=str(src/'fish.blend'));body=bpy.data.objects['Reference_head_body'];me=body.data;me.calc_loop_triangles()
 before=np.array([v.co[:]for v in me.vertices]);faces=[tuple(p.vertices)for p in me.polygons];uv=np.array([l.uv[:]for l in me.uv_layers.active.data]);weights=[[(g.group,g.weight)for g in v.groups]for v in me.vertices];actions=rig_action_snapshot()
 others={o.name:np.array([v.co[:]for v in o.data.vertices])for o in bpy.context.scene.objects if o.type=='MESH'and o!=body}
 nose=max(v.co.x for o in bpy.context.scene.objects if o.type=='MESH'for v in o.data.vertices);t=(nose-before[:,0])/L;y=abs(before[:,1])/L
 protected={v for p in me.polygons if me.materials[p.material_index].name=='Actual finite oral lining'for v in p.vertices}
 # Protect complete faces carrying any native lip texel, not only UV corners.
 native=np.load(base/'skin-r2/native-lip-pixel-map.npz')['map'];points=np.c_[native[:,0]+.5,4096-native[:,1]-.5]
 for tri in me.loop_triangles:
  q=uv[list(tri.loops)]*[2048,4096];sel=(points>=q.min(0)-1).all(1)&(points<=q.max(0)+1).all(1)
  if not sel.any():continue
  M=np.column_stack([q[1]-q[0],q[2]-q[0]])
  if abs(np.linalg.det(M))<1e-9:continue
  beta=(points[sel]-q[0])@np.linalg.inv(M).T
  if ((beta>=-1e-5).all(1)&(beta.sum(1)<=1.00001)).any():protected.update(tri.vertices)
 protected=sorted(protected)
 lateral_knots=[.072,.084,.095,.115,.135,.16,.185,.215]if great else[.060,.075,.09,.115,.135,.16,.185,.215]
 lateral_values=[0,.001,.007,.010,.007,.004,.0015,0]if great else[0,.001,.003,.006,.004,.002,.0005,0]
 upper_knots=[.065,.080,.095,.115,.145,.180,.215]if great else[.060,.080,.100,.130,.160,.190,.215]
 upper_values=[0,-.002,-.008,-.007,-.004,-.001,0]if great else[0,-.003,-.004,-.002,-.001,-.0003,0]
 new=before.copy();dy=hermite(t,lateral_knots,lateral_values)*smooth(y/.022)*(1-smooth((y-.052)/.030))*L
 new[:,1]+=np.sign(before[:,1])*dy
 # Same original side envelope normalizes upper-only relief; lower jaw stays.
 ref=json.loads((base/'shape-r2/reference.input.json').read_text());rows=ref['body_stations'];axis=ref['reference_body_axis_m'];rt=(axis/2-before[:,0])/axis
 top=np.interp(rt,[r['t']for r in rows],[r['top_z_m']for r in rows]);bottom=np.interp(rt,[r['t']for r in rows],[r['bottom_z_m']for r in rows]);height=(before[:,2]-bottom)/np.maximum(top-bottom,1e-7)
 new[:,2]+=hermite(t,upper_knots,upper_values)*smooth((height-.46)/.54)*(1-smooth((y-.045)/.025))*L
 new[protected]=before[protected]
 for v,p in zip(me.vertices,new):v.co=p
 me.update();me.normals_split_custom_set([(0,0,0)]*len(me.loops))
 bm=bmesh.new();bm.from_mesh(me);assert all(e.is_manifold for e in bm.edges)and bm.calc_volume()>0;bm.free()
 assert np.array_equal(before[protected],new[protected])and np.array_equal(before[t>=.215],new[t>=.215])
 assert np.array_equal(uv,np.array([l.uv[:]for l in me.uv_layers.active.data]))and faces==[tuple(p.vertices)for p in me.polygons]
 assert weights==[[(g.group,g.weight)for g in v.groups]for v in me.vertices]and actions==rig_action_snapshot()
 assert all(np.array_equal(v,np.array([p.co[:]for p in bpy.data.objects[n].data.vertices]))for n,v in others.items())
 out.mkdir();bpy.context.preferences.filepaths.save_version=0;bpy.ops.object.select_all(action='DESELECT')
 for ob in bpy.context.scene.objects:
  if ob.type in ['MESH','ARMATURE']:ob.select_set(True)
 bpy.context.view_layer.objects.active=body;bpy.ops.wm.save_as_mainfile(filepath=str(out/'fish.blend'));bpy.ops.export_scene.gltf(filepath=str(out/'fish.glb'),export_format='GLB',use_selection=True,export_animations=True,export_yup=True,export_def_bones=False)
 for name in ['fin-authoring.json','body-color-mask.npz']:shutil.copyfile(src/name,out/name)
 changed=np.where(np.linalg.norm(new-before,axis=1)>1e-9)[0]
 report=dict(ok=True,kind='local_hammerhead_neck_relief',baseline_sha256=sha(src/'fish.glb'),model_sha256=sha(out/'fish.glb'),species=c['species'],length_m=L,coordinate='t=(actual nose-X)/display length, Blender Y transverse/Z vertical',lateral_knots=lateral_knots,lateral_offsets_over_length=lateral_values,upper_knots=upper_knots,upper_offsets_over_length=upper_values,protected_native_lip_and_oral_vertices=protected,complete_mouth_and_lips_vertices_exact=True,all_fin_eye_vertices_exact=True,posterior_body_t_ge_0215_exact=True,UV_topology_weights_rig_actions_pixels_unchanged=True,changed_vertices=[dict(index=int(i),before=before[i].tolist(),after=new[i].tolist())for i in changed],maximum_displacement_m=float(np.linalg.norm(new-before,axis=1).max()),source_basis='Own current finite neck dip and abrupt upper ramp compared with local library model f516b1aa... reference. Engineering local relief only, not biological measurements or transferred vertices.',visual_review='pending',formal_acceptance=False)
 (out/'neck-authoring.validation.json').write_text(json.dumps(report,indent=2)+'\n');print('NECK_CANDIDATE',base.name,len(changed),report['maximum_displacement_m'])
if __name__=='__main__':main()
