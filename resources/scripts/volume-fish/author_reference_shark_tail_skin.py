"""Carry the own caudal pigment over its body-owned attachment skin.

No geometry/weights/normals change. Prevent the generic white belly from
showing as isolated pale slots through the finite caudal/body junction.
"""
import bpy,json,hashlib,sys,math
from pathlib import Path
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
args=sys.argv[sys.argv.index('--')+1:];cp=Path(args[0]).resolve();out=Path(args[1]).resolve();assert not out.exists()and'/experiments/'in out.as_posix();out.mkdir();c=json.loads(cp.read_text());src=Path(c['baseline']);sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();assert sha(src/'fish.glb')==c['baseline_sha256'];bpy.ops.wm.open_mainfile(filepath=str(src/'fish.blend'));body=bpy.data.objects['Reference_head_body'];mesh=body.data;auth=json.loads((src/'fin-authoring.json').read_text());fin=next(f for f in auth['fins']if f['name']=='Caudal');tail=bpy.data.objects['Caudal'];tail.data.calc_loop_triangles();roots=set(fin['root_ids']);tree=BVHTree.FromPolygons([v.co.copy()for v in tail.data.vertices],[tuple(t.vertices)for t in tail.data.loop_triangles if all(i in roots for i in t.vertices)],all_triangles=True);ref=json.loads(Path(c['reference_fin_input']).read_text());row=next(f for f in ref['rows']if f['name']=='Caudal');axis=json.loads(Path(ref['reference']).read_text())['reference_body_axis_m'];scale=ref['metres_per_source_pixel'];rotation=math.radians(row['plane_rotation_degrees']);co,si=math.cos(rotation),math.sin(rotation);anchor=axis*(.5-row['onset_t']);leading=np.array(row['root_endpoints_px'][0]);im=bpy.data.images.load(c['caudal_chart'],check_existing=False);assert sha(c['caudal_chart'])==c['caudal_chart_sha256'];W,H=im.size;paint=np.array(im.pixels[:]).reshape(H,W,4)
before=hashlib.sha256(repr(([(tuple(v.co),[(g.group,g.weight)for g in v.groups])for v in mesh.vertices],[tuple(f.vertices)for f in mesh.polygons],[tuple(n.vector)for n in mesh.corner_normals])).encode()).hexdigest();tiles=[];density=c['pixels_per_m'];original_images={};affected=0
for f in mesh.polygons:
    p=np.array([mesh.vertices[i].co[:]for i in f.vertices]);ts=(axis/2-p[:,0])/axis
    if ts.max()<c['transition_t'][0]:continue
    material=mesh.materials[f.material_index];tex=next(n for n in material.node_tree.nodes if n.type=='TEX_IMAGE').image
    if tex.name not in original_images:original_images[tex.name]=(tex.size[:],np.array(tex.pixels[:]).reshape(tex.size[1],tex.size[0],4))
    (sw,sh),original=original_images[tex.name];old_uv=np.array([mesh.uv_layers.active.data[i].uv[:]for i in f.loop_indices]);ex=p[1]-p[0];ex/=np.linalg.norm(ex);normal=np.cross(p[1]-p[0],p[2]-p[0]);normal/=np.linalg.norm(normal);ey=np.cross(normal,ex);q=np.stack([(p-p[0])@ex,(p-p[0])@ey],1)*density;q-=np.floor(q.min(0))-2;tw,th=np.ceil(q.max(0)+3).astype(int);xx,yy=np.meshgrid(np.arange(tw),np.arange(th));local=np.stack([xx.ravel(),yy.ravel()],1);b=np.c_[np.ones(len(local)),(local-q[0])@np.linalg.inv(np.column_stack([q[1]-q[0],q[2]-q[0]])).T];b[:,0]-=b[:,1:].sum(1);b=np.maximum(b,0);b/=b.sum(1)[:,None];points=b@p;uv=b@old_uv;ix=np.clip(np.floor(uv[:,0]*sw).astype(int),0,sw-1);iy=np.clip(np.floor(uv[:,1]*sh).astype(int),0,sh-1);base=original[iy,ix].copy();x,z=points[:,0]-anchor,points[:,2]-row['anchor_z_m'];dx,dz=co*x+si*z,-si*x+co*z;sx=leading[0]-dx/scale;sy=leading[1]-dz/scale;ix=np.clip(np.rint(sx).astype(int),0,W-1);iy=np.clip(H-1-np.rint(sy).astype(int),0,H-1);donor=paint[iy,ix];distance=np.array([tree.find_nearest(Vector(point))[3]for point in points]);t=(axis/2-points[:,0])/axis;gain=np.clip((t-c['transition_t'][0])/(c['transition_t'][1]-c['transition_t'][0]),0,1);gain=gain*gain*(3-2*gain);contact=np.clip(1-distance/c['attachment_skin_fade_m'],0,1);contact=contact*contact*(3-2*contact);gain*=contact;affected+=int((gain>.5).sum());base[:,:3]=base[:,:3]*(1-gain[:,None])+donor[:,:3]*gain[:,None];base[:,3]=1;tiles.append(dict(face=f.index,q=q,w=int(tw),h=int(th),pixels=base.reshape(th,tw,4)))
