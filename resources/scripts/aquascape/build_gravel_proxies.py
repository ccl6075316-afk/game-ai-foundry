"""Tiny gravel convex envelopes derived from existing illustrated stone meshes.

Directional support samples keep source proportions; the full source three-view
paint is reused by the runtime shader. These proxies are for millimetre gravel,
not replacements for the large detailed source props.
"""
import argparse,hashlib,json
from pathlib import Path
import numpy as np
from scipy.spatial import ConvexHull
from PIL import Image
from build_from_art import Glb,donor
from rig_plant_current import read_glb,array

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();root=a.root.resolve();game=root/'projects/fishing-2d/game';catalog=json.loads((game/'assets/aquascape-v5/catalog.json').read_text(encoding='utf-8'));a.output.mkdir(parents=True,exist_ok=True);rows=[]
    for id in ['rock','river_boulder']:
        spec=next(s for s in catalog['assets'] if s['id']==id);source=game/spec['model'].removeprefix('res://');d,b=read_glb(source)
        points=np.unique(np.concatenate([array(d,b,p['attributes']['POSITION']) for m in d['meshes'] for p in m['primitives']]),axis=0)
        directions=[]
        for i in range(36):
            y=1-2*(i+.5)/36;r=np.sqrt(1-y*y);t=i*2.399963229728653
            directions.append([r*np.cos(t),y,r*np.sin(t)])
        directions.extend(np.eye(3).tolist());directions.extend((-np.eye(3)).tolist())
        v=points[np.unique(np.argmax(points@np.array(directions).T,axis=0))];hull=ConvexHull(v);f=hull.simplices.copy()
        for i,face in enumerate(f):
            if np.dot(np.cross(v[face[1]]-v[face[0]],v[face[2]]-v[face[0]]),hull.equations[i,:3])<0:f[i,[1,2]]=f[i,[2,1]]
        g=Glb();art=game/spec['material_dir'].removeprefix('res://')/(id+'-front.png');mi=g.material(donor(Image.open(art).convert('RGBA')),'existing_source_front');g.mesh(v,f,np.full((len(v),2),.5),mi,id+'_gravel_proxy');output=a.output/(id+'-gravel.glb');g.save(output)
        rows.append({'id':id,'source':str(source),'source_sha256':sha(source),'output':str(output),'sha256':sha(output),'vertices':len(v),'triangles':len(f),'projection_bounds':spec['projection_bounds'],'material_dir':spec['material_dir'],'source_art':str(art),'source_art_sha256':sha(art)})
    data={'schema_version':1,'command':'aquascape.build-gravel-proxies','ok':True,'status':'done','next_action':'human_review','outputs':rows,'failures':[],'scope':'Convex tiny-gravel proxies from source stone support samples; full three-view generated source paint reused at runtime. Not large-rock reconstruction or collision certification.'};(a.output/'proxy-build.validation.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps({'ok':True,'triangles':{r['id']:r['triangles'] for r in rows}}))

if __name__=='__main__':main()
