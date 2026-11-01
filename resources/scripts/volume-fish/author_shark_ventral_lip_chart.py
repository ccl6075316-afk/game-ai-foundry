"""Native ventral upper/lower lip transport onto a real integrated mouth.

Whole head skin outside the traced lips is a separately declared derived
preview chart. No geometry, skin weights or normals are modified here.
"""
import bpy,bmesh,json,hashlib,math,sys
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).parent))
from rim_material_transport import nearest_arc,native_lip_ownership

args=sys.argv[sys.argv.index('--')+1:];cp=Path(args[0]).resolve();out=Path(args[1]).resolve();assert not out.exists()and'/experiments/'in out.as_posix();out.mkdir();c=json.loads(cp.read_text(encoding='utf8'));src=Path(c['baseline']);bpy.ops.wm.open_mainfile(filepath=str(src/'fish.blend'));ob=bpy.data.objects['Reference_head_body'];mesh=ob.data
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
for item in c['sources'].values():assert sha(item['path'])==item['sha256']
cfg=json.loads(Path(c['reference']).read_text(encoding='utf8'));axis=cfg['reference_body_axis_m'];headspan=cfg['head_span_m'];headdepth=cfg['head_axial_extent_m'];density=c['native_pixels_per_m'];coords=np.array([v.co[:]for v in mesh.vertices]);before=hashlib.sha256(coords.tobytes()+repr([tuple(f.vertices)for f in mesh.polygons]).encode()).hexdigest()
bm=bmesh.new();bm.from_mesh(mesh);bm.verts.ensure_lookup_table();edges=[tuple(v.index for v in e.verts)for e in bm.edges if len(e.link_faces)==2 and any(f.material_index==1 for f in e.link_faces)and any(f.material_index==0 for f in e.link_faces)];bm.free();adj={}
for a,b in edges:adj.setdefault(a,[]).append(b);adj.setdefault(b,[]).append(a)
assert adj and all(len(v)==2 for v in adj.values());lo=min(adj,key=lambda i:coords[i,1]);hi=max(adj,key=lambda i:coords[i,1]);paths=[]
for first in adj[lo]:
    ids=[lo,first]
    while ids[-1]!=hi:
        follow=[i for i in adj[ids[-1]]if i!=ids[-2]];assert len(follow)==1;ids.append(follow[0]);assert len(ids)<=len(adj)
    p=coords[ids];paths.append((p,np.r_[0,np.cumsum(np.linalg.norm(np.diff(p,axis=0),axis=1))]))
paths.sort(key=lambda p:p[0][:,0].mean(),reverse=True);boundaries=dict(zip(['upper','lower'],paths))
images={}
for name,item in c['sources'].items():
    im=bpy.data.images.load(item['path'],check_existing=False);w,h=im.size;images[name]=(w,h,np.array(im.pixels[:]).reshape(h,w,4)[::-1].copy())
skin_tiles={}
for name,item in c.get('derived_preview_skin_tiles',{}).items():
    assert sha(item['path'])==item['sha256'];im=bpy.data.images.load(item['path'],check_existing=False);w,h=im.size;skin_tiles[name]=(w,h,np.array(im.pixels[:]).reshape(h,w,4)[::-1].copy())
gill_pixels=None
if c.get('gill_chart'):
    item=c['gill_chart'];assert sha(item['path'])==item['sha256'];im=bpy.data.images.load(item['path'],check_existing=False);w,h=im.size;gill_pixels=np.array(im.pixels[:]).reshape(h,w,4)[::-1].copy()
assert sha(c['base_donor_map']['path'])==c['base_donor_map']['sha256'];fallback=np.load(c['base_donor_map']['path'])
def sample(name,xy,derived_base=False):
    w,h,a=images[name];i=np.rint(xy).astype(int);i[:,0]=np.clip(i[:,0],0,w-1);i[:,1]=np.clip(i[:,1],0,h-1)
    if derived_base:i=fallback[name][i[:,1],i[:,0]]
    p=a[i[:,1],i[:,0]];assert (p[:,3]>.99).all();return p.copy()
def donor(name,phase,total,distance):
    curve=np.array(c[name+'_source_curve_px'],float);arc=np.r_[0,np.cumsum(np.linalg.norm(np.diff(curve,axis=0),axis=1))];a=np.clip(phase/total,0,1)*arc[-1];xy=np.stack([np.interp(a,arc,curve[:,0]),np.interp(a,arc,curve[:,1])],1);i=np.clip(np.searchsorted(arc,a,side='right')-1,0,len(curve)-2);t=curve[i+1]-curve[i];n=np.stack([t[:,1],-t[:,0]],1);n/=np.linalg.norm(n,axis=1)[:,None]
    if name=='lower':n*=-1
    return xy+n*distance[:,None]
