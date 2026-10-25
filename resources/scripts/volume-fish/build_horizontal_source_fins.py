"""Build paired horizontal fins from a frozen top artwork, not a rotated side fin.

Native pixels/one TL mapping, finite source basal strip, body skin at attachment,
original fin joint elsewhere. GLB rig/animations and other meshes are retained.
"""
import sys,json,hashlib,copy,struct,math
from pathlib import Path
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.geometry import delaunay_2d_cdt,barycentric_transform
sys.path.insert(0,str(Path(__file__).parent))
from patch_existing_fin_meshes import read,write
from build_source_fins141 import nearest_line,inside,smooth
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
 p=json.loads(Path(sys.argv[sys.argv.index('--')+1]).read_text());assert p.get('input_sha256'),'Freeze model/body/mapping/fin-plan input hashes before building'
 for path,digest in p['input_sha256'].items():assert sha(path)==digest,'Stale horizontal-fin input: '+path
 assert all(p[key]in p['input_sha256']for key in ['model','body','mapping','fin_plan']),'Incomplete frozen inputs'
 out=Path(p['output']);out.mkdir(parents=True,exist_ok=True);doc,blob=read(p['model']);binary=bytearray(blob);original=bytes(blob)
 body=json.loads(Path(p['body']).read_text());v=[];tr=[];skin=[]
 for part in body['parts']:
  offset=len(v);v.extend(Vector(q)for q in part['vertices']);ids=part['triangles'];tr.extend(tuple(offset+j for j in ids[i:i+3])for i in range(0,len(ids),3));skin.extend(dict(zip(j,w))for j,w in zip(part['joints'],part['weights']))
 if sum(v[a].dot(v[b].cross(v[c]))for a,b,c in tr)<0:tr=[tuple(reversed(t))for t in tr]
 bvh=BVHTree.FromPolygons(v,tr,all_triangles=True)
 mapping=json.loads(Path(p['mapping']).read_text());ppu=mapping['pixels_per_native'];hi=mapping['hi_native'];nose=mapping['nose_px'];mid=mapping['mid_px'];w,h=mapping['size'];plan=json.loads(Path(p['fin_plan']).read_text());spec=plan['items'][0];records=[]
 def put(rows,kind,component=5126):
  count={'SCALAR':1,'VEC2':2,'VEC3':3,'VEC4':4}[kind];fmt={5126:'f',5125:'I',5123:'H'}[component];binary.extend(b'\0'*(-len(binary)%4));off=len(binary)
  for row in rows:binary.extend(struct.pack('<'+fmt*count,*row))
  view=len(doc['bufferViews']);doc['bufferViews'].append({'buffer':0,'byteOffset':off,'byteLength':len(binary)-off,'target':34963 if kind=='SCALAR' else 34962});a={'bufferView':view,'byteOffset':0,'componentType':component,'count':len(rows),'type':kind}
  if kind=='VEC3':a.update(min=[min(q[i]for q in rows)for i in range(3)],max=[max(q[i]for q in rows)for i in range(3)])
  doc['accessors'].append(a);return len(doc['accessors'])-1
 for f in p['fins']:
  name=f['name'];assert sha(f['texture']['path'])==f['texture']['sha256'];node=next(n for n in doc['nodes']if n.get('name')==name and'mesh'in n);body_node=next(n for n in doc['nodes']if n.get('name')=='Closed_body'and'mesh'in n);assert node['skin']==body_node['skin'];names=[doc['nodes'][j]['name']for j in doc['skins'][node['skin']]['joints']];finbone=next(i for i,n in enumerate(names)if n==name)
  side=1 if name.endswith('left')else-1;base=[Vector(q)for q in f['baseline_px']];raw=[Vector(q)for q in f['polygon_px']];poly=[]
  for a,b in zip(raw,raw[1:]+raw[:1]):
   step=f['root_grid_px']if min(nearest_line(q,base)[0]for q in[a,b,(a+b)*.5])<f['root_band_px']+f['blend_px']else f['grid_px'];count=max(1,math.ceil((b-a).length/step));poly.extend(a.lerp(b,i/count)for i in range(count))
  points=poly[:]
  for step,near in[(f['grid_px'],False),(f['root_grid_px'],True)]:
   for yy in range(math.floor(min(q.y for q in poly)),math.ceil(max(q.y for q in poly))+1,round(step)):
    for xx in range(math.floor(min(q.x for q in poly)),math.ceil(max(q.x for q in poly))+1,round(step)):
     q=Vector((xx+.27,yy+.13))
     if inside(q,poly)and(not near or nearest_line(q,base)[0]<f['root_band_px']+f['blend_px']+3):points.append(q)
  verts,_,faces,*_=delaunay_2d_cdt([q/w for q in points],[(i,(i+1)%len(poly))for i in range(len(poly))],[list(range(len(poly)))],1,1e-8)
  canonical={};remap=[];source=[]
  for q in verts:
   key=(round(q.x*w,4),round(q.y*w,4))
   if key not in canonical:canonical[key]=len(source);source.append(q*w)
   remap.append(canonical[key])
  triangles=[];seen=set()
  for face in faces:
   ids=[remap[i]for i in face]
   for k in range(1,len(ids)-1):
    t=[ids[0],ids[k],ids[k+1]];key=tuple(sorted(t))
    if len(set(t))==3 and key not in seen:seen.add(key);triangles.append(t)
  used=sorted({i for t in triangles for i in t});remap={i:j for j,i in enumerate(used)};source=[source[i]for i in used];triangles=[[remap[i]for i in t]for t in triangles]
  positions=[];joints=[];weights=[];rootids=[];distances=[]
  for i,q in enumerate(source):
   distance,basal=nearest_line(q,base);distances.append(distance);bp=Vector((hi-(nose-basal.x)/ppu,f['root_y_native'],(mid-basal.y)/ppu));probe=bp.copy();probe.y+=distance/ppu*.65;hit,n,face,_=bvh.find_nearest(probe)
   root_target=hit-n*f['root_inset_native'];free=Vector((hi-(nose-q.x)/ppu,f['free_y_native'],(mid-q.y)/ppu));gain=1-smooth((distance-f['root_band_px'])/f['blend_px']);point=free.lerp(root_target,gain)
   isroot=distance<=f['root_band_px']+1e-5
   if isroot:rootids.append(i);point=root_target
   else:
    # Preserve the top-plan silhouette where possible. At the body seam use
    # the outward lateral intersection at this real height, never shrink fin.
    origin=Vector((point.x,point.y,side*2));h0,n0,_,_=bvh.ray_cast(origin,Vector((0,0,-side)),4.)
    clearance=f['free_half_thickness_native']+f['clearance_native']
    if h0 is not None:point.z=side*max(side*point.z,side*h0.z+clearance)
   positions.append(point);hh,nn,face,_=bvh.find_nearest(point);aa,bb,cc=tr[face];bw=barycentric_transform(hh,v[aa],v[bb],v[cc],Vector((1,0,0)),Vector((0,1,0)),Vector((0,0,1)));mix={};finweight=smooth((distance-f['root_band_px']-4)/max(25,100.))*.7
   for vi,g in zip((aa,bb,cc),bw):
    for j,amount in skin[vi].items():mix[j]=mix.get(j,0)+max(0,g)*amount*(1-finweight)
   mix[finbone]=mix.get(finbone,0)+finweight;items=sorted(mix.items(),key=lambda p:-p[1])[:4]
   while len(items)<4:items.append((0,0.))
   total=sum(amount for _,amount in items);joints.append([j for j,_ in items]);weights.append([amount/total for _,amount in items])
  ns=[Vector()for _ in positions]
  for a,b,c in triangles:
   n=(positions[b]-positions[a]).cross(positions[c]-positions[a])
   if n.y<0:b,c=c,b;n=-n
   for j in(a,b,c):ns[j]+=n
  # Orient every face consistently toward +Y before closing the thin shell.
  for t in triangles:
   if(positions[t[1]]-positions[t[0]]).cross(positions[t[2]]-positions[t[0]]).y<0:t[1],t[2]=t[2],t[1]
  ns=[n.normalized()if n.length>1e-12 else Vector((0,1,0))for n in ns];half=[f['root_half_thickness_native']+(f['free_half_thickness_native']-f['root_half_thickness_native'])*smooth((d-f['root_band_px'])/f['blend_px'])for d in distances];count=len(positions);solid=[q+ns[i]*half[i]for i,q in enumerate(positions)]+[q-ns[i]*half[i]for i,q in enumerate(positions)];alltri=triangles+[[count+c,count+b,count+a]for a,b,c in triangles];edges={}
  for t in triangles:
   for a,b in zip(t,t[1:]+t[:1]):edges.setdefault(tuple(sorted((a,b))),[]).append((a,b))
  for rows in edges.values():
   if len(rows)==1:
    a,b=rows[0];alltri.extend([[a,count+a,count+b],[a,count+b,b]])
  uv=[(q.x/w,q.y/h)for q in source];uv+=uv;normal=ns+[-n for n in ns];image=Path(f['texture']['path']).read_bytes();binary.extend(b'\0'*(-len(binary)%4));off=len(binary);binary.extend(image);view=len(doc['bufferViews']);doc['bufferViews'].append({'buffer':0,'byteOffset':off,'byteLength':len(image)});ii=len(doc['images']);doc['images'].append({'name':name+' native top151 source cut','bufferView':view,'mimeType':'image/png'});sampler=len(doc['samplers']);doc['samplers'].append({'magFilter':9728,'minFilter':9728,'wrapS':33071,'wrapT':33071});tx=len(doc['textures']);doc['textures'].append({'source':ii,'sampler':sampler});mi=len(doc['materials']);doc['materials'].append({'name':name+' top151 pixel material','pbrMetallicRoughness':{'baseColorTexture':{'index':tx},'metallicFactor':0.,'roughnessFactor':1.},'doubleSided':True,'alphaMode':'MASK','alphaCutoff':.5})
  attrs={'POSITION':put([tuple(q)for q in solid],'VEC3'),'NORMAL':put([tuple(q)for q in normal],'VEC3'),'TEXCOORD_0':put(uv,'VEC2'),'JOINTS_0':put(joints+joints,'VEC4',5123),'WEIGHTS_0':put(weights+weights,'VEC4')};index=put([(j,)for t in alltri for j in t],'SCALAR',5125);doc['meshes'][node['mesh']]={'name':name,'primitives':[{'attributes':attrs,'indices':index,'material':mi,'mode':4}]};roots=rootids+[j+count for j in rootids];spec['fins'][name].update(ids=roots,rest_points_gltf=[list(solid[i])for i in roots],vertices=len(solid),source_baseline=[[q[0]/w,q[1]/h]for q in f['baseline_px']],rule='Complete source top1515pixel basal strip, finite wrapped support; not resized side fin')
  records.append({'name':name,'vertices':len(solid),'triangles':len(alltri),'roots':len(roots),'source_cut_sha256':sha(f['texture']['path'])})
 assert bytes(binary[:len(original)])==original;target=out/'fish.glb';write(target,doc,binary);spec.update(model=str(target),model_sha256=sha(target));spec['membrane_clearance']['targets']=[f['name']for f in p['fins']];spec['repair_body_geometry']=p['body'];spec['repair_body_geometry_sha256']=sha(p['body']);spec['membrane_clearance']['contact_edge_length_native']=.002
 (out/'candidate.plan.json').write_text(json.dumps(plan,indent=2));(out/'build.validation.json').write_text(json.dumps({'ok':True,'model_sha256':sha(target),'plan_sha256':sha(sys.argv[sys.argv.index('--')+1]),'records':records,'scope':'Top-source horizontal geometry and native cutouts; finite/root/action and visual gates pending.'},indent=2));print(json.dumps({'ok':True,'records':records}))
if __name__=='__main__':main()
