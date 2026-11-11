"""Append four rooted two-sided stylized teeth to the current guarded source."""
from pathlib import Path
import bpy,numpy as np,json,sys,argparse,hashlib
E=Path(__file__).resolve().parent;R=E.parents[1];sys.path[:0]=[str(R/'resources/scripts/volume-fish/portable'),str(R/'resources/scripts/volume-fish')]
from glb_io import read_glb,arrays
def packed_arrays(path,spec):
 d,b=read_glb(path);node=next(n for n in d['nodes']if 'mesh'in n);pr=d['meshes'][node['mesh']]['primitives'][0];attrs={k:arrays(d,b,pr['attributes'][k])for k in ['POSITION','NORMAL','TEXCOORD_0','JOINTS_0','WEIGHTS_0']};idx=arrays(d,b,pr['indices']).reshape(-1).astype(int);parts=[dict(name=p['logical_name'],role=p['role'],vertex_range=[p['vertex_start'],p['vertex_start']+p['vertex_count']],index_range=[p['index_start'],p['index_start']+p['index_count']])for p in d['extras']['geometry_parts']];names=[d['nodes'][i]['name']for i in d['skins'][node['skin']]['joints']];return d,b,node,pr,parts,attrs,idx,names,{'triangles':len(idx)//3}
from export_packed_fish_source import geometry_signature,normal_attribute_signature,float_uv_signature,part_signature,material_signature,EXACT_NORMAL_ATTRIBUTE,EXACT_UV,PART_ID,SOURCE_VERTEX,FACE_PART
from source_snapshot import rig_action_snapshot
from export_source import export_source
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args(sys.argv[sys.argv.index('--')+1:]);out=a.output.resolve();assert out.is_relative_to(E)and not out.exists();out.mkdir()
base=E/'source-r1';spec=json.loads((E/'parts-spec.json').read_text());doc,blob,node,prim,parts,attrs,idx,names,expected=packed_arrays(base/'fish.glb',spec);P=attrs['POSITION'];mouth=next(p for p in parts if p['role']=='mouth');mi=np.arange(*mouth['vertex_range'])
# Explicit actual upper-lip boundary landmarks, measured from the frozen source.
xs=[.43996360898017883,.4460279047489166,.4551243185997009,.4581564664840698,.4668276309967041,.470285028219223,.4763492941856384,.4823797345161438,.4877603352069855,.4919205904006958,.495876282453537]
curve=[];curve_ids=[]
for x in xs:
 ids=[i for i in mi if abs(float(P[i,0])-x)<1e-7 and P[i,2]>=0];i=max(ids,key=lambda i:float(P[i,1]));curve.append(P[i]);curve_ids.append(int(i))
curve=np.array(curve)
def anchor(x,sign):
 j=min(max(int(np.searchsorted(curve[:,0],x)-1),0),len(curve)-2);t=(x-curve[j,0])/(curve[j+1,0]-curve[j,0]);p=curve[j]*(1-t)+curve[j+1]*t;p[2]*=sign
 weights={}
 for k,wgt in [(curve_ids[j],1-t),(curve_ids[j+1],t)]:
  for joint,weight in zip(attrs['JOINTS_0'][k],attrs['WEIGHTS_0'][k]):
   if weight>0:weights[int(joint)]=weights.get(int(joint),0)+float(weight)*wgt
 return p,weights,dict(source_ids=[curve_ids[j],curve_ids[j+1]],fraction=float(t),mirror_z=sign)
newp=[];newn=[];neww=[];teeth=[]
for sign,side in [(1,'left'),(-1,'right')]:
 for center,label,width,height in [(.455,'rear',.011,.0031),(.483,'front',.010,.00355)]:
  left,lw,lp=anchor(center-width/2,sign);right,rw,rp=anchor(center+width/2,sign);middle,mw,mp=anchor(center,sign)
  rawroots=[left.copy(),right.copy()]
  left[1]+=.00035;right[1]+=.00035;left[2]-=sign*.00008;right[2]-=sign*.00008
  tip=middle.copy();tip[1]-=height;tip[2]+=sign*.0002
  points=np.array([left,right,tip]);normal=np.cross(points[1]-points[0],points[2]-points[0]);normal/=np.linalg.norm(normal)
  if normal[2]*sign<0:points=points[[1,0,2]];weights=[rw,lw,mw]
  else:weights=[lw,rw,mw]
  n=np.cross(points[1]-points[0],points[2]-points[0]);n/=np.linalg.norm(n)
  start=len(P)+len(newp)
  for ordering in [[0,1,2],[2,1,0]]:
   for j in ordering:newp.append(points[j]);newn.append(n if ordering[0]==0 else -n);neww.append(weights[j])
  teeth.append({'name':side+'_'+label,'source_vertex_ids':list(range(start,start+6)),'unoffset_upper_lip_roots_gltf':[x.tolist()for x in rawroots],'root_source_bindings':[lp,rp],'tip_source_binding':mp,'root_offset_native':[0,.00035,-sign*.00008],'tip_height_native':height,'width_native':width})
newp=np.array(newp,dtype=np.float32);newn=np.array(newn,dtype=np.float32);newuv=np.tile([(1419.5)/4096,(3692.5)/8192],(24,1)).astype(np.float32)
bpy.ops.wm.open_mainfile(filepath=str(base/'fish.blend'));ob=next(o for o in bpy.data.objects if o.type=='MESH');mesh=ob.data;assert geometry_signature(ob)==mesh['foundry_normal_geometry_sha256'];assert part_signature(mesh)==mesh['foundry_part_signature_sha256'];frozen=rig_action_snapshot();matsha=material_signature(mesh.materials[0]);nv=len(mesh.vertices);nl=len(mesh.loops);nf=len(mesh.polygons);assert nv==len(P)and nf==1992
old_normal=[tuple(x.vector)for x in mesh.attributes[EXACT_NORMAL_ATTRIBUTE].data];old_uv=[tuple(x.vector)for x in mesh.attributes[EXACT_UV].data]
mesh.vertices.add(24);mesh.loops.add(24);mesh.polygons.add(8)
for j,p in enumerate(newp):mesh.vertices[nv+j].co=(float(p[0]),float(-p[2]),float(p[1]))
for j in range(24):mesh.loops[nl+j].vertex_index=nv+j
for j in range(8):
 poly=mesh.polygons[nf+j];poly.loop_start=nl+j*3;poly.material_index=0;poly.use_smooth=False
mesh.update(calc_edges=True)
for j in range(24):
 vi=nv+j;mesh.attributes[PART_ID].data[vi].value=22;mesh.attributes[SOURCE_VERTEX].data[vi].value=vi
 for joint,weight in neww[j].items():ob.vertex_groups[names[joint]].add([vi],float(weight),'REPLACE')
for j in range(8):mesh.attributes[FACE_PART].data[nf+j].value=22
for j in range(nl):
 mesh.attributes[EXACT_NORMAL_ATTRIBUTE].data[j].vector=old_normal[j];mesh.attributes[EXACT_UV].data[j].vector=old_uv[j]
for j in range(24):
 mesh.attributes[EXACT_NORMAL_ATTRIBUTE].data[nl+j].vector=newn[j].tolist();mesh.attributes[EXACT_UV].data[nl+j].vector=newuv[j].tolist();mesh.uv_layers['UVMap'].data[nl+j].uv=(float(newuv[j,0]),float(1-newuv[j,1]))
custom=[]
for item in mesh.attributes[EXACT_NORMAL_ATTRIBUTE].data:
 n=item.vector;custom.append((float(n[0]),float(-n[2]),float(n[1])))
mesh.normals_split_custom_set(custom);mesh.update()
raw=json.loads(mesh['foundry_geometry_parts_json']);raw.append({'name':'Upper_teeth_mesh','logical_name':'Upper_teeth_mesh','source_node':'Upper_teeth_mesh','source_surface':0,'part_id':22,'role':'teeth','opaque_uv':True,'vertex_count':24,'index_count':24,'source_vertex_start':nv,'source_model_sha256':sha(base/'fish.glb')});mesh['foundry_geometry_parts_json']=json.dumps(raw)
mesh['foundry_normal_geometry_sha256']=geometry_signature(ob);mesh['foundry_exact_normal_sha256']=normal_attribute_signature(ob);mesh['foundry_exact_uv_sha256']=float_uv_signature(mesh);mesh['foundry_part_signature_sha256']=part_signature(mesh)
assert rig_action_snapshot()==frozen and material_signature(mesh.materials[0])==matsha
bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(out/'fish.blend'));exp=export_source(out/'fish.glb')
spec['parts'].append({k:raw[-1][k]for k in ['name','role','source_node','source_surface','logical_name','opaque_uv']});spec['expected']['triangles']=2000;(out/'parts-spec.json').write_text(json.dumps(spec,indent=2)+'\n')
nd,nb,nn,npr,nparts,na,ni,_,_=packed_arrays(out/'fish.glb',spec)
for key in attrs:assert np.array_equal(na[key][:len(P)],attrs[key]),key
assert np.array_equal(ni[:len(idx)],idx)
for key in ['nodes','skins','animations','materials','textures','samplers']:assert doc.get(key)==nd.get(key),key
v=doc['bufferViews'][doc['images'][0]['bufferView']];v2=nd['bufferViews'][nd['images'][0]['bufferView']];assert blob[v.get('byteOffset',0):v.get('byteOffset',0)+v['byteLength']]==nb[v2.get('byteOffset',0):v2.get('byteOffset',0)+v2['byteLength']]
report={'ok':True,'kind':'source_owned_attached_upper_teeth','baseline_model_sha256':sha(base/'fish.glb'),'baseline_source_sha256':sha(base/'fish.blend'),'model_sha256':sha(out/'fish.glb'),'source_sha256':sha(out/'fish.blend'),'base_21_parts_all_geometry_uv_weights_normals_indices_exact':True,'base_material_texture_alpha_rig_animation_exact':True,'triangles':2000,'added_triangles':8,'added_vertices':24,'logical_part':'Upper_teeth_mesh','role':'teeth','teeth':teeth,'export':exp,'limits':'Four stylized zero-thickness double-faced triangular teeth, not thick anatomical solids. Upper roots embedded about0.06mm; require actual pose root/clearance and visual checks.'};(out/'teeth-authoring.validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'ok':True,'model_sha256':report['model_sha256']}))
