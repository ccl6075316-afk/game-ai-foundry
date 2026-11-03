"""Audit renderer hierarchy scale for a local Unity bind-geometry shape reference."""
import argparse,hashlib,json,sys
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
ROOT=Path(__file__).resolve().parents[3]
def main(a):
    sys.path.insert(0,str(a.dependencies.resolve()));import UnityPy
    bundle=a.bundle.resolve();raw=bundle.read_bytes();prefix=32 if raw[32:40]==b'UnityFS\0' else 0
    env=UnityPy.load(raw[prefix:]);objects={o.path_id:o for o in env.objects};trans={o.path_id:o.read_typetree() for o in env.objects if o.type.name=='Transform'}
    renderer=next(o for o in env.objects if o.type.name=='SkinnedMeshRenderer');r=renderer.read_typetree();go=r['m_GameObject']['m_PathID'];tid=next(k for k,v in trans.items() if v['m_GameObject']['m_PathID']==go)
    chain=[];matrix=np.eye(4)
    while tid:
        t=trans[tid];s=np.array([t['m_LocalScale'][k] for k in 'xyz']);q=[t['m_LocalRotation'][k] for k in 'xyzw'];v=[t['m_LocalPosition'][k] for k in 'xyz'];m=np.eye(4);m[:3,:3]=Rotation.from_quat(q).as_matrix()@np.diag(s);m[:3,3]=v;matrix=m@matrix
        chain.append({'transform_id':tid,'local_scale':s.tolist(),'local_quaternion':q,'local_position':v});tid=t['m_Father']['m_PathID']
    singular=np.linalg.svd(matrix[:3,:3],compute_uv=False);ratio=float(singular.max()/singular.min());assert ratio<1.00001,'Nonuniform renderer hierarchy; do not use raw mesh ratios'
    result={'ok':True,'kind':'local_unity_bind_geometry_reference_transform_audit','bundle':str(bundle.relative_to(ROOT)),'bundle_sha256':hashlib.sha256(raw).hexdigest(),'parser':'UnityPy '+UnityPy.__version__,'prefix_skipped':prefix,'renderer_path_id':renderer.path_id,'mesh_path_id':r['m_Mesh']['m_PathID'],'renderer_ancestor_chain':chain,'world_singular_values':singular.tolist(),'anisotropy_ratio':ratio,'ratio_scope':'Rotation/uniform scale preserve intrinsic length-width ratios of mesh-local bind geometry. OBJ axes are chosen by actual body/fin inspection.','limits':['Bind geometry only; not animation playback or current posed prefab.','Bone transformations and source artistic shape do not establish species biology, age or dimensional accuracy.']}
    out=a.output.resolve();assert out.is_relative_to(ROOT/'output') and not out.exists();out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'ok':True,'anisotropy_ratio':ratio,'output':str(out)}))
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for k in ['dependencies','bundle','output']:p.add_argument('--'+k,required=True,type=Path)
    main(p.parse_args())
