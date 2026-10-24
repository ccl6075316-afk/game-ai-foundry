"""Derive UV ownership/edge data, never alter accepted source image pixels or GLB.

The runtime remaps skin donors only on body surfaces sharing the paired fin's
source texture. This is a production inference of concealed skin, not new art.
"""
import argparse,hashlib,io,json,struct
from pathlib import Path
import cv2
import numpy as np
from PIL import Image

def read_glb(path):
    b=path.read_bytes();n=struct.unpack_from('<I',b,12)[0]
    return json.loads(b[20:20+n]),b[28+n:]

def accessor(d,b,index):
    a=d['accessors'][index];v=d['bufferViews'][a['bufferView']]
    dt=np.dtype('<'+{5126:'f4',5125:'u4',5123:'u2',5121:'u1'}[a['componentType']]);c={'SCALAR':1,'VEC2':2,'VEC3':3,'VEC4':4}[a['type']]
    return np.ndarray((a['count'],c),dtype=dt,buffer=b,offset=v.get('byteOffset',0)+a.get('byteOffset',0),strides=(v.get('byteStride',c*dt.itemsize),dt.itemsize)).copy()

def freeze(path,parameters=None):
    d,b=read_glb(path);images=[]
    parameters=parameters or {}
    spec=parameters.get(path.stem,{})
    for image in d['images']:
        v=d['bufferViews'][image['bufferView']];images.append(np.asarray(Image.open(io.BytesIO(b[v.get('byteOffset',0):v.get('byteOffset',0)+v['byteLength']])).convert('RGBA')))
    def texture(primitive):
        m=d['materials'][primitive['material']]
        t=m.get('pbrMetallicRoughness',{}).get('baseColorTexture')
        return d['textures'][t['index']]['source'] if t else None
    skins={};fins={};paired={};tokens=['dorsal','anal','caudal','pectoral','pelvic','tail_fin','adipose']
    for node in d['nodes']:
        if 'mesh' not in node:continue
        name=node['name'];isfin=any(t in name.lower() for t in tokens)
        if not isfin:continue
        for si,prim in enumerate(d['meshes'][node['mesh']]['primitives']):
            ti=texture(prim)
            if ti is None:continue
            image=images[ti];h,w=image.shape[:2];uv=accessor(d,b,prim['attributes']['TEXCOORD_0']);tri=accessor(d,b,prim['indices']).reshape(-1,3)
            occupancy=np.zeros((h,w),np.uint8)
            for face in tri:
                p=np.round(uv[face]*[w,h]).astype(np.int32)
                a=p[1]-p[0];z=p[2]-p[0]
                if abs(int(a[0])*int(z[1])-int(a[1])*int(z[0]))>.5:cv2.fillConvexPoly(occupancy,p,255)
            contours,_=cv2.findContours(occupancy,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
            edges=[];boundary=np.zeros_like(occupancy)
            for c in contours:
                simple=cv2.approxPolyDP(c,1.2,True).reshape(-1,2)
                cv2.drawContours(boundary,[c],-1,255,max(2,round(w/600)))
                for a,z in zip(simple,np.roll(simple,-1,axis=0)):edges.append([a[0]/w,a[1]/h,z[0]/w,z[1]/h])
            # A basal attachment is not a free border. Explicit species source
            # baselines exclude only those boundary segments from added ink.
            for base in spec.get('attached_fin_baselines',{}).get(name,[]):
                aa,bb=np.asarray(base['points'],float)*[w,h];ab=bb-aa
                retained=[];denom=max(np.dot(ab,ab),1e-12)
                for edge in edges:
                    pa,pb=np.asarray(edge[:2])*[w,h],np.asarray(edge[2:])*[w,h]
                    ta,tb=np.dot(pa-aa,ab)/denom,np.dot(pb-aa,ab)/denom
                    if max(np.linalg.norm(pa-aa-ta*ab),np.linalg.norm(pb-aa-tb*ab))>base['tolerance_px'] or abs(tb-ta)<1e-10:
                        retained.append(edge);continue
                    cuts=sorted(set([0.,1.]+[float(np.clip((t-ta)/(tb-ta),0,1)) for t in [0.,1.]]))
                    for lo,hi in zip(cuts,cuts[1:]):
                        t=ta+(tb-ta)*(lo+hi)/2
                        if 0<=t<=1:continue
                        retained.append(np.r_[(pa+(pb-pa)*lo)/[w,h],(pa+(pb-pa)*hi)/[w,h]].tolist())
                edges=retained
            assert len(edges)<=128,(name,len(edges))
            ink=image[(boundary>0)&(image[:,:,3]>240),:3]/255
            if len(ink):ink=ink[np.argsort(ink@np.array([.2126,.7152,.0722]))[max(0,int(len(ink)*.08))]].tolist()
            else:ink=[.10,.10,.08]
            fins.setdefault(name,{})[str(si)]={'edges':edges,'size':[w,h],'ink':ink,'width_px':max(1.5,w/800)}
            if 'pectoral' in name.lower() or 'pelvic' in name.lower():paired.setdefault(ti,[]).append(occupancy)
    patches={}
    for ti,masks in paired.items():
        image=images[ti];h,w=image.shape[:2];mask=np.maximum.reduce(masks)
        mask=cv2.dilate(mask,np.ones((max(5,round(w/50))|1,)*2,np.uint8))
        # Authored fin UVs can exclude the original source ink. Reviewed source
        # footprints live with species parameters, separate from this algorithm.
        for footprint in spec.get('source_footprints',[]):
            if footprint['image_index']!=ti:continue
            assert footprint['source_size']==[w,h],'Stale source footprint dimensions'
            assert footprint['source_rgba_sha256']==hashlib.sha256(image.tobytes()).hexdigest(),'Stale source footprint pixels'
            cv2.fillPoly(mask,[np.array(footprint['polygon_px'],np.int32)],255)
        contours,_=cv2.findContours(mask,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE);regions=[]
        for c in contours:
            if cv2.contourArea(c)<3:continue
            points=cv2.approxPolyDP(c,1.2,True).reshape(-1,2);assert len(points)<=64
            x,y,rw,rh=cv2.boundingRect(c)
            # Adjacent posterior skin retains the same vertical colour zone.
            high=max(0.,x/w-.004);low=max(0.,high-min(.035,rw/w*.65))
            regions.append({'polygon':(points/[w,h]).tolist(),'rect':[x/w,y/h,(x+rw)/w,(y+rh)/h],'donor_u':[low,high]})
        assert len(regions)<=8
        patches[ti]=regions
    for node in d['nodes']:
        if 'mesh' not in node or node['name'] in fins:continue
        for si,prim in enumerate(d['meshes'][node['mesh']]['primitives']):
            ti=texture(prim)
            if ti in patches:skins.setdefault(node['name'],{})[str(si)]={'patches':patches[ti]}
    clean=spec.get('existing_separate_clean_body_texture')
    if clean:
        assert clean['model_sha256']==hashlib.sha256(path.read_bytes()).hexdigest(),'Stale clean body review'
    assert skins or clean,'No matching body material; explicitly review existing separate body skin'
    return {'model_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'skin_status':'existing_separate_clean_body_texture' if clean else 'runtime_donor_remap','method':'Source-image UV ownership; nearby posterior skin donors inferred at runtime; source bytes and fin sampling unchanged. Free-edge ink follows each fin UV boundary.','skins':skins,'fins':fins}

def main():
    p=argparse.ArgumentParser();p.add_argument('--models',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--parameters',type=Path,default=Path(__file__).resolve().parents[2]/'volume-fish/surface-ownership-074.json');a=p.parse_args()
    parameters=json.loads(a.parameters.read_text(encoding='utf8'))
    data={'schema_version':1,'parameters_sha256':hashlib.sha256(a.parameters.read_bytes()).hexdigest(),'profiles':{f.stem:freeze(f,parameters['species']) for f in sorted(a.models.glob('*.glb'))}}
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps({s:{'skins':len(v['skins']),'fins':len(v['fins'])} for s,v in data['profiles'].items()}))
if __name__=='__main__':main()