width=1024;x=y=3;height=0
for tile in tiles:
    if x+tile['w']+3>width:x=3;y+=height+3;height=0
    tile['at']=(x,y);x+=tile['w']+3;height=max(height,tile['h'])
height=2**math.ceil(math.log2(y+height+3));atlas=np.ones((height,width,4),np.float32)
for tile in tiles:x,y=tile['at'];atlas[y:y+tile['h'],x:x+tile['w']]=tile['pixels']
image=bpy.data.images.new('Body-owned caudal attachment pigment transport',width,height,alpha=True);image.colorspace_settings.name='sRGB';image.pixels.foreach_set(atlas.ravel());image.pack();material=mesh.materials[0].copy();material.name='Derived body-owned caudal attachment continuity';next(n for n in material.node_tree.nodes if n.type=='TEX_IMAGE').image=image;mesh.materials.append(material);slot=len(mesh.materials)-1
for tile in tiles:
    face=mesh.polygons[tile['face']];face.material_index=slot
    for loop,q in zip(face.loop_indices,tile['q']):mesh.uv_layers.active.data[loop].uv=((q[0]+tile['at'][0]+.5)/width,(q[1]+tile['at'][1]+.5)/height)
after=hashlib.sha256(repr(([(tuple(v.co),[(g.group,g.weight)for g in v.groups])for v in mesh.vertices],[tuple(f.vertices)for f in mesh.polygons],[tuple(n.vector)for n in mesh.corner_normals])).encode()).hexdigest();assert before==after and affected>0
bpy.ops.object.select_all(action='DESELECT')
for o in bpy.context.scene.objects:
    if o.type in ['MESH','ARMATURE']:o.select_set(True)
bpy.ops.wm.save_as_mainfile(filepath=str(out/'fish.blend'));bpy.ops.export_scene.gltf(filepath=str(out/'fish.glb'),export_format='GLB',use_selection=True,export_animations=True,export_yup=True,export_def_bones=False);(out/'fin-authoring.json').write_bytes((src/'fin-authoring.json').read_bytes());report=dict(ok=True,kind='body_owned_caudal_attachment_pigment_transport',model_sha256=sha(out/'fish.glb'),config_sha256=sha(cp),geometry_skin_normals_exact=True,affected_body_faces=len(tiles),transported_texels=affected,atlas_size=[width,height],source_chart_sha256=c['caudal_chart_sha256'],meaning='Same-fish caudal chart RGB transported onto body-owned skin within the actual full root-cap support and a declared finite fade. Derived blend, not a biological pigment measurement. No alpha hole, root selection or geometry change.',formal_acceptance=False);(out/'authoring.validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
