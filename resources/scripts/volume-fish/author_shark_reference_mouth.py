"""Photo-ratio side envelope and integrated native lip material, author time.

Keeps the accepted transverse envelope, original eyes, finite jaw cut and rig.
Only own traced source lip pixels cross the complete 3D rim; auxiliary front
skin is excluded inside that domain. New source/cold and actual reviews needed.
"""
import bpy,bmesh,json,sys,math,hashlib
from pathlib import Path
import numpy as np
from mathutils import Vector
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE));from rim_material_transport import ordered_boundary,nearest_arc,side_curve_donor,native_lip_ownership
args=sys.argv[sys.argv.index('--')+1:];cp=Path(args[0]).resolve();out=Path(args[1]).resolve();cfg=json.loads(cp.read_text(encoding='utf8'));src=Path(cfg['baseline']);assert not out.exists()and'/experiments/'in out.as_posix();out.mkdir();bpy.ops.wm.open_mainfile(filepath=str(src/'fish.blend'));body=bpy.data.objects['Closed_body'];mesh=body.data
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def geometry():return hashlib.sha256(repr([(o.name,[(tuple(v.co),[(g.group,g.weight)for g in v.groups])for v in o.data.vertices],[tuple(f.vertices)for f in o.data.polygons])for o in bpy.data.objects if o.type=='MESH']).encode()).hexdigest()
coords=np.array([v.co[:]for v in mesh.vertices]);tris=[tuple(f.vertices)for f in mesh.polygons];oral={i for f in mesh.polygons if f.material_index==1 for i in f.vertices};bm=bmesh.new();bm.from_mesh(mesh);bm.verts.ensure_lookup_table();rimedges=[tuple(v.index for v in e.verts)for e in bm.edges if len(e.link_faces)==2 and any(f.material_index==1 for f in e.link_faces)and any(f.material_index!=1 for f in e.link_faces)];bm.free();boundary=np.array([coords[i]for e in rimedges for i in e]);radius=cfg['mouth_shift_fade_native'];oldlo,oldhi=cfg['mouth_x_bounds_before'];newlo,newhi=cfg['mouth_x_bounds_after'];moved=[]
for v in mesh.vertices:
 p=v.co.copy();d=float(np.linalg.norm(boundary-np.array(p),axis=1).min());t=np.clip(d/radius,0,1);gain=1 if v.index in oral else 1-t*t*(3-2*t)
 if cfg.get('material_only',False):gain=0
 target=newlo+(p.x-oldlo)*(newhi-newlo)/(oldhi-oldlo)
 if gain>0:v.co.x=p.x+(target-p.x)*gain;moved.append(v.index)
# Exact outer section, using all body triangle/plane intersections.
def section(x):
 values=[]
 for ids in tris:
  for a,b in zip(ids,ids[1:]+ids[:1]):
   p,q=coords[a],coords[b]
   if abs(p[0]-x)<1e-8:values.append(p[2])
   if(p[0]-x)*(q[0]-x)<0:values.append(p[2]+(q[2]-p[2])*(x-p[0])/(q[0]-p[0]))
 assert values;return min(values),max(values)
h=cfg['head_side'];nose=h['nose_u'];eye=h['eye_u'];photo=np.array(h['stations_px']);e_low,e_high=section(eye-.5);pixel_scale=(e_high-e_low)/(photo[-1,2]-photo[-1,1]);eye_mid=(e_low+e_high)/2;frozen=[]
for v in mesh.vertices:
 if cfg.get('material_only',False):break
 u=v.co.x+.5
 if u<eye:continue
 px=h['nose_px'][0]+(nose-u)/(nose-eye)*(h['eye_px'][0]-h['nose_px'][0]);a=np.interp(px,photo[:,0],photo[:,1]);b=np.interp(px,photo[:,0],photo[:,2]);top=eye_mid-(a-h['eye_px'][1])*pixel_scale;bottom=eye_mid-(b-h['eye_px'][1])*pixel_scale;lo,hi=section(min(u,nose-1e-7)-.5);center=(lo+hi)/2;r=(v.co.z-center)/max((hi-lo)/2,1e-8);v.co.z=(top+bottom)/2+r*(top-bottom)/2;frozen.append([u,top,bottom])
bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));assert all(len(e.link_faces)==2 for e in bm.edges);bm.to_mesh(mesh);bm.free();mesh.update();before_material=geometry();coords=np.array([v.co[:]for v in mesh.vertices]);bm=bmesh.new();bm.from_mesh(mesh);bm.normal_update();bm.verts.ensure_lookup_table();edge_ids={}
for name,sign in [('upper',-1),('lower',1)]:edge_ids[name]=[tuple(v.index for v in e.verts)for e in bm.edges if len(e.link_faces)==2 and any(f.material_index!=1 for f in e.link_faces)and any(f.material_index==1 and f.normal.x*sign>.1 for f in e.link_faces)]
bm.free();transport={k:ordered_boundary(coords,edges)for k,edges in edge_ids.items()};uv=mesh.uv_layers.active;image=next(n.image for n in mesh.materials[0].node_tree.nodes if n.type=='TEX_IMAGE');W,H=image.size;pixels=np.array(image.pixels[:]).reshape(H,W,4);native=bpy.data.images.load(cfg['source']['path'],check_existing=False);SW,SH=native.size;sp=np.array(native.pixels[:]).reshape(SH,SW,4);domain=cfg['lip_domain'];tiles=[];protected=0;range_min=np.array([SW,SH]);range_max=np.array([0,0]);max_aux=0.
skin_slots={}
for slot in[0,2]:
 if slot>=len(mesh.materials):continue
 im=next(n.image for n in mesh.materials[slot].node_tree.nodes if n.type=='TEX_IMAGE');w,h=im.size;skin_slots[slot]=(w,h,np.array(im.pixels[:]).reshape(h,w,4))
old_lip_faces={f.index for f in mesh.polygons if f.material_index==2}
for face in mesh.polygons:
 if face.material_index not in skin_slots:continue
 W,H,pixels=skin_slots[face.material_index]
 ids=list(face.vertices);p=coords[ids];mid=p.mean(0);d=min(nearest_arc(np.array([mid]),v)[0][0]for v in transport.values());r=max(np.linalg.norm(p-mid,axis=1))
 if face.material_index==0 and(d-r)*SW>max(domain['upper_width_px'],domain['lower_width_px'])+domain['outer_fade_px']:continue
 olduv=np.array([uv.data[li].uv[:]for li in face.loop_indices]);q=olduv*[W,H];lo=np.floor(q.min(0)-1);hi=np.ceil(q.max(0)+1);tw,th=(hi-lo+1).astype(int);xx,yy=np.meshgrid(np.arange(tw),np.arange(th));local=np.stack([xx.ravel(),yy.ravel()],1)+lo;M=np.column_stack([q[1]-q[0],q[2]-q[0]])
 if abs(np.linalg.det(M))<1e-8:continue
 bary=np.c_[np.ones(len(local)),(local-q[0])@np.linalg.inv(M).T];bary[:,0]-=bary[:,1:].sum(1);wc=np.maximum(bary,0);wc/=wc.sum(1)[:,None];points=wc@p;baseq=wc@olduv;base=pixels[np.clip(np.rint(baseq[:,1]*H).astype(int),0,H-1),np.clip(np.rint(baseq[:,0]*W).astype(int),0,W-1)].copy();near={k:nearest_arc(points,v)for k,v in transport.items()};upper=near['upper'][0]<=near['lower'][0];distance=np.where(upper,near['upper'][0],near['lower'][0])*SW;width=np.where(upper,domain['upper_width_px'],domain['lower_width_px']);weight=native_lip_ownership(distance,width,domain['outer_fade_px']);core=distance<=width
 for name in ['upper','lower']:
  take=(upper if name=='upper'else~upper)&(weight>0)
  if not take.any():continue
  xy=side_curve_donor(near[name][1][take],transport[name][1][-1],distance[take],cfg[name+'_source_curve_px'],name=='upper');ix=np.rint(xy).astype(int);ix[:,0]=np.clip(ix[:,0],0,SW-1);ix[:,1]=np.clip(ix[:,1],0,SH-1);donor=sp[SH-1-ix[:,1],ix[:,0]];assert(donor[:,3]>.95).all();a=weight[take,None];base[take]=base[take]*(1-a)+donor*a;range_min=np.minimum(range_min,ix.min(0));range_max=np.maximum(range_max,ix.max(0))
 protected+=int(core.sum());assert np.all(weight[core]==1);max_aux=max(max_aux,float((1-weight[core]).max(initial=0)));tiles.append(dict(face=face.index,q=q-lo,w=int(tw),h=int(th),pixels=base.reshape(th,tw,4)))
