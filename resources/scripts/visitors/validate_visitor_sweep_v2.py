#!/usr/bin/env python3
"""Hash-bound shader-equivalent visitor sweep; sampling is not visual approval."""
import argparse, importlib.util, json, math, re
from pathlib import Path
import numpy as np


def rx(p,a):
    out=p.copy();c,s=np.cos(a),np.sin(a)
    out[:,1]=c*p[:,1]-s*p[:,2];out[:,2]=s*p[:,1]+c*p[:,2]
    return out


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--assets',type=Path,required=True);ap.add_argument('--shader',type=Path,required=True);ap.add_argument('--output',type=Path,required=True)
    a=ap.parse_args();path=Path(__file__).with_name('build_visitors_v2.py')
    spec=importlib.util.spec_from_file_location('builder',path);b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b)
    m=json.loads((a.assets/'build_manifest.json').read_text());p=json.loads((a.assets/'build_profile.json').read_text())
    assert m['builder_sha256']==b.sha(path) and m['shader_sha256']==b.sha(a.shader)
    shader=a.shader.read_text();arm,hip=map(float,re.search(r'limb<2.5\?(-?[\d.]+):([\d.]+)',shader).groups());knee_amp=float(re.search(r'motion\*([\d.]+);\n\s*vec3 kp',shader).group(1))
    models={}
    for name in b.ARCHETYPES:
        assert m['meshes'][name]['sha256']==b.sha(a.assets/f'visitor_{name}.res')
        for appearance in range(3):
            mesh=b.Sculpt(name,appearance,p,m['rects'],m['atlas_size']).build()
            vertices=np.array(mesh.positions);rig=np.array(mesh.rig);weights=np.array(mesh.weights)[:,None];maximum=0;worst={}
            # Unique vertices avoid repeatedly testing triangle seam duplicates.
            unique=np.unique(np.column_stack([vertices,rig,weights]),axis=0)
            vertices=unique[:,:3];rig=unique[:,3:7];weights=unique[:,7:8]
            sole_min=float(vertices[:,1].min());animated_min=1e9;stance_max=-1e9
            for phase in np.linspace(0,2*math.pi,360,endpoint=False):
                for motion in np.linspace(0,1,9):
                    pos=vertices.copy()
                    for limb in range(1,5):
                        selected=rig[:,3]==limb;v=pos[selected];pivot=rig[selected,:3];w=weights[selected]
                        swing=math.sin(phase)*(1 if limb in (1,3) else -1);angle=swing*motion*(arm if limb<3 else hip)
                        if limb>=3:
                            knee=pivot[:,1]*.51;t=np.clip((v[:,1]-(knee-.055))/.080,0,1);kw=(1-t*t*(3-2*t))[:,None]
                            kp=pivot.copy();kp[:,1]=knee
                            v=v*(1-kw)+(kp+rx(v-kp,max(0,-swing)*motion*knee_amp))*kw
                        pos[selected]=v*(1-w)+(pivot+rx(v-pivot,angle))*w
                    pos[:,1]+=abs(math.sin(phase))*.009*motion
                    feet_low=float(pos[:,1].min());animated_min=min(animated_min,feet_low);stance_max=max(stance_max,feet_low)
                    radius=np.linalg.norm(pos[:,[0,2]],axis=1);value=float(radius.max())
                    if value>maximum:maximum=value;worst={'phase':float(phase),'motion':float(motion),'vertex':int(radius.argmax())}
            models[f'{name}/{appearance}']={'radius_m':maximum,'worst_pose':worst,'mesh_sha256':m['meshes'][name]['sha256'],'static_min_y_m':sole_min,'animated_lowest_vertex_range_m':[animated_min,stance_max]}
    maximum=max(item['radius_m'] for item in models.values())
    report={'ok':True,'method':'All unique authored vertices matching saved mesh hashes; 360 phases x9 motion blends; all18 appearance morphs; shader knee and root blend equations. Head yaw about xz origin preserves radius. Discrete sampling with5mm engineering margin, not continuous proof or visual acceptance.','builder_sha256':b.sha(path),'shader_sha256':b.sha(a.shader),'profile_sha256':m['profile_sha256'],'models':models,'maximum_m':maximum,'recommended_nav_radius_m':math.ceil((maximum+.005)*100)/100,'user_acceptance':'pending'}
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'ok':True,'maximum_m':maximum,'recommended_nav_radius_m':report['recommended_nav_radius_m']}))
if __name__=='__main__': main()