tiles=[];protected=0;native_min=np.array([1e9,1e9]);native_max=np.zeros(2);rows=cfg['body_stations'];head_z=np.mean([(r['top_z_m']+r['bottom_z_m'])/2 for r in rows if r['t']<.15])
hr=cfg['head_transverse_stations'];hy=np.array([r['y_m']for r in hr]);hf=np.array([r['front_x_m']for r in hr]);hb=np.array([r['rear_x_m']for r in hr])
def head_projection(name,points):
    bounds=np.array(c['head_source_row_bounds'][name]);y=bounds[0,0]+(.5-points[:,1]/headspan)*(bounds[-1,0]-bounds[0,0]);y=np.clip(y,bounds[0,0],bounds[-1,0]);lo=np.interp(y,bounds[:,0],bounds[:,1]);hi=np.interp(y,bounds[:,0],bounds[:,2]);front=np.interp(points[:,1],hy,hf);rear=np.interp(points[:,1],hy,hb);q=np.clip((front-points[:,0])/(front-rear),.025,.975);xy=np.stack([hi*(1-q)+lo*q,y],1)
    # Both views use this target's own row/chord map, never per-face repeated tiles.
    # Preview neck is a bounded interior patch until the body chart is made.
    neck=points[:,0]<rear;xy[neck,0]=1780+np.clip((points[neck,0]-.17)/.04,0,1)*24;xy[neck,1]=330+np.clip(points[neck,1]/.03,-1,1)*30
    if name=='ventral':
        old=(xy[:,0]>1698)&(xy[:,0]<1768)&(xy[:,1]>296)&(xy[:,1]<430);xy[old,0]=1780+np.mod(xy[old,0]-1698,24)
    eyes=((xy[:,1]<100)|(xy[:,1]>575))&(xy[:,0]>1800);xy[eyes,0]-=70
    return sample(name,xy,True)
for f in mesh.polygons:
    if f.material_index!=0:continue
    p=coords[list(f.vertices)]
    if p[:,0].max()<c['preview_head_start_x_m']:continue
    ex=p[1]-p[0];ex/=np.linalg.norm(ex);normal=np.cross(p[1]-p[0],p[2]-p[0]);normal/=np.linalg.norm(normal);ey=np.cross(normal,ex);q=np.stack([(p-p[0])@ex,(p-p[0])@ey],1)*density;origin=np.floor(q.min(0))-2;q-=origin;tw,th=np.ceil(q.max(0)+3).astype(int);xx,yy=np.meshgrid(np.arange(tw),np.arange(th));local=np.stack([xx.ravel(),yy.ravel()],1);M=np.column_stack([q[1]-q[0],q[2]-q[0]]);b=np.c_[np.ones(len(local)),(local-q[0])@np.linalg.inv(M).T];b[:,0]-=b[:,1:].sum(1);b=np.maximum(b,0);b/=b.sum(1)[:,None];points=b@p
    xy=np.stack([c['source_head_front_px']-(axis/2-points[:,0])/headdepth*c['source_head_depth_px'],c['source_head_center_y_px']-points[:,1]/headspan*c['source_head_span_px']],1)
    # Remove only the old drawn mouth from the base before transporting it.
    # Eyes/outer contour are pending separate ownership; use interior skin there.
    if skin_tiles:
        shades={}
        for name,(w,h,a)in skin_tiles.items():
            ix=np.floor(np.mod(points[:,0]*density,w)).astype(int)%w;iy=np.floor(np.mod(points[:,1]*density,h)).astype(int)%h;shades[name]=a[iy,ix]
        bottom=shades['ventral'];top=shades['dorsal']
    else:bottom=head_projection('ventral',points);top=head_projection('dorsal',points)
    # Outside lips this is a color interpolation, not an exact native-pixel claim.
    body_mid=np.interp((axis/2-points[:,0])/axis,[r['t']for r in rows],[(r['top_z_m']+r['bottom_z_m'])/2 for r in rows]);mix=np.clip((points[:,0]-.19)/.045,0,1);mid=body_mid*(1-mix)+head_z*mix;g=np.clip((points[:,2]-mid)/.009+.5,0,1);g=g*g*(3-2*g);base=bottom*(1-g[:,None])+top*g[:,None]
    if gill_pixels is not None:
        t=(axis/2-points[:,0])/axis;ts=[r['t']for r in rows];body_top=np.interp(t,ts,[r['top_z_m']for r in rows]);body_bottom=np.interp(t,ts,[r['bottom_z_m']for r in rows]);halfwidth=np.interp(t,ts,[r['full_width_m']/2 for r in rows]);fraction=(body_top-points[:,2])/np.maximum(body_top-body_bottom,1e-8);sx=1624-(t-.16)/(.216-.16)*96;sy=314+(fraction-.25)/(.88-.25)*80;ix=np.clip(np.rint(sx).astype(int),0,gill_pixels.shape[1]-1);iy=np.clip(np.rint(sy).astype(int),0,gill_pixels.shape[0]-1);paint=gill_pixels[iy,ix];lateral=np.clip((abs(points[:,1])/np.maximum(halfwidth,1e-9)-.45)/.20,0,1);lateral=lateral*lateral*(3-2*lateral);weight=paint[:,3]*lateral;weight[(t<.145)|(t>.231)]=0;base[:,:3]=base[:,:3]*(1-weight[:,None])+paint[:,:3]*weight[:,None]
    near={name:nearest_arc(points,boundary)for name,boundary in boundaries.items()};upper=near['upper'][0]<=near['lower'][0];distance=np.where(upper,near['upper'][0],near['lower'][0])*density;width=np.where(upper,c['lip_domain']['upper_width_px'],c['lip_domain']['lower_width_px']);weight=native_lip_ownership(distance,width,c['lip_domain']['outer_fade_px']);protected+=int((distance<=width).sum())
    for name in ['upper','lower']:
        take=(upper if name=='upper'else~upper)&(weight>0)
        if not take.any():continue
        xy=donor(name,near[name][1][take],boundaries[name][1][-1],distance[take]);native=sample('ventral',xy);a=weight[take,None];base[take]=base[take]*(1-a)+native*a;native_min=np.minimum(native_min,xy.min(0));native_max=np.maximum(native_max,xy.max(0))
    assert np.all(weight[distance<=width]==1)
    tiles.append(dict(face=f.index,q=q,w=int(tw),h=int(th),pixels=base.reshape(th,tw,4)))
