"""Scale exposed paired foil layers from actual same-span library t/c audit.

Complete basal vertices and all body/rig/source pixels are frozen. Invalid
reference rows are never treated as measured targets. Exact targets/art priors
and every changed vertex are recorded; fresh finite fin/pose gates required.
"""
import bpy,bmesh,json,sys,hashlib
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).parent/'portable'));from source_snapshot import rig_action_snapshot
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
 base,out=map(lambda p:Path(p).resolve(),sys.argv[sys.argv.index('--')+1:]);assert not out.exists()and'/experiments/'in str(out);audit=json.loads((base/'feedback-r14/fin-reference-audit.json').read_text());src=base/'candidate-r13';assert sha(src/'fish.glb')==audit['model_sha256'];bpy.ops.wm.open_mainfile(filepath=str(src/'fish.blend'));rig=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE');rig.data.pose_position='REST';bpy.context.scene.frame_set(1);actions=rig_action_snapshot();body=bpy.data.objects['Reference_head_body'];body_vertices=np.array([v.co[:]for v in body.data.vertices]);auth=json.loads((src/'fin-authoring.json').read_text());cfg=json.loads((base/'preparation-r2/config.json').read_text());L=cfg['display_length_m'];nose=max(v.co.x for o in bpy.context.scene.objects if o.type=='MESH'for v in o.data.vertices);records=[]
 for f in auth['fins']:
  name=f['name'];ob=bpy.data.objects[name];me=ob.data;old=np.array([v.co[:]for v in me.vertices]);new=old.copy();roots=set(f['root_ids']);item=next(x for x in audit['fins']if x['name']==name)
  if name=='Caudal':
   records.append(dict(name=name,changed=False,reason='Full current tail cap and upper/lower lobe remain frozen during exposed noncaudal calibration. Separate anatomical lower-lobe origin audit required; no common gain is applied to tail.'));continue
  pairs=[];attr=lambda k:np.array([v.value for v in me.attributes[k].data]);xy=np.stack([attr('source_mask_x_px'),attr('source_mask_y_px')],1);layer=attr('source_layer_sign');pos=[i for i in range(len(old))if i not in roots and layer[i]>.999];neg=np.array([i for i in range(len(old))if i not in roots and layer[i]<-.999])
  for i in pos:
   distances=np.linalg.norm(xy[neg]-xy[i],axis=1);j=int(neg[distances.argmin()])
   if distances.min()<.002:pairs.append((i,j))
  assert len(pairs)>12,(name,len(pairs));mid=np.array([(old[i]+old[j])/2 for i,j in pairs]);halfvec=np.array([(old[i]-old[j])/2 for i,j in pairs]);half=np.linalg.norm(halfvec,axis=1);norm=halfvec/half[:,None];coords=np.array([xy[i]for i,j in pairs]);frame=item['current']['frame'];o=np.array(frame['origin']);B=np.array(frame['basis']);S=frame['span_over_length'];anat=np.stack([(nose-old[:,0])/L,old[:,2]/L,old[:,1]/L],1);s=(anat-o)@B[1]/S;valid=[(a['s'],a['peak_t_over_c']/b['peak_t_over_c'])for a,b in zip(item['library']['rows'],item['current']['rows'])if a['valid']and b['valid']];assert len(valid)>=2;knots=[0,.06]+[x for x,y in valid]+[.98,1.];gains=[1,1]+[y for x,y in valid]+[1.2,1.];changed=[]
  for i,p in enumerate(old):
   if i in roots or abs(layer[i])<1e-7:continue
   ids=np.argsort(np.linalg.norm(coords-xy[i],axis=1))[:4];w=1/np.maximum(np.linalg.norm(coords[ids]-xy[i],axis=1),1e-6)**2;h=float(np.dot(w,half[ids])/w.sum());n=np.sum(norm[ids]*w[:,None],axis=0);n/=np.linalg.norm(n);gain=float(np.interp(s[i],knots,gains));delta=max(0,h-.0002)*(gain-1);new[i]=p+n*float(layer[i])*delta
   if np.linalg.norm(new[i]-p)>1e-10:changed.append(dict(vertex=i,span_fraction=float(s[i]),gain=gain,displacement_m=float(np.linalg.norm(new[i]-p))))
  for v,p in zip(me.vertices,new):v.co=p
  me.update();me.normals_split_custom_set([(0,0,0)]*len(me.loops));bm=bmesh.new();bm.from_mesh(me);assert all(e.is_manifold for e in bm.edges)and bm.calc_volume()>0;volume=bm.calc_volume();bm.free();assert np.array_equal(old[list(roots)],new[list(roots)]);records.append(dict(name=name,changed=True,root_vertices_exact=True,gain_knots=knots,gains=gains,valid_library_span_fractions=[x for x,y in valid],unknown_proximal_interpolation='Invalid library rows omitted; interpolate construction field from fixed own root to first valid free row.'if len(valid)<4 else None,vertices=changed,volume_m3=volume));f['thickness_calibration']='actual library t/c audit, source planform/UV/root IDs retained; fresh pose validation pending'
 assert np.array_equal(body_vertices,np.array([v.co[:]for v in body.data.vertices]));assert rig_action_snapshot()==actions;rig.data.pose_position='POSE';out.mkdir();bpy.context.preferences.filepaths.save_version=0;bpy.ops.object.select_all(action='DESELECT')
 for ob in bpy.context.scene.objects:
  if ob.type in ['MESH','ARMATURE']:ob.select_set(True)
 bpy.context.view_layer.objects.active=body;bpy.ops.wm.save_as_mainfile(filepath=str(out/'fish.blend'));bpy.ops.export_scene.gltf(filepath=str(out/'fish.glb'),export_format='GLB',use_selection=True,export_animations=True,export_yup=True,export_def_bones=False);(out/'fin-authoring.json').write_text(json.dumps(auth,indent=2)+'\n');report=dict(ok=True,kind='actual_library_section_guided_exposed_fin_calibration',model_sha256=sha(out/'fish.glb'),baseline_sha256=sha(src/'fish.glb'),audit_sha256=sha(base/'feedback-r14/fin-reference-audit.json'),body_positions_exact=True,rig_actions_exact=True,complete_root_vertices_exact=True,source_images_UV_topology_weights_unedited=True,fins=records,visual_review='pending',formal_acceptance=False);(out/'section-calibration.validation.json').write_text(json.dumps(report,indent=2)+'\n');print('FIN_SECTION_CANDIDATE',base.name)
if __name__=='__main__':main()
