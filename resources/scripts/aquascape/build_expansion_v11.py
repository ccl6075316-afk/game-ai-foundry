"""Budget-first 3D foliage from native painted sprigs, and three-view props.

No skeletal clips, sampled animation textures, procedural replacement paint or
full-clump billboards. Each leaf/sprig is a separate thin 3D shell on a stem.
MASK foliage retains the real gaps inside fern/moss/fan drawings.
"""
import argparse,copy,io,json,math
from pathlib import Path
import numpy as np
from PIL import Image
from scipy import ndimage as ndi
from scipy.spatial import ConvexHull
from skimage.measure import approximate_polygon
from build_from_art import Glb,foreground,split_leaves,donor
from build_catalog_models import reviewed,crop_white
from build_decor_ten import build as decor_build,semantic_checks,source_image
from optimize_scenery import save,load,sha,metrics,build_solid
from rig_plant_current import array,read_glb
from leaf_polygon import ears
from expand_catalog_v11 import ROOT,CFG,REVIEW,folder,views_folder

GAME=ROOT/'projects/fishing-2d/game'
OUT=GAME/'assets/aquascape-v11'

def extract(cfg):
    rows=[]
    for s in cfg['plants']+cfg['solids']:
        kind='plants' if s['category']=='plant' else 'solids'
        for view in ['front','leaves'] if kind=='plants' else ['front','right','top']:
            project=folder(kind) if view=='front' else views_folder(s)
            reviewed(project,s['id']+'_'+view)
            dest=REVIEW/'sources'/s['id']/f'{s["id"]}-{view}.png';dest.parent.mkdir(parents=True,exist_ok=True)
            r=crop_white(project/f'output/{s["id"]}_{view}_raw.png',dest,keep_all=view=='leaves');rows.append(dict(id=s['id'],view=view,**r))
    save(REVIEW/'source-extraction.validation.json',dict(command='aquascape.expansion-extract',ok=True,status='done',next_action='human_review',outputs=rows,user_acceptance='pending'))

