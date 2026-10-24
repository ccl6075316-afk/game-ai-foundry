"""Deterministic white-matte decontamination of native GLB leaf materials.

Only edge RGB and texture padding change. Geometry, UVs, skins, clips, source
art, alpha silhouettes and native image dimensions remain byte-identical.
"""
import argparse,copy,hashlib,io,json
from pathlib import Path
import numpy as np
from PIL import Image
from scipy import ndimage as ndi
from build_from_art import Glb,foreground,split_leaves
from rig_plant_current import read_glb

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def white_mix(rgb,reference):
    c=rgb.astype(float);f=reference.astype(float);direction=255-f
    alpha=np.clip(np.sum((255-c)*direction,axis=2)/np.maximum(np.sum(direction*direction,axis=2),1),0,1)
    residual=np.linalg.norm(c-(255-alpha[:,:,None]*direction),axis=2)/np.sqrt(3)
    near_white=(c.min(2)>=175)&(np.ptp(c,axis=2)<70)
    return near_white&(alpha<.90)&(residual<24)&((c-f).mean(2)>12)

def clean(image,mask):
    a=np.array(image.convert('RGBA'));before=a.copy()
    distance=ndi.distance_transform_edt(np.pad(mask,1))[1:-1,1:-1]
    band=mask&(distance<=3)
    core=mask&(distance>3)
    if not core.any():raise ValueError('No interior color donor in leaf')
    nearest=ndi.distance_transform_edt(~core,return_distances=False,return_indices=True)
    reference=a[nearest[0],nearest[1],:3]
    targets=band&white_mix(a[:,:,:3],reference)
    a[:,:,:3][targets]=reference[targets]
    # Opaque 3D shells need color beyond their silhouettes for nearest sampling
    # at UV boundaries. The shell geometry still supplies the exact cutout.
    valid=mask&~targets
    nearest=ndi.distance_transform_edt(~valid,return_distances=False,return_indices=True)
    outside=~mask
    a[:,:,:3][outside]=a[nearest[0],nearest[1],:3][outside]
    remaining=band&white_mix(a[:,:,:3],reference)
    return Image.fromarray(a),{'native_size':list(image.size),'edge_band_pixels':int(band.sum()),'white_matte_pixels_before':int(targets.sum()),'white_matte_pixels_after':int(remaining.sum()),'interior_rgb_identical':bool(np.array_equal(a[:,:,:3][core],before[:,:,:3][core])),'alpha_identical':bool(np.array_equal(a[:,:,3],before[:,:,3])),'non_target_foreground_identical':bool(np.array_equal(a[:,:,:3][mask&~targets],before[:,:,:3][mask&~targets])),'padding_pixels':int(outside.sum())}

def source_parts(root,id):
    if id=='anubias':return root/'projects/aquascape-anubias-v2-leaves/output/anubias_leaves_nobg.png'
    if id=='java_fern':return root/'projects/aquascape-fern-v2-leaves/output/fern_leaves_nobg.png'
    return root/f'projects/fishing-2d/plans/reviews/aquascape-catalog-v5/sources/{id}/{id}-leaves.png'

