#!/usr/bin/env python3
"""Read-only zander108 native-source/actual-mouth alignment; no repair."""
import argparse,json,hashlib
from pathlib import Path
from collections import Counter
import numpy as np
from PIL import Image,ImageDraw
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def boundary(data):
 v=np.asarray(data['rest_xyz']);keys=[tuple(np.round(q,7)) for q in v];counts=Counter();pairs={}
 for tri in np.asarray(data['indices']).reshape(-1,3):
  for i,j in zip(tri,np.roll(tri,-1)):
   key=tuple(sorted([keys[i],keys[j]]));counts[key]+=1;pairs[key]=(int(i),int(j))
 return [(k,pairs[k]) for k,n in counts.items() if n==1]
def plane_points(data,x):
 v=np.asarray(data['rest_xyz']);tri=v[np.asarray(data['indices']).reshape(-1,3)];tri=tri[(tri[:,:,0].min(1)<=x+1e-10)&(tri[:,:,0].max(1)>=x-1e-10)];points=[]
 for i,j in [(0,1),(1,2),(2,0)]:
  A=tri[:,i];B=tri[:,j];dx=B[:,0]-A[:,0];good=abs(dx)>1e-12;t=np.zeros(len(A));t[good]=(x-A[good,0])/dx[good];good&=(t>=-1e-9)&(t<=1+1e-9);points.extend(A[good]+t[good,None]*(B[good]-A[good]));flat=(abs(dx)<=1e-12)&(abs(A[:,0]-x)<=1e-9);points.extend(A[flat]);points.extend(B[flat])
 return np.asarray(points).reshape(-1,3)
