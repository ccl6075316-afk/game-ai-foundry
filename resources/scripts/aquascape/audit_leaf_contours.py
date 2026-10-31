"""Compare generated paint, extracted alpha and actual exported leaf UV coverage."""
import argparse,json,sys
from pathlib import Path
import numpy as np
import cv2
from PIL import Image,ImageDraw,ImageFont
from scipy import ndimage as ndi
from build_from_art import split_leaves,foreground
from rig_plant_current import read_glb,array
from clean_plant_material_edges import source_parts

p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--output',type=Path);a=p.parse_args();root=a.root.resolve()
out=a.output or root/'projects/fishing-2d/plans/reviews/aquascape-leaf-contours-v7';out.mkdir(parents=True,exist_ok=True)
catalog=json.loads((root/'projects/fishing-2d/game/assets/aquascape-v5/catalog.json').read_text(encoding='utf-8'))
report=[];font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',23)
for row in catalog['assets']:
    if not row['animated']:continue
    leaves=split_leaves(source_parts(root,row['id']));doc,binary=read_glb(root/'projects/fishing-2d/game'/row['model'].removeprefix('res://'))
    results=[]
    leaf_count=sum(m['name'].startswith('traced_leaf_') for m in doc['meshes'])
    for leaf_id in range(leaf_count):
        leaf=leaves[leaf_id%len(leaves)]
        prim=next(m for m in doc['meshes'] if m['name']=='traced_leaf_'+str(leaf_id+1))['primitives'][0]
        uv=array(doc,binary,prim['attributes']['TEXCOORD_0']).reshape(-1,3,2)
        h,w=foreground(leaf).shape;mask=foreground(leaf)
        points=uv*np.array([w,h])-.5 if doc.get('extras',{}).get('leaf_uv_pixel_centers') else uv*np.array([w-1,h-1]);ab=points[:,1]-points[:,0];ac=points[:,2]-points[:,0];area=np.abs(ab[:,0]*ac[:,1]-ab[:,1]*ac[:,0]);points=points[area>1e-5]
        scale=4;canvas=np.zeros((h*scale+8,w*scale+8),dtype='uint8')
        polygons=[np.rint(t*scale+4).astype('int32') for t in points]
        # Each polygon is filled separately: fillPoly(all) applies an even/odd
        # rule to overlapping front/back faces and is not a triangle union.
        for t in polygons:cv2.fillConvexPoly(canvas,t,255)
        actual=canvas[4:4+h*scale:scale,4:4+w*scale:scale]>0
        distance=ndi.distance_transform_edt(mask)
        missed=mask&~actual;deep=missed&(distance>1.5)
        _,holes=ndi.label(ndi.binary_fill_holes(actual)&~actual)
        results.append({'leaf':leaf_id+1,'source_size':[w,h],'source_foreground':int(mask.sum()),'model_missing_source_pixels':int(missed.sum()),'missing_more_than_1_5_px_inside':int(deep.sum()),'model_extra_pixels':int((actual&~mask).sum()),'internal_uv_holes':holes,'ok':bool(holes==0 and missed.sum()/mask.sum()<.005 and deep.sum()/mask.sum()<.001)})
        if leaf_id==0:
            sheet=Image.new('RGB',(1500,840),'#16353a');draw=ImageDraw.Draw(sheet)
            src=Image.new('RGBA',leaf.size,'#16353a');src.alpha_composite(leaf)
            silhouettes=[]
            for data in [mask,actual]:
                rgb=np.zeros((h,w,3),dtype='uint8');rgb[:]=[22,53,58];rgb[data]=[177,204,180];silhouettes.append(Image.fromarray(rgb))
            for i,(image,label) in enumerate(zip([src.convert('RGB'),*silhouettes],['生成叶片 / 原画像素','抠图轮廓 / alpha','实际模型轮廓 / UV 投影'])):
                draw.text((i*500+15,12),label,fill='#e7e1c9',font=font)
                image.thumbnail((470,760),Image.Resampling.NEAREST);sheet.paste(image,(i*500+(500-image.width)//2,60+(760-image.height)//2))
            sheet.save(out/(row['id']+'-contour.png'))
    report.append({'id':row['id'],'leaves':results})
okay=all(l['ok'] for r in report for l in r['leaves'])
data={'command':'aquascape.audit-leaf-contours','ok':okay,'status':'done' if okay else 'failed','next_action':'human_review' if okay else 'fix_input','outputs':report,'scope':'Read-only 4x raster union of all exported leaf UV triangles, compared with source masks. Requires no interior UV holes, missing area below 0.5%, and deeper missed source pixels below 0.1%. Numerical raster boundaries have subpixel tolerance; inspect images, not counts alone.'}
(out/'contour-audit.validation.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps([{'id':r['id'],'missing':sum(l['model_missing_source_pixels'] for l in r['leaves']),'deep_missing':sum(l['missing_more_than_1_5_px_inside'] for l in r['leaves']),'holes':sum(l['internal_uv_holes'] for l in r['leaves'])} for r in report]))
raise SystemExit(0 if okay else 1)
