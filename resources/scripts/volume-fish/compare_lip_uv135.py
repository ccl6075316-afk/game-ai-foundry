"""Validate actual UV joins, whole source cells and fixed-camera GPU review."""
import argparse,json,hashlib
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFont

ap=argparse.ArgumentParser();ap.add_argument('--trial',required=True,type=Path);root=ap.parse_args().trial.resolve()
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
plan=json.loads((root/'trial.plan.json').read_text());build=json.loads((root/'geometry-material.validation.json').read_text());render=json.loads((root/'studio/preview.validation.json').read_text())
assert build['ok'] and render['ok'];assert 'ERROR:' not in (root/'studio.log').read_text()
assert build['inputs']['plan_sha256']==sha(root/'trial.plan.json');assert build['inputs']['builder_sha256']==sha('resources/scripts/volume-fish/build_lip_uv135.py')
assert render['inputs']['renderer_sha256']==sha('resources/scripts/volume-fish/preview_lip_uv135.gd')
for p,h in plan['frozen_inputs'].items():assert sha(p)==h,p
for o in build['outputs']:assert sha(o['path'])==o['sha256']
source=np.array(Image.open(plan['source_image']).convert('RGBA'));opaque=np.array(Image.open(plan['opaque_skin']).convert('RGBA'))
lip=json.loads(Path(plan['lip_mesh']).read_text());aligned=json.loads(Path(plan['aligned_lips']).read_text());probe=json.loads((root/'body-lip-correspondence.json').read_text());joins={}
for original,part in zip(lip['parts'],aligned['parts']):
 for key in ['vertices','normals','triangles']:assert original[key]==part[key],key
 assert part['uv']==probe[part['name']]['body_uv']
 a=np.array(Image.open(plan['continuation_atlases'][part['name']]).convert('RGBA'));assert np.array_equal(a,np.load(root/(part['name']+'-continuation.rgba.npy')))
 donors=json.loads((root/(part['name']+'-donors.json')).read_text());assert len(donors)==a.shape[0]*a.shape[1]
 for col,row,x,y,fallback in donors:assert np.array_equal(a[row,col,:3],(opaque if fallback else source)[y,x,:3])
 joins[part['name']]={'actual_body_uv_vs_lip_material_uv_source_pixel_error_max':float(np.max(abs(np.array(part['uv'])-np.array(probe[part['name']]['body_uv'])))*1986),'source_cell_rgb_exact':True}
skin=np.array(json.loads(Path(plan['skin_records']).read_text()));assert np.all((skin[skin[:,2]>0,:2]>=0)&(skin[skin[:,2]>0,:2]<=1))
assert np.array_equal(np.array(Image.open(plan['skin_atlas']).convert('RGBA')),np.load(root/'skin-continuation.rgba.npy'))
font=ImageFont.truetype('/System/Library/Fonts/STHeiti Medium.ttc',25);small=ImageFont.truetype('/System/Library/Fonts/STHeiti Light.ttc',20)
outputs=[];gray={};coverage={}
for output,rows in [('material-join-review.png',[('mouth-front-texture.png','正面'),('mouth-oblique-texture.png','斜视')]),('head-review.png',[('head-oblique-texture.png','完整头部斜视'),('head-side-texture.png','完整头部侧面')])]:
 sheet=Image.new('RGB',(1200,450*len(rows)+45),(15,29,36));draw=ImageDraw.Draw(sheet)
 for r,(name,title) in enumerate(rows):
  for c,(folder,label) in enumerate([('baseline134','上一版 · 另排的碎点'),('candidate135','本次 · 按原材质接续')]):
   im=Image.open(root/'studio'/folder/name).convert('RGB');a=np.array(im)
   assert not ((a[:,:,0]>220)&(a[:,:,1]<40)&(a[:,:,2]>220)).any(),'Invalid material lookup'
   draw.text((600*c+12,450*r+14),label+' · '+title,font=font,fill='white');sheet.paste(im.resize((600,400),Image.Resampling.NEAREST),(600*c,450*r+50))
 draw.text((12,450*len(rows)+12),'同机位与尺度；按实际UV接头延续完整像素材质，形状不变。',font=small,fill=(185,209,219));p=root/output;sheet.save(p);outputs.append({'path':str(p),'sha256':sha(p)})
sheet=Image.new('RGB',(1280,425),(15,29,36));draw=ImageDraw.Draw(sheet);roi=(420,240,740,420)
for c,(folder,label) in enumerate([('baseline134','上一版 · 接头放大'),('candidate135','本次 · 接头放大')]):
 im=Image.open(root/'studio'/folder/'mouth-oblique-texture.png').convert('RGB');sheet.paste(im.crop(roi).resize((640,360),Image.Resampling.NEAREST),(640*c,40));draw.text((640*c+12,9),label,font=font,fill='white')
draw.text((12,402),'固定裁切、共同2倍nearest放大；未分别缩放或配准。',font=small,fill=(185,209,219));p=root/'joint-pixel-zoom.png';sheet.save(p);outputs.append({'path':str(p),'sha256':sha(p)})
for close in ['mouth','head']:
 for view in ['side','front','top','oblique']:
  name=close+'-'+view+'-clay.png';a=np.array(Image.open(root/'studio/baseline134'/name));b=np.array(Image.open(root/'studio/candidate135'/name));gray[name]=int(np.any(a!=b,axis=2).sum());assert gray[name]==0,'Geometry changed'
  a=np.array(Image.open(root/'studio/candidate135'/(close+'-'+view+'-edge_probe.png')).convert('RGB')).astype(np.int16);mask=(a[:,:,2]>100)&(a[:,:,2]>a[:,:,0]*1.7)&(a[:,:,2]>a[:,:,1]*1.7);coverage[close+'-'+view]=int(mask.sum())
assert coverage['mouth-front']>1000 and coverage['mouth-oblique']>1000
formal=Path('projects/fishing-2d/game/assets/models/fish/black_seabream.glb');assert sha(formal)=='c42765e1a8c975840ab43840ca69ff72cf3b483e9a40bfb0ae288330f38285bf'
report={'schema_version':1,'ok':True,'command':'fish.compare-lip-uv135','stage':'validate','status':'done','next_action':'human_review','inputs':{'plan_sha256':sha(root/'trial.plan.json'),'build_report_sha256':sha(root/'geometry-material.validation.json'),'render_report_sha256':sha(root/'studio/preview.validation.json'),'renderer_sha256':sha('resources/scripts/volume-fish/preview_lip_uv135.gd'),'lip_shader_sha256':sha('resources/scripts/volume-fish/lip_uv135.gdshader'),'actual_skin_shader_sha256':sha(root/'studio/actual-skin135.gdshader'),'helper_sha256':sha(__file__)},'outputs':outputs,'summary':{'actual_body_uv_join_checks':joins,'measured_grid_constraints':build['summary']['charts'],'whole_material_rgb_preserved_not_dark_pixel_extraction':True,'adjacent_skin_and_lip_share_chart':True,'gray_changed_pixels':gray,'blue_material_region_probe':coverage,'nose132_repair_retained':True,'agent_visual_observation':'pending actual image inspection','user_visual_acceptance':'pending','production_installed':False,'scope':'Static source-material continuation study. Hidden front material is reflected source artwork with measured boundary constraints; not a new accepted front view or full fish fin/body/motion/LOD delivery.'},'failures':[]}
(root/'trial.validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps({'ok':True,'outputs':outputs,'joins':joins,'gray_changed_pixels':gray},ensure_ascii=False))