def main():
 ap=argparse.ArgumentParser(description=__doc__)
 for name in ['input','output','surface0','surface1','source','game']:ap.add_argument('--'+name,required=True,type=Path)
 a=ap.parse_args();p=json.loads(a.input.read_text());skin=json.loads(a.surface0.read_text());oral=json.loads(a.surface1.read_text());source=Image.open(a.source).convert('RGBA');rgba=np.array(source);W,H=source.size;aspect=H/W
 assert p['species']=='zander' and (W,H)==(2024,742) and sha(a.source)=='fd2d0c154c140aca906201fcd7c7f80e043221827f4c97a14b714e24fa825b67'
 assert sha(a.game/'assets/models/fish/zander.glb')=='c1b10d96c7aa83e41129df16170d7302f4c4335b226785c5f5b5bd562b6e0aef'
 def canvas(v):
  v=np.asarray(v);return np.column_stack([(v[:,0]+.5)*W,H*.5-v[:,1]*W])
 m=p['oral_jaws'];cu,cv=m['corner'];fu,fv=m['front'];slope=(fv-cv)/(fu-cu)
 def slit(u):return cv+(u-cu)*slope
 v=np.asarray(skin['rest_xyz']);uv=np.asarray(skin['source_uv']);xy=canvas(v);u=v[:,0]+.5;signed=v[:,1]-(.5-slit(u))*aspect;tips={}
 for name,select in [('upper',(u>cu)&(signed>0)),('lower',(u>cu)&(signed<0))]:
  maximum=u[select].max();ids=np.flatnonzero(select&(u>=maximum-1e-7));tips[name]={'max_native_u':float(maximum),'max_canvas_x':float(maximum*W),'vertex_ids':ids.tolist(),'rest_xyz':v[ids].tolist(),'geometry_canvas_px':xy[ids].tolist(),'actual_uv_px':(uv[ids]*[W,H]).tolist()}
 source_tips={}
 for name,box in [('upper',(1995,370,W,418)),('lower',(1995,419,W,455))]:
  x0,y0,x1,y1=box;y,x=np.nonzero(rgba[y0:y1,x0:x1,3]>=243);mx=int(x.max()+x0);ys=y[x+x0==mx]+y0;source_tips[name]={'native_roi':box,'opaque_alpha_threshold':243,'max_source_x':mx,'tip_y_range':[int(ys.min()),int(ys.max())]}
 b0=boundary(skin);b1=boundary(oral);common=set(k for k,ij in b0)&set(k for k,ij in b1);interface=[]
 for k,(i,j) in b0:
  if k in common:interface.append({'skin_vertex_ids':[i,j],'rest_xyz':v[[i,j]].tolist(),'geometry_canvas_px':xy[[i,j]].tolist(),'actual_uv_px':(uv[[i,j]]*[W,H]).tolist(),'uv_minus_geometry_px':(uv[[i,j]]*[W,H]-xy[[i,j]]).tolist()})
 stations=[]
 for sx in [1894,1900,1920,1940,1960,1980,1995,2000,2005,2010,2015]:
  center=sx+.5;phys=plane_points(skin,center/W-.5);inner=plane_points(oral,center/W-.5);ys=np.flatnonzero(rgba[300:510,sx,3]>=243)+300;row={'source_column':sx,'mesh_plane_canvas_x':center,'source_opaque_y_min':int(ys.min()),'source_opaque_y_max':int(ys.max()),'configured_slit_center_y':float(slit(center/W)*H),'configured_gap_source_pixels':m['gap']*W}
  if len(phys):
   lo,hi=canvas(phys)[:,1].min(),canvas(phys)[:,1].max();row.update({'mesh_outer_y_min':float(lo),'mesh_chin_y_max':float(hi),'source_chin_below_mesh_px':float(ys.max()-hi)})
  if len(inner):
   lo,hi=canvas(inner)[:,1].min(),canvas(inner)[:,1].max();row.update({'actual_oral_roof_y':float(lo),'actual_oral_floor_y':float(hi),'actual_lower_wedge_thickness_px':float(row['mesh_chin_y_max']-hi),'source_available_chin_below_same_floor_px':float(ys.max()-hi)})
  stations.append(row)
 a.output.mkdir(parents=True,exist_ok=True);roi=(1870,380,2024,500);x0,y0,x1,y1=roi;scale=4;pw=(x1-x0)*scale;ph=(y1-y0)*scale
 def segment(draw,points,color):draw.line([(float(x)-x0,float(y)-y0) for x,y in points],fill=color,width=1)
 base=Image.new('RGBA',source.size,(40,55,60,255));base.alpha_composite(source);base=base.convert('RGB');panels=[('Accepted source fd2d / same native canvas',base.crop(roi))]
 im=base.crop(roi);d=ImageDraw.Draw(im)
 for edge in interface:segment(d,edge['geometry_canvas_px'],(255,20,220))
 for field in ['mesh_outer_y_min','mesh_chin_y_max']:segment(d,[(r['mesh_plane_canvas_x'],r[field]) for r in stations if field in r],(0,255,100))
 for name,color in [('upper',(255,30,30)),('lower',(30,150,255))]:
  x,y=tips[name]['geometry_canvas_px'][0];d.ellipse((x-x0-1,y-y0-1,x-x0+1,y-y0+1),fill=color)
 panels.append(('Geometry: pink=oral rim green=outer/chin',im))
 im=base.crop(roi);d=ImageDraw.Draw(im)
 for edge in interface:segment(d,edge['actual_uv_px'],(0,235,255))
 segment(d,[(cu*W,cv*H),(fu*W,fv*H)],(255,150,0));panels.append(('Actual rim UV cyan / configured slit orange',im))
 im=Image.new('RGB',(x1-x0,y1-y0),(40,55,60));d=ImageDraw.Draw(im)
 for data,color in [(skin,(70,180,230)),(oral,(235,30,200))]:
  pts=canvas(data['rest_xyz'])
  for face in np.asarray(data['indices']).reshape(-1,3):
   q=pts[face]
   if q[:,0].max()<x0 or q[:,0].min()>x1 or q[:,1].max()<y0 or q[:,1].min()>y1:continue
   d.polygon([(float(x)-x0,float(y)-y0) for x,y in q],fill=color)
 for edge in interface:segment(d,edge['geometry_canvas_px'],(255,255,255))
 panels.append(('Projected ownership blue=skin0 pink=oral1',im))
 board=Image.new('RGB',(pw*2,ph*2+72),(30,42,49));d=ImageDraw.Draw(board)
 for i,(title,im) in enumerate(panels):
  bx=(i%2)*pw;by=(i//2)*(ph+36);d.text((bx+8,by+8),title,fill='white');board.paste(im.resize((pw,ph),Image.Resampling.NEAREST),(bx,by+30))
 board.save(a.output/'same-source-canvas.png')
 inputs=[a.input,a.surface0,a.surface1,a.source,a.game/'assets/models/fish/zander.glb',a.game/'scripts/aquarium/FishBodyOpaque.gdshader',a.game/'scripts/aquarium/FishHeadSource.gdshaderinc',a.game/'assets/models/fish/motion/head-source.json',a.game/'assets/models/fish/motion/eye-ownership-107.json']
 report={'schema_version':1,'ok':True,'status':'diagnostic_only','accepted':False,'scope':'108 Phase1 only; no model/source/material/107/106 changes.','inputs':{str(path):sha(path) for path in inputs},'source_canvas':[W,H],'roi_native':roi,'coordinate_formula':'X=(rest.x+.5)*2024; Y=371-rest.y*2024. Orthographic rest projection, no fitting.','configured_oral_jaws':m,'actual_tips':tips,'source_tips':source_tips,'lower_minus_upper_tip_x_native_pixels':tips['lower']['max_canvas_x']-tips['upper']['max_canvas_x'],'surface0_boundary_edges':len(b0),'surface1_boundary_edges':len(b1),'matched_material_interface_edges':len(common),'actual_interface':interface,'stations':stations,'failure_constraints':['lower_projection=upper_retraction=0; do not call this intentional lower-jaw projection.','Check the complete chin/wedge source envelope, not only the front tip.','Actual oral roof/floor geometry, source painted line and their samplingUV are separate quantities.','Source0 painted skin and source1 constant oral inner surface share one Closed_body, no independent lower jaw.','Recolor/black-fill cannot restore missing jaw volume.','Do not classify all dark source pixels as mouth; separate native-pattern/source-image review is required.'],'limits':['Base rest mesh only, not allLOD/deformed-pose acceptance.','Projected ownership union is not perspective visibility or GPU shading proof.','Source-alpha243 boundary is an image target, not biological measurement.','Nearest UV outline inset may be intentional; do not equate that inset with geometric alignment.']}
 (a.output/'source-mouth-alignment.validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'tips':{k:z['max_canvas_x'] for k,z in tips.items()},'source_tips':source_tips,'interface_edges':len(common),'stations':stations},indent=2))
if __name__=='__main__':main()
