"""Continuous upper/lower native caudal foil field with sparse interior support.

Uses scalar library t/c only. Original silhouette, UV chart, complete body cap,
root IDs, body, source images and rig/actions remain; no library mesh copied.
"""
import bpy,bmesh,json,sys,math,hashlib
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).parent/'portable'));from source_snapshot import rig_action_snapshot
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
 base,src,out=map(lambda p:Path(p).resolve(),sys.argv[sys.argv.index('--')+1:]);assert not out.exists()and'/experiments/'in str(out);audit=json.loads((base/'feedback-r14/fin-reference-r18.json').read_text());bpy.ops.wm.open_mainfile(filepath=str(src/'fish.blend'));rig=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE');rig.data.pose_position='REST';bpy.context.scene.frame_set(1);actions=rig_action_snapshot();body=bpy.data.objects['Reference_head_body'];body_before=np.array([v.co[:]for v in body.data.vertices]);ob=bpy.data.objects['Caudal'];old=ob.data;old.calc_loop_triangles();vertices=[np.array(v.co[:],float)for v in old.vertices];original=np.array(vertices);uv=old.uv_layers.active;faces=[dict(ids=list(t.vertices),uv=[np.array(uv.data[l].uv[:],float)for l in t.loops],material=t.material_index,smooth=old.polygons[t.polygon_index].use_smooth)for t in old.loop_triangles];attributes={a.name:np.array([x.value for x in a.data],float).tolist()for a in old.attributes if a.domain=='POINT'and a.data_type=='FLOAT'and not a.name.startswith('.')};required=['source_mask_x_px','source_mask_y_px','source_span_t','source_layer_sign'];assert all(k in attributes for k in required);weights=[{int(g.group):float(g.weight)for g in v.groups}for v in old.vertices];auth=json.loads((src/'fin-authoring.json').read_text());row=next(f for f in auth['fins']if f['name']=='Caudal');roots=set(row['root_ids']);root=original[list(roots)];center=float(root[:,2].mean());bottom=float(root[:,2].min());rear=float(body_before[:,0].min());L=json.loads((base/'preparation-r2/config.json').read_text())['display_length_m'];upper_tip=float(original[:,2].max());lower_tip=float(original[:,2].min());upper=next(f for f in audit['fins']if f['name']=='Caudal');lower=next(f for f in audit['fins']if f['name']=='Caudal_lower');defs={}
 for name,origin,tip,record in [('upper',center,upper_tip,upper),('lower',bottom,lower_tip,lower)]:
  rows=[r for r in record['library']['rows']if r['valid']];assert len(rows)>=3;defs[name]=dict(origin_z=origin,tip_z=tip,span_knots=[r['s']for r in rows],t_over_c=[r['peak_t_over_c']for r in rows])
 triangles=original[np.array([f['ids']for f in faces])]
 def bounds(z):
  hits=[]
  for t in triangles:
   for a,b in zip(t,np.roll(t,-1,axis=0)):
    if abs(a[2]-z)<1e-9:hits.append(float(a[0]))
    if(a[2]-z)*(b[2]-z)<0:hits.append(float(a[0]+(b[0]-a[0])*(z-a[2])/(b[2]-a[2])))
  assert hits;return min(hits),max(hits)
 def half(x,z,previous):
  if bottom<z<center:return abs(previous)
  definition=defs['upper'if z>=center else'lower'];s=(z-definition['origin_z'])/(definition['tip_z']-definition['origin_z']);tc=float(np.interp(s,definition['span_knots'],definition['t_over_c']));lo,hi=bounds(z);chord=hi-lo
  if chord<1e-8:return abs(previous)
  q=np.clip((hi-x)/chord,0,1);shape=(.2969*np.sqrt(q)-.126*q-.3516*q*q+.2843*q**3-.1036*q**4)/.1001;shape=max(0,min(1,shape));target=.0002+max(0,tc*chord-.0004)*shape/2;f=np.clip((rear-x)/(.015*L),0,1);f=f*f*(3-2*f);return abs(previous)*(1-f)+target*f
 for i,p in enumerate(vertices):
  if i not in roots and abs(p[1])>1e-10:p[1]=math.copysign(half(p[0],p[2],p[1]),p[1])
 added=[]
 for branch in ['upper','lower']:
  definition=defs[branch]
  for s in [.25,.5,.75,.9]:
   z=definition['origin_z']+(definition['tip_z']-definition['origin_z'])*s;lo,hi=bounds(z)
   for fraction in ([.273,.513] if L<=3 and s in [.25,.9] else [.273,.513,.743]):
    x=hi+(lo-hi)*fraction;q=np.array([x,z])
    for sign in [1,-1]:
     match=None
     for fi,face in enumerate(faces):
      ids=face['ids'];layers=np.array([attributes['source_layer_sign'][i]for i in ids]);
      if not np.all(layers*sign>.99):continue
      t=np.array([vertices[i][[0,2]]for i in ids]);M=np.column_stack([t[1]-t[0],t[2]-t[0]])
      if abs(np.linalg.det(M))<1e-12:continue
      b=np.linalg.solve(M,q-t[0]);beta=np.array([1-b.sum(),*b])
      if beta.min()>1e-7:match=(fi,face,beta);break
     assert match is not None,(branch,s,fraction,sign,'No strict finite face for conforming insertion')
     fi,face,beta=match;ids=face['ids'];position=beta@np.array([vertices[i]for i in ids]);position[1]=sign*half(x,z,position[1]);position[0]=x;position[2]=z;new_index=len(vertices);vertices.append(position);source_uv=beta@np.array(face['uv']);group={}
     for i,k in zip(ids,beta):
      for j,w in weights[i].items():group[j]=group.get(j,0)+w*k
     group={j:w for j,w in group.items()if w>1e-9};assert len(group)<=4,(len(group),'Skin influence support changed');total=sum(group.values());weights.append({j:w/total for j,w in group.items()})
     for name,values in attributes.items():values.append(float(beta@np.array([values[i]for i in ids])))
     a,b,c=ids;ua,ub,uc=face['uv'];common=dict(material=face['material'],smooth=face['smooth']);faces[fi:fi+1]=[dict(common,ids=[a,b,new_index],uv=[ua,ub,source_uv]),dict(common,ids=[b,c,new_index],uv=[ub,uc,source_uv]),dict(common,ids=[c,a,new_index],uv=[uc,ua,source_uv])];added.append(dict(branch=branch,span=s,chord_fraction=fraction,layer=sign,vertex=new_index))
 new=bpy.data.meshes.new(old.name+' calibrated continuous leaf sections');new.from_pydata([p.tolist()for p in vertices],[],[f['ids']for f in faces]);new.update()
 for m in old.materials:new.materials.append(m)
 nuv=new.uv_layers.new(name=uv.name)
 for p,f in zip(new.polygons,faces):
  p.material_index=f['material'];p.use_smooth=f['smooth']
  for l,q in zip(p.loop_indices,f['uv']):nuv.data[l].uv=q
 for name,values in attributes.items():a=new.attributes.new(name=name,type='FLOAT',domain='POINT');a.data.foreach_set('value',values)
 group_names=[g.name for g in ob.vertex_groups];ob.data=new
 for name in group_names:ob.vertex_groups.new(name=name)
 for i,group in enumerate(weights):
  for j,w in group.items():ob.vertex_groups[j].add([i],w,'REPLACE')
 bm=bmesh.new();bm.from_mesh(new);assert all(e.is_manifold for e in bm.edges)and bm.calc_volume()>0;bm.free();assert np.array_equal(original[list(roots)],np.array([v.co[:]for v in new.vertices])[list(roots)]);assert np.array_equal(body_before,np.array([v.co[:]for v in body.data.vertices]));assert rig_action_snapshot()==actions;row.update(vertices=len(new.vertices),triangles=len(new.polygons),root_points_native=[list(new.vertices[i].co)for i in row['root_ids']],caudal_section_calibration='Continuous independent upper/lower t/c field and explicit12inner support points per skin, original cap/outline/UV/source and weights preserved; fresh validation pending.');count=0
 for o in bpy.context.scene.objects:
  if o.type=='MESH':o.data.calc_loop_triangles();count+=len(o.data.loop_triangles)
 assert count<=(4000 if L<=3 else 6000);auth['whole_triangles']=count;out.mkdir();bpy.context.preferences.filepaths.save_version=0;rig.data.pose_position='POSE';bpy.ops.object.select_all(action='DESELECT')
 for o in bpy.context.scene.objects:
  if o.type in ['MESH','ARMATURE']:o.select_set(True)
 bpy.context.view_layer.objects.active=body;bpy.ops.wm.save_as_mainfile(filepath=str(out/'fish.blend'));bpy.ops.export_scene.gltf(filepath=str(out/'fish.glb'),export_format='GLB',use_selection=True,export_animations=True,export_yup=True,export_def_bones=False);(out/'fin-authoring.json').write_text(json.dumps(auth,indent=2)+'\n');(out/'caudal-calibration.validation.json').write_text(json.dumps(dict(ok=True,kind='continuous_independent_native_caudal_library_section_calibration',source_sha256=sha(src/'fish.blend'),model_sha256=sha(out/'fish.glb'),reference_audit_sha256=sha(base/'feedback-r14/fin-reference-r18.json'),library_reference_sha256=audit['reference_sha256'],definitions=defs,added_supports=added,body_exact=True,complete_original_root_positions_exact=True,original_outline_and_UV_field_preserved=True,rig_actions_exact=True,whole_triangles=count,formal_acceptance=False),indent=2)+'\n');print('CAUDAL_CALIBRATED',base.name,count)
if __name__=='__main__':main()
