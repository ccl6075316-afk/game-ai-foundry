"""Blender: semantic front color chart on the existing complete anterior surface.

An experimental color-only source step. No geometry, weights or fin edits.
The source image must be reviewed separately before a production adoption.
Unlike a thin lip strip, this chart covers the frontal jaw/chin surface.
"""
import argparse,hashlib,json,math,sys
from pathlib import Path
import bpy,bmesh,numpy as np
ROOT=Path(__file__).resolve().parents[3]
sys.path[:0]=[str(ROOT/'cli'),str(Path(__file__).parent)]
from export_source_with_frozen_normals import export_guarded,EXACT_NORMAL_ATTRIBUTE
from patch_existing_fin_meshes import read as read_glb,write as write_glb
from triangulate_export_mesh import triangulate_export_mesh
from rim_material_transport import ordered_boundary,nearest_arc,side_curve_donor,bounded_roi_coordinates,native_lip_ownership
from interocular_material_mask import target_eye_material_allowance
from native_body_skin_transport import native_skin_spans,native_roof_coordinates
from fish_budget import check_triangle_budget
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text(encoding='utf8'))
p=argparse.ArgumentParser()
for name in ['blend','config','output']:p.add_argument('--'+name,type=Path,required=True)
a=p.parse_args(sys.argv[sys.argv.index('--')+1:]);cfg=read(a.config);out=a.output.resolve()
assert out.is_relative_to(ROOT/'projects/fishing-2d/experiments')and not out.exists()
assert sha(a.blend)==cfg['blend_sha256']
bpy.ops.wm.open_mainfile(filepath=str(a.blend.resolve()))
body=bpy.data.objects[cfg['body']];assert EXACT_NORMAL_ATTRIBUTE not in body.data.attributes
triangulate_export_mesh(body);mesh=body.data
def fingerprint():return hashlib.sha256(repr([(o.name,[(tuple(v.co),[(g.group,g.weight)for g in v.groups])for v in o.data.vertices],[tuple(f.vertices)for f in o.data.polygons])for o in bpy.data.objects if o.type=='MESH']).encode()).hexdigest()
frozen=fingerprint();coords=np.asarray([v.co[:]for v in mesh.vertices]);uv=np.asarray([u.uv[:]for u in mesh.uv_layers.active.data])
image=next(n.image for n in mesh.materials[0].node_tree.nodes if n.type=='TEX_IMAGE');W,H=image.size;pixels=np.asarray(image.pixels[:]).reshape(H,W,4)
donor_path=ROOT/cfg['front_color_image']['path'];assert sha(donor_path)==cfg['front_color_image']['sha256']
donor=bpy.data.images.load(str(donor_path),check_existing=False);donor.pack();FW,FH=donor.size;dp=np.asarray(donor.pixels[:]).reshape(FH,FW,4)
sections=read(ROOT/cfg['profile'])['body']['sections']
roof_spans=native_skin_spans(pixels,read(ROOT/cfg['profile']))if cfg.get('body_roof_material')else None
roof_proof={'sample_count':0,'source_min_px':[1e10,1e10],'source_max_px':[-1e10,-1e10],'pixel_density_min':1e10,'pixel_density_max':0.}
bm=bmesh.new();bm.from_mesh(mesh);bm.normal_update();bm.verts.ensure_lookup_table();chains={};edge_ids={}
for name,sign in [('upper',-1),('lower',1)]:
 edges=[]
 for e in bm.edges:
  if len(e.link_faces)==2 and any(f.material_index==0 for f in e.link_faces)and any(f.material_index==1 and f.normal.z*sign>.1 for f in e.link_faces):edges.append(tuple(v.index for v in e.verts))
 assert edges
 edge_ids[name]=edges
 chains[name]=np.asarray([(coords[u],coords[v])for u,v in edges])
