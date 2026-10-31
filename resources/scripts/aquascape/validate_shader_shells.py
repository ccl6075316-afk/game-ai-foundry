"""Validate actual exported shader-only foliage; never require a fake rig."""
import io
from pathlib import Path
import numpy as np
from PIL import Image
from optimize_scenery import load,sha
from rig_plant_current import read_glb,array

def points(v,uv,color,anchor_min,anchor_size,time,phase=0,amplitude=.27):
    anchor=anchor_min+color[:,:3]*anchor_size;t=np.clip((uv[:,0]-.08)/.92,0,1);weight=t*t*(3-2*t)*color[:,3]
    p=uv[:,1]*2*np.pi+phase*2*np.pi;wave=.78*np.sin(time*.62831853+p-uv[:,0]*.6)+.22*np.sin(time*1.25663706+p*1.7-uv[:,0]);angle=wave*amplitude*weight
    axis=np.array([.35,0,-1]);axis/=np.linalg.norm(axis);q=v-anchor;c=np.cos(angle)[:,None];s=np.sin(angle)[:,None]
    return anchor+q*c+np.cross(axis,q)*s+axis*np.sum(q*axis,axis=1)[:,None]*(1-c)

def validate(root,row,path):
    game=root/'projects/fishing-2d/game';d,b=read_glb(path);local=[];meta=load(game/row['shader_metadata'].removeprefix('res://'));proof=next(r for r in meta['outputs'] if r['id']==row['id'])
    if proof['sha256']!=sha(path):local.append('Shader build proof is stale')
    if d.get('skins') or d.get('animations') or any('JOINTS_0' in p['attributes'] for m in d['meshes'] for p in m['primitives']):local.append('Shader-only model has a rig or baked animation')
    prims=[p for m in d['meshes'] for p in m['primitives']]
    if len(prims)!=1:local.append('Expected one instanced surface per species')
    a=prims[0]['attributes'];v=array(d,b,a['POSITION']).astype(float);uv=array(d,b,a['TEXCOORD_1']);color=array(d,b,a['COLOR_0']);pinned=uv[:,0]<=.08;tip=uv[:,0]>.8
    if not pinned.any() or not tip.any():local.append('Missing rooted/tip vertices')
    if not np.isfinite(color).all() or not np.isfinite(uv).all() or ((uv<0)|(uv>1)).any():local.append('Invalid shader deformation attributes')
    lo=np.array(proof['anchor_min']);size=np.array(proof['anchor_size']);root_error=0.;loop_error=0.;tip_motion=0.
    for phase in [0,.31,.62]:
        baseline=points(v,uv,color,lo,size,0,phase)
        loop_error=max(loop_error,float(np.linalg.norm(baseline-points(v,uv,color,lo,size,10,phase),axis=1).max()))
        for time in np.linspace(0,10,81):
            p=points(v,uv,color,lo,size,time,phase);delta=np.linalg.norm(p-v,axis=1);root_error=max(root_error,float(delta[pinned].max()));tip_motion=max(tip_motion,float(np.linalg.norm((p-baseline)[tip],axis=1).max()))
    if root_error>1e-6 or loop_error>1e-6 or tip_motion<.0003:local.append('Root, loop or tip-motion failure')
    for view,h in proof['source_hashes'].items():
        source=root/f'projects/fishing-2d/plans/reviews/aquascape-expansion-v11/sources/{row["id"]}/{row["id"]}-{view}.png'
        if sha(source)!=h:local.append('Source artwork changed after build')
    bv=d['bufferViews'][d['images'][0]['bufferView']];off=bv.get('byteOffset',0);image=Image.open(io.BytesIO(b[off:off+bv['byteLength']])).convert('RGBA')
    if list(image.size)!=proof['native_atlas_size']:local.append('Atlas size does not match native packing proof')
    alpha=np.asarray(image)[:,:,3]
    if not np.isin(alpha,[0,255]).all() or not (alpha==255).any():local.append('Invalid alpha-scissor atlas')
    return {'deformation':'vertex shader; zero skeletons/clips/animation textures','poses':81,'instance_phases':[0,.31,.62],'root_motion_m':root_error,'loop_error_m':loop_error,'tip_motion_m':tip_motion,'native_atlas_size':list(image.size),'alpha_mode':'MASK','source_hashes_current':not any('Source artwork' in s for s in local),'failures':local}
