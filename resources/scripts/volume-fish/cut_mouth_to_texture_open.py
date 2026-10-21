"""Cut excess upper skin at a frozen source-texture lip boundary, fit lower jaw.

For an existing Closed_body with a skin primitive and an oral primitive sharing
one closed rim. Retains rear skin, fins, source image, skeleton and animations.
Species constraints are explicit input; this is not a universal fish mouth.
"""
import argparse, copy, hashlib, json
from collections import Counter
from pathlib import Path
import numpy as np
from scipy.interpolate import PchipInterpolator
from scipy.spatial import cKDTree
from scipy.interpolate import RBFInterpolator
from freeze_surface_ownership import read_glb, accessor
from patch_existing_fin_meshes import write

def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def smooth(t):
    t=np.clip(t,0,1)
    return t*t*(3-2*t)
def keys(v): return [tuple(round(float(x),7) for x in p) for p in v]

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    for k in ['input','source','parameters','head-config','output','config-output','report']:
        ap.add_argument('--'+k,type=Path,required=True)
    a=ap.parse_args();cfg=json.loads(a.parameters.read_text());assert sha(a.input)==cfg['baseline_sha256'];assert sha(a.source)==cfg['source_sha256']
    d,b=read_glb(a.input);original=copy.deepcopy(d);binary=bytearray(b)
    ni=next(i for i,n in enumerate(d['nodes']) if n.get('name')=='Closed_body');mi=d['nodes'][ni]['mesh'];pr=d['meshes'][mi]['primitives'];assert len(pr)==2
    data=[{k:accessor(d,b,ix).copy() for k,ix in p['attributes'].items()} for p in pr]
    faces=[accessor(d,b,p['indices']).reshape(-1,3) for p in pr]
    old=data[0]['POSITION'];okeys=keys(old);oral=data[1]['POSITION'];ikeys=keys(oral);shared=set(okeys)&set(ikeys)
    rim_edges=[]
    for p,f in zip([okeys,ikeys],faces):
        count=Counter(tuple(sorted((p[i],p[j]))) for tri in f for i,j in zip(tri,np.roll(tri,-1)) if p[i]!=p[j])
        rim_edges.append({e for e,n in count.items() if n==1 and e[0] in shared and e[1] in shared})
    edges=rim_edges[0]&rim_edges[1];adj={}
    for u,v in edges: adj.setdefault(u,[]).append(v);adj.setdefault(v,[]).append(u)
    assert adj and all(len(v)==2 for v in adj.values()),'Expected one closed skin/oral rim'
    start=min(adj);chain=[start];prev=None;cur=start
    while True:
        nxt=next(q for q in adj[cur] if q!=prev)
        if nxt==start:break
        chain.append(nxt);prev,cur=cur,nxt
    assert len(chain)==len(adj),'Multiple oral loops'
    up_map={k:float(t>.5) for k,t in zip(ikeys,data[1]['TEXCOORD_1'][:,1])}
    oldrim=np.array(chain);up=np.array([up_map[k] for k in chain]);aspect=cfg['source_canvas'][1]/cfg['source_canvas'][0]
    # Median true rim heights at nearby stations; no guessed model-path split.
    sample=np.linspace(oldrim[:,0].min(),oldrim[:,0].max(),40)
    old_edges=[]
    for x in sample:
        row=[]
        for upper in [1,0]:
            pts=oldrim[up==upper];sel=np.argsort(abs(pts[:,0]-x))[:6];row.append(float(np.median(pts[sel,1])))
        old_edges.append(row)
    old_edges=np.array(old_edges);old_upper=PchipInterpolator(sample,old_edges[:,0]);old_lower=PchipInterpolator(sample,old_edges[:,1])
    source_g=np.array(cfg['source_lip_edges_canvas_px'],float)
    # Smooth old bottom envelope from mesh-plane intersections at coarse stations.
    tri=old[faces[0]];bx=np.linspace(cfg['influence_x'][0],.4945,42);by=[]
    for x in bx:
        pts=[]
        for j,k in [(0,1),(1,2),(2,0)]:
            v,w=tri[:,j],tri[:,k];sel=((v[:,0]<=x)&(w[:,0]>x))|((w[:,0]<=x)&(v[:,0]>x));v,w=v[sel],w[sel];t=(x-v[:,0])/(w[:,0]-v[:,0]);pts.extend(v+t[:,None]*(w-v))
        by.append(np.array(pts)[:,1].min())
    old_bottom=PchipInterpolator(bx,by)
    cut=np.array(cfg['upper_cut_canvas_px'],float)
    cut_y=PchipInterpolator(cut[:,0]/cfg['source_canvas'][0]-.5,(.5-cut[:,1]/cfg['source_canvas'][1])*aspect)
    # Exact source coordinates on the upper chart are frozen BEFORE clipping.
    # Lower jaw keeps its own existing chart and is the only moved structure.
    uv=data[0]['TEXCOORD_0'].copy()
    mid=(old_upper(np.clip(old[:,0],sample[0],sample[-1]))+old_lower(np.clip(old[:,0],sample[0],sample[-1])))*.5
    upper_skin=old[:,1]>=mid
    mask=upper_skin&(old[:,0]>.415)
    uv[mask]=np.column_stack([old[mask,0]+.5,.5-old[mask,1]/aspect])
    data[0]['TEXCOORD_0']=uv
    # Clip triangles, interpolate every vertex stream at true edge intersections.
    # No shader discard and no upper vertex displacement.
    vals={k:[q.copy() for q in v] for k,v in data[0].items()}
    sign=np.ones(len(old));region=upper_skin&(old[:,0]>=cut[0,0]/2014-.5)
    sign[region]=old[region,1]-cut_y(old[region,0])
    cache={};generated=[]
    def intersection(i,j):
        key=tuple(sorted((i,j)))
        if key in cache:return cache[key]
        # Curve is evaluated in the frozen native source projection, not the
        # already deformed UV of a manufactured lip. Solve nonlinear root.
        from scipy.optimize import brentq
        p,q=old[i].astype(float),old[j].astype(float)
        def fn(t):
            r=p+(q-p)*t;return r[1]-cut_y(r[0])
        t=brentq(fn,0.,1.,xtol=1e-14)
        idx=len(vals['POSITION']);cache[key]=idx;generated.append(idx)
        for k,v in data[0].items():
            if k=='JOINTS_0':value=v[i].copy()
            elif k=='WEIGHTS_0':
                weights={}
                for jj,ww in [(i,1-t),(j,t)]:
                    for bone,w in zip(data[0]['JOINTS_0'][jj],v[jj]):weights[int(bone)]=weights.get(int(bone),0.)+float(w)*ww
                top=sorted(weights.items(),key=lambda q:-q[1])[:4];total=sum(w for _,w in top)
                vals['JOINTS_0'][idx]=np.array([bone for bone,_ in top]+[0]*(4-len(top)),dtype=data[0]['JOINTS_0'].dtype)
                value=np.array([w/total for _,w in top]+[0.]*(4-len(top)),dtype=v.dtype)
            else:value=(v[i]*(1-t)+v[j]*t).astype(v.dtype)
            vals[k].append(value)
        # Side-chart source pixel position is never rescaled or warped.
        p=vals['POSITION'][idx];vals['TEXCOORD_0'][idx]=np.array([p[0]+.5,.5-p[1]/aspect],dtype='<f4')
        return idx
    skin_faces=[];clipped=0;removed=0
    for f in faces[0]:
        kept=[]
        for i,j in zip(f,np.roll(f,-1)):
            if sign[i]>=0:kept.append(int(i))
            if (sign[i]>=0)!=(sign[j]>=0):kept.append(intersection(int(i),int(j)))
        if len(kept)!=3:clipped+=1
        if len(kept)<3:removed+=1
        for k in range(1,len(kept)-1):skin_faces.append([kept[0],kept[k],kept[k+1]])
    faces[0]=np.asarray(skin_faces,dtype='<u4')
    source_positions=np.asarray(vals['POSITION'],dtype='<f4')
    data[0]={k:np.asarray(v,dtype=data[0][k].dtype) for k,v in vals.items()}
    new=source_positions.copy()
    uv=data[0]['TEXCOORD_0'].copy()
    # Re-extract the actual cut topology, including the unchanged lower edge.
    okeys=keys(source_positions);newkeys=keys(new);count=Counter()
    for f in faces[0]:
        for i,j in zip(f,np.roll(f,-1)):
            if newkeys[i]!=newkeys[j]:count[tuple(sorted((newkeys[i],newkeys[j])))]+=1
    edges={e for e,nc in count.items() if nc==1};adj={}
    for u,v in edges:adj.setdefault(u,[]).append(v);adj.setdefault(v,[]).append(u)
    assert all(len(v)==2 for v in adj.values()),'Cut must yield one simple boundary'
    start=min(adj);chain=[start];prev=None;cur=start
    while True:
        nxt=next(q for q in adj[cur] if q!=prev)
        if nxt==start:break
        chain.append(nxt);prev,cur=cur,nxt
    assert len(chain)==len(adj),'Unexpected second boundary after clipping'
    lookup={k:i for i,k in enumerate(newkeys)};rim_ids=np.array([lookup[k] for k in chain]);rim=new[rim_ids]
    up=np.array([1. if i in generated else up_map.get(okeys[i],float(source_positions[i,1]>np.mean([old_upper(np.clip(source_positions[i,0],sample[0],sample[-1])),old_lower(np.clip(source_positions[i,0],sample[0],sample[-1]))]))) for i in rim_ids])
    # Pair the actual retained/cut upper arc and the lower arc in 3D.
    # Both run from the same left corner to the same right corner. The upper
    # boundary is fixed; arc correspondence only fits the manufactured lower.
    turns=np.where(up!=np.roll(up,1))[0]
    assert len(turns)==2,('Upper/lower boundary must be two contiguous arcs',turns.tolist())
    begin=next(int(i) for i in turns if up[i]>.5)
    order=np.roll(np.arange(len(rim)),-begin);uorder=order[up[order]>.5];lorder=order[up[order]<.5][::-1]
    U=rim[uorder].astype(float);L=rim[lorder].astype(float)
    def arc_parameter(q):
        a=np.r_[0.,np.cumsum(np.linalg.norm(np.diff(q,axis=0),axis=1))];return a/a[-1]
    tu,tl=arc_parameter(U),arc_parameter(L)
    edge=np.array(cfg['lower_source_edge_canvas_px'],float)
    edge_y=PchipInterpolator(edge[:,0]/2014-.5,(.5-edge[:,1]/727)*aspect)
    chin=np.array(cfg['source_chin_canvas_px'],float)
    chin_y=PchipInterpolator(chin[:,0]/2014-.5,(.5-chin[:,1]/727)*aspect)
    target=L.copy()
    target[:,1]=edge_y(np.clip(L[:,0],edge[0,0]/2014-.5,edge[-1,0]/2014-.5))
    # Source lower lip and chin are independent constraints: opening the mouth
    # cannot be implemented by stretching the whole lower jaw equally.
    delta=target-L
    x,y=source_positions[:,0],source_positions[:,1]
    hi=old_upper(np.clip(x,sample[0],sample[-1]));lo=old_lower(np.clip(x,sample[0],sample[-1]))
    lower_mask=y<(hi+lo)*.5
    # Continuous lower rim height over the transverse chart: nearest-rim
    # displacement created abrupt thickness changes along the previous jaw.
    q,unique=np.unique(L[:,[0,2]],axis=0,return_index=True)
    rim_height=RBFInterpolator(q,L[unique,1],kernel='thin_plate_spline',smoothing=1e-12)
    query=source_positions[:,[0,2]].astype(float);query[:,0]=np.clip(query[:,0],L[:,0].min(),L[:,0].max())
    old_lip=rim_height(query)
    original_bottom=old_bottom(np.clip(x,bx[0],bx[-1]))
    target_lip=edge_y(np.clip(x,edge[0,0]/2014-.5,edge[-1,0]/2014-.5))
    target_bottom=chin_y(np.clip(x,chin[0,0]/2014-.5,chin[-1,0]/2014-.5))
    depth=np.maximum(old_lip-original_bottom,.002)
    along=(y-original_bottom)/depth
    fitted=target_bottom+along*(target_lip-target_bottom)
    weight=smooth((x-.33)/.07)
    new[lower_mask,1]+=(fitted[lower_mask]-y[lower_mask])*weight[lower_mask]
    key_to_delta={keys(L)[j]:delta[j] for j in range(len(L))}
    for i,key in enumerate(keys(source_positions)):
        if key in key_to_delta:new[i]=source_positions[i]+key_to_delta[key]
    new=new.astype('<f4');rim=new[rim_ids];newkeys=keys(new)
    # Native source chart for lower exterior: match the open source pose
    # before assessing lip thickness. Only unseen central skin uses a donor.
    uv[lower_mask]=np.column_stack([new[lower_mask,0]+.5,.5-new[lower_mask,1]/aspect])
    # Re-key skin edge orientation to the retained/cut positions.
    okeys=newkeys
    # A periodic parameter by physical arc length of the supplied lip boundary.
    # It is used only for the hidden cavity, not as a species width measurement.
    seg=np.maximum(np.linalg.norm(np.roll(rim,-1,axis=0)-rim,axis=1),.00001);arc=np.r_[0,np.cumsum(seg[:-1])]/seg.sum()*2*np.pi
    # Align posterior ellipse to the highest front upper-lip point.
    front_upper=np.where(up>.5)[0];zero=front_upper[np.argmax(rim[front_upper,0]-abs(rim[front_upper,2])*.3)];theta=arc-arc[zero]
    # Determine direction so ellipse left/right follows the actual lip loop.
    if np.dot(np.sin(theta),rim[:,2])<0:theta=-theta
    cavity=cfg['cavity'];back=np.column_stack([np.full(len(rim),cavity['back_x']),cavity['center_y']+cavity['radius_y']*np.cos(theta),cavity['radius_z']*np.sin(theta)])
    rings=[rim]
    for t in np.linspace(0,1,cavity['rings']+1)[1:]:
        # Ease the first turn into the mouth before growing the hidden volume.
        q=rim*(1-t)+back*t;q[:,1:]+=np.sin(np.pi*t)*.001*np.column_stack([np.cos(theta),np.sin(theta)])
        rings.append(q)
    for t in [.25,.50,.75,.92]:
        q=back.copy();q[:,0]-=cavity['cap_depth']*t;q[:,1]=cavity['center_y']+(back[:,1]-cavity['center_y'])*np.sqrt(1-t*t);q[:,2]=back[:,2]*np.sqrt(1-t*t);rings.append(q)
    n=len(rim);inner=np.concatenate(rings).astype('<f4');pole=np.array([[cavity['back_x']-cavity['cap_depth'],cavity['center_y'],0]],dtype='<f4');inner=np.concatenate([inner,pole])
    inf=[]
    # Orient new faces opposite to skin along the common edge.
    edge_direction={}
    for f in faces[0]:
        for i,j in zip(f,np.roll(f,-1)):
            if okeys[i] in adj and okeys[j] in adj:edge_direction[(okeys[i],okeys[j])]=True
    same=(chain[0],chain[1]) in edge_direction
    for r in range(len(rings)-1):
        for j in range(n):
            k=(j+1)%n;inf.extend([[r*n+j,(r+1)*n+j,r*n+k],[r*n+k,(r+1)*n+j,(r+1)*n+k]])
    for j in range(n):inf.append([(len(rings)-1)*n+j,len(inner)-1,(len(rings)-1)*n+(j+1)%n])
    inf=np.asarray(inf,dtype='<u4')
    if not same:inf=inf[:,::-1].copy()
    nearest=cKDTree(new).query(inner)[1]
    attrs={k:v[nearest].copy() for k,v in data[0].items()};attrs['POSITION']=inner
    for k in ['JOINTS_0','WEIGHTS_0']:attrs[k][:n]=data[0][k][rim_ids]
    boundary_uv=uv[rim_ids]
    attrs['TEXCOORD_0']=np.concatenate([np.tile(boundary_uv,(len(rings),1)),[[1940/2014,446/727]]]).astype('<f4')
    depth=cKDTree(rim).query(inner)[0]
    attrs['TEXCOORD_1']=np.column_stack([abs(inner[:,2])+depth,np.r_[np.tile(up,len(rings)),0]]).astype('<f4')
    # Welded area normals across skin and inner primitive; rear normals preserved.
    allv=np.concatenate([new,inner]);allf=np.concatenate([faces[0],inf+len(new)]);q=allv[allf];area=np.cross(q[:,1]-q[:,0],q[:,2]-q[:,0]);normal=np.zeros_like(allv)
    for j in range(3):np.add.at(normal,allf[:,j],area)
    _,inverse=np.unique(np.round(allv,7),axis=0,return_inverse=True);joined=np.zeros((inverse.max()+1,3));np.add.at(joined,inverse,normal);normal=joined[inverse];normal/=np.maximum(np.linalg.norm(normal,axis=1)[:,None],1e-15)
    sn=normal[:len(new)].astype('<f4');sn[source_positions[:,0]<=cfg['influence_x'][0]]=data[0]['NORMAL'][source_positions[:,0]<=cfg['influence_x'][0]]
    data[0]['POSITION']=new;data[0]['NORMAL']=sn;data[0]['TEXCOORD_0']=uv.astype('<f4');attrs['NORMAL']=normal[len(new):].astype('<f4')
    def add(arr,kind):
        arr=np.ascontiguousarray(arr);binary.extend(b'\0'*(-len(binary)%4));offset=len(binary);binary.extend(arr.tobytes());vi=len(d['bufferViews']);d['bufferViews'].append({'buffer':0,'byteOffset':offset,'byteLength':arr.nbytes});ai=len(d['accessors']);ctype={np.dtype('float32'):5126,np.dtype('uint32'):5125,np.dtype('uint16'):5123,np.dtype('uint8'):5121}[arr.dtype];d['accessors'].append({'bufferView':vi,'componentType':ctype,'count':len(arr),'type':kind,'min':np.atleast_1d(arr.min(0)).tolist(),'max':np.atleast_1d(arr.max(0)).tolist()});return ai
    for pi,values in enumerate([data[0],attrs]):
        for key,val in values.items():
            val=val.astype('<f4') if val.dtype.kind=='f' else val;pr[pi]['attributes'][key]=add(val,'VEC'+str(val.shape[1]))
    pr[0]['indices']=add(faces[0].ravel(),'SCALAR')
    pr[1]['indices']=add(inf.ravel(),'SCALAR')
    a.output.parent.mkdir(parents=True,exist_ok=True);write(a.output,d,binary)
    # Independent geometric checks, before any engine import.
    edge_counts=Counter()
    for v,f in [(new,faces[0]),(inner,inf)]:
        kk=keys(v)
        for face in f:
            t=[kk[j] for j in face];assert len(set(t))==3,'Degenerate body triangle after mouth edit'
            for u,w in zip(t,t[1:]+t[:1]):edge_counts[tuple(sorted([u,w]))]+=1
    assert all(c==2 for c in edge_counts.values()),'Open mouth/body shell'
    assert d['skins']==original['skins'] and d['animations']==original['animations'] and d['images']==original['images']
    assert all(m==original['meshes'][i] for i,m in enumerate(d['meshes']) if i!=mi)
    head_cfg=json.loads(a.head_config.read_text());p=head_cfg['profiles'][cfg['species']];p['model_sha256']=sha(a.output);p['yellow_source_trial']=True;p['mouth_source_edges']=(source_g/np.array([2014,727,727])).tolist()
    # Simplify straight/small segments only for shader distance, not geometry.
    selected=[0]
    for i in range(1,n):
        if np.linalg.norm(rim[i]-rim[selected[-1]])>.0015:selected.append(i)
    if len(selected)>155:selected=selected[::2]
    selected.append(0);starts=[];ends=[]
    for i,j in zip(selected[:-1],selected[1:]):starts.append([*map(float,rim[i]),float(up[i])]);ends.append([*map(float,rim[j]),float(up[j])])
    cross=[]
    nt=new[faces[0]]
    for x in np.linspace(.29,float(nt[:,:,0].max())-.00005,32):
        intersections=[]
        for j,k in [(0,1),(1,2),(2,0)]:
            v,w=nt[:,j],nt[:,k];sel=((v[:,0]<=x)&(w[:,0]>x))|((w[:,0]<=x)&(v[:,0]>x));v,w=v[sel],w[sel];t=(x-v[:,0])/(w[:,0]-v[:,0]);intersections.extend(v+t[:,None]*(w-v))
        pts=np.asarray(intersections);lo,hi=pts[:,1].min(),pts[:,1].max();cross.append([float(x),float((lo+hi)/2),float((hi-lo)/2),float(abs(pts[:,2]).max())])
    p['rim_local']={'starts':starts,'ends':ends,'cross_sections':cross,'eye_native_center_x':p['eye']['center'][0]-.5,'eye_native_radius_x':p['eye']['radius'][0],'eye_center_angle':.1,'eye_angular_radius':.5}
    a.config_output.write_text(json.dumps(head_cfg,indent=2)+'\n')
    report={'ok':True,'input_sha256':sha(a.input),'model_sha256':sha(a.output),'source_sha256':sha(a.source),'parameters_sha256':sha(a.parameters),'rim_vertices':n,'new_inner_vertices':len(inner),'new_inner_triangles':len(inf),'closed_welded_shell':True,'fins_skeleton_animation_source_bytes_preserved':True,'rear_positions_exact':bool(np.array_equal(new[source_positions[:,0]<=cfg['influence_x'][0]],source_positions[source_positions[:,0]<=cfg['influence_x'][0]])),'rear_preservation_limit_x':cfg['influence_x'][0],'max_skin_displacement_native':float(np.linalg.norm(new-source_positions,axis=1).max()),'cavity_bounds':{'min':inner.min(0).tolist(),'max':inner.max(0).tolist()},'scope':cfg['limits']}
    retained_upper=(source_positions[:,1]>=(old_upper(np.clip(source_positions[:,0],sample[0],sample[-1]))+old_lower(np.clip(source_positions[:,0],sample[0],sample[-1])))*.5)
    report.update(lower_fit='continuous lower-rim height field and monotone lip-to-chin source fit',lower_gap_px=None,upper_retained_positions_exact=bool(np.array_equal(new[retained_upper],source_positions[retained_upper])),upper_clip_intersections=len(generated),upper_removed_triangles=removed,upper_clipped_triangles=clipped,upper_source_chart='frozen native projection before geometry cut',cut_boundary_max_source_px_error=float(max([abs(source_positions[i,1]-cut_y(source_positions[i,0]))*2014 for i in generated],default=0)))
    a.report.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))

if __name__=='__main__':main()
