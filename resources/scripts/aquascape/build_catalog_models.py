"""Batch 3D construction from separate full-resolution generated views.

Mechanical tracing, projection, crowns, weight profiles and registries are
deterministic. Artwork identity/camera/shape acceptance remains a visual gate.
"""
import argparse
import hashlib
import json
import math
import shutil
from pathlib import Path
import numpy as np
from PIL import Image
from scipy import ndimage as ndi
from build_from_art import Glb,donor,split_leaves,leaf_shell,rotation,root_curve
from build_from_three_views import build as build_solid
from rig_plant_current import rig


def load(path):return json.loads(path.read_text(encoding='utf-8-sig'))
def save(path,data):path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def reviewed(project,asset):
    manifest=load(project/'pipeline/manifest.json')
    if any(t['status'] not in ['done','skipped'] for t in manifest['tasks']):raise ValueError('Source workflow not done: '+str(project))
    data=load(project/'output/assets-manifest.json')
    if data['assets'][asset].get('review',{}).get('status')!='accepted':raise ValueError('Source visual review pending: '+asset)


def crop_white(path,output,keep_all=False):
    image=Image.open(path).convert('RGBA');a=np.array(image)
    # Native provider alpha is authoritative. Transparent RGB may contain dark
    # colour bleed and must not become a giant opaque rectangle during cropping.
    mask=(a[:,:,3]>128) if (a[:,:,3]<255).any() else (a[:,:,:3].min(2)<235)
    # A one-pixel closing only joins pixel-cluster cracks, not separate leaves.
    labels,n=ndi.label(mask);sizes=np.bincount(labels.ravel());sizes[0]=0
    if keep_all:mask=np.isin(labels,np.flatnonzero(sizes>max(40,image.width*image.height*.00015)))
    else:mask=labels==sizes.argmax()
    if not mask.any():raise ValueError('Empty source mask: '+str(path))
    yy,xx=np.nonzero(mask);box=(int(xx.min()),int(yy.min()),int(xx.max()+1),int(yy.max()+1))
    a[:,:,3]=mask*255;Image.fromarray(a).crop(box).save(output)
    return {'source':str(path),'sha256':sha(path),'box':box,'native_crop':[box[2]-box[0],box[3]-box[1]],'output':str(output)}


def extract(root,catalog,review):
    rows=[]
    for category in ['plants','solids']:
        for s in catalog[category]:
            id=s['id'];folder=review/'sources'/id;folder.mkdir(parents=True,exist_ok=True)
            front=root/f'projects/aquascape-{category}-fronts-v5';aux=root/f'projects/aquascape-{id}-views-v5'
            for view in ['front','right','top','leaves'] if category=='plants' else ['front','right','top']:
                project=front if view=='front' else aux;asset=id+'_'+view;reviewed(project,asset)
                row=crop_white(project/f'output/{asset}_raw.png',folder/f'{id}-{view}.png',keep_all=view=='leaves');row.update(id=id,view=view);rows.append(row)
    save(review/'source-extraction.validation.json',{'command':'aquascape.extract-full-view-sources','ok':True,'status':'done','next_action':'human_review','outputs':rows,'scope':'Unresampled native crops only. No multi-camera packing or downscale.'})


def plant_profile(s):
    # Reproduce an existing accepted source layout only. New plants must derive
    # their own construction profile from the approved whole clump, rather
    # than inheriting a leaf count or shared per-leaf angle arrays.
    root=Path(__file__).resolve().parents[3]
    profiles=root/'projects/fishing-2d/game/assets/aquascape-v5/plant-profiles.json'
    if profiles.exists():
        existing=next((row for row in load(profiles)['plants'] if row['id']==s['id']),None)
        if existing is not None:return existing
    provided=s.get('source_layout_profile')
    if provided:
        profile=load(root/provided)
        if profile.get('id')!=s['id']:raise ValueError('Source clump profile identity mismatch')
        return profile
    raise ValueError('New plant needs a reviewed whole-clump source layout; do not invent a fixed leaf count or a shared angle pattern: '+s['id'])