bm.free()
transport={name:ordered_boundary(coords,edges)for name,edges in edge_ids.items()}if cfg.get('lip_source_transport')else{}
central_boundaries={name:ordered_boundary(coords,edges)for name,edges in edge_ids.items()}if cfg.get('interocular_material',{}).get('preserve_mouth_rim_px')else{}
central=None;central_count=0;central_min=np.array([np.inf,np.inf]);central_max=np.array([-np.inf,-np.inf])
lip_proof={'protected_texels':0,'maximum_front_weight_inside_complete_lip':0.,'maximum_central_weight_inside_complete_lip':0.,'native_donor_min_px':[1e10,1e10],'native_donor_max_px':[-1e10,-1e10]}
if cfg.get('interocular_material'):
 c=cfg['interocular_material'];cp=ROOT/c['image']['path'];assert sha(cp)==c['image']['sha256']
 ci=bpy.data.images.load(str(cp),check_existing=False);ci.pack();CW,CH=ci.size;central=np.asarray(ci.pixels[:]).reshape(CH,CW,4)
 bounded_roi_coordinates(np.array([0.,1.]),np.array([0.,1.]),c['roi_px'],[CW,CH])
camera=cfg['front_camera'];scale=camera['model_scale'];width=camera['width_m'];height=width*camera['aspect_h_over_w']
smooth=lambda v:np.clip(v,0,1)**2*(3-2*np.clip(v,0,1))
def actual_rim_z(y,name):
 segs=chains[name];answer=np.full(len(y),-np.inf)
 for edge in segs:
  y0,y1=edge[:,1];delta=y1-y0
  if abs(delta)<1e-9:continue
  t=(y-y0)/delta;valid=(t>=0)&(t<=1)
  z=edge[0,2]+t*(edge[1,2]-edge[0,2]);answer=np.where(valid,np.maximum(answer,z),answer)
 # Outside the mouth's transverse extent use its corner continuation, not a
 # different specimen's width or a generated geometric outline.
 missing=~np.isfinite(answer)
 if missing.any():
  ends=segs.reshape(-1,3);j=np.abs(y[missing,None]-ends[:,1]).argmin(axis=1);answer[missing]=ends[j,2]
 return answer
