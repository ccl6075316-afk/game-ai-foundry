"""Extend the existing upper-lip outline AND fill across the actual front lip.

No new geometry or unrelated grey donor. Unique islands use the existing free
atlas gutter, avoiding projected-color collisions elsewhere on the head.
"""
from pathlib import Path
import argparse,json,hashlib,math,cv2
import numpy as np
from PIL import Image,ImageDraw
parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--pixel-clusters',action='store_true');args=parser.parse_args()
repo=Path(__file__).resolve().parents[3];trial=repo/'projects/fishing-2d/experiments/nile-dorsal-route-trial';history=trial/'round7-upper-lip-continuity';out=trial/('round8-upper-lip-pixel-clusters' if args.pixel_clusters else 'round7-upper-lip-continuity');old=trial/'round6-reference-repair'
read=lambda p:json.loads(p.read_text(encoding='utf8'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
guide_path=history/'upper-lip-guide.json';guide=read(guide_path);base=np.array(Image.open(old/'body-atlas-two-dimensional.png').convert('RGBA'));atlas=base.copy();marked=base.copy();h,w=atlas.shape[:2];padding=3
source=np.array(Image.open(trial/guide['side_source']).convert('RGBA'))
rows=[r for r in read(old/'A-mouth-reference.validation.json')['samples']['A']['samples'] if r['mouth_gap_lower_upper_z']]
source_x=np.array([r['u']*1961 for r in rows]);source_y=np.array([486-r['mouth_gap_lower_upper_z'][1]*1961 for r in rows])
anchor=guide['source_extension_anchor_u']*1961;ay=np.interp(anchor,source_x,source_y);slope=(np.interp(anchor+1,source_x,source_y)-np.interp(anchor-1,source_x,source_y))/2
outward=np.array([slope,-1.]);outward/=np.linalg.norm(outward)
profile_xy=np.rint(np.array([anchor,ay])[None,:]+np.arange(guide['source_band_width_px']+1)[:,None]*outward).astype(int)
profile=source[profile_xy[:,1],profile_xy[:,0]];assert np.all(profile[:,3]==255),'Upper-lip source leaves foreground'
if not args.pixel_clusters:Image.fromarray(np.repeat(profile[None,:,:],12,axis=0)).resize((660,120),Image.Resampling.NEAREST).save(out/'existing-upper-lip-outline-and-fill.png')
segments=[(np.array(guide['boundary_vertices'][str(a)]),np.array(guide['boundary_vertices'][str(b)])) for a,b in guide['upper_lip_edges']]
field_data={}
if args.pixel_clusters:
 # Order the actual shared lip boundary once. Arc coordinates, donor phase and
 # brush cells are shared by every atlas island, including the centre seam.
 adjacency={}
 for a,b in guide['upper_lip_edges']:
  adjacency.setdefault(a,[]).append(b);adjacency.setdefault(b,[]).append(a)
 chain=[guide['endpoints'][0]]
 while chain[-1]!=guide['endpoints'][1]:
  choices=[v for v in adjacency[chain[-1]] if v not in chain]
  assert len(choices)==1,'Upper lip must be one open chain';chain.append(choices[0])
 boundary=np.array([guide['boundary_vertices'][str(v)] for v in chain])
 segments=list(zip(boundary[:-1],boundary[1:]));lengths=np.linalg.norm(np.diff(boundary,axis=0),axis=1)*1961;arc=np.r_[0,np.cumsum(lengths)]
 def crossings(u):
  result=[]
  for i,(a,b) in enumerate(segments):
   x=u-.5
   if min(a[0],b[0])<=x<=max(a[0],b[0]) and a[0]!=b[0]:result.append(float(arc[i]+(x-a[0])/(b[0]-a[0])*lengths[i]))
  assert len(result)==2,(u,result)
  return sorted(result)
 joins={str(u):crossings(u) for u in [guide['front_blend_start_u'],guide['front_blend_full_u']]}
 # Preserve a complete two-dimensional strip in the original native source.
 # The range is this fish's observed alpha-safe painted lip, not a universal ROI.
 donor_x=np.linspace(.955*1961,.985*1961,601);donor_y=np.interp(donor_x,source_x,source_y)
 donor_arc=np.r_[0,np.cumsum(np.hypot(np.diff(donor_x),np.diff(donor_y)))];donor_length=float(donor_arc[-1])
 donor_anchor=float(np.interp(guide['front_blend_start_u']*1961,donor_x,donor_arc))
 brush=6;native_length=int(np.ceil(arc[-1]))+1;band_width=guide['source_band_width_px']+1
 cell_rows=int(np.ceil(band_width/brush));cell_cols=int(np.ceil(native_length/brush));cells=np.zeros((cell_rows,cell_cols,4),dtype='uint8');records=[]
 left,right=joins[str(guide['front_blend_start_u'])]
 for ci in range(cell_cols):
  sc=min(ci*brush+(brush-1)/2,arc[-1]);phase=donor_anchor+min(sc-left,right-sc)
  reflected=phase%(2*donor_length);along=reflected if reflected<=donor_length else 2*donor_length-reflected
  dx=float(np.interp(along,donor_arc,donor_x));dy=float(np.interp(along,donor_arc,donor_y));slope=float(np.interp(dx+1,source_x,source_y)-np.interp(dx-1,source_x,source_y))/2
  normal=np.array([slope,-1.]);normal/=np.linalg.norm(normal)
  for ri in range(cell_rows):
   distance=min(ri*brush+(brush-1)/2,guide['source_band_width_px']);xy=np.rint(np.array([dx,dy])+normal*distance).astype(int)
   assert 0<=xy[0]<source.shape[1] and 0<=xy[1]<source.shape[0] and source[xy[1],xy[0],3]==255,('Donor outside opaque source',xy.tolist())
   cells[ri,ci]=source[xy[1],xy[0]]
   records.append({'cell':[ci,ri],'source_xy':xy.tolist(),'rgba':cells[ri,ci].tolist(),'source_arc_px':along})
 donor_field=cells.repeat(brush,axis=0).repeat(brush,axis=1)[:band_width,:native_length]
 Image.fromarray(donor_field).save(out/'upper-lip-native-2d-field.png')
 field_data={'brush_cell_native_px':brush,'native_along_by_across_px':[native_length,band_width],'actual_boundary_vertex_chain':chain,'actual_lip_arc_native_px':float(arc[-1]),'continuous_join_arc_px':joins,'source_u_range':[.955,.985],'source_strip_arc_px':donor_length,'source_phase_anchor_arc_px':donor_anchor,'extension':'Reflect complete curved 2D donor strip; phase anchored to the actual continuous left/right start joins.','cells':records,'field_sha256':sha(out/'upper-lip-native-2d-field.png')}
 write(out/'upper-lip-donor-field.validation.json',field_data)
def smooth(x):x=np.clip(x,0,1);return x*x*(3-2*x)
rects=[]
for face in guide['faces']:
 p=np.array(face['positions']);edges=[p[(i+1)%3]-p[i] for i in range(3)];e1=max(edges,key=lambda v:np.linalg.norm(v));e1=e1/np.linalg.norm(e1);normal=np.cross(p[1]-p[0],p[2]-p[0]);normal/=np.linalg.norm(normal);e2=np.cross(normal,e1)
 xy=np.stack((p@e1,p@e2),axis=1)*1961;xy-=xy.min(axis=0)
 dims=np.ceil(xy.max(axis=0)).astype(int)+padding*2+1
 rects.append({'face':face,'xy':xy,'width':int(dims[0]),'height':int(dims[1])})
free=[guide['free_atlas_rectangle_px']]
def prune(rs):
 return [r for i,r in enumerate(rs) if not any(i!=j and r[0]>=s[0] and r[1]>=s[1] and r[2]<=s[2] and r[3]<=s[3] for j,s in enumerate(rs))]
for rect in sorted(rects,key=lambda r:max(r['width'],r['height']),reverse=True):
 choices=[]
 for i,(x0,y0,x1,y1) in enumerate(free):
  for rotated in [False,True]:
   rw,rh=(rect['height'],rect['width']) if rotated else (rect['width'],rect['height'])
   if rw<=x1-x0 and rh<=y1-y0:choices.append((min(x1-x0-rw,y1-y0-rh),(x1-x0)*(y1-y0)-rw*rh,i,rotated,rw,rh))
 assert choices,'Upper-lip islands do not fit the verified unused atlas gutter'
 _,_,i,rotated,rw,rh=min(choices);x0,y0,_,_=free[i];placed=[x0,y0,x0+rw,y0+rh];new=[]
 for f in free:
  a,b,c,d=f
  if placed[0]>=c or placed[2]<=a or placed[1]>=d or placed[3]<=b:new.append(f);continue
  if placed[0]>a:new.append([a,b,placed[0],d])
  if placed[2]<c:new.append([placed[2],b,c,d])
  if placed[1]>b:new.append([a,b,c,placed[1]])
  if placed[3]<d:new.append([a,placed[3],c,d])
 free=prune(new);xy=rect['xy'][:,::-1] if rotated else rect['xy'];rect.update(box=placed,packed_xy=xy+np.array([x0+padding,y0+padding]))
changes=0;guides=0;patch_data=[];outside_verified=0;subpixel=0
for rect in rects:
 face=rect['face'];p=np.array(face['positions']);uv=np.array(face['old_uv']);q=rect['packed_xy'];x0,y0,x1,y1=rect['box'];yy,xx=np.mgrid[y0:y1,x0:x1];at=np.stack((xx+.5,yy+.5),axis=-1)
 matrix=np.column_stack((q[1]-q[0],q[2]-q[0]));weights=(at-q[0])@np.linalg.inv(matrix).T;bary=np.concatenate((1-weights.sum(axis=2,keepdims=True),weights),axis=2);inside=np.min(bary,axis=2)>=-1e-6
 if not inside.any():
  cy,cx=np.unravel_index(np.argmin(np.linalg.norm(at-q.mean(axis=0),axis=2)),inside.shape)
  inside[cy,cx]=True;bary[cy,cx]=[1/3,1/3,1/3];subpixel+=1
 points=bary@p;old_uv=bary@uv;ox=np.mod(np.floor(old_uv[:,:,0]*w).astype(int),w);oy=np.mod(np.floor((1-old_uv[:,:,1])*h).astype(int),h);colors=base[oy,ox].copy()
 best=np.full(inside.shape,np.inf);closest=np.zeros_like(points);along_px=np.zeros(inside.shape)
 for segment_index,(a,b) in enumerate(segments):
  edge=b-a;t=np.clip(np.sum((points-a)*edge,axis=2)/np.dot(edge,edge),0,1);hit=a+t[:,:,None]*edge;dist=np.linalg.norm(points-hit,axis=2);use=dist<best;best[use]=dist[use];closest[use]=hit[use]
  if args.pixel_clusters:along_px[use]=arc[segment_index]+t[use]*lengths[segment_index]
 distance_px=best*1961;front=smooth(((closest[:,:,0]+.5)-guide['front_blend_start_u'])/(guide['front_blend_full_u']-guide['front_blend_start_u']))
 band=(distance_px<=guide['source_band_width_px'])&(points[:,:,2]>=closest[:,:,2]-.0003)&inside
 if args.pixel_clusters:
  ci=np.clip(np.floor(along_px/brush).astype(int),0,cell_cols-1);ri=np.clip(np.floor(distance_px/brush).astype(int),0,cell_rows-1)
  # Transition selects whole native brush cells; never interpolates new RGB.
  sc=np.minimum(ci*brush+(brush-1)/2,arc[-1]);cx=np.interp(sc,arc,boundary[:,0])+.5
  cell_front=smooth((cx-guide['front_blend_start_u'])/(guide['front_blend_full_u']-guide['front_blend_start_u']))
  threshold=(((ci*3+ri*5)%7)+.5)/7
  mix=((cell_front>=threshold)&band).astype(float);paint=cells[ri,ci];colors[mix>0]=paint[mix>0]
 else:
  mix=front*band;pi=np.clip(np.rint(distance_px).astype(int),0,len(profile)-1);paint=profile[pi]
  colors[:,:,:3]=np.round(colors[:,:,:3]*(1-mix[:,:,None])+paint[:,:,:3]*mix[:,:,None]).astype('uint8')
 colors[:,:,3]=255
 assert np.array_equal(colors[inside&~band],base[oy,ox][inside&~band]),'Non-lip source colors changed'
 outside_verified+=int((inside&~band).sum());changes+=int((inside&(mix>0)).sum())
 debug=colors.copy();line=inside&(distance_px<=1.5);debug[line]=[20,240,220,255];guides+=int(line.sum())
 # Fill each island gutter from its own valid pixels; no unrelated colors.
 _,labels=cv2.distanceTransformWithLabels((~inside).astype('uint8'),cv2.DIST_L2,5,labelType=cv2.DIST_LABEL_PIXEL);sy,sx=np.where(inside);indices=np.clip(labels-1,0,len(sx)-1)
 colors[~inside]=colors[sy[indices[~inside]],sx[indices[~inside]]];debug[~inside]=debug[sy[indices[~inside]],sx[indices[~inside]]]
 atlas[y0:y1,x0:x1]=colors;marked[y0:y1,x0:x1]=debug
 patch_data.append({'face_index':face['index'],'vertices':face['vertices'],'uv':[[float(x/w),float(1-y/h)] for x,y in q],'box_px':rect['box']})
assert np.array_equal(atlas[:,280:],base[:,280:]),'Original forehead/body atlas pixels outside unused gutter changed'
Image.fromarray(atlas).save(out/'upper-lip-continuous-atlas.png');Image.fromarray(marked).save(out/'upper-lip-marked-atlas.png')
plan={'kind':'nile_upper_lip_material_only','geometry_changes':False,'source_blend':guide['source_blend_sha256'],'source_atlas_sha256':sha(old/'body-atlas-two-dimensional.png'),'source_art_sha256':sha(trial/guide['side_source']),'guide_sha256':sha(guide_path),'source_profile_pixels':profile_xy.tolist(),'source_profile_rgba':profile.tolist(),'source_profile_role':'Historical one-dimensional source reference; pixel-cluster mode samples the full 2D donor field instead.' if args.pixel_clusters else 'Existing left upper-lip inner outline, pale fill, outer outline copied together and continued across the actual anterior lip curve to the right side.','texture_size':[w,h],'new_texture_memory':0,'new_triangles':0,'patches':patch_data,'subpixel_triangles_centroid_baked':subpixel,'painted_native_texels':changes,'guide_native_texels':guides,'unchanged_non_band_texels_verified':outside_verified,'outside_free_gutter_identical':True,'outputs':{name:sha(out/name) for name in ['upper-lip-continuous-atlas.png','upper-lip-marked-atlas.png']}}
if args.pixel_clusters:plan.update(pixel_clusters=True,guide_path=str(guide_path.relative_to(trial)),donor_field=field_data)
write(out/'upper-lip-paint.plan.json',plan)
print(json.dumps({'ok':True,'islands':len(patch_data),'painted_texels':changes,'guide_texels':guides,'atlas_size':[w,h]}))
