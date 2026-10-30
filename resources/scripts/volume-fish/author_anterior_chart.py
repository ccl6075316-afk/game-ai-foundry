"""Bake a finite anterior skin chart from explicit two-dimensional species donors.

Rest geometry, skin and existing deep oral faces stay unchanged. Smooth color
mixing is baked offline, rather than interpolating UV across unrelated features.
"""
import argparse,json,hashlib,sys,math
from pathlib import Path
import bpy,numpy as np
sys.path.insert(0,str(Path(__file__).parent/'portable'))
from fish_asset_spec import artifact_output as fresh_output
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text(encoding='utf8'))

p=argparse.ArgumentParser()
for k in ['blend','config','output']:p.add_argument('--'+k,type=Path,required=True)
a=p.parse_args(sys.argv[sys.argv.index('--')+1:]);out=fresh_output(a.output);assert not out.exists();settings=read(a.config)
assert sha(a.blend)==settings['blend_sha256'];bpy.ops.wm.open_mainfile(filepath=str(a.blend.resolve()));body=bpy.data.objects[settings['body']]
# Use precisely Blender's existing export triangles, not a different remesher.
old=body.data;old.calc_loop_triangles();triangles=list(old.loop_triangles)
original_polygons=len(old.polygons)
if any(len(f.vertices)!=3 for f in old.polygons):
    coords=[v.co[:]for v in old.vertices];weights=[[(g.group,g.weight)for g in v.groups]for v in old.vertices];group_names=[g.name for g in body.vertex_groups];uvs=[tuple(v.uv)for v in old.uv_layers.active.data];normals=[tuple(n.vector)for n in old.corner_normals]
    face_data=[(tuple(t.vertices),tuple(t.loops),t.material_index,old.polygons[t.polygon_index].use_smooth)for t in triangles]
    mesh=bpy.data.meshes.new('Exact export triangles for finite color charts');mesh.from_pydata(coords,[],[r[0]for r in face_data]);mesh.update()
    for material in old.materials:mesh.materials.append(material)
    layer=mesh.uv_layers.new(name='UVMap');custom=[]
    for face,row in zip(mesh.polygons,face_data):
        face.material_index=row[2];face.use_smooth=row[3]
        for li,old_li in zip(face.loop_indices,row[1]):layer.data[li].uv=uvs[old_li];custom.append(normals[old_li])
    mesh.normals_split_custom_set(custom);body.data=mesh
    body.vertex_groups.clear()
    for name in group_names:body.vertex_groups.new(name=name)
    for vi,groups in enumerate(weights):
        for group,weight in groups:body.vertex_groups[group].add([vi],weight,'REPLACE')
def geometry():return hashlib.sha256(repr(([(tuple(v.co),[(g.group,g.weight)for g in v.groups])for v in body.data.vertices],[tuple(f.vertices)for f in body.data.polygons])).encode()).hexdigest()
before=geometry();oldmat=body.data.materials[0];oldimage=next(n.image for n in oldmat.node_tree.nodes if n.type=='TEX_IMAGE');w,h=oldimage.size;pixels=np.asarray(oldimage.pixels[:]).reshape(h,w,4)
profile=read(Path(settings['profile']));sections=profile['body']['sections'];slit_path=profile['oral_jaws']['slit_path'];start,end=settings['u_interval'];s0,s1=settings['side_preservation'];density=w
def smooth(x):x=np.clip(x,0,1);return x*x*(3-2*x)
def sample(uv):return pixels[np.clip((uv[:,1]*h).astype(int),0,h-1),np.clip((uv[:,0]*w).astype(int),0,w-1)]
def color(co):
    u=co[:,0]+.5;v=.5-co[:,2]/settings['source_y_factor'];width=np.interp(u,[s[0]for s in sections],[s[3]for s in sections]);top=np.interp(u,[s[0]for s in sections],[s[1]for s in sections]);bottom=np.interp(u,[s[0]for s in sections],[s[2]for s in sections]);side=np.clip(abs(co[:,1])/np.maximum(width,1e-8),0,1)
    base=sample(np.stack([u,1-v],axis=1));height=np.clip((v-top)/np.maximum(bottom-top,1e-8),0,1)
    # Each jaw uses its own reviewed source skin rectangle, not the side outline,
    # eye or a repeated row. Its full two-dimensional variation is preserved.
    upper=v<np.interp(u,[p[0]for p in slit_path],[p[1]for p in slit_path]);donor=np.zeros((len(co),2))
    for flag,key in [(True,'upper_donor_uv'),(False,'lower_donor_uv')]:
        rect=settings[key];mask=upper==flag;donor[mask,0]=rect[0]+(rect[2]-rect[0])*(.5+.5*co[mask,1]/np.maximum(width[mask],1e-8));donor[mask,1]=1-(rect[1]+(rect[3]-rect[1])*height[mask])
    replacement=sample(donor);assert np.all(replacement[:,3]>.95),'Nonopaque anterior donor'
    lateral=(1-smooth((side-s0)/(s1-s0)))if settings.get('preserve_lateral_pixels',True)else np.ones(len(co))
    amount=smooth((u-start)/(end-start))*lateral;result=base*(1-amount[:,None])+replacement*amount[:,None];result[:,3]=1;return result
