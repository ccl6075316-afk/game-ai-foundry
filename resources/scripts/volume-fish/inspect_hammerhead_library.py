"""Read-only hammerhead library comparison; no production geometry copied.

Run with repository Python and UnityPy 1.25.4 on --deps. Output is a diagnostic
software rendering, not an original-game screenshot or a biological measurement.
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

ROOT = next(p for p in Path(__file__).resolve().parents if (p / 'cli/gamefactory.py').exists())
sys.path.insert(0, str(ROOT / 'resources/scripts/volume-fish/portable'))
from glb_io import read_glb, arrays


def render(v, f, size, view, center, extent, uv=None, tex=None, flip_v=False):
    """Finite triangles, orthographic camera, nearest sampling, opaque clay."""
    basis = {'side': [[1,0,0],[0,1,0],[0,0,1]],
             'top': [[1,0,0],[0,0,1],[0,1,0]],
             'bottom': [[1,0,0],[0,0,-1],[0,-1,0]],
             'front': [[0,0,1],[0,1,0],[-1,0,0]]}[view]
    basis = np.array(basis); w,h=size; q=v @ basis.T
    q[:,:2] = (q[:,:2] - (np.array(center) @ basis.T)[:2]) * (w / extent)
    q[:,0] += w/2; q[:,1] = h/2-q[:,1]
    im=np.full((h,w,3),235,np.uint8); zb=np.full((h,w),-np.inf)
    light=np.array([-.4,.8,.5]);light/=np.linalg.norm(light)
    for inds in f:
        xyz=q[inds]; lo=np.maximum(np.floor(xyz[:,:2].min(0)).astype(int),0); hi=np.minimum(np.ceil(xyz[:,:2].max(0)).astype(int),[w-1,h-1])
        if np.any(lo>hi):continue
        x,y=np.meshgrid(np.arange(lo[0],hi[0]+1)+.5,np.arange(lo[1],hi[1]+1)+.5)
        a,b,c=xyz; den=(b[1]-c[1])*(a[0]-c[0])+(c[0]-b[0])*(a[1]-c[1])
        if abs(den)<1e-12:continue
        aa=((b[1]-c[1])*(x-c[0])+(c[0]-b[0])*(y-c[1]))/den
        bb=((c[1]-a[1])*(x-c[0])+(a[0]-c[0])*(y-c[1]))/den;cc=1-aa-bb
        depth=aa*a[2]+bb*b[2]+cc*c[2];sl=np.s_[lo[1]:hi[1]+1,lo[0]:hi[0]+1]
        keep=(aa>=-1e-8)&(bb>=-1e-8)&(cc>=-1e-8)&(depth>zb[sl])
        n=np.cross(v[inds[1]]-v[inds[0]],v[inds[2]]-v[inds[0]]);n/=max(np.linalg.norm(n),1e-12)
        shade=.5+.5*abs(float(n@light));rgb=np.broadcast_to(np.array([126,151,166])*shade,(*x.shape,3))
        if tex is not None:
            t=uv[inds]; u=aa*t[0,0]+bb*t[1,0]+cc*t[2,0]; vv=aa*t[0,1]+bb*t[1,1]+cc*t[2,1]
            px=np.clip((u*tex.shape[1]).astype(int),0,tex.shape[1]-1);py=np.clip(((1-vv if flip_v else vv)*tex.shape[0]).astype(int),0,tex.shape[0]-1)
            rgba=tex[py,px];keep&=rgba[:,:,3]>=128;rgb=rgba[:,:,:3]*shade
        im[sl][keep]=np.clip(rgb[keep],0,255).astype(np.uint8);zb[sl][keep]=depth[keep]
    return Image.fromarray(im)


def trs(d):
    x,y,z,w=[d['m_LocalRotation'][k] for k in 'xyzw'];q=np.array([x,y,z,w]);q/=np.linalg.norm(q);x,y,z,w=q
    r=np.array([[1-2*(y*y+z*z),2*(x*y-z*w),2*(x*z+y*w)],[2*(x*y+z*w),1-2*(x*x+z*z),2*(y*z-x*w)],[2*(x*z-y*w),2*(y*z+x*w),1-2*(x*x+y*y)]])
    m=np.eye(4);m[:3,:3]=r@np.diag([d['m_LocalScale'][k] for k in 'xyz']);m[:3,3]=[d['m_LocalPosition'][k] for k in 'xyz'];return m


def wing_sections(v, f):
    """Intersections of actual triangles. Head-only transverse stations, no AABB thickness."""
    tris=v[f];span=float(np.max(np.abs(v[v[:,0]<.14,2])))
    rows=[]
    for fraction in [.55,.7,.85]:
        z=fraction*span;points=[]
        for i,j in [(0,1),(1,2),(2,0)]:
            a=tris[:,i];b=tris[:,j];mask=(a[:,2]-z)*(b[:,2]-z)<0;a=a[mask];b=b[mask]
            q=a+(z-a[:,2,None])/(b[:,2,None]-a[:,2,None])*(b-a);points.extend(q[q[:,0]<.14])
        points=np.array(points);front=float(points[:,0].min());rear=float(points[:,0].max());stations=[]
        a,b,c=tris[:,0],tris[:,1],tris[:,2];den=(b[:,2]-c[:,2])*(a[:,0]-c[:,0])+(c[:,0]-b[:,0])*(a[:,2]-c[:,2]);valid=np.abs(den)>1e-12
        for chord_t in [.005,.05,.15,.3,.5,.7,.85,.95,.995]:
            x=front+(rear-front)*chord_t
            aa=np.zeros(len(tris));bb=aa.copy();aa[valid]=((b[valid,2]-c[valid,2])*(x-c[valid,0])+(c[valid,0]-b[valid,0])*(z-c[valid,2]))/den[valid];bb[valid]=((c[valid,2]-a[valid,2])*(x-c[valid,0])+(a[valid,0]-c[valid,0])*(z-c[valid,2]))/den[valid];cc=1-aa-bb
            hit=valid&(aa>=-1e-7)&(bb>=-1e-7)&(cc>=-1e-7);ys=(aa*a[:,1]+bb*b[:,1]+cc*c[:,1])[hit]
            stations.append({'chord_t':chord_t,'x':x,'thickness_over_whole_length':float(np.ptp(ys)) if len(ys)>1 else None,'surface_hits':len(ys)})
        rows.append({'half_span_fraction':fraction,'z':z,'front_x':front,'rear_x':rear,'chord_over_whole_length':rear-front,'stations':stations})
    return {'head_half_span_over_whole_length':span,'definition':'Actual vertical intersections of finite rest triangles at positive lateral head-wing stations; exclude central body and eye-end extrema. Not tissue measurements.','sections':rows}


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--deps',required=True);ap.add_argument('--candidate',required=True);ap.add_argument('--output',required=True);a=ap.parse_args()
    out=Path(a.output).resolve();assert out.is_relative_to(ROOT/'projects/fishing-2d/experiments') and not out.exists();out.mkdir(parents=True)
    sys.path.insert(0,str(Path(a.deps).resolve()));import UnityPy
    sys.path.insert(0,str(ROOT/'resources/fish-database/evidence/fishing-master-cdn-cnformal1-20261102/collection-scripts'))
    from decode_compressed_skin import decode_compressed_skin
    db=ROOT/'resources/fish-database';refpath=db/'references/fishing-master-cdn-cnformal1-20261102-hammerheadshark.json';ref=json.loads(refpath.read_text());obj=db/ref['verified_facts']['mesh_objects'][0]['export_path'];bundle=db/'artifacts/fishing-master-cdn-cnformal1-20261102/b_fish_hammerheadshark.unity3d';own=Path(a.candidate).resolve()
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();assert sha(obj)==ref['verified_facts']['mesh_objects'][0]['sha256']
    vs=[];uvs=[];faces=[];uvfaces=[];groups=[];g=''
    for line in obj.read_text().splitlines():
        if line.startswith('v '):vs.append(list(map(float,line.split()[1:])))
        elif line.startswith('vt '):uvs.append(list(map(float,line.split()[1:])))
        elif line.startswith('g '):g=line[2:]
        elif line.startswith('f '):
            row=[x.split('/') for x in line.split()[1:]];faces.append([int(x[0])-1 for x in row]);uvfaces.append([int(x[1])-1 for x in row]);groups.append(g)
    rv=np.array(vs);rf=np.array(faces);ruv=np.array(uvs)[np.array(uvfaces)].reshape(-1,2)
    raw=bundle.read_bytes();env=UnityPy.load(raw[32:] if raw[32:40]==b'UnityFS\0' else raw)
    trees={o.path_id:o.read_typetree() for o in env.objects if o.type.name in ['Transform','GameObject','SkinnedMeshRenderer','Mesh']};types={o.path_id:o.type.name for o in env.objects};trans={k:d for k,d in trees.items() if types[k]=='Transform'}
    def world(k):return np.eye(4) if not k else world(trans[k]['m_Father']['m_PathID'])@trs(trans[k])
    renderer=next(d for k,d in trees.items() if types[k]=='SkinnedMeshRenderer');mesh=trees[renderer['m_Mesh']['m_PathID']];tf=next(k for k,d in trans.items() if d['m_GameObject']==renderer['m_GameObject']);wm=world(tf)
    bones=[p['m_PathID'] for p in renderer['m_Bones']];ibms=np.array([[[d[f'e{i}{j}'] for j in range(4)] for i in range(4)] for d in mesh['m_BindPose']]);skin=np.array([np.linalg.inv(wm)@world(k)@ibms[i] for i,k in enumerate(bones)])
    meshobj=next(o.read() for o in env.objects if o.type.name=='Mesh');weights,joints=map(np.array,decode_compressed_skin(meshobj.m_CompressedMesh,len(rv)))
    rawv=rv.copy();rawv[:,0]*=-1;hom=np.c_[rawv,np.ones(len(rv))];deformed=np.zeros((len(rv),4))
    for slot in range(4):deformed+=np.einsum('nij,nj->ni',skin[joints[:,slot]],hom)*weights[:,slot,None]
    delta=float(np.max(np.linalg.norm(deformed[:,:3]-rawv,axis=1)));singular=np.linalg.svd(wm[:3,:3],compute_uv=False)
    assert np.ptp(singular)<1e-5;assert delta/np.ptp(rawv[:,1])<1e-4
    texture=next(o.read().image.convert('RGBA') for o in env.objects if o.type.name=='Texture2D' and o.read_typetree()['m_Name']=='HammerheadShark_D');texture.save(out/'reference-diffuse.png')
    # Common X snout->tail, Y up, Z transverse; rigid axis conversion only.
    rv=rv[:,[1,2,0]];L=np.ptp(rv[:,0]);rv[:,0]=(rv[:,0]-rv[:,0].min())/L;rv[:,1]-=(rv[:,1].min()+rv[:,1].max())/2;rv[:,1:]/=L
    doc,blob=read_glb(own);ovs=[];ofs=[];bodyv=[];bodyf=[];offset=0
    for node in doc['nodes']:
        if 'mesh' not in node:continue
        assert not any(k in node for k in ['matrix','rotation','scale','translation'])
        for p in doc['meshes'][node['mesh']]['primitives']:
            v=arrays(doc,blob,p['attributes']['POSITION']).copy();v[:,0]*=-1;f=arrays(doc,blob,p['indices']).reshape(-1,3)
            ovs.append(v);ofs.append(f+offset)
            if node['name']=='Reference_head_body':bodyv.append(v);bodyf.append(f+offset)
            offset+=len(v)
    ov=np.concatenate(ovs);of=np.concatenate(ofs);OL=np.ptp(ov[:,0]);start=ov[:,0].min();cy=(ov[:,1].min()+ov[:,1].max())/2;ov[:,0]=(ov[:,0]-start)/OL;ov[:,1]-=cy;ov[:,1:]/=OL
    # Length normalization includes vertical caudal fin, explicitly engineering TL-like.
    views=['side','top','front','bottom'];sheet=Image.new('RGB',(2400,1100),'#ebebeb');draw=ImageDraw.Draw(sheet)
    for row,(label,v,f) in enumerate([('Project artwork candidate r5 / whole length = 1',ov,of),('Library HammerheadShark / species unverified / whole length = 1',rv,rf)]):
        draw.text((15,row*540+5),label,fill='black')
        for col,view in enumerate(views):
            im=render(v,f,(600,480),view,[.1,0,0],.53);sheet.paste(im,(col*600,row*540+35));draw.text((col*600+10,row*540+45),view,fill='black')
    sheet.save(out/'head-clay-comparison.png')
    fuv=np.arange(len(rf)*3).reshape(-1,3);img=render(rv[rf].reshape(-1,3),fuv,(1400,800),'bottom',[.11,0,0],.55,ruv,np.array(texture),True);img.save(out/'reference-mouth-texture.png')
    whole=Image.new('RGB',(1600,1000),'#ebebeb')
    for i,view in enumerate(['side','top']):whole.paste(render(rv,rf,(1600,500),view,[.5,0,0],1.15),(0,i*500))
    whole.save(out/'reference-whole-clay.png')
    group_rows=[]
    for group in sorted(set(groups)):
        ids=np.flatnonzero(np.array(groups)==group);p=rv[np.unique(rf[ids])];group_rows.append({'group':group,'triangles':len(ids),'normalized_min':p.min(0).tolist(),'normalized_max':p.max(0).tolist()})
    report={'ok':True,'kind':'read_only_hammerhead_library_geometry_inspection','completion_scope':'Source transform proof and diagnostic views; no anatomy acceptance or production geometry changes','inputs':[{'path':str(p.relative_to(ROOT)),'sha256':sha(p)} for p in [obj,bundle,own,refpath]],'reference_species':'unverified game-name HammerheadShark, family-level shape reference only','source_transform_check':{'mesh_world_matrix':wm.tolist(),'singular_values':singular.tolist(),'bind_to_default_max_delta':delta,'bind_to_default_relative_delta':delta/L,'bone_names':[trees[trans[k]['m_GameObject']['m_PathID']]['m_Name'] for k in bones]},'length_basis':'Each whole-fish longitudinal rest extent normalized to 1; engineering TL-like, not biological TL. No separate head scaling.','reference_original_whole_length':float(L),'candidate_original_whole_length_m':float(OL),'groups':group_rows,'wing_measurements':{'candidate':wing_sections(ov,np.concatenate(bodyf)),'reference':wing_sections(rv,rf[np.array(groups)=='HammerheadShark_0'])},'outputs':['head-clay-comparison.png','reference-mouth-texture.png','reference-whole-clay.png'],'unknowns':['Exact reference species, age, sex and biological proportions unverified','Body and fin geometry not yet partitioned; no fin-excluded body-width claim','Library runtime motion and mouth animation unreviewed','Software diagnostic shading is not original-game or Godot rendering']}
    (out/'validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps({'ok':True,'output':str(out),'default_pose_delta':delta,'bones':report['source_transform_check']['bone_names'],'groups':group_rows}))


if __name__=='__main__':main()