def color(points,old_uv,role,surface_normal):
 global central_count,central_min,central_max
 original=pixels[np.clip((old_uv[:,1]*H).astype(int),0,H-1),np.clip((old_uv[:,0]*W).astype(int),0,W-1)]
 if roof_spans is not None and role==0:
  rxy,ra,density=native_roof_coordinates(points,sections,W,H,roof_spans,cfg['body_roof_material']);take=ra>.001
  if take.any():
   assert np.isfinite(rxy[take]).all();safe=np.nan_to_num(rxy,nan=0);rix=np.rint(safe).astype(int);rix[:,0]=np.clip(rix[:,0],0,W-1);rix[:,1]=np.clip(rix[:,1],0,H-1);rp=pixels[H-1-rix[:,1],rix[:,0]];assert (rp[take,3]>.95).all(),'Body roof donor must be opaque native skin'
   ra=np.where(take,ra,0);original=original*(1-ra[:,None])+rp*ra[:,None]
   roof_proof['sample_count']+=int(take.sum());roof_proof['source_min_px']=np.minimum(roof_proof['source_min_px'],rxy[take].min(axis=0)).tolist();roof_proof['source_max_px']=np.maximum(roof_proof['source_max_px'],rxy[take].max(axis=0)).tolist();roof_proof['pixel_density_min']=min(roof_proof['pixel_density_min'],float(density[take].min()));roof_proof['pixel_density_max']=max(roof_proof['pixel_density_max'],float(density[take].max()))
 u=points[:,0]+.5;w=np.interp(u,[s[0]for s in sections],[s[3]for s in sections]);side=np.abs(points[:,1])/np.maximum(w,1e-7)
 lip_zone=None;lip_near=None;lip_choose=None;lip_core=None
 if transport and role==0 and cfg['lip_source_transport'].get('complete_native_lip'):
  c=cfg['lip_source_transport']['complete_native_lip'];lip_near={name:nearest_arc(points,b)for name,b in transport.items()};lip_choose=lip_near['upper'][0]<=lip_near['lower'][0]
  distance=np.where(lip_choose,lip_near['upper'][0],lip_near['lower'][0])*W
  widths=np.where(lip_choose,c['upper_width_px'],c['lower_width_px']);lip_zone=native_lip_ownership(distance,widths,c['outer_fade_px']);lip_core=distance<=widths
 x=.5+points[:,1]*scale/width;fx=x*FW
 upper=actual_rim_z(points[:,1],'upper');lower=actual_rim_z(points[:,1],'lower')
 gy={}
 for name in ['upper','lower']:
  curve=np.asarray(cfg['front_'+name+'_edge_px']);gy[name]=np.interp(fx,curve[:,0],curve[:,1])
 z=points[:,2];upper_y=gy['upper'];lower_y=gy['lower'];native_pixels_per_z=scale/height*FH
 y=np.where(z>=upper,upper_y+(upper-z)*native_pixels_per_z*cfg.get('upper_exterior_scale',1.),
    np.where(z<=lower,lower_y+(lower-z)*native_pixels_per_z*cfg.get('lower_exterior_scale',1.),
      upper_y+(upper-z)/np.maximum(upper-lower,1e-8)*(lower_y-upper_y)))
 if role==1:
  # Finite interior is actual geometry. Keep its color in the reviewed oral
  # donor interval, preventing an exterior cheek sample on a deep wall.
  y=np.clip(y,upper_y+.18*(lower_y-upper_y),lower_y-.18*(lower_y-upper_y))
  if cfg.get('oral_depth_u'):
   back,front=cfg['oral_depth_u'];depth=np.clip((front-u)/(front-back),0,1)
   fraction=.18+.27*depth if surface_normal[2]<0 else .82-.27*depth
   y=upper_y+fraction*(lower_y-upper_y)
 valid=(fx>=0)&(fx<FW)&(y>=0)&(y<FH)
 xy=np.stack([np.clip(np.rint(fx),0,FW-1),np.clip(np.rint(y),0,FH-1)],axis=1).astype(int)
 rgba=dp[FH-1-xy[:,1],xy[:,0]]
 if role==1 and cfg.get('oral_material_roi_px'):
  # Mouth-wall color has its own measured donor domain. Projecting the full
  # head width into a small reference aperture otherwise samples white cheeks
  # onto the roof/floor and stretches the lip outline through the cavity.
  back,front=cfg['oral_depth_u']
  depth=np.clip((front-u)/(front-back),0,1)
  across=.5+.5*points[:,1]/np.maximum(w,1e-7)
  if cfg.get('oral_material_depth_reverse'):depth=1-depth
  oral_xy=bounded_roi_coordinates(across,depth,cfg['oral_material_roi_px'],[FW,FH])
  oral_xy=np.rint(oral_xy).astype(int)
  rgba=dp[FH-1-oral_xy[:,1],oral_xy[:,0]]
  valid=np.ones(len(points),dtype=bool)
 amount=smooth((u-cfg['front_start_u'])/(cfg['front_full_u']-cfg['front_start_u']))*(1-smooth((side-cfg['side_full'])/(cfg['side_original']-cfg['side_full'])))
 # Preserve the side surface but include the actual rounded anterior cap.
 cap=smooth((u-cfg['cap_start_u'])/(cfg['cap_full_u']-cfg['cap_start_u']))
 amount=np.maximum(amount,cap)
 if role==1:amount=np.ones(len(points))
 if role==0 and cfg.get('protect_source_eyes_in_front_material'):
  c=cfg['interocular_material'];support=c['target_eye_lateral_support']
  source_xy=np.stack([old_uv[:,0]*W,(1-old_uv[:,1])*H],axis=1)
  amount*=target_eye_material_allowance(source_xy,side,c['protected_target_source_rects_px'],c['target_protection_fade_px'],support['start'],support['full'])
 amount*=valid
 if lip_zone is not None:
  amount*=1-lip_zone
  lip_proof['protected_texels']+=int(lip_core.sum());lip_proof['maximum_front_weight_inside_complete_lip']=max(lip_proof['maximum_front_weight_inside_complete_lip'],float(amount[lip_core].max(initial=0)))
 bad=(amount>.001)&(rgba[:,3]<.95)
 assert not np.any(bad),{'failure':'front donor samples transparent pixels','role':role,'donor_xy_px':(oral_xy if role==1 and cfg.get('oral_material_roi_px')else xy)[bad][:10].tolist(),'source_u':u[bad][:10].tolist()}
 result=original*(1-amount[:,None])+rgba*amount[:,None];result[:,3]=1
 if central is not None and role==0:
  # Only the explicitly allowed material BETWEEN the eyes. No generated eye,
  # lateral cheek, head outline or mouth coordinates enter this branch.
  c=cfg['interocular_material'];v=.5-points[:,2]/(H/W)
  xf=.5+.5*points[:,1]/np.maximum(w,1e-7)
  yf=(v-c['source_v_top'])/(c['source_v_bottom']-c['source_v_top'])
  cxy=bounded_roi_coordinates(xf,yf,c['roi_px'],[CW,CH]);ix=np.rint(cxy).astype(int)
  ca=smooth((u-c['head_start_u'])/(c['head_full_u']-c['head_start_u']))*(1-smooth((side-c['side_full'])/(c['side_original']-c['side_full'])))*(1-smooth((v-c['source_v_fade_start'])/(c['source_v_fade_end']-c['source_v_fade_start'])))
  if c.get('target_eye_lateral_support'):
   support=c['target_eye_lateral_support'];source_xy=np.stack([old_uv[:,0]*W,(1-old_uv[:,1])*H],axis=1)
   ca*=target_eye_material_allowance(source_xy,side,c.get('protected_target_source_rects_px',[]),c.get('target_protection_fade_px',12),support['start'],support['full'])
  else:
   for x0,y0,x1,y1 in c.get('protected_target_source_rects_px',[]):
    source_x=old_uv[:,0]*W;source_y=(1-old_uv[:,1])*H
    distance=np.hypot(np.maximum(np.maximum(x0-source_x,source_x-x1),0),np.maximum(np.maximum(y0-source_y,source_y-y1),0))
    ca*=smooth(distance/c.get('target_protection_fade_px',12))
  if central_boundaries:
   rim_distance=np.minimum.reduce([nearest_arc(points,b)[0]for b in central_boundaries.values()])*W
   ca*=smooth((rim_distance-c['preserve_mouth_rim_px'])/c['mouth_protection_fade_px'])
  if lip_zone is not None:
   ca*=1-lip_zone;lip_proof['maximum_central_weight_inside_complete_lip']=max(lip_proof['maximum_central_weight_inside_complete_lip'],float(ca[lip_core].max(initial=0)))
  take=ca>.001
  if take.any():central_count+=int(take.sum());central_min=np.minimum(central_min,cxy[take].min(axis=0));central_max=np.maximum(central_max,cxy[take].max(axis=0))
  result=result*(1-ca[:,None])+central[CH-1-ix[:,1],ix[:,0]]*ca[:,None]
 if transport and(role==0 or cfg['lip_source_transport'].get('inner_lip_return_px',0)>0 or cfg['lip_source_transport'].get('transport_oral',False)):
  c=cfg['lip_source_transport'];near=lip_near or{name:nearest_arc(points,b)for name,b in transport.items()};choose=lip_choose if lip_choose is not None else near['upper'][0]<=near['lower'][0]
  for name,flag in [('upper',True),('lower',False)]:
   mask=choose==flag
   if not mask.any():continue
   distance,phase=near[name];curve=np.asarray(cfg[name+'_inner_edge_px'],float);curve=curve[(curve[:,0]>=c['source_start_x'])&(curve[:,0]<=c['source_end_x'])];assert len(curve)>=3
   d=distance[mask]*W;across=d if role==0 else d*c.get('inner_lip_source_across_scale',.5)
   xy=side_curve_donor(phase[mask],transport[name][1][-1],across,curve,name=='upper')
   if role==0:
    if lip_zone is not None:a=lip_zone[mask]
    else:
     a=(1-smooth((d-(c['skin_band_px']-c['blend_px']))/c['blend_px']))*smooth((u[mask]-c.get('surface_start_u',.905))/c.get('surface_start_fade_u',.025))
     a*=np.maximum(1-smooth((side[mask]-c['side_full'])/(c['side_original']-c['side_full'])),smooth((u[mask]-c['cap_start_u'])/(c['cap_full_u']-c['cap_start_u'])))
   elif c.get('transport_oral',False):
    sx=xy[:,0];up=np.asarray(cfg['upper_inner_edge_px']);lo=np.asarray(cfg['lower_inner_edge_px']);depth=np.clip(d/18,0,1)
    xy[:,1]=np.interp(sx,up[:,0],up[:,1])+(np.interp(sx,lo[:,0],lo[:,1])-np.interp(sx,up[:,0],up[:,1]))*(.3+.4*depth)
    a=np.ones(len(d))
   else:
    a=1-smooth((d-c['inner_lip_return_px'])/c['inner_lip_fade_px'])
   ix=np.rint(xy).astype(int);inside=(ix[:,0]>=0)&(ix[:,0]<W)&(ix[:,1]>=0)&(ix[:,1]<H)
   assert not np.any((a>.001)&~inside),'Active lip sample outside own source'
   ix[:,0]=np.clip(ix[:,0],0,W-1);ix[:,1]=np.clip(ix[:,1],0,H-1);rgba=pixels[H-1-ix[:,1],ix[:,0]]
   invalid=(a>.001)&(rgba[:,3]<.95)
   assert not invalid.any(),('Active lip sample lacks opaque skin',name,role,ix[invalid][:12].tolist())
   if lip_zone is not None and(a>.001).any():
    lip_proof['native_donor_min_px']=np.minimum(lip_proof['native_donor_min_px'],xy[a>.001].min(axis=0)).tolist();lip_proof['native_donor_max_px']=np.maximum(lip_proof['native_donor_max_px'],xy[a>.001].max(axis=0)).tolist()
   result[mask]=result[mask]*(1-a[:,None])+rgba*a[:,None]
 result[:,3]=1
 return result
