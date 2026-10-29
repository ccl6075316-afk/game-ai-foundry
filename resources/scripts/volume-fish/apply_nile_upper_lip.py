"""Apply the marked upper-lip UV islands and atlas; geometry/rig stay frozen."""
import bpy,json,hashlib,struct
from pathlib import Path
repo=Path(__file__).resolve().parents[3];trial=repo/'projects/fishing-2d/experiments/nile-dorsal-route-trial';out=trial/'round7-upper-lip-continuity';source=trial/'round6-reference-repair/B-artifacts/fish.blend';target=out/'B-artifacts';target.mkdir(exist_ok=True)
read=lambda p:json.loads(p.read_text(encoding='utf8'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
plan=read(out/'upper-lip-paint.plan.json');assert sha(source)==plan['source_blend']
def geometry(ob):return hashlib.sha256(repr(([tuple(v.co) for v in ob.data.vertices],[tuple(p.vertices) for p in ob.data.polygons],[[tuple((ob.vertex_groups[g.group].name,g.weight)) for g in v.groups] for v in ob.data.vertices])).encode()).hexdigest()
bpy.ops.wm.open_mainfile(filepath=str(source));meshes=[ob for ob in bpy.context.scene.objects if ob.type=='MESH'];frozen={ob.name:geometry(ob) for ob in meshes};body=bpy.data.objects['Closed_body_B'];mesh=body.data
before_uv={f.index:[tuple(mesh.uv_layers.active.data[li].uv) for li in f.loop_indices] for f in mesh.polygons};selected=set()
for row in plan['patches']:
 face=mesh.polygons[row['face_index']];assert list(face.vertices)==row['vertices'] and face.material_index==0
 for li,uv in zip(face.loop_indices,row['uv']):mesh.uv_layers.active.data[li].uv=uv
 selected.add(face.index)
for f in mesh.polygons:
 if f.index not in selected:assert before_uv[f.index]==[tuple(mesh.uv_layers.active.data[li].uv) for li in f.loop_indices]
image=bpy.data.images.load(str(out/'upper-lip-continuous-atlas.png'),check_existing=False);image.pack();nodes=[n for n in mesh.materials[0].node_tree.nodes if n.type=='TEX_IMAGE'];assert len(nodes)==1;nodes[0].image=image
assert frozen=={ob.name:geometry(ob) for ob in meshes}
rig=next(ob for ob in bpy.context.scene.objects if ob.type=='ARMATURE');bpy.context.scene.frame_set(0)
bpy.ops.wm.save_as_mainfile(filepath=str(target/'fish.blend'),check_existing=False)
bpy.ops.object.select_all(action='DESELECT')
for ob in meshes+[rig]:ob.select_set(True)
bpy.context.view_layer.objects.active=rig
bpy.ops.export_scene.gltf(filepath=str(target/'fish.glb'),export_format='GLB',use_selection=True,export_animations=True,export_skins=True,export_yup=True)
p=target/'fish.glb';data=p.read_bytes();n,kind=struct.unpack_from('<II',data,12);doc=json.loads(data[20:20+n])
for mat in doc['materials']:
 fin=mat.get('name','').startswith('fin_');mat['alphaMode']='MASK' if fin else 'OPAQUE';mat['doubleSided']=False
 if fin:mat['alphaCutoff']=.5
for sampler in doc.get('samplers',[]):sampler.update(magFilter=9728,minFilter=9728)
raw=json.dumps(doc,separators=(',',':')).encode();raw+=b' '*((-len(raw))%4);tail=data[20+n:];p.write_bytes(struct.pack('<III',0x46546c67,2,20+len(raw)+len(tail))+struct.pack('<II',len(raw),kind)+raw+tail)
tris=sum(doc['accessors'][primitive['indices']]['count']//3 for m in doc['meshes'] for primitive in m['primitives']);assert tris==1476
report={'kind':'nile_upper_lip_material_only','route':'B','triangles':tris,'formal_acceptance':False,'user_visual_acceptance':'pending','geometry_topology_weights_unchanged':True,'body_lower_lip_and_fins_unchanged':True,'changed_upper_skin_faces':len(selected),'unchanged_UV_on_all_other_faces':True,'source_guide':sha(out/'upper-lip-guide.json'),'source_paint_plan':sha(out/'upper-lip-paint.plan.json'),'texture_size':[1961,1024],'new_texture_memory':0,'new_triangles':0,'source_geometry_digests':frozen,'hashes':{name:sha(target/name) for name in ['fish.blend','fish.glb']}}
(target/'validation.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf8');print(json.dumps({'ok':True,'triangles':tris,'patched_faces':len(selected),'geometry_unchanged':True}))