def build_plant(root,s,profile,review,output):
    folder=review/'sources'/s['id'];images=split_leaves(folder/f'{s["id"]}-leaves.png');g=Glb()
    mats=[g.material(donor(im),f'generated_leaf_{i+1}') for i,im in enumerate(images)]
    for i,length in enumerate(profile['lengths_m']):
        v,f,uv=leaf_shell(images[i%len(images)],length,profile['shell_thickness_m'],profile.get('rest_bend_ratio',.025))
        R=np.asarray(profile['rotation_matrices'][i]) if 'rotation_matrices' in profile else rotation(profile['pitch_degrees'][i],profile['depth_rotations_degrees'][i],-profile['angles_degrees'][i])
        v=v@R.T+profile['attachments_m'][i]
        g.mesh(v,f,uv,mats[i%len(mats)],f'traced_leaf_{i+1}')
    master=Image.open(folder/f'{s["id"]}-front.png').convert('RGBA');w,h=master.size
    root_crop=master.crop((int(w*.25),int(h*.60),int(w*.75),h))
    root_pixels=np.array(root_crop)
    # Thin root antialias pixels near the white matte must not become large
    # cream facets on the crown. Extend only actual darker source root colors.
    color=root_pixels[:,:,:3].astype(float)
    brown=(color[:,:,0]>color[:,:,1]*1.12)&(color[:,:,2]<color[:,:,0]*.85)&(color.min(2)<115)
    if not brown.any():brown=color.min(2)<110
    root_pixels[:,:,3]=np.where((root_pixels[:,:,3]>0)&brown,255,0)
    root_paint=donor(Image.fromarray(root_pixels))
    root_mat=g.material(root_paint,'generated_root_crown_paint');base=profile['base_y_m']
    if s['growth_form']=='rhizome':
        span=profile['rhizome_length_m'];points=np.array([[-span*.53,base*.8,0],[-span*.2,base,0],[span*.2,base,.002],[span*.53,base,.004]])
        v,f,uv=root_curve(points,[.003,.004,.004,.0028]);g.mesh(v,f,uv,root_mat,'creeping_rhizome')
    else:
        # Rooted crowns/tuber are fixed; species blade geometry still comes from art.
        points=np.array([[0,0,0],[0,base*.35,0],[0,base*.8,0],[0,base,0]])
        radius=.009 if s['growth_form']=='bulb' else .0045
        v,f,uv=root_curve(points,[.002,radius,radius*.75,.002]);g.mesh(v,f,uv,root_mat,'basal_tuber' if s['growth_form']=='bulb' else 'rooted_crown')
    for i in range(8):
        angle=i*math.tau/8;x=(i/7-.5)*profile['rhizome_length_m'] if s['growth_form']=='rhizome' else math.cos(angle)*.003
        z=0 if s['growth_form']=='rhizome' else math.sin(angle)*.003
        points=np.array([[x,base*.85,z],[x+math.cos(angle)*.002,base*.38,z+math.sin(angle)*.003],[x+math.cos(angle)*.004,0,z+math.sin(angle)*.006]])
        v,f,uv=root_curve(points,[.0007,.0005,.00014]);g.mesh(v,f,uv,root_mat,f'attachment_root_{i}')
    path=output/(s['id']+'.glb');g.save(path)
    return {'id':s['id'],'output':str(path),'sha256':sha(path),'triangles':g.triangles,'source_parts':str(folder/f'{s["id"]}-leaves.png'),'profile':profile,'visual_review':'pending'}