tiles=[]
for f in mesh.polygons:
 role=f.material_index;assert role in [0,1];co=coords[list(f.vertices)]
 if role==0 and co[:,0].max()+.5<cfg.get('chart_start_u',cfg['front_start_u']):
  if roof_spans is None or not(native_roof_coordinates(co,sections,W,H,roof_spans,cfg['body_roof_material'])[1]>.001).any():continue
 axis=co[1]-co[0];axis/=np.linalg.norm(axis);normal=np.cross(co[1]-co[0],co[2]-co[0]);normal/=np.linalg.norm(normal);other=np.cross(normal,axis)
 q=np.stack([(co-co[0])@axis,(co-co[0])@other],axis=1)*W;low=np.floor(q.min(axis=0))-3;high=np.ceil(q.max(axis=0))+3;tw,th=(high-low+1).astype(int)
 assert tw*th<400000
 yy,xx=np.mgrid[:th,:tw];plane=np.stack([xx.ravel()+low[0],yy.ravel()+low[1]],axis=1)
 v=(plane-q[0])@np.linalg.inv(np.stack([q[1]-q[0],q[2]-q[0]],axis=1)).T
 bary=np.stack([1-v.sum(axis=1),v[:,0],v[:,1]],axis=1);bary=np.maximum(bary,0);bary/=bary.sum(axis=1)[:,None]
 texels=color(bary@co,bary@uv[list(f.loop_indices)],role,normal).reshape(th,tw,4)
 tiles.append({'face':f.index,'role':role,'q':q-low,'w':tw,'h':th,'pixels':texels})
