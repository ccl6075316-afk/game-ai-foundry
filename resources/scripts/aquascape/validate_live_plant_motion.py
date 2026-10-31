"""Regression: moving LEAF pixels in real time, not just water or a clock."""
import argparse
from pathlib import Path
import numpy as np
from PIL import Image
from optimize_scenery import load,save,sha
from rig_plant_current import read_glb,array

def green(image):
    return (image[:,:,1]>image[:,:,0]*1.12)&(image[:,:,1]>image[:,:,2]*1.12)&(image[:,:,1]>30)

def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--input',type=Path,required=True);a=p.parse_args();root=a.root.resolve();base=a.input.resolve();r=load(base/'motion.validation.json');failures=[]
    first=np.asarray(Image.open(base/'playing-start.png').convert('RGB')).astype(int);later=np.asarray(Image.open(base/'playing-later.png').convert('RGB')).astype(int);mask=green(first)|green(later);changed=np.any(abs(first-later)>4,axis=2)&mask;fraction=float(changed.sum()/max(1,mask.sum()))
    if fraction<=.05:failures.append('Leaf pixels do not visibly move over two real seconds; water changes do not count')
    pause_same=np.array_equal(np.asarray(Image.open(base/'paused-start.png')),np.asarray(Image.open(base/'paused-later.png')))
    if not pause_same:failures.append('Paused GPU view changes')
    if not all(r['checks'].values()):failures.append('Live clock/pause/resume failed')
    game=root/'projects/fishing-2d/game';catalog=load(game/'assets/aquascape-v5/catalog.json');metadata={row['shader_metadata'] for row in catalog['assets'] if row.get('animated')};rows=[r for path in sorted(metadata) for r in load(game/path.removeprefix('res://'))['outputs']];cases=[]
    for row in rows:
        path=Path(row['model']);path=path if path.is_absolute() else root/path
        doc,binary=read_glb(path);attr=doc['meshes'][0]['primitives'][0]['attributes'];v=array(doc,binary,attr['POSITION']).astype(float);uv=array(doc,binary,attr['TEXCOORD_1']);color=array(doc,binary,attr['COLOR_0']);anchor=np.array(row['anchor_min'])+color[:,:3]*row['anchor_size'];low=v.min(0);size=np.ptp(v,axis=0);center=(low+v.max(0))/2
        factor=min(.47/max(size[1],.001),.78/max(size[0],.001),.48/max(size[2],.001));t=np.clip((uv[:,0]-.08)/.92,0,1);weight=t*t*(3-2*t)*color[:,3];axis=np.array([.35,0,-1.]);axis/=np.linalg.norm(axis);q=v-anchor;pinned=(uv[:,0]<=.08)|(color[:,3]==0);root_error=0.;excursion=0.
        for strength in [1.,1.5]:
            for instance in range(3):
                scale=factor if instance==0 else factor*.52;x=0 if instance==0 else (-.32 if instance==1 else .32);z=.04 if instance==0 else -.10;base_y=.025 if row.get('alpha_mode')=='MASK' else .025-low[1]*scale;offset=np.array([x-center[0]*scale,base_y,z-center[2]*scale]);phase=uv[:,1]*2*np.pi+instance*.31*2*np.pi
                for seconds in np.linspace(0,10,81):
                    wave=.78*np.sin(seconds*.62831853+phase-uv[:,0]*.6)+.22*np.sin(seconds*1.25663706+phase*1.7-uv[:,0]);angle=wave*.18*strength*weight;c=np.cos(angle)[:,None];s=np.sin(angle)[:,None];points=anchor+q*c+np.cross(axis,q)*s+axis*np.sum(q*axis,axis=1)[:,None]*(1-c)
                    root_error=max(root_error,float(np.linalg.norm((points-v)[pinned],axis=1).max())*scale)
                    points=points*scale+offset;excursion=max(excursion,float(max(0,-.60-points[:,0].min(),points[:,0].max()-.60,-.30-points[:,2].min(),points[:,2].max()-.30,points[:,1].max()-.58)))
        okay=root_error<1e-6 and excursion<.001
        if not okay:failures.append(row['id']+': root or tank envelope failed')
        cases.append({'id':row['id'],'ok':okay,'root_motion_m':root_error,'sampled_glass_or_surface_excursion_m':excursion,'model_sha256':sha(path),'phases':81,'strengths':[1,1.5],'instances':3})
    r.update(ok=not failures,status='done' if not failures else 'failed',next_action='human_review' if not failures else 'fix_input',failures=failures,gpu_image_checks={'green_leaf_pixel_change_fraction_over_two_real_seconds':fraction,'paused_images_pixel_identical':pause_same},root_and_tank_checks=cases,inputs={str(root/'resources/runtime/godot/aquascape/ShaderPlantTank.gd'):sha(root/'resources/runtime/godot/aquascape/ShaderPlantTank.gd')})
    save(base/'motion.validation.json',r);print({'ok':r['ok'],'leaf_pixel_change_fraction':fraction,'pause_pixel_identical':pause_same,'species':len(cases),'failures':failures});return 0 if r['ok'] else 1
if __name__=='__main__':raise SystemExit(main())
