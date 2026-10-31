"""Serialized shader attributes plus actual GPU loop/movement image checks."""
import argparse,json
from pathlib import Path
import numpy as np
from PIL import Image
from rig_plant_current import read_glb,array
from optimize_scenery import load,save,sha

def main():
    p=argparse.ArgumentParser();p.add_argument('--input',type=Path,required=True);p.add_argument('--native',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();rows=[];failures=[]
    for row in load(a.input/'shader-plants.validation.json')['outputs']:
        path=a.input/(row['id']+'.glb');d,b=read_glb(path);prim=d['meshes'][0]['primitives'][0];attrs=prim['attributes'];v=array(d,b,attrs['POSITION']).astype(float);uv=array(d,b,attrs['TEXCOORD_1']);color=array(d,b,attrs['COLOR_0']);anchor=np.array(row['anchor_min'])+color[:,:3]*row['anchor_size'];pinned=(uv[:,0]<=.08)|(color[:,3]==0);tip=(uv[:,0]>.9)&(color[:,3]>0)
        t=np.clip((uv[:,0]-.08)/.92,0,1);weight=t*t*(3-2*t)*color[:,3];peak=0.;root=0.;loop=0.
        def deform(time,phase,yaw):
            ph=uv[:,1]*2*np.pi+phase*2*np.pi;wave=.78*np.sin(time*.62831853+ph-uv[:,0]*.6)+.22*np.sin(time*1.25663706+ph*1.7-uv[:,0]);angle=wave*.085*weight
            # The shader transforms the world current into instance local space.
            axis=np.array([.35,0,-1.]);R=np.array([[np.cos(yaw),0,np.sin(yaw)],[0,1,0],[-np.sin(yaw),0,np.cos(yaw)]]);axis=R.T@axis;axis/=np.linalg.norm(axis);q=v-anchor;c=np.cos(angle)[:,None];s=np.sin(angle)[:,None]
            return anchor+q*c+np.cross(axis,q)*s+axis*np.sum(q*axis,axis=1)[:,None]*(1-c)
        for yaw in [0,np.pi/2,np.pi,np.pi*1.5]:
            for phase in [0,.37]:
                for time in np.linspace(0,10,41):
                    moved=deform(time,phase,yaw)-v
                    root=max(root,float(np.linalg.norm(moved[pinned],axis=1).max()));peak=max(peak,float(np.linalg.norm(moved[tip],axis=1).max()))
                loop=max(loop,float(np.linalg.norm(deform(0,phase,yaw)-deform(10,phase,yaw),axis=1).max()))
        okay=not d.get('skins') and not d.get('animations') and len(d['meshes'])==1 and len(d['meshes'][0]['primitives'])==1 and pinned.any() and tip.any() and root<1e-6 and loop<1e-6 and peak>.0001
        if not okay:failures.append(row['id']+': shader attribute/root/loop test failed')
        rows.append({'id':row['id'],'sha256':sha(path),'ok':bool(okay),'root_vertices':int(pinned.sum()),'tip_vertices':int(tip.sum()),'cpu_root_error_m':root,'cpu_loop_error_m':loop,'tip_motion_m':peak,'sampled_times':41,'headings':4,'instance_phases':2,'skeletal_or_sampled_animation_payload':False})
    gpu=[]
    ids=[row['id'] for row in rows if (a.native/f'closeup-{row["id"]}-0.0.png').exists()]
    if len(ids)<min(3,len(rows)):failures.append('Missing representative actual GPU closeup evidence')
    for id in ids:
        first=np.array(Image.open(a.native/f'closeup-{id}-0.0.png').convert('RGB')).astype(int);end=np.array(Image.open(a.native/f'closeup-{id}-10.0.png').convert('RGB')).astype(int);other=np.array(Image.open(a.native/f'closeup-{id}-2.5.png').convert('RGB')).astype(int)
        loop=float(np.mean(np.any(abs(first-end)>3,axis=2)));motion=float(np.mean(np.any(abs(first-other)>3,axis=2)));okay=loop<.002 and motion>.0005
        if not okay:failures.append(id+': actual GPU loop/motion evidence failed')
        gpu.append({'id':id,'ok':okay,'loop_changed_pixel_fraction':loop,'quarter_cycle_changed_pixel_fraction':motion})
    # A regular MeshInstance closeup does not prove MultiMesh animation. Check
    # the actual instanced population too, excluding unchanged background/HUD.
    first=np.asarray(Image.open(a.native/'shader-phase-0.0.png').convert('RGB')).astype(int);other=np.asarray(Image.open(a.native/'shader-phase-2.5.png').convert('RGB')).astype(int)
    green=lambda x:(x[:,:,1]>x[:,:,0]*1.12)&(x[:,:,1]>x[:,:,2]*1.12)&(x[:,:,1]>30)
    mask=green(first)|green(other);changed=float((np.any(abs(first-other)>4,axis=2)&mask).sum()/max(1,mask.sum()))
    if changed<=.01:failures.append('Actual MultiMesh leaf pixels do not move; MeshInstance closeups are insufficient')
    report={'schema_version':1,'command':'aquascape.validate-shader-plants','ok':not failures,'status':'done' if not failures else 'failed','next_action':'human_review' if not failures else 'fix_input','outputs':rows,'gpu_image_checks':gpu,'multimesh_green_leaf_change_fraction':changed,'failures':failures,'user_acceptance':'pending','limitations':['CPU equations verify serialized anchoring attributes; GPU image checks verify actual motion/loop, not per-vertex GPU positions or continuous collision.']};save(a.output,report);print(json.dumps({'ok':report['ok'],'failures':failures,'gpu':gpu,'multimesh_leaf_change_fraction':changed}));return 0 if report['ok'] else 1
if __name__=='__main__':raise SystemExit(main())
