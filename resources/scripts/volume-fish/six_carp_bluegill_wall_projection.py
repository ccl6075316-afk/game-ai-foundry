import sys,json,pathlib,numpy as np
from PIL import Image,ImageDraw
R=pathlib.Path('E:/game-ai-foundry');sys.path.insert(0,str(R/'resources/scripts/volume-fish/portable'));from glb_io import read_glb,arrays
q=R/'projects/fishing-2d/plans/reviews/six-fish-release-20261104/bluegill';model=R/'projects/fishing-2d/game/assets/models/fish/bluegill.glb';d,b=read_glb(model);v=arrays(d,b,d['meshes'][0]['primitives'][0]['attributes']['POSITION']);report=json.loads((q/'wall-alpha.validation.json').read_text());sheet=Image.new('RGB',(1800,1240),(37,52,60));summary=[]
for rowi,name in enumerate(['Dorsal_mesh','Caudal_mesh']):
 part=next(p for p in d['extras']['geometry_parts']if p['source_node']==name);vs=v[part['vertex_start']:part['vertex_start']+part['vertex_count']];center=(vs.max(0)+vs.min(0))/2;zoom=np.linalg.norm(vs.max(0)-vs.min(0))*1.25
 for ci,view in enumerate(['left','oblique']):
  path=R/f'projects/fishing-2d/experiments/six-fish-database-20261104/bluegill/fin-views-r6/fin-{name}-{view}-texture.png';im=Image.open(path).convert('RGB');dr=ImageDraw.Draw(im);direction=np.array([0.,0.,1.])if view=='left'else np.array([.8,.3,1.]);direction/=np.linalg.norm(direction);right=np.cross([0,1,0],direction);right/=np.linalg.norm(right);up=np.cross(direction,right);records=[]
  for j,p in enumerate(next(x for x in report['fins']if x['name']==name)['opaque_wall_over_transparent_cap']):
   delta=np.array(p['point_native'])-center;x=int(round(450+delta@right*900/zoom));y=int(round(310-delta@up*900/zoom));
   if 0<=x<900 and 0<=y<620:
    rgb=im.getpixel((x,y));records.append({'probe':j,'image_xy':[x,y],'actual_GPU_RGB':rgb,'face':p['face']});dr.line((x-3,y,x+3,y),fill=(255,0,0));dr.line((x,y-3,x,y+3),fill=(255,0,0))
  dr.text((8,8),name+' '+view+' : red=current wall255/cap0 probes, diagnostic only',fill='white');sheet.paste(im,(ci*900,rowi*620));summary.append({'fin':name,'view':view,'projected':records})
sheet.save(q/'wall-probe-locations.jpg',quality=96);(q/'wall-probe-projection.validation.json').write_text(json.dumps({'kind':'diagnostic_wall_probe_GPU_projection','samples':summary,'scope':'Read-only approximate camera projection into actual same-model captures; red marks do not constitute a repair or pass.'},indent=2)+'\n')
