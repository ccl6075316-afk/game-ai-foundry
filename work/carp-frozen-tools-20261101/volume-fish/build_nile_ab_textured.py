"""Reproducible, isolated A-material / B-reference-cage comparison.

Run in Blender --background --python this_file -- --route A|B.
A never changes mesh coordinates, topology or skin weights. B reads only the
shared rig, image/profile landmarks and independent fin outlines, not old meshes.
"""
import argparse, hashlib, json, math, struct, subprocess, sys, time
from pathlib import Path
import bpy, bmesh
from mathutils import Vector

repo = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(repo/'cli'), str(Path(__file__).parent)]
from oral_jaws import build_closed_oral_jaws
from reference_fin_cages import build as build_fins

p=argparse.ArgumentParser();p.add_argument('--route',choices=['A','B'],required=True)
args=p.parse_args(sys.argv[sys.argv.index('--')+1:]);started=time.perf_counter()
trial=repo/'projects/fishing-2d/experiments/nile-dorsal-route-trial'
out=trial/'round4-ab-textured';base=trial/'round2';shared=out/'shared'
recipe=json.loads((out/'comparison.plan.validation.json').read_text(encoding='utf8'))
profile=json.loads((repo/recipe['profile']).read_text(encoding='utf8'))
settings=json.loads((trial/'trial-profile.json').read_text(encoding='utf8'))
settings.update(recipe)
plan=json.loads((base/'fin-build.plan.json').read_text(encoding='utf8'))
target=out/(args.route+'-artifacts');target.mkdir(exist_ok=True)
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def write(path,value):Path(path).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
def digest(ob):
    return hashlib.sha256(repr((
        [tuple(v.co) for v in ob.data.vertices],
        [tuple(f.vertices) for f in ob.data.polygons],
        [[(ob.vertex_groups[g.group].name,g.weight) for g in v.groups] for v in ob.data.vertices],
        [list(row) for row in ob.matrix_world])).encode()).hexdigest()
def interp(u,column):
    rows=profile['body']['sections']
    if u<=rows[0][0]:return rows[0][column]
    for a,b in zip(rows,rows[1:]):
        if u<=b[0]:return a[column]+(b[column]-a[column])*(u-a[0])/(b[0]-a[0])
    return rows[-1][column]

def material(name,path=None,alpha=False,color=None):
    mat=bpy.data.materials.new(name);mat.use_nodes=True
    mat.node_tree.nodes.clear()
    bsdf=mat.node_tree.nodes.new('ShaderNodeBsdfPrincipled');output=mat.node_tree.nodes.new('ShaderNodeOutputMaterial')
    mat.node_tree.links.new(bsdf.outputs['BSDF'],output.inputs['Surface'])
    for key,value in [('Roughness',1.),('Metallic',0.),('Specular IOR Level',0.)]:bsdf.inputs[key].default_value=value
    if path:
        image=bpy.data.images.load(str(path),check_existing=True);image.pack()
        tex=mat.node_tree.nodes.new('ShaderNodeTexImage');tex.image=image;tex.interpolation='Closest';tex.extension='REPEAT' if name=='body_skin' else 'EXTEND'
        mat.node_tree.links.new(tex.outputs['Color'],bsdf.inputs['Base Color'])
        if alpha:
            mat.surface_render_method='DITHERED';mat.node_tree.links.new(tex.outputs['Alpha'],bsdf.inputs['Alpha'])
    if color:bsdf.inputs['Base Color'].default_value=color;mat.diffuse_color=color
    mat['static_material_role']=name
    return mat

