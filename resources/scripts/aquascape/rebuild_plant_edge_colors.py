"""Erode the color donor region, then rebuild the entire contaminated leaf rim.

This intentionally replaces colored matte fringes too. It does not threshold
for 'white', alter the silhouette, resample art, or change geometry/animation.
"""
import argparse, copy, io, json
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage as ndi
from build_from_art import Glb, foreground, split_leaves
from clean_plant_material_edges import source_parts, sha
from rig_plant_current import read_glb

def rebuild(image, mask, width=4):
    before=np.array(image.convert('RGBA')); after=before.copy()
    distance=ndi.distance_transform_edt(np.pad(mask,1))[1:-1,1:-1]
    # Keep a medial donor in stems narrower than twice the requested inset.
    # A one-pixel tip cannot be trusted as a color donor; its shape is retained
    # and receives paint from the nearest usable part of the same leaf.
    ridge=(distance>=ndi.maximum_filter(distance,size=9)) & (distance>=2)
    core=mask & ((distance>width) | ridge)
    if not core.any():raise ValueError('No uncontaminated leaf donor')
    nearest=ndi.distance_transform_edt(~core,return_distances=False,return_indices=True)
    band=mask & ~core
    after[:,:,:3][~core]=before[nearest[0],nearest[1],:3][~core]
    report={'native_size':list(image.size),'donor_inset_pixels':width,
        'rebuilt_rim_pixels':int(band.sum()),
        'changed_foreground_pixels':int(np.any(before[:,:,:3]!=after[:,:,:3],axis=2)[mask].sum()),
        'interior_rgb_identical':bool(np.array_equal(before[core],after[core])),
        'alpha_identical':bool(np.array_equal(before[:,:,3],after[:,:,3])),
        'all_rim_rgb_matches_interior_donor':bool(np.array_equal(after[:,:,:3][band],before[nearest[0],nearest[1],:3][band]))}
    return Image.fromarray(after),report

def embedded(doc,binary,index):
    v=doc['bufferViews'][doc['images'][index]['bufferView']];o=v.get('byteOffset',0)
    return Image.open(io.BytesIO(binary[o:o+v['byteLength']])).convert('RGBA')

def patch(source,parts,output,width):
    doc,binary=read_glb(source);g=Glb();g.doc=copy.deepcopy(doc);g.bin=bytearray(binary);rows=[]
    for i,leaf in enumerate(split_leaves(parts)):
        if not doc['images'][i]['name'].startswith('generated_leaf_'):raise ValueError('Unexpected material order')
        image=embedded(doc,binary,i)
        if image.size!=leaf.size:raise ValueError('Native source/texture size mismatch')
        result,report=rebuild(image,foreground(leaf),width)
        stream=io.BytesIO();result.save(stream,format='PNG')
        g.doc['images'][i]['bufferView']=g.view(stream.getvalue());report['leaf']=i+1;rows.append(report)
    g.doc['asset']['generator']='Foundry complete leaf rim color reconstruction v8'
    output.parent.mkdir(parents=True,exist_ok=True);g.save(output)
    after,after_binary=read_glb(output)
    same=all(doc.get(k)==after.get(k) for k in ['nodes','meshes','skins','animations','accessors','materials','textures','samplers']) and after_binary[:len(binary)]==binary
    root_images_same=all(doc['images'][i]==after['images'][i] for i in range(6,len(doc['images'])))
    okay=same and root_images_same and all(r['interior_rgb_identical'] and r['alpha_identical'] and r['all_rim_rgb_matches_interior_donor'] for r in rows)
    return {'id':source.stem,'ok':okay,'source':str(source),'source_sha256':sha(source),'source_parts':str(parts),'source_parts_sha256':sha(parts),'output':str(output),'sha256':sha(output),'geometry_uv_skin_animation_binary_identical':same,'root_materials_identical':root_images_same,'leaves':rows}

