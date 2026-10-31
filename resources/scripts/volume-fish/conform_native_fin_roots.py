"""Blender: fit newly outlined finite fin bands to the accepted body's surface.

Only target fin cages change. No body, head, mouth, eye, retained fin, bone or
animation edit. Adaptive edge splits repair actual sampled finite-face faults.
"""
import sys,json,copy,struct,hashlib
from pathlib import Path
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.geometry import barycentric_transform
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE));sys.path.insert(0,str(HERE/'portable'))
from glb_io import read_glb,arrays,sha
from patch_existing_fin_meshes import write
def load(p):return json.loads(Path(p).read_text(encoding='utf8'))
def save(p,d):Path(p).write_text(json.dumps(d,indent=2,ensure_ascii=False)+'\n',encoding='utf8')
def line_distance(q,line):
 a=line[:-1];v=np.diff(line,axis=0);t=np.clip(((q-a)*v).sum(1)/np.maximum((v*v).sum(1),1e-12),0,1);return float(np.min(np.linalg.norm(a+t[:,None]*v-q,axis=1)))
def main():
 source=Path(sys.argv[sys.argv.index('--')+1]).resolve();out=Path(sys.argv[sys.argv.index('--')+2]).resolve();assert not out.exists()and'/experiments/'in out.as_posix();out.mkdir(parents=True)
 report=load(source/'author.validation.json');cfg=load(report['input_masks']['path']);masks={r['name']:r for r in cfg['fins']};settings_path=HERE.parents[2]/'resources/volume-fish/fin-detail-cage-20261031.json';settings=load(settings_path)[cfg['species']];packing=load(source/'packing.validation.json');d,b=read_glb(source/'author-reference.glb');b=bytearray(b);pr=d['meshes'][0]['primitives'][0];attrs={k:arrays(d,b,v)for k,v in pr['attributes'].items()};ids=arrays(d,b,pr['indices']).reshape(-1);parts=d['extras']['geometry_parts'];scale=load(Path(report['baseline']['path']).parent/'capture.plan.json')['model_scale'];uvscale=np.array(packing['atlas']['size']);bv=[Vector(v)for v in attrs['POSITION']];bf=[]
 for part in parts:
  if part['role']=='body_skin':
   i=part['index_start'];bf.extend(tuple(map(int,t))for t in ids[i:i+part['index_count']].reshape(-1,3))
 if sum(bv[a].dot(bv[c].cross(bv[e]))for a,c,e in bf)<0:bf=[t[::-1]for t in bf]
 tree=BVHTree.FromPolygons(bv,bf,all_triangles=True);ray=Vector((.231,.371,.899)).normalized()
 def surface(q):
  q=Vector(q);hit,no,face,dist=tree.find_nearest(q);rh,rn,_,_=tree.ray_cast(q,ray);inside=rh is not None and rn.dot(ray)>0;return hit,no,face,(-dist if inside else dist)
 def body_skin(q,face):
  vs=bf[face];bw=barycentric_transform(q,*[bv[i]for i in vs],Vector((1,0,0)),Vector((0,1,0)),Vector((0,0,1)));mix=np.zeros(18)
  for v,gain in zip(vs,bw):
   for joint,value in zip(attrs['JOINTS_0'][v],attrs['WEIGHTS_0'][v]):mix[int(joint)]+=max(0,gain)*value
  mix[mix<1e-4]=0;js=np.argsort(-mix)[:4];ws=mix[js];ws/=ws.sum();return js,ws
 newattrs={k:[]for k in attrs};newids=[];newparts=[];newpack=[];records=[];vo=ioff=0;fixed_count=sum(p['index_count']//3 for p in parts if not any(p['source_node'].startswith(k+'_')for k in masks));remaining=2000-fixed_count
 for part,packed in zip(parts,packing['parts']):
  start=part['vertex_start'];end=start+part['vertex_count'];begin=part['index_start'];tri=ids[begin:begin+part['index_count']].reshape(-1,3).astype(int)-start;v={k:x[start:end].copy()for k,x in attrs.items()};kind=next((k for k in masks if part['source_node'].startswith(k+'_')),None);proof=None
  if kind:
   mr=masks[kind];root=np.array(mr['root_px']);place=np.array(packed['atlas_placement']);px=v['TEXCOORD_0']*uvscale-place;rows=[{k:x[i].tolist()for k,x in v.items()}for i in range(len(px))]
   for i,row in enumerate(rows):row.update(px=px[i].tolist(),root=line_distance(px[i],root)<=17,layer=i>=len(px)//2)
   def attach(row):
    hit,no,face,signed=surface(row['POSITION']);isroot=row['root'];target=(.00007 if row['layer']else .00004)/scale if isroot else settings['free_clearance_mm']/1000/scale
    if isroot or signed<target:
     row['POSITION']=list(hit+no*target)
     js,ws=body_skin(hit,face)
     # Entire frozen basal band inherits the actual local body surface.
     # Newly sampled clearance vertices close to it retain that influence.
     if isroot:row['JOINTS_0']=js.tolist();row['WEIGHTS_0']=ws.tolist()
   for row in rows:attach(row)
   history=[];original_n=len(rows)
   for iteration in range(12):
    marked=set();worst=0.
    for t in tri:
     q=[Vector(rows[int(i)]['POSITION'])for i in t];a,c,e=q;allroot=all(rows[int(i)]['root']for i in t);limit=(.00040 if allroot else .00001)/scale;probes=[(a+c+e)/3,a*.6+c*.2+e*.2,a*.2+c*.6+e*.2,a*.2+c*.2+e*.6]+[x.lerp(y,f)for x,y in zip(q,q[1:]+q[:1])for f in [.25,.5,.75]]
     if any(surface(q)[3]<-limit for q in probes):
      edges=[tuple(sorted((int(x),int(y))))for x,y in zip(t,np.roll(t,-1))];marked.add(max(edges,key=lambda e:(Vector(rows[e[0]]['POSITION'])-Vector(rows[e[1]]['POSITION'])).length_squared))
    history.append({'round':iteration,'split_edges':len(marked)})
    if not marked:break
    mids={}
    for aa,bb in sorted(marked):
     x,y=rows[aa],rows[bb];qpx=(np.array(x['px'])+y['px'])/2;row={k:((np.array(x[k])+y[k])/2).tolist()for k in ['POSITION','NORMAL','TEXCOORD_0']};row.update(px=qpx.tolist(),root=line_distance(qpx,root)<=17,layer=x['layer']and y['layer']);mix=np.zeros(18)
     for source_row in [x,y]:
      for j,w in zip(source_row['JOINTS_0'],source_row['WEIGHTS_0']):mix[int(j)]+=.5*w
     mix[mix<1e-4]=0;js=np.argsort(-mix)[:4];ws=mix[js];ws/=ws.sum();row.update(JOINTS_0=js.tolist(),WEIGHTS_0=ws.tolist());attach(row);mids[(aa,bb)]=len(rows);rows.append(row)
    rebuilt=[]
    for t in tri:
     pieces=[tuple(map(int,t))]
     for aa,bb in zip(t,np.roll(t,-1)):
      mid=mids.get(tuple(sorted((int(aa),int(bb)))))
      if mid is None:continue
      expanded=[]
      for piece in pieces:
       if aa not in piece or bb not in piece:expanded.append(piece);continue
       for k in range(3):
        x,y,z=piece[k],piece[(k+1)%3],piece[(k+2)%3]
        if {x,y}=={aa,bb}:expanded.extend([(x,mid,z),(mid,y,z)]);break
      pieces=expanded
     rebuilt.extend(pieces)
    tri=np.array(rebuilt,dtype=int);assert len(tri)<=remaining,('Adaptive repair exceeds whole-fish budget',part['source_node'],len(tri),remaining,history)
   assert not marked,('Finite static root adaptation did not converge',part['source_node']);remaining-=len(tri);v={k:np.array([r[k]for r in rows],dtype='<u2'if k=='JOINTS_0'else'<f4')for k in attrs};norm=np.zeros_like(v['POSITION'])
   for t in tri:
    x,y,z=v['POSITION'][t];n=np.cross(y-x,z-x)
    for i in t:norm[i]+=n
   norm/=np.maximum(np.linalg.norm(norm,axis=1)[:,None],1e-12);v['NORMAL']=norm
   outset=settings.get('outward_mm',{}).get(part['source_node'],0)
   if outset:v['POSITION'][:,2]+=np.sign(v['POSITION'][:,2].mean())*outset/1000/scale
   translation=settings.get('translation_mm',{}).get(part['source_node'],[0,0,0]);v['POSITION']+=np.array(translation)/1000/scale
   rootids=[i for i,r in enumerate(rows)if r['root']];proof={'name':part['source_node'],'added_vertices':len(rows)-original_n,'history':history,'triangles':len(tri),'outward_mm':outset,'root_band_ids':rootids,'root_band_rest_points_gltf':v['POSITION'][rootids].tolist(),'root_strategy':'Entire original 17px finite source band, locally projected to actual body and inherits actual barycentric body weights; original rig unchanged.'};records.append(proof)
  for k in attrs:newattrs[k].append(v[k])
  row=copy.deepcopy(part);row.update(vertex_start=vo,source_vertex_start=vo,vertex_count=len(v['POSITION']),index_start=ioff,index_count=tri.size);newparts.append(row);row=copy.deepcopy(packed);row.update(new_vertex_range=[vo,vo+len(v['POSITION'])],new_index_range=[ioff,ioff+tri.size]);newpack.append(row);newids.extend((tri.reshape(-1)+vo).tolist());vo+=len(v['POSITION']);ioff+=tri.size
 assert ioff//3<=2000
 def append(raw):
  b.extend(b'\0'*(-len(b)%4));offset=len(b);b.extend(raw);idx=len(d['bufferViews']);d['bufferViews'].append({'buffer':0,'byteOffset':offset,'byteLength':len(raw)});return idx
 def put(ar,kind,ctype):
  ar=np.ascontiguousarray(ar);idx=len(d['accessors']);row={'bufferView':append(ar.tobytes()),'componentType':ctype,'count':len(ar),'type':kind}
  if kind=='VEC3':row.update(min=ar.min(0).tolist(),max=ar.max(0).tolist())
  d['accessors'].append(row);return idx
 for k in attrs:pr['attributes'][k]=put(np.concatenate(newattrs[k]).astype('<u2'if k=='JOINTS_0'else'<f4'),{'POSITION':'VEC3','NORMAL':'VEC3','TEXCOORD_0':'VEC2','JOINTS_0':'VEC4','WEIGHTS_0':'VEC4'}[k],5123 if k=='JOINTS_0' else 5126)
 pr['indices']=put(np.array(newids,dtype='<u4'),'SCALAR',5125);d['extras']['geometry_parts']=newparts;dest=out/'author-reference.glb';write(dest,d,b)
 for name in ['atlas.png','parts.json']:(out/name).write_bytes((source/name).read_bytes())
 packing.update(parts=newpack,candidates={'author-reference':{'path':str(dest),'sha256':sha(dest)}},atlas={**packing['atlas'],'path':str(out/'atlas.png')});save(out/'packing.validation.json',packing)
 report.update(parent_author={'path':str(source/'author.validation.json'),'sha256':sha(source/'author.validation.json')},triangles_after=ioff//3,vertices_after=vo,model=str(dest),model_sha256=sha(dest),fins=records,static_finite_surface_check=True,physical_acceptance='Full current posed gates pending');save(out/'author.validation.json',report);print(json.dumps({'ok':True,'triangles':ioff//3,'vertices':vo,'records':[{k:r[k]for k in ['name','added_vertices','history']}for r in records]}))
if __name__=='__main__':main()