def oral_material():
    # Median of the darkest source mouth-line pixels; shared by both models.
    image=bpy.data.images.load(str(base/'Closed_body-0-source_texture.png'),check_existing=True)
    w,h=image.size;pixels=image.pixels[:];colors=[]
    for u in range(round(w*.962),round(w*.99),2):
        v=.552+(.502-.552)*(u/w-.95)/(.995-.95)
        for dy in [-2,-1,0,1,2]:
            k=(max(0,min(h-1,round((1-v)*h)+dy))*w+u)*4
            rgba=pixels[k:k+4]
            if rgba[3]>.95:colors.append(tuple(rgba[:3]))
    colors.sort(key=lambda c:sum(c));donors=colors[:max(1,len(colors)//8)]
    color=tuple(sum(c[i] for c in donors)/len(donors) for i in range(3))+(1.,)
    return material('oral_source_shadow',color=color)

def body_uv(ob):
    uv=ob.data.uv_layers.active or ob.data.uv_layers.new(name='UVMap')
    aspect=972/1961
    for face in ob.data.polygons:
        values=[]
        for li in face.loop_indices:
            v=ob.data.vertices[ob.data.loops[li].vertex_index].co;u=v.x+.5
            top,bottom,width=interp(u,1),interp(u,2),interp(u,3)
            center=(.5-(top+bottom)/2)*aspect;radius=(bottom-top)/2*aspect
            angle=math.atan2(v.y/max(width,1e-6),(v.z-center)/max(radius,1e-6))%(2*math.pi)
            values.append([li,u,angle/(2*math.pi)])
        seam=max(r[2] for r in values)-min(r[2] for r in values)>.5
        for li,u,v in values:uv.data[li].uv=(u,1-(v+1 if seam and v<.5 else v))
        face.use_smooth=True

def glb_fix(path):
    data=path.read_bytes();length,kind=struct.unpack_from('<II',data,12);doc=json.loads(data[20:20+length])
    for mat in doc.get('materials',[]):
        fin=mat.get('name','').startswith('fin_');mat['alphaMode']='MASK' if fin else 'OPAQUE'
        mat['doubleSided']=False
        if fin:mat['alphaCutoff']=.5
    for sampler in doc.get('samplers',[]):sampler.update(magFilter=9728,minFilter=9728)
    raw=json.dumps(doc,separators=(',',':')).encode();raw+=b' '*((-len(raw))%4)
    tail=data[20+length:];result=struct.pack('<III',0x46546c67,2,20+len(raw)+len(tail))+struct.pack('<II',len(raw),kind)+raw+tail
    path.write_bytes(result)
    return doc

def export(path,objects):
    bpy.ops.object.select_all(action='DESELECT')
    for ob in objects:ob.select_set(True)
    bpy.context.view_layer.objects.active=next(ob for ob in objects if ob.type=='ARMATURE')
    bpy.ops.export_scene.gltf(filepath=str(path),export_format='GLB',use_selection=True,export_animations=True,export_yup=True,export_skins=True,export_texcoords=True,export_normals=True,export_materials='EXPORT',export_image_format='AUTO')
    return glb_fix(path)

if args.route=='A':
    source=repo/recipe['A_source'];assert sha(source)==recipe['A_source_sha256']
    bpy.ops.wm.open_mainfile(filepath=str(source))
    meshes=[ob for ob in bpy.context.scene.objects if ob.type=='MESH'];rig=next(ob for ob in bpy.context.scene.objects if ob.type=='ARMATURE')
    before={ob.name:digest(ob) for ob in meshes}
    body=next(ob for ob in meshes if ob.name.startswith('Closed_body'))
    old_slots=[m.name if m else '' for m in body.data.materials]
    skin=material('body_skin',shared/'body-atlas.png');oral=oral_material()
    for i in range(len(body.data.materials)):body.data.materials[i]=oral if i else skin
    body_uv(body)
    for ob in meshes:
        if ob==body:continue
        spec=next(row for row in plan['fins'] if row['name']==ob.name)
        ob.data.materials.clear();ob.data.materials.append(material('fin_'+ob.name,base/spec['image'],True))
    assert before=={ob.name:digest(ob) for ob in meshes},'A geometry/weights changed'
    # The reusable skeleton/animation is explicitly separate from A geometry.
    method={'geometry_weights_before':before,'geometry_weights_after':{ob.name:digest(ob) for ob in meshes},'geometry_unchanged':True,'old_body_material_roles':old_slots,'A_includes_previously_rebuilt_B_fin_cages':True}
else:
    handoff=json.loads((out/'B.json').read_text(encoding='utf8'))
    gate=subprocess.run([str(repo/'.venv/Scripts/python.exe'),'-c',
        'import json,sys;from pathlib import Path;sys.path.insert(0,"cli");from volume_archive import fresh_archive;p=Path(sys.argv[1]);fresh_archive(json.loads(p.read_text(encoding="utf8")),p);print("accepted archive unchanged")',str(out/'B.json')],cwd=str(repo),capture_output=True,text=True)
    assert gate.returncode==0,gate.stderr
    assert sha(repo/recipe['profile'])==handoff['profile_snapshot']['sha256']
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(shared/'rig.glb'))
    rig=next(ob for ob in bpy.context.scene.objects if ob.type=='ARMATURE')
    # Importer creates an icosphere viewport bone-shape helper, not fish skin.
    helpers={bone.custom_shape for bone in rig.pose.bones if bone.custom_shape}
    for helper in helpers:bpy.data.objects.remove(helper,do_unlink=True)
    assert not any(ob.type=='MESH' for ob in bpy.context.scene.objects),[(ob.name,ob.type) for ob in bpy.context.scene.objects]
    sections=profile['body']['sections'];radial=profile['body']['radial'];aspect=972/1961
    vertices=[]
    for u,top,bottom,width in sections:
        for j in range(radial):
            angle=2*math.pi*j/radial
            vertices.append((u-.5,width*math.sin(angle),(.5-(top+bottom)/2)*aspect+(bottom-top)/2*aspect*math.cos(angle)))
    faces=[]
    for i in range(len(sections)-1):
        for j in range(radial):
            a=i*radial+j;b=i*radial+(j+1)%radial;faces.append((a,b,b+radial,a+radial))
    faces.extend([tuple(reversed(range(radial))),tuple((len(sections)-1)*radial+j for j in range(radial))])
    mesh=bpy.data.meshes.new('Image-fitted sparse body cage');mesh.from_pydata(vertices,[],faces);mesh.update()
    body=bpy.data.objects.new('Closed_body_B',mesh);bpy.context.collection.objects.link(body)
    bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(mesh);bm.free()
    mesh.materials.append(material('body_skin',shared/'body-atlas.png'))
    spine=profile['rig']['spine'];ordered=sorted((row[0],f'body_{i:02d}') for i,row in enumerate(spine))
    def weights(u):
        if u<=ordered[0][0]:return {ordered[0][1]:1.}
        for a,b in zip(ordered,ordered[1:]):
            if u<=b[0]:
                t=(u-a[0])/(b[0]-a[0]);return {a[1]:1-t,b[1]:t}
        return {ordered[-1][1]:1.}
    for _,name in ordered:assert rig.data.bones.get(name),name
    control={'vertices':vertices,'faces':faces,'rings':len(sections),'radial':radial,'old_body_mesh_read':False,'method':recipe['B_method']}
    write(target/'control-cage.validation.json',control)
    oral=build_closed_oral_jaws(body,profile['oral_jaws'],aspect,weights)
    mesh=body.data
    for i in range(1,len(mesh.materials)):mesh.materials[i]=oral_material()
    bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.triangulate(bm,faces=list(bm.faces));bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(mesh);bm.free()
    body_uv(body);body.parent=rig;mod=body.modifiers.new('Swim skin','ARMATURE');mod.object=rig
    records,roots=build_fins(body,rig,plan,settings,base,material)
    write(target/'fin-roots.json',roots)
    # Editable source retains the actual side-image reference, excluded from GLB.
    ref=bpy.data.objects.new('Body-only side reference',None);ref.empty_display_type='IMAGE';ref.data=bpy.data.images.load(str(shared/'body-side.png'));ref.data.pack();ref.empty_display_size=1.;ref.rotation_euler=(math.pi/2,0,0);ref.hide_render=True;bpy.context.collection.objects.link(ref)
    method={'control_cage':{'vertices':len(vertices),'quads':(len(sections)-1)*radial,'rings':len(sections),'radial':radial},'old_body_mesh_read':False,'old_fin_mesh_read':False,'mouth':oral,'fins':records,'rig_source_sha256':sha(shared/'rig.glb')}

meshes=[ob for ob in bpy.context.scene.objects if ob.type=='MESH']
parts={ob.name:sum(len(face.vertices)-2 for face in ob.data.polygons) for ob in meshes}
total=sum(parts.values());assert total<=recipe['hard_max'],f'Whole fish {total} exceeds hard maximum'
topology={}
for ob in meshes:
    bm=bmesh.new();bm.from_mesh(ob.data)
    topology[ob.name]={'closed':all(e.is_manifold for e in bm.edges),'zero_area':sum(f.calc_area()<1e-13 for f in bm.faces),'vertices':len(bm.verts),'triangles':parts[ob.name]}
    bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-6)
    topology[ob.name]['closed_after_position_weld']=all(e.is_manifold for e in bm.edges);bm.free()
    assert topology[ob.name]['zero_area']==0,topology[ob.name]
    if args.route=='B':assert topology[ob.name]['closed'],topology[ob.name]
