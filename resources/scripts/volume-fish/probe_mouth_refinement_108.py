#!/usr/bin/env python3
"""Single frozen bounded conforming CPU trial108. Never writes model/runtime assets."""
import argparse,json,hashlib,struct
from pathlib import Path
from collections import defaultdict,Counter
import numpy as np
from PIL import Image,ImageDraw,ImageFont
from audit_mouth_refinement_108 import load_frozen_field
from validate_oral_cdt_108 import crossing

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--input',required=True,type=Path);ap.add_argument('--output',required=True,type=Path);a=ap.parse_args();b=a.input.resolve().parent;a.output.mkdir(parents=True,exist_ok=True)
 readonly=json.loads(a.input.read_text());script=Path(__file__).with_name('probe_mouth_monotone_108.py');frozen=json.loads((b/'cpu-y-uv-monotone/monotone-frozen.validation.json').read_text());assert sha(script)==next(v for k,v in frozen['dependencies_sha256'].items() if k.endswith('/probe_mouth_monotone_108.py'))
 ns=load_frozen_field(script,b/'source-mouth-alignment.validation.json');st=ns['st'];data=ns['data'];old=ns['old'];canvas=ns['canvas'];ev=ns['evaluate'];cfg=json.loads((b/'cpu-upper-cdt/cdt-input-frozen.validation.json').read_text());cdt=json.loads((b/'cpu-upper-cdt/cdt-api-result.validation.json').read_text());skin=np.array(data[0]['indices']).reshape(-1,3);oral=np.array(data[1]['indices']).reshape(-1,3);keep=np.ones(len(oral),bool);keep[cfg['old_oral_triangle_ids']]=False;oral=np.r_[oral[keep],np.array([p['oral_actual_vertex_id'] for p in cfg['points']])[np.array(cdt['input_origin_faces'])]];n=len(st[0]);inputv=np.concatenate(st);original=np.r_[skin,oral+n];srcfaces=[skin,oral]
 # Exact geometric identity, shared across hardedge/material domains; attributes stay face-local barycentric.
 geom=[];keyid={};actualgeo=[]
 for p in inputv:
  key=tuple(p)
  if key not in keyid:keyid[key]=len(geom);geom.append(p.copy())
  actualgeo.append(keyid[key])
 actualgeo=np.array(actualgeo);basefaces=actualgeo[original];roots=[]
 for i,tri in enumerate(basefaces):roots.append({'g':tuple(map(int,tri)),'root':i,'depth':0,'bary':np.eye(3)})
 faces={i:t for i,t in enumerate(roots)};nextface=len(faces);geom=list(geom);adj=defaultdict(set)
 def add_adj(fid,t):
  for u,v in zip(t['g'],np.roll(t['g'],-1)):adj[tuple(sorted((int(u),int(v))))].add(fid)
 def del_adj(fid,t):
  for u,v in zip(t['g'],np.roll(t['g'],-1)):
   key=tuple(sorted((int(u),int(v))));adj[key].remove(fid)
   if not adj[key]:del adj[key]
 for i,t in faces.items():add_adj(i,t)
 initial=set(readonly['selected_combined_triangle_ids']);neighbor={j for edge,ids in adj.items() if ids&initial for j in ids}-initial;allowed=initial|neighbor;assert len(initial)==761 and len(neighbor)==125
 baselineparents=[]
 ct=Counter(tuple(sorted((int(u),int(v)))) for f in basefaces[:len(skin)] for u,v in zip(f,np.roll(f,-1)))
 for e,c in ct.items():
  if c==1:baselineparents.append(e)
 assert len(baselineparents)==397
 parents={e:{0.:e[0],1.:e[1]} for e in baselineparents};edgeparent={e:(e,0.,1.) for e in baselineparents};midcache={};generated=0;splits=0;events=[];fail=None;iteration=0;history=[]
 def mapped(g):
  q=canvas(np.asarray(g));out,dy,uv=ev(q,True);v=np.asarray(g).copy();on=out[:,1]!=q[:,1];v[on,1]=(371-out[on,1])/2024;return v,out,dy,uv
 def finite_check():
  ids=sorted(faces);ff=np.array([faces[i]['g'] for i in ids]);vv,q,dy,uv=mapped(geom);tt=np.asarray(geom)[ff];ot=vv[ff];normal=np.cross(tt[:,1]-tt[:,0],tt[:,2]-tt[:,0]);on=np.cross(ot[:,1]-ot[:,0],ot[:,2]-ot[:,0]);cent=canvas(tt.mean(1));_,cdy,_=ev(cent);eps=1e-4;dx=(ev(cent+[eps,0])[0][:,1]-ev(cent-[eps,0])[0][:,1])/(2*eps);expected=normal.copy();expected[:,0]+=dx/cdy*normal[:,1];expected[:,1]/=cdy;dot=(expected*on).sum(1);valid=np.linalg.norm(normal,axis=1)>1e-14;bad=(valid&((dot<=0)|(np.linalg.norm(on,axis=1)<=1e-14)));changed=np.zeros(len(geom),bool)
  for j in ids:
   t=faces[j]
   if t['root'] in allowed or t['root']>=len(skin) and t['root']>=len(original)-97:changed[list(t['g'])]=True
  changed|=np.any(vv!=np.asarray(geom),axis=1);cr=crossing(vv,ff,changed);badids={ids[j] for j in np.flatnonzero(bad)};badids|={ids[j] for pair in cr['pairs'] for j in pair};badids|={ids[j] for r in cr['coplanar_overlap_examples'] for j in r['pair']};return ids,ff,vv,cr,badids,{'opposite_or_degenerate':int(bad.sum()),'minimum_sampled_dYdY':float(min(dy.min(),cdy.min()))}
 frozenout={'status':'approved_single_cpu_refinement_frozen','asset_written':False,'scale':'original_Stage1_XY_longest_edge<=1nativepixel','max_depth_per_original_face':8,'max_cumulative_generated_children':50000,'allowed_roots':sorted(allowed),'initial_roots':sorted(initial),'neighbor_roots':sorted(neighbor),'field_unchanged':True,'dependencies':{str(p):sha(p) for p in [a.input,script,Path(__file__),b/'phase2e-conforming-refinement-proposal.md',b/'cpu-y-uv-monotone/monotone-frozen.validation.json',b/'cpu-upper-cdt/cdt-api-result.validation.json']}};(a.output/'refinement-frozen.validation.json').write_text(json.dumps(frozenout,indent=2)+'\n')
 while True:
  iteration+=1;marks=set()
  for fid,t in faces.items():
   if t['root'] not in initial:continue
   p=canvas(np.array([geom[g] for g in t['g']]));lens=np.linalg.norm(p-np.roll(p,-1,axis=0),axis=1)
   if lens.max()>1:marks.add(fid)
  if not marks:
   ids,ff,vv,cr,badids,ori=finite_check();history.append({'iteration':iteration,'faces':len(faces),'generated_children':generated,'crossings':cr['proper_crossings'],'coplanar_overlap':cr['coplanar_positive_area_overlap_pairs'],**ori});marks=badids
   if not marks:break
  requests=[]
  for fid in sorted(marks):
   t=faces[fid]
   if t['root'] not in allowed:fail={'kind':'cross_flip_outside_frozen_scope','face':fid,'root':t['root']};break
   points=canvas(np.array([geom[g] for g in t['g']]));edges=[tuple(sorted((int(u),int(v)))) for u,v in zip(t['g'],np.roll(t['g'],-1))];lengths=np.linalg.norm(points-np.roll(points,-1,axis=0),axis=1);mx=max(lengths)
   if mx==0:fail={'kind':'zero_XY_edge_with_failure','face':fid};break
   requests.append(sorted(e for e,l in zip(edges,lengths) if l==mx)[0])
  if fail:break
  # A fixed batch of marked faces; each edge uses current incidence, ensuring closure children count.
  for edge in sorted(set(requests)):
   if edge not in adj:continue
   touching=sorted(adj[edge]);outside=[i for i in touching if faces[i]['root'] not in allowed]
   if outside:fail={'kind':'closure_outside_frozen_761_plus125','edge':list(edge),'outside_roots':[faces[i]['root'] for i in outside]};break
   blocked=[i for i in touching if faces[i]['depth']>=8]
   if blocked:fail={'kind':'maximum_per_original_face_depth8','edge':list(edge),'blocked_roots':[faces[i]['root'] for i in blocked],'blocked_faces':blocked};break
   if generated+2*len(touching)>50000:fail={'kind':'cumulative_generated_children_budget50000','would_generate':generated+2*len(touching)};break
   if edge in midcache:raise ValueError('split edge unexpectedly remains after conforming closure')
   m=len(geom);geom.append((np.array(geom[edge[0]])+geom[edge[1]])/2);midcache[edge]=m
   if edge in edgeparent:
    pe,t0,t1=edgeparent.pop(edge);tm=(t0+t1)/2;parents[pe][tm]=m
    for aa,bb,ta,tb in [(edge[0],m,t0,tm),(m,edge[1],tm,t1)]:
     ee=tuple(sorted((aa,bb)));edgeparent[ee]=(pe,ta,tb) if aa<bb else (pe,tb,ta)
   for fid in touching:
    t=faces.pop(fid);del_adj(fid,t);g=list(t['g']);ia=g.index(edge[0]);ib=g.index(edge[1]);k=3-ia-ib;bb=(t['bary'][ia]+t['bary'][ib])/2
    # Keep original triangle winding; rotate to directed edge and opposing corner.
    ia,ib=next((j,(j+1)%3) for j in range(3) if {g[j],g[(j+1)%3]}==set(edge));k=(ib+1)%3
    for indices,bary in [((g[ia],m,g[k]),np.array([t['bary'][ia],bb,t['bary'][k]])),((m,g[ib],g[k]),np.array([bb,t['bary'][ib],t['bary'][k]]))]:
     child={'g':indices,'root':t['root'],'depth':t['depth']+1,'bary':bary};faces[nextface]=child;add_adj(nextface,child);nextface+=1
   generated+=2*len(touching);splits+=1
  events.append({'iteration':iteration,'marked_faces':len(marks),'requested_edges':len(set(requests)),'faces':len(faces),'generated_children':generated,'max_depth':max(t['depth'] for t in faces.values())})
  if fail:break
 ids,ff,vv,cr,badids,ori=finite_check();q=canvas(np.array(geom));mappedq=canvas(vv);allclosed=all(len(v)==2 for v in adj.values());parentreports=[]
 for pe,chain in parents.items():
  ch=sorted(chain.items());ok=True
  for (_,u),(_,v) in zip(ch,ch[1:]):
   edge=tuple(sorted((u,v)));inc=adj.get(edge,set());dirs=[]
   for fid in inc:
    t=faces[fid];sg=0 if t['root']<len(skin) else 1
    for aa,bb in zip(t['g'],np.roll(t['g'],-1)):
     if {int(aa),int(bb)}==set(edge):dirs.append((sg,int(aa)==u))
   ok&=len(dirs)==2 and dirs[0][0]!=dirs[1][0] and dirs[0][1]!=dirs[1][1]
  parentreports.append({'parent':list(pe),'segments':len(ch)-1,'covered_0_1':ch[0][0]==0 and ch[-1][0]==1,'opposite_skin_oral_children':bool(ok)})
 # Baseline640 and both eyes compare original actual arrays, not merely Stage1.
 checks=[]
 for s in range(2):
  ey=np.array(ns['eye']['surfaces'][s]['frozen_vertex_ids']);off=0 if s==0 else n;gg=actualgeo[off+ey];checks.append({'surface':s,'eye_vertices':len(ey),'POS_vs_baseline_exact':bool(np.array_equal(vv[gg],old[s][ey])),'UV_original_untouched':True,'NORMAL_original_untouched':True,'note':'protected attributes are copied, no output assets generated'})
 interface=np.array([p for e in ns['alignment']['actual_interface'] for p in e['rest_xyz']]);iq=canvas(interface);sq=ns['stage1'](iq)[0];fq=ev(sq)[0];rear=iq[:,0]<=1988;unknown=sq[:,0]<=2000.5;rearcheck={'baseline640_count':int(rear.sum()),'baseline640_POS_exact':bool(np.array_equal(fq[rear],iq[rear])),'unknown704_endpoint_samples_F2_identity':bool(np.array_equal(fq[unknown],sq[unknown])),'original_UV_NORMAL_JW_not_recomputed':True}
 newpoints=np.arange(len(keyid),len(geom));newrear=[];newuvbad=[];facebarymax=0
 for t in faces.values():
  root=t['root'];surface=0 if root<len(skin) else 1;source=original[root]-(0 if surface==0 else n);origUV=np.array(data[surface]['source_uv'])[source]*[2024,742]
  for g,bc in zip(t['g'],t['bary']):
   if g<len(keyid):continue
   p=bc@inputv[original[root]];facebarymax=max(facebarymax,float(np.linalg.norm(p-geom[g])));v0=canvas(p[None]);out,dy,(w,des)=ev(v0,True)
   # Newly split parent-rim points in the unknown X domain must preserve old bary UV and position.
   if g in {j for ch in parents.values() for j in ch.values()} and v0[0,0]<=2000.5:
    newrear.append(g)
    if not np.array_equal(v0,out) or surface==0 and w[0]!=0:newuvbad.append(g)
 # All corners retain original-face barycentric provenance; raw JW checked by exact float32 POSITION.
 raw=Path(cfg['raw_glb']).read_bytes();ln=struct.unpack_from('<I',raw,12)[0];gl=json.loads(raw[20:20+ln]);binary=raw[28+ln:];dtypes={5126:'<f4',5123:'<u2',5121:'u1'};num={'VEC2':2,'VEC3':3,'VEC4':4};jw=[];jconflict=0
 def accessor(ix):
  ac=gl['accessors'][ix];bv=gl['bufferViews'][ac['bufferView']];dt=np.dtype(dtypes[ac['componentType']]);co=num[ac['type']];return np.ndarray((ac['count'],co),dt,buffer=binary,offset=bv.get('byteOffset',0)+ac.get('byteOffset',0),strides=(bv.get('byteStride',co*dt.itemsize),dt.itemsize)).copy()
 prims=next(m for m in gl['meshes'] if m.get('name')=='Closed_body')['primitives']
 for s in range(2):
  aa={k:accessor(v) for k,v in prims[s]['attributes'].items()};groups=defaultdict(list)
  for j,p in enumerate(aa['POSITION']):groups[tuple(p.astype(float))].append(j)
  actual=[]
  for p in old[s]:
   ii=groups[tuple(p.astype(np.float32).astype(float))];ref=ii[0];jconflict+=sum(not np.array_equal(aa['JOINTS_0'][ref],aa['JOINTS_0'][k]) or not np.array_equal(aa['WEIGHTS_0'][ref],aa['WEIGHTS_0'][k]) for k in ii[1:]);actual.append((aa['JOINTS_0'][ref],aa['WEIGHTS_0'][ref]))
  jw.append(actual)
 maxbones=0;jwfail=0;jwshared={};jwsharedconflict=0
 for t in faces.values():
  root=t['root'];s=0 if root<len(skin) else 1;src=original[root]-(0 if s==0 else n)
  for g,bc in zip(t['g'],t['bary']):
   if g<len(keyid):continue
   weights=defaultdict(float)
   for vertex,lam in zip(src,bc):
    for bone,w in zip(*jw[s][vertex]):
     if lam*w>0:weights[int(bone)]+=float(lam*w)
   total=sum(weights.values());weights={k:v/total for k,v in weights.items()};maxbones=max(maxbones,len(weights));jwfail+=len(weights)>4;key=tuple(sorted(weights.items()))
   if g in jwshared and jwshared[g]!=key:jwsharedconflict+=1
   else:jwshared[g]=key
 sourcepath=b.parent/'surface-mouth-audit-102/sources/zander/image-0.png';src=Image.open(sourcepath).convert('RGBA');board=Image.new('RGB',(792,620),(25,35,43));panel=Image.new('RGBA',src.size,(30,43,48,255));panel.alpha_composite(src);roi=(1760,280,2024,550);panel=panel.convert('RGB').crop(roi).resize((792,810),Image.Resampling.NEAREST);draw=ImageDraw.Draw(panel)
 # Actual projected triangle edges, clipped by panel canvas; this displays the stopped discrete mesh honestly.
 for t in faces.values():
  if t['root'] not in allowed or t['root']>=len(skin):continue
  xy=mappedq[list(t['g'])];pp=[((x-roi[0])*3,(y-roi[1])*3) for x,y in xy];draw.line(pp+[pp[0]],fill=(30,220,140),width=1)
 board=Image.new('RGB',(792,880),(25,35,43));board.paste(panel,(0,40));font=ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial Unicode.ttf',18);dd=ImageDraw.Draw(board);dd.text((12,8),'梭鲈｜固定细分 CPU：'+('失败停止' if fail or badids else '待独审'),font=font,fill='white');dd.text((12,852),'源图不改；绿为实际有限三角；未写模型/材质，不是最终验收。',font=font,fill='white');board.save(a.output/'refinement-source-projection.png')
 passed=not fail and not badids and allclosed and all(p['opposite_skin_oral_children'] for p in parentreports) and not newuvbad and not jwfail and not jwsharedconflict and all(c['POS_vs_baseline_exact'] for c in checks) and rearcheck['baseline640_POS_exact']
 report={'status':'bounded_CPU_refinement_pass_pending_review' if passed else 'bounded_CPU_refinement_REJECTED','accepted':False,'cpu_gate_passed':passed,'asset_written':False,'failure_stop':fail,'counts':{'initial_triangles':len(original),'final_triangles':len(faces),'new_geometric_points':len(geom)-len(keyid),'edge_bisections':splits,'cumulative_generated_children':generated,'max_face_lineage_depth':max(t['depth'] for t in faces.values()),'new_topology_faces':sum(t['depth']>0 for t in faces.values())},'scope':{'initial761':len(initial),'neighbor125':len(neighbor),'changed_roots':sorted({t['root'] for t in faces.values() if t['depth']>0}),'no_expansion_outside_frozen_allowed':all(t['root'] in allowed for t in faces.values() if t['depth']>0)},'geometry':{'closed_all_geometric_edges_incident2':allclosed,'parents397_all_covered_opposite':all(p['opposite_skin_oral_children'] and p['covered_0_1'] for p in parentreports),'parent_child_segments':sum(p['segments'] for p in parentreports),'refined_parents':sum(p['segments']>1 for p in parentreports),'barycentric_origin_max_roundoff_rest':facebarymax,**ori},'actual_full_canonical_crossing':cr,'protection':checks,'rear_lip':rearcheck,'new_unknown_parent_points':{'count':len(set(newrear)),'F2_or_UV_weight_failure_points':sorted(set(newuvbad))},'JW':{'max_nonzero_bones':maxbones,'over4_rejected_corner_count':jwfail,'raw_exact_position_JW_group_conflicts':jconflict,'new_shared_point_JW_conflicts':jwsharedconflict,'normal_policy':'corner-local original face/hardedge groups retained; no attribute assets written'},'events':events,'post_scale_geometry_iterations':history,'inputs_sha256':frozenout['dependencies'],'limits':['Finite CPU only, old generated LOD failures unchanged; no GLB, runtime, GPU or final normals emitted.','Existing analytic UV dark fallback remains separate unresolved material issue.','Stopped mesh is failure evidence, not permitted installation output.']};(a.output/'refinement-completion.validation.json').write_text(json.dumps(report,indent=2)+'\n');(a.output/'parent-chains.validation.json').write_text(json.dumps(parentreports,indent=2)+'\n');print(json.dumps({k:report[k] for k in ['status','failure_stop','counts','geometry','actual_full_canonical_crossing','new_unknown_parent_points','JW']},indent=2))
if __name__=='__main__':main()