def shell(image,length):
    """Convex coarse closed shell; alpha keeps source's divided inner foliage."""
    mask=foreground(image);yy,xx=np.nonzero(mask);h,w=mask.shape
    # Hull uses actual painted contour; no same polygon/angle array per species.
    stride=max(1,len(xx)//12000);points=np.c_[xx[::stride],yy[::stride]].astype(float)
    hull=points[ConvexHull(points).vertices];tol=.5
    while True:
        p=approximate_polygon(np.vstack([hull,hull[0]]),tol)[:-1]
        if len(p)<=7:break
        tol*=1.3
    if len(p)<4:p=np.array([[xx.min(),yy.min()],[xx.max(),yy.min()],[xx.max(),yy.max()],[xx.min(),yy.max()]])
    # All source silhouette pixels must be inside the carrier. Outward margin
    # avoids clipping details to gain triangles. It is transparent, not new paint.
    center=p.mean(0);p=center+(p-center)*1.055
    p[:,0]=np.clip(p[:,0],0,w-1);p[:,1]=np.clip(p[:,1],0,h-1)
    import cv2
    covered=np.zeros(mask.shape,np.uint8);cv2.fillPoly(covered,[np.rint(p).astype(np.int32)],1)
    if (covered.astype(bool)&mask).sum()/mask.sum()<.995:
        # A rectangular carrier keeps the full painted frond when coarse hull
        # reduction would amputate tiny leaflets. Alpha removes its empty area.
        p=np.array([[0,0],[w-1,0],[w-1,h-1],[0,h-1]],float)
    uv=(p+.5)/[w,h];f=ears(p)
    bottom=xx[yy>=yy.max()-max(2,int(h*.04))].mean()/w
    width=length*w/h
    base=np.c_[(uv[:,0]-bottom)*width,(1-uv[:,1])*length,np.sin((1-uv[:,1])*math.pi)*length*.012]
    thick=max(.00010,length*.0018);n=len(base);v=np.vstack([base+[0,0,thick/2],base-[0,0,thick/2]])
    # Pixel Y is down, model Y is up: reverse face orientation.
    faces=[*map(tuple,f[:,[0,2,1]]),*map(tuple,f+n)]
    for a in range(n):b=(a+1)%n;faces.extend([(a,b,b+n),(a,b+n,a+n)])
    return v,np.asarray(faces),np.tile(uv,(2,1))

def tube(points,radius):
    points=np.asarray(points,float);v=[];uv=[];f=[];sides=3
    for k,p in enumerate(points):
        direction=points[min(k+1,len(points)-1)]-points[max(0,k-1)];direction/=np.linalg.norm(direction)
        across=np.cross(direction,[0,0,1]);across/=max(np.linalg.norm(across),1e-10);depth=np.cross(across,direction)
        for j in range(sides):
            a=j*math.tau/sides;v.append(p+radius*(math.cos(a)*across+math.sin(a)*depth));uv.append([j/sides,k/(len(points)-1)])
    for k in range(len(points)-1):
        for j in range(sides):a=k*sides+j;b=k*sides+(j+1)%sides;f.extend([(a,a+sides,b+sides),(a,b+sides,b)])
    f.extend([(0,2,1),((len(points)-1)*sides,(len(points)-1)*sides+1,(len(points)-1)*sides+2)])
    return np.asarray(v),np.asarray(f),np.asarray(uv)

def native_alpha(image):
    a=np.asarray(image.convert('RGBA')).copy();mask=foreground(image);a[:,:,3]=mask*255
    inds=ndi.distance_transform_edt(~mask,return_distances=False,return_indices=True);a[:,:,:3][~mask]=a[inds[0],inds[1],:3][~mask]
    return Image.fromarray(a)

def build_plant(s,profile):
    id=s['id'];source=REVIEW/'sources'/id;images=split_leaves(source/f'{id}-leaves.png')
    g=Glb();mats=[]
    for i,im in enumerate(images):
        mat=g.material(native_alpha(im),f'{id}_native_sprig_{i}');g.doc['materials'][mat].update(alphaMode='MASK',alphaCutoff=.5);mats.append(mat)
    front=Image.open(source/f'{id}-front.png').convert('RGBA');w,h=front.size
    stem_paint=donor(front.crop((int(w*.42),int(h*.55),int(w*.57),int(h*.92))))
    stem_mat=g.material(stem_paint,id+'_source_stem')
    for i,stem in enumerate(profile['stems']):
        v,f,uv=tube(stem,s.get('stem_radius_m',.001));g.mesh(v,f,uv,stem_mat,f'{id}_stem_{i}')
    for i,leaf in enumerate(profile['foliage']):
        im=images[leaf.get('source',i)%len(images)];v,f,uv=shell(im,leaf['length'])
        direction=np.asarray(leaf['direction'],float);direction/=np.linalg.norm(direction)
        across=np.cross(direction,np.asarray(leaf.get('face_normal',[0,0,1]),float));across/=np.linalg.norm(across);normal=np.cross(across,direction)
        v=v@np.stack([across,direction,normal])+leaf['at'];g.mesh(v,f,uv,mats[leaf.get('source',i)%len(images)],f'{id}_foliage_{i}')
    # Pack without resampling the native source art; consolidate one surface.
    d=g.doc;b=g.bin;tex=[]
    for im in d['images']:
        bv=d['bufferViews'][im['bufferView']];off=bv.get('byteOffset',0);tex.append(Image.open(io.BytesIO(b[off:off+bv['byteLength']])).convert('RGBA'))
    pad=4;area=sum((im.width+pad*2)*(im.height+pad*2) for im in tex);aw=2**math.ceil(math.log2(max(max(im.width+pad*2 for im in tex),math.sqrt(area))))
    positions=[];x=y=line=0
    for im in tex:
        if x+im.width+pad*2>aw:y+=line;x=0;line=0
        positions.append((x+pad,y+pad));x+=im.width+pad*2;line=max(line,im.height+pad*2)
    ah=y+line;atlas=Image.new('RGBA',(aw,ah),(0,0,0,0))
    for im,(x,y) in zip(tex,positions):atlas.paste(Image.fromarray(np.pad(np.asarray(im),((pad,pad),(pad,pad),(0,0)),mode='edge')),(x-pad,y-pad))
    out=OUT/'shader-plants';out.mkdir(parents=True,exist_ok=True);atlaspath=out/(id+'.png');atlas.save(atlaspath)
    vertices=[];normals=[];uvs=[]
    for mesh in d['meshes']:
        for p in mesh['primitives']:
            attrs=p['attributes'];v=array(d,b,attrs['POSITION']);uv=array(d,b,attrs['TEXCOORD_0']);normal=array(d,b,attrs['NORMAL']);ti=d['materials'][p['material']]['pbrMetallicRoughness']['baseColorTexture']['index'];ii=d['textures'][ti]['source'];im=tex[ii];x,y=positions[ii]
            vertices.append(v);normals.append(normal);uvs.append((uv*np.array(im.size)+[x,y])/[aw,ah])
    v=np.vstack(vertices);lo=v.min(0);span=np.maximum(np.ptp(v,axis=0),1e-6);anchor=np.array([0,0,0]);col=np.tile(np.r_[(anchor-lo)/span,1],(len(v),1));t=np.clip(v[:,1]/max(v[:,1].max(),1e-6),0,1);aux=np.c_[t,np.zeros(len(t))]
    final=Glb();mat=final.material(atlas,id+'_native_foliage_atlas');final.doc['materials'][mat].update(alphaMode='MASK',alphaCutoff=.5)
    attributes={'POSITION':final.accessor(v,'VEC3'),'NORMAL':final.accessor(np.vstack(normals),'VEC3'),'TEXCOORD_0':final.accessor(np.vstack(uvs),'VEC2'),'TEXCOORD_1':final.accessor(aux,'VEC2'),'COLOR_0':final.accessor(col,'VEC4')}
    final.doc['meshes']=[{'name':id,'primitives':[{'attributes':attributes,'material':mat,'mode':4}]}];final.doc['nodes']=[{'name':id,'mesh':0}];final.doc['scenes'][0]['nodes']=[0]
    final.doc['extras']={'anchor_min':lo.tolist(),'anchor_size':span.tolist(),'animation':'rooted vertex shader, no rig or baked data','foliage':'separate source-textured thin 3D shells, alpha-scissored divided leaves','source_layout':profile}
    path=out/(id+'.glb');final.save(path);m=metrics(path)
    if m['triangles']>1000:raise ValueError(id+' exceeds complete clump budget: '+str(m['triangles']))
    return dict(id=id,model=str(path),atlas=str(atlaspath),anchor_min=lo.tolist(),anchor_size=span.tolist(),native_atlas_size=[aw,ah],**m,source_hashes={key:sha(source/f'{id}-{key}.png') for key in ['front','leaves']},foliage_shells=len(profile['foliage']),stems=len(profile['stems']),alpha_mode='MASK',layout_profile_sha256=sha(REVIEW/'source-layouts.json'))

def plants(cfg):
    profiles=load(REVIEW/'source-layouts.json');rows=[build_plant(s,profiles[s['id']]) for s in cfg['plants']]
    save(OUT/'shader-plants/shader-plants.validation.json',dict(command='aquascape.expansion-shader-build',ok=True,status='done',next_action='human_review',outputs=rows,failures=[],user_acceptance='pending',limitations=['Species layout is an operator reconstruction from whole-clump artwork, not a botanical scan.','Fine divided leaves use alpha scissor; texture overdraw remains a rendering cost even at a low triangle count.']))

def solids(cfg):
    out=OUT/'solids';out.mkdir(parents=True,exist_ok=True);scratch=REVIEW/'intermediate-solids';scratch.mkdir(parents=True,exist_ok=True);policy=load(ROOT/'resources/aquascape/geometry-budgets.json');rows=load(REVIEW/'solids.validation.json')['outputs'] if (REVIEW/'solids.validation.json').exists() else []
    cavities={'bamboo_shelter':'pipe','slate_cave':'box_tunnel','ruined_tower':'arched_tunnel'}
    for s in cfg['solids']:
        projects={v:str((folder('solids') if v=='front' else views_folder(s)).relative_to(ROOT)) for v in ['front','right','top']}
        # Direct topology-preserving reduction from the dense surface. An
        # intermediate aggressive QEM pass can fuse tiny branch/crown edges.
        spec={**s,'source_projects':projects,'cavity':cavities.get(s['id'],'none'),'resolution':105,'smoothing_voxels':1.2,'triangle_budget':100000000,'fill_silhouette_holes':s['category']=='rock','largest_component_only':True}
        built=decor_build(ROOT,spec,scratch)
        built['simplifier']='No intermediate simplification; final welded topology-preserving pymeshlab QEM only.'
        if not built['ok']:raise ValueError('Disconnected source hull or construction cavity: '+s['id'])
        row={**s,'projection_bounds':built['projection_bounds']};final=out/(s['id']+'.glb');build_solid(row,scratch/(s['id']+'.glb'),final,policy)
        for view in ['front','right','top']:
            import shutil
            shutil.copy2(scratch/(s['id']+'-'+view+'.png'),out/(s['id']+'-'+view+'.png'))
        # These oblique donors contain a facade/open mouth in their lower/left
        # region. Use only the actual upward roof/bamboo skin for top surfaces,
        # instead of projecting a fake doorway/open end onto a solid roof/side.
        donor_crops={'slate_cave':{'top':[.15,.06,.87,.42]},'bamboo_shelter':{'front':[.34,.13,.97,.83],'top':[.34,.13,.97,.83]}}
        built['native_material_crops']={}
        for view,box_norm in donor_crops.get(s['id'],{}).items():
            target=out/(s['id']+'-'+view+'.png');im=Image.open(target).convert('RGB');ww,hh=im.size;box_px=tuple(round(value*(ww if k%2==0 else hh)) for k,value in enumerate(box_norm));im=im.crop(box_px);im.save(target)
            built['native_material_crops'][view]={'input':str(scratch/(s['id']+'-'+view+'.png')),'native_pixel_crop':list(box_px),'size':list(im.size),'sha256':sha(target),'resampled':False}
            if view=='front':
                doc,bin_data=read_glb(final);gg=Glb();gg.doc=doc;gg.bin=bytearray(bin_data);stream=io.BytesIO();im.convert('RGBA').save(stream,format='PNG');gg.doc['images'][0]['bufferView']=gg.view(stream.getvalue());from optimize_scenery import compact;compact(gg);gg.save(final)
        d,b=read_glb(final);v=np.vstack([array(d,b,p['attributes']['POSITION']) for mesh in d['meshes'] for p in mesh['primitives']]);vv,ids=np.unique(v,axis=0,return_inverse=True);f=ids.reshape(-1,3);box=built['projection_bounds'];fm=source_image(folder('solids')/f'output/{s["id"]}_front_raw.png')[1]
        tests=semantic_checks(vv,f,box['width'],box['height'],box['depth'],spec,fm);m=metrics(final)
        if m['triangles']>policy['types'][s['category']]['hard_limit'] or any(not t['ok'] for t in tests):raise ValueError('Budget/cavity failure: '+s['id']+' '+str(tests))
        rows=[r for r in rows if r['id']!=s['id']];rows.append(dict(id=s['id'],output=str(final),projection_bounds=box,source_build=built,semantic_checks=tests,**m));print(json.dumps(dict(id=s['id'],triangles=m['triangles'],semantic_ok=all(t['ok'] for t in tests))),flush=True)
    save(REVIEW/'solids.validation.json',dict(command='aquascape.expansion-solid-build',ok=True,status='done',next_action='human_review',outputs=rows,failures=[],user_acceptance='pending'))

def registry(cfg):
    policy=load(ROOT/'resources/aquascape/geometry-budgets.json');rows=[]
    for s in cfg['plants']:
        model='res://assets/aquascape-v11/shader-plants/'+s['id']+'.glb';rows.append(dict(**s,existing=False,animated=True,model=model,pre_budget_model=model,shader_model=model,shader_metadata='res://assets/aquascape-v11/shader-plants/shader-plants.validation.json',deformation='shader',geometry_revision='source-shells-v11',geometry_budget={**policy['types'][s['budget_type']],'type':s['budget_type']},plant_art_policy=cfg['plant_art_policy']))
    builds={r['id']:r for r in load(REVIEW/'solids.validation.json')['outputs']}
    for s in cfg['solids']:
        model='res://assets/aquascape-v11/solids/'+s['id']+'.glb';rows.append(dict(**s,existing=False,animated=False,model=model,pre_budget_model=model,projection_bounds=builds[s['id']]['projection_bounds'],material_dir='res://assets/aquascape-v11/solids',geometry_revision='budget-first-v11',geometry_budget={**policy['types'][s['category']],'type':s['category']}))
    save(OUT/'catalog.json',dict(schema_version=1,assets=rows,counts={'plants':10,'solids':10},user_acceptance='pending'))
    save(OUT/'plant-catalog.json',dict(schema_version=1,assets=[r for r in rows if r['animated']],counts={'plants':10},user_acceptance='pending'))

def deploy(cfg):
    from validate_scenery_budget import validate
    proof=validate(ROOT,[OUT/'catalog.json'],REVIEW/'budget.validation.json')
    if not proof['ok']:raise ValueError('Expansion deployment blocked: '+str(proof['failures']))
    additions=load(OUT/'catalog.json')['assets'];ids={r['id'] for r in additions}
    for path,decor in [(GAME/'assets/aquascape-v5/catalog.json',False),(GAME/'assets/aquascape-decor-v1/catalog.json',True)]:
        catalog=load(path);catalog['assets']=[r for r in catalog['assets'] if r['id'] not in ids]+[r for r in additions if (r['category']=='decor')==decor]
        catalog['counts']={'plants':sum(r.get('animated',False) for r in catalog['assets']),'solids':sum(not r.get('animated',False) for r in catalog['assets'])};catalog['user_acceptance']='pending';save(path,catalog)

def main():
    p=argparse.ArgumentParser();p.add_argument('stage',choices=['extract','plants','solids','registry','deploy']);a=p.parse_args();cfg=load(CFG);OUT.mkdir(parents=True,exist_ok=True)
    globals()[a.stage](cfg)
if __name__=='__main__':main()
