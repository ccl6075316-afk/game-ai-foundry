"""Local source-jaw fit and curved cavity replacement on a preserved rigged GLB.

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
    g=np.array(cfg['oral_edges_canvas_px'],float);gx=g[:,0]/cfg['source_canvas'][0]-.5
    new_upper=PchipInterpolator(gx,(.5-g[:,1]/cfg['source_canvas'][1])*aspect)
    new_lower=PchipInterpolator(gx,(.5-g[:,2]/cfg['source_canvas'][1])*aspect)
    chin=np.array(cfg['chin_canvas_px'],float);cx=chin[:,0]/cfg['source_canvas'][0]-.5
    new_bottom=PchipInterpolator(cx,(.5-chin[:,1]/cfg['source_canvas'][1])*aspect)
    source_g=np.array(cfg.get('reference_oral_edges_canvas_px',cfg['oral_edges_canvas_px']),float)
    source_chin=np.array(cfg.get('reference_chin_canvas_px',cfg['chin_canvas_px']),float)
    reference_upper=PchipInterpolator(source_g[:,0]/cfg['source_canvas'][0]-.5,(.5-source_g[:,1]/cfg['source_canvas'][1])*aspect)
    reference_lower=PchipInterpolator(source_g[:,0]/cfg['source_canvas'][0]-.5,(.5-source_g[:,2]/cfg['source_canvas'][1])*aspect)
    reference_bottom=PchipInterpolator(source_chin[:,0]/cfg['source_canvas'][0]-.5,(.5-source_chin[:,1]/cfg['source_canvas'][1])*aspect)
    # Smooth old bottom envelope from mesh-plane intersections at coarse stations.
    tri=old[faces[0]];bx=np.linspace(cfg['influence_x'][0],.4945,42);by=[]
    for x in bx:
        pts=[]
        for j,k in [(0,1),(1,2),(2,0)]:
            v,w=tri[:,j],tri[:,k];sel=((v[:,0]<=x)&(w[:,0]>x))|((w[:,0]<=x)&(v[:,0]>x));v,w=v[sel],w[sel];t=(x-v[:,0])/(w[:,0]-v[:,0]);pts.extend(v+t[:,None]*(w-v))
        by.append(np.array(pts)[:,1].min())
    old_bottom=PchipInterpolator(bx,by)
    def deform(v,reference=False):
        x,y=v[:,0],v[:,1];xx=np.clip(x,sample[0],sample[-1]);ux=np.clip(x,gx[0],gx[-1]);lx=old_lower(xx);uy=old_upper(xx)
        tu,tl=(reference_upper(ux),reference_lower(ux)) if reference else (new_upper(ux),new_lower(ux))
        center=(tu+tl)*.5;half=(tu-tl)*.5*(.20+.80*smooth((x-sample[0])/.010))
        du=center+half-uy;dl=center-half-lx
        depth=np.maximum(lx-old_bottom(np.clip(x,bx[0],bx[-1])),.002)
        t=smooth((lx-y)/depth)
        bottom_function=reference_bottom if reference else new_bottom
        db=bottom_function(np.clip(x,cx[0],cx[-1]))-old_bottom(np.clip(x,bx[0],bx[-1]))
        lower=dl*(1-t)+db*t
        gap=np.maximum(uy-lx,.001)
        dy=np.where(y<lx,lower,np.where(y>uy,du*(1-smooth((y-uy)/cfg['upper_fade_native'])),dl+(du-dl)*smooth((y-lx)/gap)))
        out=v.astype(float).copy();out[:,1]+=dy*smooth((x-cfg['influence_x'][0])/(cfg['influence_x'][1]-cfg['influence_x'][0]));return out
    new=deform(old).astype('<f4');rim=deform(oldrim).astype('<f4')
    # Exact skin boundary drives the new inner wall. Avoid rounded-key drift.
    lookup={k:p for k,p in zip(okeys,new)};rim=np.array([lookup[k] for k in chain])
    # A periodic parameter by physical arc length of the supplied lip boundary.
    # It is used only for the hidden cavity, not as a species width measurement.
    seg=np.linalg.norm(np.roll(rim,-1,axis=0)-rim,axis=1);arc=np.r_[0,np.cumsum(seg[:-1])]/seg.sum()*2*np.pi
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
    skin_index={k:i for i,k in enumerate(okeys)};rim_ids=np.array([skin_index[k] for k in chain])
    nearest=cKDTree(new).query(inner)[1]
    attrs={k:v[nearest].copy() for k,v in data[0].items()};attrs['POSITION']=inner
    for k in ['JOINTS_0','WEIGHTS_0']:
        attrs[k][:n]=data[0][k][rim_ids]
    # Native source lips retained; hidden front continues the same source strip.
    reference_vertices=deform(old,reference=True)
    uv=data[0]['TEXCOORD_0'].copy();head=new[:,0]>.415;uv[head]=np.column_stack([reference_vertices[head,0]+.5,.5-reference_vertices[head,1]/aspect])
    def lip_uv(points,upper):
        donor=points[:,0]+.5;front=smooth((donor-.975)/.019);across=np.clip(abs(points[:,2])/.018,0,1);donor=donor*(1-front)+(.967+.014*across)*front
        vv=np.where(upper>.5,np.interp(donor,source_g[:,0]/2014,source_g[:,1]/727),np.interp(donor,source_g[:,0]/2014,source_g[:,2]/727));vv+=np.where(upper>.5,-5,5)/727
        return np.column_stack([donor,vv])
    boundary_uv=lip_uv(rim,up)
    # Blend by spatial distance to true rim only at the rounded front.
    dist,idx=cKDTree(rim).query(new);front=smooth((new[:,0]-.478)/.015)*(1-smooth(.001+dist/.008))
    mapped=lip_uv(rim[idx],up[idx]);uv=uv*(1-front[:,None])+mapped*front[:,None]
    attrs['TEXCOORD_0']=np.tile(boundary_uv,(len(rings),1));attrs['TEXCOORD_0']=np.concatenate([attrs['TEXCOORD_0'],[[1940/2014,446/727]]]).astype('<f4');attrs['TEXCOORD_0'][:n]=uv[rim_ids]
    depth=cKDTree(rim).query(inner)[0]
    attrs['TEXCOORD_1']=np.column_stack([abs(inner[:,2])+depth,np.r_[np.tile(up,len(rings)),0]]).astype('<f4')
    # Welded area normals across skin and inner primitive; rear normals preserved.
    allv=np.concatenate([new,inner]);allf=np.concatenate([faces[0],inf+len(new)]);q=allv[allf];area=np.cross(q[:,1]-q[:,0],q[:,2]-q[:,0]);normal=np.zeros_like(allv)
    for j in range(3):np.add.at(normal,allf[:,j],area)
    _,inverse=np.unique(np.round(allv,7),axis=0,return_inverse=True);joined=np.zeros((inverse.max()+1,3));np.add.at(joined,inverse,normal);normal=joined[inverse];normal/=np.maximum(np.linalg.norm(normal,axis=1)[:,None],1e-15)
    sn=normal[:len(new)].astype('<f4');sn[old[:,0]<=cfg['influence_x'][0]]=data[0]['NORMAL'][old[:,0]<=cfg['influence_x'][0]]
    data[0]['POSITION']=new;data[0]['NORMAL']=sn;data[0]['TEXCOORD_0']=uv.astype('<f4');attrs['NORMAL']=normal[len(new):].astype('<f4')
    def add(arr,kind):
        arr=np.ascontiguousarray(arr);binary.extend(b'\0'*(-len(binary)%4));offset=len(binary);binary.extend(arr.tobytes());vi=len(d['bufferViews']);d['bufferViews'].append({'buffer':0,'byteOffset':offset,'byteLength':arr.nbytes});ai=len(d['accessors']);ctype={np.dtype('float32'):5126,np.dtype('uint32'):5125,np.dtype('uint16'):5123,np.dtype('uint8'):5121}[arr.dtype];d['accessors'].append({'bufferView':vi,'componentType':ctype,'count':len(arr),'type':kind,'min':np.atleast_1d(arr.min(0)).tolist(),'max':np.atleast_1d(arr.max(0)).tolist()});return ai
    for pi,values in enumerate([data[0],attrs]):
        for key,val in values.items():
            if pi==0 and key not in ['POSITION','NORMAL','TEXCOORD_0']:continue
            val=val.astype('<f4') if val.dtype.kind=='f' else val;pr[pi]['attributes'][key]=add(val,'VEC'+str(val.shape[1]))
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
    for k in ['JOINTS_0','WEIGHTS_0','TEXCOORD_1']:assert pr[0]['attributes'][k]==original['meshes'][mi]['primitives'][0]['attributes'][k]
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
    for x in np.linspace(.29,.4949,32):
        intersections=[]
        for j,k in [(0,1),(1,2),(2,0)]:
            v,w=nt[:,j],nt[:,k];sel=((v[:,0]<=x)&(w[:,0]>x))|((w[:,0]<=x)&(v[:,0]>x));v,w=v[sel],w[sel];t=(x-v[:,0])/(w[:,0]-v[:,0]);intersections.extend(v+t[:,None]*(w-v))
        pts=np.asarray(intersections);lo,hi=pts[:,1].min(),pts[:,1].max();cross.append([float(x),float((lo+hi)/2),float((hi-lo)/2),float(abs(pts[:,2]).max())])
    p['rim_local']={'starts':starts,'ends':ends,'cross_sections':cross,'eye_native_center_x':p['eye']['center'][0]-.5,'eye_native_radius_x':p['eye']['radius'][0],'eye_center_angle':.1,'eye_angular_radius':.5}
    a.config_output.write_text(json.dumps(head_cfg,indent=2)+'\n')
    report={'ok':True,'input_sha256':sha(a.input),'model_sha256':sha(a.output),'source_sha256':sha(a.source),'parameters_sha256':sha(a.parameters),'rim_vertices':n,'new_inner_vertices':len(inner),'new_inner_triangles':len(inf),'closed_welded_shell':True,'fins_skeleton_animation_source_bytes_preserved':True,'rear_positions_exact':bool(np.array_equal(new[old[:,0]<=cfg['influence_x'][0]],old[old[:,0]<=cfg['influence_x'][0]])),'rear_preservation_limit_x':cfg['influence_x'][0],'max_skin_displacement_native':float(np.linalg.norm(new-old,axis=1).max()),'cavity_bounds':{'min':inner.min(0).tolist(),'max':inner.max(0).tolist()},'scope':cfg['limits']}
    a.report.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))

if __name__=='__main__':main()