tiles=[];changed=[]
for face in body.data.polygons:
    if face.material_index!=0:continue
    co=np.asarray([body.data.vertices[i].co[:]for i in face.vertices]);assert len(co)==3
    if max(co[:,0]+.5)<start:continue
    x=co[1]-co[0];x/=np.linalg.norm(x);normal=np.cross(co[1]-co[0],co[2]-co[0]);normal/=np.linalg.norm(normal);y=np.cross(normal,x);q=np.stack([(co-co[0])@x,(co-co[0])@y],axis=1)*density
    low=np.floor(q.min(axis=0))-3;high=np.ceil(q.max(axis=0))+3;tw,th=(high-low+1).astype(int);assert tw*th<200000
    yy,xx=np.mgrid[:th,:tw];plane=np.stack([xx.ravel()+low[0],yy.ravel()+low[1]],axis=1);matrix=np.stack([q[1]-q[0],q[2]-q[0]],axis=1);bary=(plane-q[0])@np.linalg.inv(matrix).T;bary=np.stack([1-bary.sum(axis=1),bary[:,0],bary[:,1]],axis=1);bary=np.maximum(bary,0);bary/=bary.sum(axis=1)[:,None]
    tile=color(bary@co).reshape(th,tw,4);tiles.append({'face':face.index,'q':q-low,'pixels':tile,'w':tw,'h':th});changed.append(face.index)
assert tiles
aw=1024;px=3;py=3;row=0
for tile in tiles:
    if px+tile['w']+3>aw:px=3;py+=row+3;row=0
    tile['at']=(px,py);px+=tile['w']+3;row=max(row,tile['h'])
ah=2**math.ceil(math.log2(py+row+3));atlas=np.ones((ah,aw,4),dtype='float32')
for tile in tiles:
    x,y=tile['at'];atlas[y:y+tile['h'],x:x+tile['w']]=tile['pixels']
image=bpy.data.images.new('Species finite anterior skin chart',aw,ah,alpha=True);image.colorspace_settings.name=oldimage.colorspace_settings.name;image.pixels.foreach_set(atlas.ravel());image.pack()
mat=oldmat.copy();mat.name='Baked finite anterior skin, no runtime correction';next(n for n in mat.node_tree.nodes if n.type=='TEX_IMAGE').image=image;body.data.materials.append(mat);index=len(body.data.materials)-1
for tile in tiles:
    face=body.data.polygons[tile['face']];face.material_index=index
    for li,q in zip(face.loop_indices,tile['q']):body.data.uv_layers.active.data[li].uv=((q[0]+tile['at'][0]+.5)/aw,(q[1]+tile['at'][1]+.5)/ah)
assert geometry()==before;out.mkdir(parents=True);bpy.ops.wm.save_as_mainfile(filepath=str(out/'fish.blend'));bpy.ops.object.select_all(action='DESELECT')
for ob in bpy.context.scene.objects:
    if ob.type in ('MESH','ARMATURE'):ob.select_set(True)
model=out/'fish.glb';bpy.ops.export_scene.gltf(filepath=str(model),export_format='GLB',use_selection=True,export_animations=True,export_yup=True,export_skins=True)
# Match the explicit ordinary matte contract, without changing any arrays.
from patch_existing_fin_meshes import read as read_glb,write as write_glb
d,b=read_glb(model)
for node in d['nodes']:
    if'mesh'not in node:continue
    for pr in d['meshes'][node['mesh']]['primitives']:
        material=d['materials'][pr['material']];material.update(alphaMode='OPAQUE'if node['name']==settings['body']else'MASK',doubleSided=False)
        if material['alphaMode']=='MASK':material['alphaCutoff']=.5
for sampler in d['samplers']:sampler.update(magFilter=9728,minFilter=9728)
write_glb(model,d,b)
report={'ok':True,'kind':'offline_anterior_color_chart','input_blend_sha256':sha(a.blend),'config_sha256':sha(a.config),'geometry_skin_topology_unchanged':geometry()==before,'changed_skin_faces':changed,'deep_oral_faces_unchanged':True,'atlas_size':[aw,ah],'source_image':oldimage.name,'derived_colors':True,'blend_sha256':sha(out/'fish.blend'),'model_sha256':sha(model),'visual_review':'pending','scope':'Own source safe2D jaw skin donors with offline smooth color blending. No geometry change, no independent lip layers, no runtime static patch. Actual views still required.'}
(out/'authoring.validation.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf8');print(json.dumps({'ok':True,'faces':len(changed),'atlas':[aw,ah]}))
