"""Blender: conform explicit precise native fin cages to their own current body.

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
 report=load(source/'author.validation.json');cfg=load(report['input_masks']['path']);masks={r['fin']:r for r in cfg['fins']};settings={'free_clearance_mm':0.2};author_fins={r['name']:r for r in report['fins']};packing=load(source/'packing.validation.json');d,b=read_glb(source/'author-reference.glb');b=bytearray(b);pr=d['meshes'][0]['primitives'][0];attrs={k:arrays(d,b,v)for k,v in pr['attributes'].items()};ids=arrays(d,b,pr['indices']).reshape(-1);parts=d['extras']['geometry_parts'];scale=load(Path(report['baseline']['path']).parent/'capture.plan.json')['model_scale'];uvscale=np.array(packing['atlas']['size']);bones=len(d['skins'][0]['joints']);bv=[Vector(v)for v in attrs['POSITION']];bf=[]
 for part in parts:
  if part['role']=='body_skin':
   i=part['index_start'];bf.extend(tuple(map(int,t))for t in ids[i:i+part['index_count']].reshape(-1,3))
 if sum(bv[a].dot(bv[c].cross(bv[e]))for a,c,e in bf)<0:bf=[t[::-1]for t in bf]
 tree=BVHTree.FromPolygons(bv,bf,all_triangles=True);ray=Vector((.231,.371,.899)).normalized()
 def surface(q):
  q=Vector(q);hit,no,face,dist=tree.find_nearest(q);rh,rn,_,_=tree.ray_cast(q,ray);inside=rh is not None and rn.dot(ray)>0;return hit,no,face,(-dist if inside else dist)
 def body_skin(q,face):
  vs=bf[face];bw=barycentric_transform(q,*[bv[i]for i in vs],Vector((1,0,0)),Vector((0,1,0)),Vector((0,0,1)));mix=np.zeros(bones)
  for v,gain in zip(vs,bw):
   for joint,value in zip(attrs['JOINTS_0'][v],attrs['WEIGHTS_0'][v]):mix[int(joint)]+=max(0,gain)*value
  mix[mix<1e-4]=0;js=np.argsort(-mix)[:4];ws=mix[js];ws/=ws.sum();return js,ws
 newattrs={k:[]for k in attrs};newids=[];newparts=[];newpack=[];records=[];vo=ioff=0;fixed_count=sum(p['index_count']//3 for p in parts if not any(p['source_node'].startswith(k+'_')for k in masks));remaining=2000-fixed_count
 for part,packed in zip(parts,packing['parts']):
  start=part['vertex_start'];end=start+part['vertex_count'];begin=part['index_start'];tri=ids[begin:begin+part['index_count']].reshape(-1,3).astype(int)-start;v={k:x[start:end].copy()for k,x in attrs.items()};kind=next((k for k in masks if part['source_node'].startswith(k+'_')),None);proof=None
  if kind:
   mr=masks[kind];original_author=author_fins[part['source_node']];root=np.array(mr['source_root_local_px']);band_px=original_author['root_band_px'];place=np.array(packed['atlas_placement']);px=v['TEXCOORD_0']*uvscale-place+packed['virtual_crop_origin'];rows=[{k:x[i].tolist()for k,x in v.items()}for i in range(len(px))];clearance=load(report['entry'])['fin_cage']
   paired=part['source_node'].endswith(('_left_mesh','_right_mesh'));direction=1 if v['POSITION'][:,1].mean()>0 else -1;side=1 if v['POSITION'][:,2].mean()>0 else -1
   flank_ids=[i for i,t in enumerate(bf)if all(bv[j].z*side>=-1e-8 for j in t)]if paired else[]
   flank=BVHTree.FromPolygons(bv,[bf[i]for i in flank_ids],all_triangles=True)if paired else None
   def directional_surface(point):
    point=Vector(point)
    if paired:
     hit,no,face,dist=flank.find_nearest(point);return hit,no,flank_ids[face],surface(point)[3]
    hit,no,face,_=tree.ray_cast(Vector((point.x,direction*2,point.z)),Vector((0,-direction,0)),4)
    if hit is None:return surface(point)
    signed=(point.y-hit.y)*direction;return hit,no,face,signed
   for i,row in enumerate(rows):row.update(px=px[i].tolist(),root=line_distance(px[i],root)<=band_px,layer=i>=len(px)//2)
   def attach(row):
    hit,no,face,signed=directional_surface(row['POSITION']);isroot=row['root'];target=(clearance['root_offset_mm'][int(row['layer'])]if isroot else clearance['free_clearance_mm'])/1000/scale
    if isroot or signed<target:
     row['POSITION']=list(hit+no*target)if paired else list(hit+Vector((0,direction*target/max(abs(no.y),.1),0)))
     js,ws=body_skin(hit,face)
     # Entire frozen basal band inherits the actual local body surface.
     # Newly sampled clearance vertices close to it retain that influence.
     if isroot:row['JOINTS_0']=js.tolist();row['WEIGHTS_0']=ws.tolist()
   def lift_pair(pair):
    axis=2 if paired else 1;sgn=side if paired else direction;lift=0.
    for row in pair:
     q=Vector(row['POSITION']);origin=q.copy();origin[axis]=sgn*2;ray_direction=Vector();ray_direction[axis]=-sgn;hit,no,face,_=tree.ray_cast(origin,ray_direction,4)
     if hit is not None:lift=max(lift,sgn*(hit[axis]-q[axis])+clearance['free_clearance_mm']/1000/scale)
    for row in pair:row['POSITION'][axis]+=sgn*max(0,lift)
   for i in range(len(rows)//2):
    pair=[rows[i],rows[i+len(rows)//2]]
    assert np.linalg.norm(np.array(pair[0]['px'])-pair[1]['px'])<.004
    if pair[0]['root']:
     for row in pair:attach(row)
    else:lift_pair(pair)
   history=[];original_n=len(rows)
   for iteration in range(18):
    marked=set();worst=0.;faults=[]
    for t in tri:
     q=[Vector(rows[int(i)]['POSITION'])for i in t];a,c,e=q;allroot=all(rows[int(i)]['root']for i in t);limit=(.00040 if allroot else .00001)/scale;probes=[(a+c+e)/3,a*.6+c*.2+e*.2,a*.2+c*.6+e*.2,a*.2+c*.2+e*.6]+[x.lerp(y,f)for x,y in zip(q,q[1:]+q[:1])for f in [.25,.5,.75]]
     depths=[surface(q)[3]for q in probes]
     if min(depths)<-limit or(allroot and max(depths)>.00048/scale):
      if len(faults)<3:faults.append({'ids':t.tolist(),'root_flags':[rows[int(i)]['root']for i in t],'depth_mm':min(depths)*scale*1000,'points':[rows[int(i)]['POSITION']for i in t]})
      edges=[tuple(sorted((int(x),int(y))))for x,y in zip(t,np.roll(t,-1))];marked.add(max(edges,key=lambda e:(Vector(rows[e[0]]['POSITION'])-Vector(rows[e[1]]['POSITION'])).length_squared))
    history.append({'round':iteration,'split_edges':len(marked),'triangles':len(tri),'vertices':len(rows),'faults':faults})
    save(out/'adaptation.progress.json',{'part':part['source_node'],'history':history,'remaining_budget':remaining})
    if not marked:break
    # Mirrored finite layers split together. Independent clipping of one cap
    # can collapse or invert a foil even when its vertices clear the body.
    actual_edges={tuple(sorted((int(a),int(b))))for t in tri for a,b in zip(t,np.roll(t,-1))}
    def mate(i):
     choices=[j for j,r in enumerate(rows)if r['layer']!=rows[i]['layer']]
     if not choices:return None
     distances=[np.linalg.norm(np.array(rows[j]['px'])-rows[i]['px'])for j in choices];j=int(np.argmin(distances));return choices[j]if distances[j]<.004 else None
    for aa,bb in list(marked):
     if rows[aa]['layer']==rows[bb]['layer']:
      ma,mb=mate(aa),mate(bb)
      if ma is not None and mb is not None and tuple(sorted((ma,mb)))in actual_edges:marked.add(tuple(sorted((ma,mb))))
    mids={}
    for aa,bb in sorted(marked):
     x,y=rows[aa],rows[bb];qpx=(np.array(x['px'])+y['px'])/2;row={k:((np.array(x[k])+y[k])/2).tolist()for k in ['POSITION','NORMAL','TEXCOORD_0']};row.update(px=qpx.tolist(),root=line_distance(qpx,root)<=band_px,layer=x['layer']and y['layer']);mix=np.zeros(bones)
     for source_row in [x,y]:
      for j,w in zip(source_row['JOINTS_0'],source_row['WEIGHTS_0']):mix[int(j)]+=.5*w
     mix[mix<1e-4]=0;js=np.argsort(-mix)[:4];ws=mix[js];ws/=ws.sum();row.update(JOINTS_0=js.tolist(),WEIGHTS_0=ws.tolist());mids[(aa,bb)]=len(rows);rows.append(row)
    handled=set()
    for i in mids.values():
     if i in handled:continue
     row=rows[i]
     if row['root']:attach(row);handled.add(i);continue
     other=mate(i)
     if other is not None and other in mids.values()and not rows[other]['root']:lift_pair([row,rows[other]]);handled.update([i,other])
     else:attach(row);handled.add(i)
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
   assert not marked,('Finite static root adaptation did not converge',part['source_node']);coalesced=[]
   # A nearest finite-body projection can coalesce two subpixel support
   # corners. Remove only exact redundant root edges with identical skin.
   # This preserves the entire physical root-point set, not a narrower band.
   while True:
    xyz=np.array([r['POSITION']for r in rows]);areas=np.linalg.norm(np.cross(xyz[tri[:,1]]-xyz[tri[:,0]],xyz[tri[:,2]]-xyz[tri[:,0]]),axis=1);bad=np.where(areas<=1e-16)[0]
    if not len(bad):break
    face=tri[bad[0]];edge=next(((int(a),int(b))for a,b in zip(face,np.roll(face,-1))if np.linalg.norm(xyz[a]-xyz[b])<1e-10 and rows[int(a)]['root']and rows[int(b)]['root']),None);assert edge,('Nonredundant zero-area fin face',part['source_node'],face.tolist());aa,bb=edge
    def skin_map(i):return {int(j):float(w)for j,w in zip(rows[i]['JOINTS_0'],rows[i]['WEIGHTS_0'])if w>0}
    sa,sb=skin_map(aa),skin_map(bb);assert max(abs(sa.get(k,0)-sb.get(k,0))for k in set(sa)|set(sb))<1e-6,'Coincident roots with different dynamic skin cannot merge';tri[tri==bb]=aa;tri=tri[np.array([len(set(t))==3 for t in tri])];coalesced.append({'kept':aa,'redundant':bb,'position_error_native':float(np.linalg.norm(xyz[aa]-xyz[bb])),'skin_error_below':1e-6})
   if coalesced:
    used=np.unique(tri);mapping={int(v):i for i,v in enumerate(used)};tri=np.array([[mapping[int(v)]for v in t]for t in tri]);rows=[rows[i]for i in used]
   remaining-=len(tri);v={k:np.array([r[k]for r in rows],dtype='<u2'if k=='JOINTS_0'else'<f4')for k in attrs};norm=np.zeros_like(v['POSITION'])
   for t in tri:
    x,y,z=v['POSITION'][t];n=np.cross(y-x,z-x)
    for i in t:norm[i]+=n
   norm/=np.maximum(np.linalg.norm(norm,axis=1)[:,None],1e-12);v['NORMAL']=norm
   outset=settings.get('outward_mm',{}).get(part['source_node'],0)
   if outset:v['POSITION'][:,2]+=np.sign(v['POSITION'][:,2].mean())*outset/1000/scale
   translation=settings.get('translation_mm',{}).get(part['source_node'],[0,0,0]);v['POSITION']+=np.array(translation)/1000/scale
   rootids=[i for i,r in enumerate(rows)if r['root']];proof={'name':part['source_node'],'kind':kind,'root_band_px':band_px,'root_px':root.tolist(),'foil_target_mm':original_author['foil_target_mm'],'source_band_fraction':original_author['source_band_fraction'],'added_vertices':len(rows)-original_n,'coalesced_exact_redundant_roots':coalesced,'history':history,'triangles':len(tri),'outward_mm':outset,'root_band_ids':rootids,'root_band_rest_points_gltf':v['POSITION'][rootids].tolist(),'root_strategy':'Independent complete native basal curve, at least original full source-band width (minimum17px), both layers projected to actual finite body; actual body weights, original rig/actions preserved.'};records.append(proof)
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
