"""Bake shallow source-matched eye caps with actual body skin weights.

Underlying opaque bodies remain intact. Each cap follows the original eye UV
footprint and is a real skinned mesh, not a normal-map or flat billboard.
"""
import argparse,hashlib,json
from pathlib import Path
import numpy as np
from freeze_surface_ownership import read_glb,accessor

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def barycentric2(points,point):
    a=points[:,0];ab=points[:,1]-a;ac=points[:,2]-a;delta=point-a
    den=ab[:,0]*ac[:,1]-ab[:,1]*ac[:,0];safe=np.abs(den)>1e-14
    u=np.zeros(len(a));v=u.copy();u[safe]=(delta[safe,0]*ac[safe,1]-delta[safe,1]*ac[safe,0])/den[safe]
    v[safe]=(ab[safe,0]*delta[safe,1]-ab[safe,1]*delta[safe,0])/den[safe]
    weights=np.column_stack([1-u-v,u,v]);return weights,safe&(weights.min(1)>-1e-5)&(weights.max(1)<1.00001)
def main():
    ap=argparse.ArgumentParser(description=__doc__)
    for key in ['game','parameters','output']:ap.add_argument('--'+key,type=Path,required=True)
    ap.add_argument('--species',nargs='*');a=ap.parse_args();p=json.loads(a.parameters.read_text());profiles={};reports=[]
    own=json.loads((a.game/'assets/models/fish/motion/body-opacity.json').read_text())['profiles']
    surface=json.loads((a.game/'assets/models/fish/motion/surface-ownership.json').read_text())['profiles']
    a.output.mkdir(parents=True,exist_ok=True)
    for species,row in p['species'].items():
        if a.species and species not in a.species:continue
        if not row.get('enabled',True):continue
        model=a.game/'assets/models/fish'/(species+'.glb');assert sha(model)==row['model_sha256']
        d,b=read_glb(model);candidates=[]
        for node in d['nodes']:
            if 'mesh' not in node or node['name'] in surface[species]['fins'] or node['name'] in own[species].get('decorative_overlays',{}):continue
            for si,pr in enumerate(d['meshes'][node['mesh']]['primitives']):
                if 'TEXCOORD_0' not in pr['attributes']:continue
                pos=accessor(d,b,pr['attributes']['POSITION']);candidates.append((np.ptp(pos[:,0]),node,si,pr))
        _,node,si,pr=max(candidates,key=lambda v:v[0]);assert 'skin' in node
        attrs=pr['attributes'];pos=accessor(d,b,attrs['POSITION']);uv=accessor(d,b,attrs['TEXCOORD_0']);normal=accessor(d,b,attrs['NORMAL'])
        joints=accessor(d,b,attrs['JOINTS_0']);weights=accessor(d,b,attrs['WEIGHTS_0']);tri=accessor(d,b,pr['indices']).reshape(-1,3)
        native_projection=bool(row.get('projection') or row.get('native_xy'))
        if native_projection:
            # Existing multi-material heads may have different UV charts on the
            # cap. Intersect the complete actual body in native XY space.
            vp=[];up=[];npieces=[];jp=[];wp=[];tp=[];offset=0
            if row.get('native_surface'):
                frozen=row['native_surface'];support=Path(frozen['path'])
                if not support.is_absolute():support=Path(__file__).resolve().parents[3]/support
                assert sha(support)==frozen['sha256'],'Stale actual eye support body'
                actual=json.loads(support.read_text())
                for part in actual['parts']:
                    vv=np.asarray(part['vertices']);vp.append(vv);up.append(np.asarray(part['uv']));npieces.append(np.asarray(part['normals']))
                    jp.append(np.asarray(part['joints']));wp.append(np.asarray(part['weights']))
                    tp.append(np.asarray(part['triangles']).reshape(-1,3)+offset);offset+=len(vv)
            else:
                for part in d['meshes'][node['mesh']]['primitives']:
                    at=part['attributes'];vv=accessor(d,b,at['POSITION'])
                    vp.append(vv);up.append(accessor(d,b,at['TEXCOORD_0']));npieces.append(accessor(d,b,at['NORMAL']))
                    jp.append(accessor(d,b,at['JOINTS_0']));wp.append(accessor(d,b,at['WEIGHTS_0']))
                    tp.append(accessor(d,b,part['indices']).reshape(-1,3)+offset);offset+=len(vv)
            pos=np.concatenate(vp);uv=np.concatenate(up);normal=np.concatenate(npieces);joints=np.concatenate(jp);weights=np.concatenate(wp);tri=np.concatenate(tp)
        src=np.asarray(row['center_uv']);radius=np.asarray(row['radius_uv'])*float(row.get('footprint',.93));scale=float(row.get('body_eye_scale',1.))
        samples=[(0.,0.)];rings=int(row.get('rings',8));sectors=int(row.get('sectors',40))
        for ring in range(1,rings+1):
            for i in range(sectors):
                theta=i*2*np.pi/sectors;r=ring/rings;samples.append((r*np.cos(theta),r*np.sin(theta)))
        caps=[];peak=[]
        for side in [-1,1]:
            all_vertices=[];all_uv=[];all_normals=[];all_joints=[];all_weights=[];base=[]
            if row.get('projection'):
                calibration=row['projection'];size=np.asarray(row['source_size']);pixel=np.asarray(calibration['pixel_native_xy'])
                anchor=np.asarray(calibration['anchor_rest_xy'])-[0,float(calibration['downshift_native_pixels'])*pixel[1]]
                pupil=np.asarray(calibration['source_pupil_px'])
                center_native=anchor+(src*size-pupil)*pixel*[1,-1]
                radius_native=radius*size*pixel
            elif row.get('native_xy'):
                center_native=np.asarray(row['native_xy']['center']);radius_native=np.asarray(row['native_xy']['radius'])*float(row.get('footprint',.93))
            # Select by outward side, not just matching UV on the opposite face.
            tpos=pos[tri];side_mask=tpos[:,:,2].mean(1)*side>=-1e-7
            selected=tri[side_mask];test=(pos[selected][:,:,:2] if native_projection else uv[selected])
            if native_projection:
                low=center_native-radius_native*1.03;high=center_native+radius_native*1.03
            else:low=src-radius*scale*1.03;high=src+radius*scale*1.03
            keep=(test.max(1)>=low).all(1)&(test.min(1)<=high).all(1);selected=selected[keep];test=test[keep]
            assert len(selected)>0,(species,side,'No eye-side triangles')
            for q in samples:
                q=np.asarray(q);tex=src+q*radius
                if native_projection:point=center_native+q*radius_native*[1,-1]
                else:point=src+q*radius*scale
                bary,valid=barycentric2(test,point);ids=np.flatnonzero(valid)
                assert len(ids),(species,side,'Source eye sample outside body',tex.tolist())
                z=np.sum(pos[selected[ids],2]*bary[ids],1)*side;pick=ids[z.argmax()];face=selected[pick];bw=bary[pick]
                surface_point=np.sum(pos[face]*bw[:,None],0);n=np.sum(normal[face]*bw[:,None],0);n/=max(np.linalg.norm(n),1e-12)
                if n[2]*side<.15:
                    n[2]=side*max(abs(n[2]),.15);n/=np.linalg.norm(n)
                base.append(surface_point.tolist())
                if native_projection:native_radius=float(min(radius_native))
                else:
                    # Source-to-body metric is fitted to the actual local eye UV triangles.
                    coeff=np.linalg.lstsq(np.column_stack([uv[np.unique(selected)],np.ones(len(np.unique(selected)))]),pos[np.unique(selected)],rcond=None)[0]
                    native_radius=float(min(np.linalg.norm(coeff[0])*radius[0]*scale,np.linalg.norm(coeff[1])*radius[1]*scale))
                height=float(row['height_over_radius'])*native_radius
                relief=height*(1-float(q@q))**2+height*.015
                new=surface_point+n*relief
                influence={}
                for vertex,blend in zip(face,bw):
                    for bone,weight in zip(joints[vertex],weights[vertex]):
                        influence[int(bone)]=influence.get(int(bone),0.)+float(blend*weight)
                top=sorted(influence.items(),key=lambda v:v[1],reverse=True)[:4]
                while len(top)<4:top.append((0,0.))
                total=sum(v for _,v in top);assert total>.99
                all_vertices.append(new.tolist());all_uv.append(tex.tolist());all_normals.append(n.tolist());all_joints.append([i for i,_ in top]);all_weights.append([max(0.,v)/total for _,v in top])
            indices=[]
            for i in range(sectors):indices.extend([0,1+i,1+(i+1)%sectors])
            for ring in range(1,rings):
                a0=1+(ring-1)*sectors;b0=a0+sectors
                for i in range(sectors):
                    j=(i+1)%sectors;indices.extend([a0+i,b0+i,b0+j,a0+i,b0+j,a0+j])
            # Derive smooth normals from the actual raised triangular cap.
            vv=np.array(all_vertices);tt=np.array(indices).reshape(-1,3);nn=np.zeros_like(vv)
            fn=np.cross(vv[tt[:,1]]-vv[tt[:,0]],vv[tt[:,2]]-vv[tt[:,0]])
            if np.mean(fn[:,2])*side<0:tt=tt[:,[0,2,1]];fn=-fn
            for j in range(3):np.add.at(nn,tt[:,j],fn)
            nn/=np.maximum(np.linalg.norm(nn,axis=1)[:,None],1e-12)
            caps.append({'side':side,'vertices':all_vertices,'normals':nn.tolist(),'uv':all_uv,'joints':all_joints,'weights':all_weights,'indices':tt.reshape(-1).tolist(),'base_surface_points':base})
            peak.append(float(np.max(np.linalg.norm(vv-np.array(base),axis=1))))
        bone_names=[d['nodes'][i]['name'] for i in d['skins'][node['skin']]['joints']]
        profiles[species]={'model_sha256':row['model_sha256'],'mesh':node['name'],'source_surface':si,'source_size':row['source_size'],'source_center':row['center_uv'],'source_radius':row['radius_uv'],'bones':bone_names,'caps':caps}
        if row.get('native_surface'):profiles[species]['native_surface']=row['native_surface']
        reports.append({'species':species,'model_sha256':row['model_sha256'],'caps':2,'vertices_per_cap':len(samples),'peak_native':peak,'underlying_body_unchanged':True,'source_footprint_preserved':True,'limits':'Height is a subtle game-art choice, not measured corneal projection. Original opaque body remains under each skinned cap.'})
        print('EYE_RELIEF',species,flush=True)
    (a.output/'eye-relief112.json').write_text(json.dumps({'schema_version':1,'profiles':profiles},separators=(',',':'))+'\n')
    (a.output/'build.validation.json').write_text(json.dumps({'ok':bool(reports),'script_sha256':sha(__file__),'parameters_sha256':sha(a.parameters),'items':reports},indent=2)+'\n')
if __name__=='__main__':main()