def patch(source,parts,output):
    doc,binary=read_glb(source);g=Glb();g.doc=copy.deepcopy(doc);g.bin=bytearray(binary)
    leaves=split_leaves(parts);rows=[]
    for i,leaf in enumerate(leaves):
        im=doc['images'][i]
        if not im['name'].startswith('generated_leaf_'):raise ValueError('Unexpected leaf material ordering')
        view=doc['bufferViews'][im['bufferView']];offset=view.get('byteOffset',0)
        original=Image.open(io.BytesIO(binary[offset:offset+view['byteLength']])).convert('RGBA')
        if original.size!=leaf.size:raise ValueError('Source parts and model texture disagree')
        result,report=clean(original,foreground(leaf));stream=io.BytesIO();result.save(stream,format='PNG')
        g.doc['images'][i]['bufferView']=g.view(stream.getvalue())
        report['leaf']=i+1;rows.append(report)
    roots=[]
    for i in range(6,len(doc['images'])):
        im=doc['images'][i]
        if im['name'] not in ['source_rhizome_paint','generated_root_crown_paint']:continue
        view=doc['bufferViews'][im['bufferView']];offset=view.get('byteOffset',0)
        original=np.array(Image.open(io.BytesIO(binary[offset:offset+view['byteLength']])).convert('RGBA'));result=original.copy()
        # Legacy crown donor crops contain actual white background gaps between
        # stems. A closed tube has no cutout there: extend its existing color.
        white=(original[:,:,:3].min(2)>=200)&(np.ptp(original[:,:,:3].astype(float),axis=2)<=40)
        valid=(~white)&(original[:,:,:3].min(2)<160)
        if not valid.any():raise ValueError('No root paint donor')
        nearest=ndi.distance_transform_edt(~valid,return_distances=False,return_indices=True)
        result[:,:,:3][white]=original[nearest[0],nearest[1],:3][white]
        stream=io.BytesIO();Image.fromarray(result).save(stream,format='PNG');g.doc['images'][i]['bufferView']=g.view(stream.getvalue())
        roots.append({'material':im['name'],'white_background_pixels_corrected':int(white.sum()),'other_pixels_identical':bool(np.array_equal(original[~white],result[~white])),'native_size':[original.shape[1],original.shape[0]]})
    g.doc['asset']['generator']='Foundry material-only leaf white-matte cleanup'
    output.parent.mkdir(parents=True,exist_ok=True);g.save(output)
    after,after_binary=read_glb(output)
    # Every original binary byte remains in place. Only image references point
    # to appended PNGs, so all accessor/animation/inverse-bind bytes are exact.
    identical=all(doc.get(k)==after.get(k) for k in ['nodes','meshes','skins','animations','accessors','materials','textures','samplers']) and after_binary[:len(binary)]==binary
    okay=identical and all(r['white_matte_pixels_after']==0 and r['interior_rgb_identical'] and r['alpha_identical'] and r['non_target_foreground_identical'] for r in rows) and all(r['other_pixels_identical'] for r in roots)
    return {'id':source.stem,'source':str(source),'source_sha256':sha(source),'source_parts':str(parts),'source_parts_sha256':sha(parts),'output':str(output),'sha256':sha(output),'ok':okay,'geometry_uv_skin_animation_binary_identical':identical,'leaves':rows,'roots':roots,'changed_pixels':sum(r['white_matte_pixels_before'] for r in rows)+sum(r['white_background_pixels_corrected'] for r in roots)}

def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--input',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    root=a.root.resolve();catalog=json.loads(a.input.read_text(encoding='utf-8'));rows=[]
    for row in catalog['assets']:
        if not row['animated']:continue
        original=row.get('pre_edge_cleanup_model',row['model'])
        source=root/'projects/fishing-2d/game'/original.removeprefix('res://')
        output=a.output/'plants'/(row['id']+'.glb')
        report=patch(source,source_parts(root,row['id']),output);rows.append(report)
        if not report['ok']:raise ValueError('Material cleanup validation failed: '+row['id'])
        row['pre_edge_cleanup_model']=original
        row['model']='res://'+str(output.resolve().relative_to(root/'projects/fishing-2d/game')).replace('\\','/')
        row['material_revision']='white-matte-cleanup-v6'
    a.input.write_text(json.dumps(catalog,ensure_ascii=False,indent=2),encoding='utf-8')
    data={'schema_version':1,'command':'aquascape.clean-plant-material-edges','ok':all(r['ok'] for r in rows),'status':'done','next_action':'human_review','outputs':rows,'failures':[],'scope':'Leaf rim RGB decontamination and color padding only. Original white-backed images, silhouettes, UVs, mesh, bones and animation are preserved. Interior high-light pixels are protected.','visual_review':'pending','user_acceptance':'pending'}
    a.output.mkdir(parents=True,exist_ok=True);(a.output/'edge-cleanup.validation.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'ok':data['ok'],'plants':len(rows),'white_edge_pixels_corrected':sum(r['changed_pixels'] for r in rows),'models_and_motion_unchanged':all(r['geometry_uv_skin_animation_binary_identical'] for r in rows)}))

if __name__=='__main__':main()
