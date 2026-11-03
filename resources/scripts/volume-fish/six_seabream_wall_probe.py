"""Read-only four interior probes on every source-domain closing triangle."""
import argparse,bpy,json,hashlib,sys
from pathlib import Path
import numpy as np
from mathutils.kdtree import KDTree
ROOT=Path('E:/game-ai-foundry');sys.path[:0]=[str(ROOT/'resources/scripts/volume-fish')]
from export_packed_fish_source import EXACT_UV,PART_ID
p=argparse.ArgumentParser()
for k in ['source','packed','packing','output']:p.add_argument('--'+k,type=Path,required=True)
a=p.parse_args(sys.argv[sys.argv.index('--')+1:]);sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();packing=json.loads(a.packing.read_text());aw,ah=packing['atlas']['size'];sources={}
bpy.ops.wm.open_mainfile(filepath=str(a.source))
for ob in bpy.data.objects:
 if ob.type!='MESH' or 'foundry_fin_source_u'not in ob.data.attributes:continue
 m=ob.data;q=np.c_[[v.value for v in m.attributes['foundry_fin_source_u'].data],[v.value for v in m.attributes['foundry_fin_source_v'].data]];cap={}
 for f in m.polygons:
  co=q[list(f.vertices)];area=sum(np.cross(co[i]-co[0],co[i+1]-co[0])for i in range(1,len(co)-1))
  if abs(area)<1e-10:continue
  for li in f.loop_indices:cap.setdefault(m.loops[li].vertex_index,tuple(m.uv_layers.active.data[li].uv))
 for sid in range(len(m.vertices)):
  if sid in cap:continue
  options={cap[i]for i in cap if np.max(abs(q[i]-q[sid]))<1e-7}
  assert len(options)==1,(ob.name,sid,options);cap[sid]=next(iter(options))
 sources[ob.name]={'co':[tuple(v.co)for v in m.vertices],'q':q,'cap':cap}
bpy.ops.wm.open_mainfile(filepath=str(a.packed));ob=next(o for o in bpy.data.objects if o.type=='MESH');m=ob.data;parts=json.loads(m['foundry_geometry_parts_json']);ids=[round(v.value)for v in m.attributes[PART_ID].data];rows=[]
for part in parts:
 if part['role']!='fin':continue
 name=part['source_node'];s=sources[name];kd=KDTree(len(s['co']))
 for i,c in enumerate(s['co']):kd.insert(c,i)
 kd.balance();match={v.index:kd.find(v.co)for v in m.vertices if ids[v.index]==part['part_id']};assert max(x[2]for x in match.values())<2e-6
 tile=next(x for x in packing['parts']if x['node']==name);W,H=tile['source_size'];ox,oy=tile['virtual_crop_origin'];ax,ay=tile['atlas_placement'];walls=[];caps=0;actual_cap={}
 for f in m.polygons:
  if ids[f.vertices[0]]!=part['part_id']:continue
  sid=[match[i][1]for i in f.vertices];co=s['q'][sid];area=float(np.cross(co[1]-co[0],co[2]-co[0]))
  if abs(area)<=1e-10:continue
  for li,i in zip(f.loop_indices,sid):actual_cap.setdefault(tuple(s['q'][i]),set()).add(tuple(m.attributes[EXACT_UV].data[li].vector))
 for f in m.polygons:
  if ids[f.vertices[0]]!=part['part_id']:continue
  sid=[match[i][1]for i in f.vertices];co=s['q'][sid];area=float(np.cross(co[1]-co[0],co[2]-co[0]))
  if abs(area)>1e-10:caps+=1;continue
  expected=[]
  for i in sid:
   u,v=s['cap'][i];expected.append([(u*W-ox+ax)/aw,((1-v)*H-oy+ay)/ah])
  actual=[]
  for i in sid:
   options=actual_cap[tuple(s['q'][i])];assert len(options)==1,(name,i,'Ambiguous actual cap address');actual.append(list(next(iter(options))))
  walls.append({'polygon':f.index,'actual_uv':[list(m.attributes[EXACT_UV].data[li].vector)for li in f.loop_indices],'cap_uv':actual,'ideal_source_cap_uv_before_FLOAT32_quantization':expected})
 rows.append({'name':name,'source_mapping_maximum_native':max(x[2]for x in match.values()),'cap_triangles':caps,'closing_wall_triangles':len(walls),'walls':walls})
a.output.write_text(json.dumps({'ok':True,'packed':str(a.packed),'packed_sha256':sha(a.packed),'anatomical_source':str(a.source),'anatomical_source_sha256':sha(a.source),'packing':str(a.packing),'packing_sha256':sha(a.packing),'atlas_size':[aw,ah],'fins':rows},indent=2)+'\n');print('WALL_SOURCE_PROBES_OK',len(rows))