def comparisons(root,catalog,output,width):
    board=Image.new('RGB',(1440,1200),'#142226');draw=ImageDraw.Draw(board)
    for n,id in enumerate(['amazon_sword','vallisneria','lagenandra_red']):
        row=next(r for r in catalog['assets'] if r['id']==id)
        src=root/'projects/fishing-2d/game'/row['pre_rim_rebuild_model'].removeprefix('res://')
        d,b=read_glb(src);im=embedded(d,b,0);mask=foreground(split_leaves(source_parts(root,id))[0]);fixed,_=rebuild(im,mask,width)
        # Same native patch and nearest 5x enlargement on a dark background.
        ys,xs=np.where(mask);y=int(np.quantile(ys,.33));x=int(np.where(mask[y])[0][-1]);box=(max(0,x-32),max(0,y-30),min(im.width,x+10),min(im.height,y+45))
        for j,variant in enumerate([im,fixed]):
            a=np.array(variant);a[:,:,3]=mask.astype('uint8')*255
            piece=Image.fromarray(a).crop(box);piece=piece.resize((piece.width*5,piece.height*5),Image.Resampling.NEAREST)
            at=(n*480+10+j*225,55);board.paste(piece,at,piece)
            draw.text((at[0],25),id+(' BEFORE' if j==0 else ' AFTER'),fill='white')
        # Whole blade with the same silhouette, to check characteristic paint.
        for j,variant in enumerate([im,fixed]):
            a=np.array(variant);a[:,:,3]=mask.astype('uint8')*255;piece=Image.fromarray(a);piece.thumbnail((210,600),Image.Resampling.NEAREST)
            board.paste(piece,(n*480+10+j*225,550),piece)
    board.save(output/'native-rim-before-after.png')

def main():
    p=argparse.ArgumentParser();p.add_argument('--root',required=True,type=Path);p.add_argument('--input',required=True,type=Path);p.add_argument('--output',required=True,type=Path);p.add_argument('--review',required=True,type=Path);p.add_argument('--width',type=int,default=4);a=p.parse_args()
    root=a.root.resolve();catalog=json.loads(a.input.read_text(encoding='utf-8'));rows=[]
    for row in catalog['assets']:
        if not row['animated']:continue
        baseline=row.get('pre_rim_rebuild_model',row['model'])
        source=root/'projects/fishing-2d/game'/baseline.removeprefix('res://');target=a.output/'plants'/(row['id']+'.glb')
        report=patch(source,source_parts(root,row['id']),target,a.width);rows.append(report)
        if not report['ok']:raise ValueError('Rim reconstruction failed: '+row['id'])
        row['pre_rim_rebuild_model']=baseline
        row['model']='res://'+target.resolve().relative_to(root/'projects/fishing-2d/game').as_posix()
        row['material_revision']='complete-rim-reconstruction-v8'
    a.input.write_text(json.dumps(catalog,ensure_ascii=False,indent=2),encoding='utf-8')
    a.review.mkdir(parents=True,exist_ok=True);comparisons(root,catalog,a.review,a.width)
    data={'schema_version':1,'command':'aquascape.rebuild-plant-edge-colors','ok':all(r['ok'] for r in rows),'status':'done','next_action':'human_review','outputs':rows,'failures':[],'visual_review':'pending','user_acceptance':'pending','scope':'All rim RGB rebuilt from inset interior donors, including colored matte fringes. Native resolution, alpha, healthy silhouettes, UVs, skeletons and clips preserved. This is not proof that every pale pixel is unwanted; enlarged native engine review is required.'}
    a.output.mkdir(parents=True,exist_ok=True);(a.output/'rim-rebuild.validation.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'ok':data['ok'],'plants':len(rows),'rebuilt_rim_pixels':sum(l['rebuilt_rim_pixels'] for r in rows for l in r['leaves']),'geometry_motion_unchanged':all(r['geometry_uv_skin_animation_binary_identical'] for r in rows)}))

if __name__=='__main__':main()