aw=1024;px=3;py=3;row=0
for t in tiles:
 if px+t['w']+3>aw:px=3;py+=row+3;row=0
 t['at']=(px,py);px+=t['w']+3;row=max(row,t['h'])
ah=2**math.ceil(math.log2(py+row+3));atlas=np.ones((ah,aw,4),dtype='float32')
for t in tiles:x,y=t['at'];atlas[y:y+t['h'],x:x+t['w']]=t['pixels']
chart=bpy.data.images.new('Complete anterior mouth color chart',aw,ah,alpha=True);chart.colorspace_settings.name=image.colorspace_settings.name;chart.pixels.foreach_set(atlas.ravel());chart.pack()
for role in [0,1]:
 mat=mesh.materials[0].copy();mat.name='Front skin source chart'if role==0 else'Front mouth oral chart';next(n for n in mat.node_tree.nodes if n.type=='TEX_IMAGE').image=chart;mesh.materials.append(mat)
for t in tiles:
 f=mesh.polygons[t['face']];f.material_index=2+t['role']
 for li,q in zip(f.loop_indices,t['q']):mesh.uv_layers.active.data[li].uv=((q[0]+t['at'][0]+.5)/aw,(q[1]+t['at'][1]+.5)/ah)
assert fingerprint()==frozen
out.mkdir();bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(out/'fish.blend'))
model=out/'fish.glb'
if any(o.type=='MESH'and EXACT_NORMAL_ATTRIBUTE in o.data.attributes for o in bpy.data.objects):
 proof=export_guarded(model)
