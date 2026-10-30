"""Replace own reference cage mouth with two independent source lip boundaries.

Experimental local candidate only. Preserve complete existing fins/rig, enforce
whole-fish budget, save editable source. No visual pass or rectangular recolor.
"""
import argparse,hashlib,json,math,sys
from pathlib import Path
import bpy,bmesh,numpy as np
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[3];sys.path[:0]=[str(ROOT/'cli'),str(Path(__file__).parent)]
from oral_jaws import build_closed_oral_jaws
from export_source_with_frozen_normals import export_guarded,EXACT_NORMAL_ATTRIBUTE
from patch_existing_fin_meshes import read as read_glb,write as write_glb

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text(encoding='utf8'))
def fingerprint(ob):
    ob.data.calc_loop_triangles()
    return hashlib.sha256(repr(([(tuple(v.co),[(ob.vertex_groups[g.group].name,g.weight)for g in v.groups])for v in ob.data.vertices],[(tuple(f.vertices),f.material_index)for f in ob.data.polygons],[[tuple(x.uv)for x in layer.data]for layer in ob.data.uv_layers],list(ob.matrix_world))).encode()).hexdigest()
p=argparse.ArgumentParser()
for key in ['blend','config','output']:p.add_argument('--'+key,type=Path,required=True)
a=p.parse_args(sys.argv[sys.argv.index('--')+1:]);cfg=read(a.config);out=a.output.resolve();assert out.is_relative_to(ROOT/'projects/fishing-2d/experiments')and not out.exists();assert sha(a.blend)==cfg['blend_sha256'];out.mkdir()
profile=read(ROOT/cfg['profile']);assert sha(ROOT/cfg['source'])==cfg['source_sha256']
bpy.ops.wm.open_mainfile(filepath=str(a.blend.resolve()));old=bpy.data.objects[cfg['body']];rig=old.parent;assert rig.type=='ARMATURE';fin_names=cfg['fins'];frozen={n:fingerprint(bpy.data.objects[n])for n in fin_names}
old.data.calc_loop_triangles();old_body_tri=len(old.data.loop_triangles);skin=old.data.materials[0];source_image=next(n.image for n in skin.node_tree.nodes if n.type=='TEX_IMAGE');W,H=source_image.size;aspect=H/W;pixels=np.asarray(source_image.pixels[:]).reshape(H,W,4)
assert [W,H]==cfg['source_size'];upper=np.asarray(cfg['upper_inner_edge_px'],float);lower=np.asarray(cfg['lower_inner_edge_px'],float);assert np.array_equal(upper[:,0],lower[:,0])and np.all(np.diff(upper[:,0])>0)and np.all(lower[:,1]>upper[:,1])
sections=profile['body']['sections'];remove=set(cfg.get('remove_interpolated_stations',[]))
assert not remove&{s[0]for s in sections},'Keep every original envelope control station'
assert not remove&{s[0]for s in profile['rig']['spine']},'Keep every original body-weight break'
stations=sorted((set(profile['body']['ring_positions'])-remove)|set(upper[:,0]/W));R=profile['body']['radial'];vertices=[];faces=[]
def section(u):return [float(np.interp(u,[s[0]for s in sections],[s[i]for s in sections]))for i in [1,2,3]]
ordered=sorted((point[0],f'body_{i:02d}')for i,point in enumerate(profile['rig']['spine']))
def weights(u):
    if u<=ordered[0][0]:return {ordered[0][1]:1.}
    for (lo,ln),(hi,hn)in zip(ordered,ordered[1:]):
        if u<=hi:
            t=(u-lo)/(hi-lo);return {ln:1-t,hn:t}
    return {ordered[-1][1]:1.}
for i,u in enumerate(stations):
    top,bottom,width=section(u)
    for j in range(R):
        angle=math.tau*j/R;v=(top+bottom)/2-(bottom-top)/2*math.cos(angle);vertices.append((u-.5,width*math.sin(angle),(.5-v)*aspect))
        if i:
            q=(i-1)*R+j;r=(i-1)*R+(j+1)%R;faces.append((q,r,r+R,q+R))