# Candidate-only orphan data purge; original source files remain untouched.
for block in (bpy.data.meshes,bpy.data.materials,bpy.data.images):
    for item in list(block):
        if item.users==0:block.remove(item)
bpy.context.scene.frame_set(0)
bpy.ops.wm.save_as_mainfile(filepath=str(target/'fish.blend'),check_existing=False)
doc=export(target/'fish.glb',meshes+[rig])
exported=sum(doc['accessors'][primitive['indices']]['count']//3 for mesh in doc['meshes'] for primitive in mesh['primitives'])
assert exported==total
report={'kind':'nile_AB_build_validation','route':args.route,'status':'experimental_requires_visual_review','formal_acceptance':False,'triangles':total,'preferred_max':1500,'hard_max':2000,'preferred_met':total<=1500,'parts':parts,'topology':topology,'method':method,'shared_material_hashes':recipe['shared_material_outputs'],'exported_triangles':exported,'materials':[m['name'] for m in doc['materials']],'runtime_static_construction_required':False,'process_seconds':time.perf_counter()-started,'new_external_model_calls':0,'new_external_API_fee':0,'hashes':{n:sha(target/n) for n in ['fish.blend','fish.glb']}}
write(target/'validation.json',report)
if args.route=='A':
    # Blender exports skinned children even with armature-only selection.
    # Remove them from this disposable process after saving A, then export rig.
    for ob in meshes:bpy.data.objects.remove(ob,do_unlink=True)
    export(shared/'rig.glb',[rig])
print(json.dumps({'ok':True,'route':args.route,'triangles':total,'parts':parts,'seconds':report['process_seconds']}))
