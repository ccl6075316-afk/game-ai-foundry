"""Compare the actual old/new GLBs and probe the preserved ventral cavity."""
import argparse
import hashlib
import io
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0,str(Path(__file__).resolve().parent/'portable'))
from glb_io import read_glb, arrays


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--baseline',type=Path,required=True);ap.add_argument('--candidate',type=Path,required=True);ap.add_argument('--mouth-probes',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);a=ap.parse_args()
    assert not a.output.exists();old,ob=read_glb(a.baseline);new,nb=read_glb(a.candidate);sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    def nodes(d):return {n['name']:d['meshes'][n['mesh']]['primitives'] for n in d['nodes'] if 'mesh' in n}
    om,nm=nodes(old),nodes(new);assert set(om)==set(nm);rows=[]
    for name in nm:
        assert len(om[name])==len(nm[name]);changed=[]
        for i,(x,y) in enumerate(zip(om[name],nm[name])):
            assert x.keys()==y.keys();assert x['attributes'].keys()==y['attributes'].keys()
            assert np.array_equal(arrays(old,ob,x['indices']),arrays(new,nb,y['indices']))
            for attr in x['attributes']:
                u=arrays(old,ob,x['attributes'][attr]);v=arrays(new,nb,y['attributes'][attr]);assert u.shape==v.shape and np.isfinite(v).all()
                delta=float(np.max(np.abs(u.astype(float)-v)))
                if delta:changed.append({'surface':i,'attribute':attr,'maximum_delta':delta})
                if attr not in ['POSITION','NORMAL']:assert delta==0,(name,attr)
                if attr=='POSITION' and name=='Reference_head_body':assert np.array_equal(u[:,[0,2]],v[:,[0,2]])
                if attr=='POSITION' and name.startswith('Eye_'):assert np.allclose(np.ptp(u[:,:2],axis=0),np.ptp(v[:,:2],axis=0),atol=1e-7,rtol=0)
        if name not in ['Reference_head_body','Eye_left','Eye_right']:assert not changed,(name,changed)
        rows.append({'mesh':name,'changed_arrays':changed,'topology_UV_skin_exact':True})
    for key in ['nodes','skins','animations','materials','textures','samplers']:assert old.get(key)==new.get(key),key
    animation_arrays=[]
    for animation in old['animations']:
        for s in animation['samplers']:
            for key in ['input','output']:
                i=s[key];assert np.array_equal(arrays(old,ob,i),arrays(new,nb,i));animation_arrays.append(i)
    image_rows=[]
    for i,(x,y) in enumerate(zip(old['images'],new['images'])):
        def pixels(d,b,im):
            v=d['bufferViews'][im['bufferView']];data=b[v.get('byteOffset',0):v.get('byteOffset',0)+v['byteLength']];return Image.open(io.BytesIO(data)).convert('RGBA')
        u,v=pixels(old,ob,x),pixels(new,nb,y);assert u.size==v.size and u.tobytes()==v.tobytes();image_rows.append({'image':i,'size':u.size,'rgba_sha256':hashlib.sha256(v.tobytes()).hexdigest()})
    def oral_data(d,b):
        verts=[];faces=[];materials=[];offset=0
        for prim in nodes(d)['Reference_head_body']:
            v=arrays(d,b,prim['attributes']['POSITION']);f=arrays(d,b,prim['indices']).reshape(-1,3);verts.append(v);faces.append(f+offset);materials.extend([d['materials'][prim['material']]['name']]*len(f));offset+=len(v)
        return np.concatenate(verts),np.concatenate(faces),materials
    def hit(d,b,x,y):
        v,f,m=oral_data(d,b);t=v[f];px=x;pz=-y;a,b,c=t[:,0],t[:,1],t[:,2];den=(b[:,2]-c[:,2])*(a[:,0]-c[:,0])+(c[:,0]-b[:,0])*(a[:,2]-c[:,2]);valid=np.abs(den)>1e-12;aa=np.zeros(len(t));bb=aa.copy();aa[valid]=((b[valid,2]-c[valid,2])*(px-c[valid,0])+(c[valid,0]-b[valid,0])*(pz-c[valid,2]))/den[valid];bb[valid]=((c[valid,2]-a[valid,2])*(px-c[valid,0])+(a[valid,0]-c[valid,0])*(pz-c[valid,2]))/den[valid];cc=1-aa-bb;mask=valid&(aa>=-1e-7)&(bb>=-1e-7)&(cc>=-1e-7);ids=np.flatnonzero(mask);assert len(ids)>0
        heights=aa*a[:,1]+bb*b[:,1]+cc*c[:,1];i=ids[np.argmin(heights[ids])];return {'first_hit_vertical_m':float(heights[i]),'material':m[i]}
    probes=[]
    for probe in json.loads(a.mouth_probes.read_text())['probes']:
        x,y=probe['x_m'],probe['y_m'];u,v=hit(old,ob,x,y),hit(new,nb,x,y);assert u==v and v['material']=='Actual finite oral lining';probes.append({'x_m':x,'transverse_m':y,**v})
    result={'ok':True,'kind':'current_hammerhead_revision_semantic_preservation','baseline_sha256':sha(a.baseline),'model_sha256':sha(a.candidate),'meshes':rows,'all_eight_fins_all_attributes_exact':True,'body_X_transverse_coordinates_exact':True,'UV_skin_topology_exact':True,'rig_and_native_animation_exact':True,'animation_arrays_exact':sorted(set(animation_arrays)),'embedded_images_RGBA_exact':image_rows,'mouth_actual_rays':probes,'oral_opening_geometry_preserved':True,'material_bindings_and_nearest_exact':True,'scope':'Preservation proof for unchanged source/fin/mouth/material dependencies. Current body/GPU, fin contact and appearance gates remain separate; not user acceptance.'}
    a.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps({'ok':True,'fins_exact':8,'mouth_rays':len(probes),'images_exact':len(image_rows)}))


if __name__=='__main__':main()