def plants(root,catalog,review,output):
    static=output/'plant-static';dynamic=output/'plants';static.mkdir(parents=True,exist_ok=True);dynamic.mkdir(parents=True,exist_ok=True)
    profiles=[plant_profile(s) for s in catalog['plants']];sources={}
    for s in catalog['plants']:sources[s['id']+'_parts']=str((review/'sources'/s['id']/f'{s["id"]}-leaves.png').relative_to(root))
    source_profile={'plants':profiles,'sources':sources};save(output/'plant-profiles.json',source_profile)
    built=[build_plant(root,s,p,review,static) for s,p in zip(catalog['plants'],profiles)]
    motion_specs=[]
    for i,s in enumerate(catalog['plants']):
        degree=[.65,.8,1,1.2] if s['motion']=='stiff' else ([1.2,1.6,1.9,2.2] if s['motion']=='medium' else [1.6,2,2.4,2.8])
        motion_specs.append({'id':s['id'],'scientific_name':s['scientific_name'],'bend_degrees':degree,'sideways_ratio':.38,'twist_ratio':.3,'plant_phase':i*.37,'tip_displacement_range_m':[.0003,max(.012,s['max_length_m']*.15)]})
    cfg={'source_profile':str((output/'plant-profiles.json').relative_to(root)),'source_models':str(static.relative_to(root)),'clip':'WaterSway','duration_s':10,'sample_fps':30,'joints_at_leaf_fraction':[0,.2,.4,.6,.8],'weight_fraction':[.08,.28,.48,.68,.88],'root_pin_fraction':.08,'plants':motion_specs}
    save(output/'plant-motion.json',cfg);rigged=[rig(root,cfg,s,dynamic) for s in motion_specs]
    save(dynamic/'rig.handoff.json',{'command':'aquascape.rig-catalog-plants','ok':True,'status':'done','next_action':'human_review','outputs':rigged,'failures':[],'config_sha256':sha(output/'plant-motion.json'),'visual_review':'pending'})
    save(output/'plant-build.validation.json',{'command':'aquascape.build-catalog-plants','ok':True,'status':'done','next_action':'human_review','outputs':built,'failures':[]})


def solids(root,catalog,review,output):
    models=output/'solids';models.mkdir(parents=True,exist_ok=True);specs=[]
    for s in catalog['solids']:
        folder=review/'sources'/s['id']
        specs.append({'id':s['id'],'reference_prefix':s['id'],'reference_dir':str(folder.relative_to(root)),'width_m':s['width_m'],'resolution':140,'smoothing_voxels':1.2,'preserve_holes':True,'materials':{v:str((folder/f'{s["id"]}-{v}.png').relative_to(root)) for v in ['front','right','top']}})
    save(output/'solid-profiles.json',{'assets':specs});rows=[build_solid(root,s,models) for s in specs]
    save(models/'build.validation.json',{'command':'aquascape.build-catalog-solids','ok':True,'status':'done','next_action':'human_review','outputs':rows,'failures':[],'visual_review':'pending'})


def registry(root,catalog,output):
    rows=[]
    existing=load(root/'projects/fishing-2d/game/assets/aquascape-v3/build.validation.json')['outputs']
    for e in catalog['existing']:
        row={**e,'model':'res://'+str(Path(e['model']).relative_to('projects/fishing-2d/game')).replace('\\','/'),'existing':True,'animated':e['category']=='plant'}
        if e['category']!='plant':
            b=next(b for b in existing if b['id']==e['id']);row['projection_bounds']=b['projection_bounds'];row['material_dir']='res://assets/aquascape-v3'
        rows.append(row)
    for s in catalog['plants']:
        rows.append({**s,'category':'plant','existing':False,'animated':True,'model':'res://assets/aquascape-v5/plants/'+s['id']+'.glb'})
    solid_rows=load(output/'solids/build.validation.json')['outputs']
    for s in catalog['solids']:
        b=next(b for b in solid_rows if b['id']==s['id']);rows.append({**s,'existing':False,'animated':False,'model':'res://assets/aquascape-v5/solids/'+s['id']+'.glb','projection_bounds':b['projection_bounds'],'material_dir':'res://assets/aquascape-v5/solids'})
    rows.sort(key=lambda r:(0 if r['category']=='plant' else 1))
    assert len(rows)==20 and sum(r['category']=='plant' for r in rows)==10 and len({r['id'] for r in rows})==20
    save(output/'catalog.json',{'schema_version':1,'assets':rows,'counts':{'plants':10,'solids':10},'user_acceptance':'pending'})


def main():
    p=argparse.ArgumentParser();p.add_argument('--input',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--review',type=Path,required=True);p.add_argument('--root',type=Path,required=True);p.add_argument('--stage',choices=['extract','plants','solids','registry'],required=True);a=p.parse_args();a.output=a.output.resolve();a.review=a.review.resolve();a.output.mkdir(parents=True,exist_ok=True)
    catalog=load(a.input)
    if a.stage=='extract':extract(a.root,catalog,a.review)
    elif a.stage=='plants':plants(a.root,catalog,a.review,a.output)
    elif a.stage=='solids':solids(a.root,catalog,a.review,a.output)
    else:registry(a.root,catalog,a.output)
    print(json.dumps({'ok':True,'stage':a.stage,'status':'done','next_action':'human_review'}))


if __name__=='__main__':main()
