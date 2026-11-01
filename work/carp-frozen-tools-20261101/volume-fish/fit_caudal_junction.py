"""Fit the whole caudal/peduncle junction, retaining complete basal coverage.

The user permits reducing the tail. The free tail and its UV artwork are scaled
together; the attachment collar blends back to the actual body cap. Original
body/rig/other fins stay intact. Thickness is a bounded construction inference.
"""
import argparse,copy,hashlib,json
from pathlib import Path
import numpy as np
from freeze_surface_ownership import read_glb,accessor
from patch_existing_fin_meshes import write

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    cli=argparse.ArgumentParser();cli.add_argument('--plan',type=Path,required=True);cli.add_argument('--output',type=Path,required=True);cli.add_argument('--scale',type=float,default=.9);cli.add_argument('--collar',type=float,default=.035);a=cli.parse_args()
    assert .8<=a.scale<=1 and .015<=a.collar<=.06
    result=[]
    for spec in json.loads(a.plan.read_text(encoding='utf8'))['items']:
        source=Path(spec['model']);assert sha(source)==spec['model_sha256'];d,blob=read_glb(source);binary=bytearray(blob)
        body=next(n for n in d['nodes'] if n.get('name')==spec['body'] and 'mesh' in n)
        body_v=np.concatenate([accessor(d,blob,p['attributes']['POSITION']) for p in d['meshes'][body['mesh']]['primitives']])
        rear=float(body_v[:,0].min());cap=body_v[np.abs(body_v[:,0]-rear)<1e-6];yc=float((cap[:,1].min()+cap[:,1].max())/2)
        ys=np.unique(np.round(cap[:,1],7));width=np.array([np.abs(cap[np.abs(cap[:,1]-y)<1.1e-7,2]).max() for y in ys])
        node=next(n for n in d['nodes'] if n.get('name')=='Caudal' and 'mesh' in n);p=d['meshes'][node['mesh']]['primitives'][0]
        vs=accessor(d,blob,p['attributes']['POSITION']);normals=accessor(d,blob,p['attributes']['NORMAL']);tri=accessor(d,blob,p['indices']).reshape(-1,3)
        old=vs.copy();roots=np.asarray(spec['fins']['Caudal']['rest_points_gltf']);ids=np.asarray(spec['fins']['Caudal']['ids'],int)
        assert len(ids)==len(roots) and np.max(np.abs(vs[ids]-roots))<1e-6
        distance=np.maximum(0,rear-vs[:,0]);t=np.clip(distance/a.collar,0,1);smooth=t*t*(3-2*t)
        # Whole free fin scale. The complete original basal region still spans
        # the body's full cap, rather than shrinking the validated selection.
        gain=1+(a.scale-1)*smooth;vs[:,0]=rear+(vs[:,0]-rear)*gain;vs[:,1]=yc+(vs[:,1]-yc)*gain
        side=np.where(old[:,2]>=0,1.,-1.);z=np.interp(old[:,1],ys,width,left=0,right=0)
        z=np.maximum(np.abs(old[:,2]),z*.9998)
        vs[:,2]=side*(np.abs(old[:,2])*smooth+z*(1-smooth))
        # Preserve all original base XY; only expand its section to match cap.
        vs[ids,:2]=old[ids,:2]
        ns=np.zeros_like(vs);face=np.cross(vs[tri[:,1]]-vs[tri[:,0]],vs[tri[:,2]]-vs[tri[:,0]])
        assert np.min(np.linalg.norm(face,axis=1))>1e-13
        for j in range(3):np.add.at(ns,tri[:,j],face)
        ns/=np.maximum(np.linalg.norm(ns,axis=1)[:,None],1e-20)
        # Share the actual body's boundary normal across the joint. Independent
        # normal averaging treats the two connected pieces as capped objects
        # and creates a false bright cut even when their positions coincide.
        bv=[];bn=[]
        for primitive in d['meshes'][body['mesh']]['primitives']:
            pv=accessor(d,blob,primitive['attributes']['POSITION']);pn=accessor(d,blob,primitive['attributes']['NORMAL'])
            selected=(np.abs(pv[:,0]-rear)<1e-6)&(pv[:,2]>=-1e-8)
            bv.extend(pv[selected]);bn.extend(pn[selected])
        bv=np.asarray(bv);bn=np.asarray(bn);order=np.argsort(bv[:,1]);bv=bv[order];bn=bn[order]
        join=np.stack([np.interp(old[:,1],bv[:,1],bn[:,j]) for j in range(3)],axis=1);join[:,2]*=side
        blend=np.clip(distance/.012,0,1);blend=blend*blend*(3-2*blend)
        ns=ns*blend[:,None]+join*(1-blend[:,None]);ns/=np.maximum(np.linalg.norm(ns,axis=1)[:,None],1e-20)
        for semantic,values in [('POSITION',vs),('NORMAL',ns)]:
            original=p['attributes'][semantic];acc=copy.deepcopy(d['accessors'][original]);data=np.asarray(values,dtype='<f4');binary.extend(b'\0'*(-len(binary)%4));offset=len(binary);binary.extend(data.tobytes())
            acc.update(bufferView=len(d['bufferViews']),byteOffset=0,min=data.min(axis=0).tolist(),max=data.max(axis=0).tolist());d['bufferViews'].append({'buffer':0,'byteOffset':offset,'byteLength':data.nbytes,'target':34962});d['accessors'].append(acc);p['attributes'][semantic]=len(d['accessors'])-1
        assert binary[:len(blob)]==blob
        folder=a.output/spec['species'];folder.mkdir(parents=True,exist_ok=True);dest=folder/'fish.glb';write(dest,d,binary)
        spec=copy.deepcopy(spec);spec.update(model=str(dest.resolve()),model_sha256=sha(dest))
        spec['fins']['Caudal']['rest_points_gltf']=vs[ids].tolist()
        allv=np.concatenate([vs]+[accessor(d,blob,q['attributes']['POSITION']) for n in d['nodes'] if 'mesh' in n and n['mesh']!=node['mesh'] for q in d['meshes'][n['mesh']]['primitives']])
        length=float(np.ptp(allv[:,0]));spec['scale_cm']*=spec['length_native']/length;spec['length_native']=length
        report={'ok':True,'source':str(source),'source_sha256':sha(source),'model_sha256':sha(dest),'tail_scale':a.scale,'attachment_collar_native':a.collar,'body_cap_x':rear,'body_cap_center_y':yc,'body_cap_half_width_native':float(width.max()),'root_count':len(ids),'root_ids_complete_and_unchanged':True,'root_xy_preserved':True,'body_other_meshes_uv_skinning_animation_images_preserved':True,'root_section_method':'Actual body-cap polygon width at each original basal Y; two caudal sides expand to the matching section. 0.9998 lateral inset; root XY remains unchanged.','limits':'Thickness between observed cap and thin free lobe is production inference; all dynamic root and membrane gates required.'}
        (folder/'junction.validation.json').write_text(json.dumps(report,indent=2),encoding='utf8');result.append(spec);print(json.dumps(report))
    (a.output/'candidate.plan.json').write_text(json.dumps({'items':result},indent=2),encoding='utf8')
if __name__=='__main__':main()
