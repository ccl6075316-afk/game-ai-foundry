"""Freeze repaired fin accessors without replacing the original rig/body GLB."""
import argparse,hashlib,json
from pathlib import Path
from freeze_surface_ownership import read_glb,accessor
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    p=argparse.ArgumentParser();p.add_argument('--plan',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();spec=json.loads(a.plan.read_text())['items'][0];assert spec['species']=='peacock_bass'
    model=Path(spec['model']);assert sha(model)==spec['model_sha256'];d,b=read_glb(model);fins=[]
    for name in spec['fins']:
        node=next(n for n in d['nodes'] if n.get('name')==name and 'mesh' in n)
        assert not any(k in node for k in ['translation','rotation','scale','matrix'])
        names=[d['nodes'][i]['name'] for i in d['skins'][node['skin']]['joints']];parts=[]
        for prim in d['meshes'][node['mesh']]['primitives']:
            attrs=prim['attributes'];part={key:accessor(d,b,attrs[source]).tolist() for key,source in [('vertices','POSITION'),('normals','NORMAL'),('uv','TEXCOORD_0'),('joints','JOINTS_0'),('weights','WEIGHTS_0')]}
            part['triangles']=accessor(d,b,prim['indices']).reshape(-1).tolist()
            for key,source in [('uv2','TEXCOORD_1'),('colors','COLOR_0')]:
                if source in attrs:part[key]=accessor(d,b,attrs[source]).tolist()
            parts.append(part)
        fins.append({'name':name,'skin_joint_names':names,'parts':parts})
    output={'species':spec['species'],'source_model_sha256':sha(model),'fins':fins};a.output.write_text(json.dumps(output,separators=(',',':')));print(json.dumps({'ok':True,'fins':len(fins),'sha256':sha(a.output)}))
if __name__=='__main__':main()