faces.extend([tuple(reversed(range(R))),tuple((len(stations)-1)*R+j for j in range(R))]);mesh=bpy.data.meshes.new('Own source cage with independent lip opening');mesh.from_pydata(vertices,[],faces);mesh.materials.append(skin)
bpy.data.objects.remove(old,do_unlink=True);body=bpy.data.objects.new(cfg['body'],mesh);bpy.context.collection.objects.link(body)
bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(mesh);bm.free()
layer=mesh.uv_layers.new(name='UVMap')
for face in mesh.polygons:
    face.use_smooth=True
    for li in face.loop_indices:
        co=mesh.vertices[mesh.loops[li].vertex_index].co;u=co.x+.5;top,bottom,_=section(u);inset=min(12/H,(bottom-top)*.2);v=np.clip(.5-co.z/aspect,top+inset,bottom-inset);layer.data[li].uv=(u,1-v)
settings=profile['oral_jaws'].copy();settings['corner']=[upper[0,0]/W,float((upper[0,1]+lower[0,1])/2/H)];settings['boolean_solver']='EXACT';settings['lip_bevel']=0
settings['slit_path']=[settings['corner'],*[[float(x/W),float((y+lower[i,1])/2/H)]for i,(x,y)in enumerate(upper)if i>0]];settings['front']=settings['slit_path'][-1]
cut=[[float(x/W),float((.5-lower[i,1]/H)*aspect),float((.5-y/H)*aspect)]for i,(x,y)in enumerate(upper)]
oral=build_closed_oral_jaws(body,settings,aspect,weights,cut_profile=cut)
body.parent=rig;modifier=body.modifiers.new('Swim skin','ARMATURE');modifier.object=rig
assert {n:fingerprint(bpy.data.objects[n])for n in fin_names}==frozen,'Existing fin topology/UV/weights/transforms changed'
counts={}
for ob in bpy.context.scene.objects:
    if ob.type=='MESH':ob.data.calc_loop_triangles();counts[ob.name]=len(ob.data.loop_triangles)
total=sum(counts.values());assert total<=cfg['hard_triangles'],('Whole-fish budget exceeded',counts,total)
bm=bmesh.new();bm.from_mesh(mesh);closed=all(e.is_manifold for e in bm.edges);bm.free();assert closed
bpy.context.scene.frame_set(0);bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(out/'fish.blend'))
model=out/'fish.glb'
if any(ob.type=='MESH'and EXACT_NORMAL_ATTRIBUTE in ob.data.attributes for ob in bpy.data.objects):normal_export=export_guarded(model)
else:
    bpy.ops.export_scene.gltf(filepath=str(model),export_format='GLB',export_animations=True,export_yup=True,export_skins=True);normal_export={'mode':'ordinary_new_source'}
d,b=read_glb(model)
for node in d['nodes']:
    if'mesh'not in node:continue
    for pr in d['meshes'][node['mesh']]['primitives']:
        mat=d['materials'][pr['material']];mat.update(alphaMode='OPAQUE'if node['name']==cfg['body']else'MASK',doubleSided=False)
        if mat['alphaMode']=='MASK':mat['alphaCutoff']=.5
for sampler in d.get('samplers',[]):sampler.update(magFilter=9728,minFilter=9728)
write_glb(model,d,b)
exported=sum(d['accessors'][p['indices']]['count']//3 for m in d['meshes']for p in m['primitives']);assert exported==total
report={'ok':True,'kind':'source_boundary_mouth_local_candidate','model_sha256':sha(model),'editable_source_sha256':sha(out/'fish.blend'),'config_sha256':sha(a.config),'whole_fish_triangles':total,'body_before_triangles':old_body_tri,'parts':counts,'hard_triangles':cfg['hard_triangles'],'preferred_triangles':cfg['preferred_triangles'],'all_existing_fins_exact':True,'body_closed':closed,'oral':oral,'normal_export':normal_export,'mouth_visual_review':'pending','remaining':['Source/lower-lip/actual opening multiview review','Separate left/right and cross-lip source pixel continuation','Current source/cold and all affected final gates'],'scope':'Experimental geometry replacement within whole-fish budget. Geometry/texture review required; no mouth or fish approval.'};(out/'authoring.validation.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf8');print(json.dumps({'ok':True,'triangles':total,'parts':counts,'visual_review':'pending'}))
