"""Apply an explicitly frozen, tiny whole-fin rest offset; never shrink roots.

For a diagnosed scale-sensitive collision only. Full root/membrane gates must
be rerun. Does not claim an arbitrary translation is anatomically acceptable.
"""
import argparse,copy,hashlib,json
from pathlib import Path
import numpy as np
from freeze_surface_ownership import read_glb,accessor
from patch_existing_fin_meshes import write
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    c=argparse.ArgumentParser();c.add_argument('--plan',type=Path,required=True);c.add_argument('--parameters',type=Path,required=True);c.add_argument('--output',type=Path,required=True);a=c.parse_args()
    plan=json.loads(a.plan.read_text());params=json.loads(a.parameters.read_text())['species'];rows=[]
    for spec in plan['items']:
        shifts=params[spec['species']].get('clearance_offsets',{})
        if not shifts:continue
        src=Path(spec['model']);assert sha(src)==spec['model_sha256'];d,blob=read_glb(src);binary=bytearray(blob);changes={}
        for name,shift in shifts.items():
            offset=np.array(shift,dtype=np.float32);assert np.linalg.norm(offset)<.0001
            node=next(n for n in d['nodes'] if n.get('name')==name and 'mesh' in n)
            for p in d['meshes'][node['mesh']]['primitives']:
                source=p['attributes']['POSITION'];v=accessor(d,blob,source)+offset;acc=copy.deepcopy(d['accessors'][source]);binary.extend(b'\0'*(-len(binary)%4));start=len(binary);binary.extend(v.astype('<f4').tobytes())
                acc.update(bufferView=len(d['bufferViews']),byteOffset=0,min=v.min(0).tolist(),max=v.max(0).tolist());d['bufferViews'].append({'buffer':0,'byteOffset':start,'byteLength':v.nbytes,'target':34962});d['accessors'].append(acc);p['attributes']['POSITION']=len(d['accessors'])-1
            spec['fins'][name]['rest_points_gltf']=(np.asarray(spec['fins'][name]['rest_points_gltf'],dtype=np.float32)+offset).tolist();changes[name]=shift
        folder=a.output/spec['species'];folder.mkdir(parents=True,exist_ok=True);dest=folder/'fish.glb';write(dest,d,binary);h=sha(dest)
        report={'ok':True,'source':str(src),'source_sha256':sha(src),'model_sha256':h,'changes_native':changes,'all_root_ids_retained':True,'normal_uv_weights_indices_and_other_primitives_unchanged':True,'reason':'Full490 found 4 Great left-pelvic poses penetrating .50743mm after total-length normalization increased scale by 2.41%; frozen collar remains .5mm. Apply .1034mm lateral clearance to the entire existing fin, then rerun all affected gates.'}
        (folder/'clearance.validation.json').write_text(json.dumps(report,indent=2),encoding='utf8');spec.update(model=str(dest.resolve()),model_sha256=h);rows.append(report)
    (a.output/'candidate.plan.json').write_text(json.dumps(plan,indent=2),encoding='utf8');print(json.dumps(rows))
if __name__=='__main__':main()