else:
 bpy.ops.export_scene.gltf(filepath=str(model),export_format='GLB',export_animations=True,export_yup=True,export_skins=True)
 proof={'mode':'ordinary_new_source','scope':'Ordinary source, no frozen-normal stream to restore; final source/cold parity and real gates remain required.'}
d,b=read_glb(model)
for node in d['nodes']:
 if 'mesh'not in node:continue
 for pr in d['meshes'][node['mesh']]['primitives']:
  mat=d['materials'][pr['material']];mat.update(alphaMode='OPAQUE'if node['name']==cfg['body']else'MASK',doubleSided=False)
  if mat['alphaMode']=='MASK':mat['alphaCutoff']=.5
for s in d['samplers']:s.update(magFilter=9728,minFilter=9728)
write_glb(model,d,b);node=next(n for n in d['nodes']if n.get('name')==cfg['body'])
roles={str(i):('mouth'if 'oral'in d['materials'][pr['material']].get('name','').lower()else'body_skin')for i,pr in enumerate(d['meshes'][node['mesh']]['primitives'])}
triangles=sum(d['accessors'][pr['indices']]['count']//3 for m in d['meshes']for pr in m['primitives']);budget=check_triangle_budget(triangles,read(ROOT/cfg['profile'])['real_length_cm'],cfg['hard_triangles'])
report={'ok':True,'kind':'complete_anterior_semantic_color_chart','input_blend_sha256':sha(a.blend),'config_sha256':sha(a.config),'image_sha256':sha(donor_path),'geometry_weights_triangles_unchanged':True,'whole_fish_triangles':triangles,'triangle_budget':budget,'body_surface_roles':roles,'atlas_size':[aw,ah],'normal_export':proof,'model_sha256':sha(model),'blend_sha256':sha(out/'fish.blend'),'visual_review':'pending','scope':'Experimental full anterior chart using actual upper/lower mesh rims and reviewed color donor; no generated geometry, added mesh or runtime patch.'}
report.update(species=read(ROOT/cfg['profile'])['species'],source_sha256=cfg['source_sha256'])
if transport:report['actual_3d_rim_transport']={'upper_edges':len(edge_ids['upper']),'lower_edges':len(edge_ids['lower']),'source':'own original side curve and complete across-lip pixels','no_transverse_only_height_collapse':True,'geometry_changed':False}
if lip_proof['protected_texels']:
 assert lip_proof['maximum_front_weight_inside_complete_lip']==0 and lip_proof['maximum_central_weight_inside_complete_lip']==0
 report['complete_native_lip_ownership']=dict(lip_proof,domain=cfg['lip_source_transport']['complete_native_lip'],scope='Actual baked texel contribution, native lip transport crosses center. Semantic domain still requires real source/material image review.')
if roof_proof['sample_count']:report['native_body_roof_material']=dict(roof_proof,parameters=cfg['body_roof_material'],native_side_UV_unchanged=True,scope='Native side-skin 2D donor baked per surface texel; finite source spans exclude median-fin polygons. No global dark-color removal, generated material or geometry edits. Actual pixel style and transitions still require review.')
if central is not None:
 assert central_count>0
 report['restricted_generated_material']={'image':cfg['interocular_material']['image'],'allowed_roi_px':cfg['interocular_material']['roi_px'],'actual_sample_min_px':central_min.tolist(),'actual_sample_max_px':central_max.tolist(),'sample_count':central_count,'generated_eye_lateral_mouth_samples':0,'scope':'Strict central interocular donor only, no generated geometry.'}
(out/'authoring.validation.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf8');print(json.dumps({'ok':True,'triangles':triangles,'roles':roles,'atlas':[aw,ah]}))
