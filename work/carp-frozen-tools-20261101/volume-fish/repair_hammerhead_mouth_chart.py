"""Use one source chart across overlapping hammerhead body/cephalofoil skins.

Closed-mouth appearance comes from the accepted source artwork. This does not
create mouth opening animation, teeth geometry, or an independently moving jaw.
"""
import argparse,copy,hashlib,json
from pathlib import Path
import numpy as np
from scipy.interpolate import PchipInterpolator
from freeze_surface_ownership import read_glb,accessor
from patch_existing_fin_meshes import write
def smooth(t):
    t=np.clip(t,0,1)
    return t*t*t*(10+t*(-15+6*t))

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--plan',type=Path,required=True);ap.add_argument('--report',type=Path,required=True);a=ap.parse_args();records=[]
    for row in json.loads(a.plan.read_text())['items']:
        assert sha(row['source'])==row['source_sha256'];d,b=read_glb(Path(row['source']));old=copy.deepcopy(d);binary=bytearray(b);counts=[]
        for name in ['Closed_body','Cephalofoil']:
            node=next(n for n in d['nodes'] if n.get('name')==name)
            assert not any(k in node for k in ['matrix','translation','rotation','scale'])
            for channel in row['channels']:
                assert channel['surface']==2, 'Only ventral mouth UV is authorized'
                si=channel['surface'];part=d['meshes'][node['mesh']]['primitives'][si];at=part['attributes'];p=accessor(old,b,at['POSITION']).astype(float);uv=accessor(old,b,at['TEXCOORD_0']).astype(float)
                curve=np.asarray(channel['u_curve']);uu=PchipInterpolator(curve[:,0],curve[:,1])(np.clip(p[:,0],curve[0,0],curve[-1,0]))
                target=np.column_stack((uu,.5-p[:,2]*channel['v_scale']))
                amount=smooth((p[:,0]-.33)/.045)*(1-smooth((abs(p[:,2])-.045)/.035))
                out=(uv*(1-amount[:,None])+target*amount[:,None]).astype('<f4')
                binary.extend(b'\0'*(-len(binary)%4));offset=len(binary);binary.extend(out.tobytes());vi=len(d['bufferViews']);d['bufferViews'].append(dict(buffer=0,byteOffset=offset,byteLength=out.nbytes,target=34962))
                ac=copy.deepcopy(d['accessors'][at['TEXCOORD_0']]);ac.update(bufferView=vi,byteOffset=0,min=out.min(0).tolist(),max=out.max(0).tolist());at['TEXCOORD_0']=len(d['accessors']);d['accessors'].append(ac)
                counts.append(dict(mesh=name,surface=si,changed_vertices=int(np.any(out!=uv,axis=1).sum())))
        assert bytes(binary[:len(b)])==b
        for key in ['nodes','skins','animations','images','materials','textures','samplers']:assert d.get(key)==old.get(key)
        expected=copy.deepcopy(old['meshes'])
        for node in d['nodes']:
            if node.get('name') in ['Closed_body','Cephalofoil']:
                mi=node['mesh']
                expected[mi]['primitives'][2]['attributes']['TEXCOORD_0']=d['meshes'][mi]['primitives'][2]['attributes']['TEXCOORD_0']
        assert d['meshes']==expected, 'Unexpected geometry, fin or other surface change'
        write(Path(row['target']),d,binary);records.append(dict(species=row['species'],source_sha256=row['source_sha256'],model_sha256=sha(row['target']),changes=counts,geometry_unchanged=True))
    a.report.write_text(json.dumps(dict(ok=True,items=records,plan_sha256=sha(a.plan),builder_sha256=sha(__file__)),indent=2)+'\n')
if __name__=='__main__':main()