aw=2048;x=y=3;row=0
for tile in tiles:
 if x+tile['w']+3>aw:x=3;y+=row+3;row=0
 tile['at']=(x,y);x+=tile['w']+3;row=max(row,tile['h'])
ah=2**math.ceil(math.log2(y+row+3));atlas=np.ones((ah,aw,4),np.float32)
for t in tiles:x,y=t['at'];atlas[y:y+t['h'],x:x+t['w']]=t['pixels']
assert old_lip_faces.issubset({t['face']for t in tiles})
chart=bpy.data.images.new('Own complete native shark lip chart',aw,ah,alpha=True);chart.colorspace_settings.name=native.colorspace_settings.name;chart.pixels.foreach_set(atlas.ravel());chart.pack();mat=mesh.materials[0].copy();mat.name='Own native upper lower lip transition';next(n for n in mat.node_tree.nodes if n.type=='TEX_IMAGE').image=chart
if len(mesh.materials)>2:mesh.materials[2]=mat;slot=2
else:mesh.materials.append(mat);slot=len(mesh.materials)-1
for t in tiles:
 face=mesh.polygons[t['face']];face.material_index=slot
 for li,q in zip(face.loop_indices,t['q']):uv.data[li].uv=((q[0]+t['at'][0]+.5)/aw,(q[1]+t['at'][1]+.5)/ah)
assert geometry()==before_material;assert protected>0;bpy.ops.object.select_all(action='DESELECT')
for ob in bpy.context.scene.objects:
 if ob.type in['MESH','ARMATURE']:ob.select_set(True)
bpy.ops.wm.save_as_mainfile(filepath=str(out/'fish.blend'));bpy.ops.export_scene.gltf(filepath=str(out/'fish.glb'),export_format='GLB',use_selection=True,export_animations=True,export_yup=True,export_def_bones=False);(out/'fin-authoring.json').write_bytes((src/'fin-authoring.json').read_bytes());report=dict(ok=True,kind='complete_anterior_semantic_color_chart',species=cfg['species'],source_sha256=cfg['source']['sha256'],model_sha256=sha(out/'fish.glb'),geometry_weights_triangles_unchanged=True,scope='Material step preserves the preceding explicitly recorded photographed-head/integrated-mouth geometry. No auxiliary front contribution inside complete native lip domains; original source lip pixels transported on actual3D arcs.',actual_3d_rim_transport=dict(upper_edges=len(edge_ids['upper']),lower_edges=len(edge_ids['lower'])),complete_native_lip_ownership=dict(protected_texels=protected,maximum_front_weight_inside_complete_lip=max_aux,maximum_central_weight_inside_complete_lip=max_aux,domain=domain,native_donor_min_px=range_min.tolist(),native_donor_max_px=range_max.tolist()),preceding_geometry=dict(mouth_source_bounds_before=cfg['mouth_x_bounds_before'],mouth_source_bounds_after=cfg['mouth_x_bounds_after'],moved_mouth_vertices=len(moved),head_side_photo=cfg['head_side'],head_stations_native=frozen,geometry_fingerprint_before_material=before_material),formal_acceptance=False,visual_review='pending');(out/'authoring.validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'lip_texels':protected,'lip_tiles':len(tiles),'atlas':[aw,ah],'body_materials':len(mesh.materials)}))