aw=2048;x=y=3;row=0
for t in tiles:
    if x+t['w']+3>aw:x=3;y+=row+3;row=0
    t['at']=(x,y);x+=t['w']+3;row=max(row,t['h'])
ah=2**math.ceil(math.log2(y+row+3));atlas=np.ones((ah,aw,4),np.float32)
for t in tiles:x,y=t['at'];atlas[y:y+t['h'],x:x+t['w']]=t['pixels']
im=bpy.data.images.new('Ventral native lips and declared derived head preview',aw,ah,alpha=True);im.colorspace_settings.name='sRGB';im.pixels.foreach_set(atlas.ravel());im.pack();material=mesh.materials[0].copy();material.name='Native ventral lip ownership; derived head preview';next(n for n in material.node_tree.nodes if n.type=='TEX_IMAGE').image=im;mesh.materials.append(material);slot=len(mesh.materials)-1;uv=mesh.uv_layers.active or mesh.uv_layers.new(name='UVMap')
for t in tiles:
    f=mesh.polygons[t['face']];f.material_index=slot
    for li,q in zip(f.loop_indices,t['q']):uv.data[li].uv=((q[0]+t['at'][0]+.5)/aw,(q[1]+t['at'][1]+.5)/ah)
after=hashlib.sha256(np.array([v.co[:]for v in mesh.vertices]).tobytes()+repr([tuple(f.vertices)for f in mesh.polygons]).encode()).hexdigest();assert before==after and protected>0
bpy.ops.object.select_all(action='DESELECT');ob.select_set(True);bpy.context.view_layer.objects.active=ob;bpy.ops.wm.save_as_mainfile(filepath=str(out/'fish.blend'));bpy.ops.export_scene.gltf(filepath=str(out/'fish.glb'),export_format='GLB',use_selection=True,export_animations=True,export_yup=True,export_def_bones=False);(out/'fin-authoring.json').write_bytes((src/'fin-authoring.json').read_bytes())
r=dict(ok=True,kind='complete_anterior_semantic_color_chart',species='scalloped_hammerhead',source_sha256=c['sources']['ventral']['sha256'],model_sha256=sha(out/'fish.glb'),geometry_weights_triangles_unchanged=True,actual_3d_rim_transport={k:dict(points=len(v[0]),length_m=float(v[1][-1]))for k,v in boundaries.items()},complete_native_lip_ownership=dict(protected_texels=protected,maximum_front_weight_inside_complete_lip=0,maximum_central_weight_inside_complete_lip=0,domain=c['lip_domain'],native_donor_min_px=native_min.tolist(),native_donor_max_px=native_max.tolist()),atlas_size=[aw,ah],body_preview_scope='Derived skin preview only, no native-pixel claim outside traced lip/gill domain. De-lit donor records identify modified RGB. Native eye/fin stages separate.',derived_skin=c.get('derived_preview_skin_tiles'),native_five_gill_chart=c.get('gill_chart'),config_sha256=sha(cp),formal_acceptance=False,visual_review='pending');(out/'authoring.validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
