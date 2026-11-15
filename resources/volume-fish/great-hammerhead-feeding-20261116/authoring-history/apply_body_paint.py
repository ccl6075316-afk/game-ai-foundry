"""Whole-body generated color atlas, no geometry/UV/action edits, R2 isolated base."""
import bpy,json,hashlib,struct
from pathlib import Path
W=Path(__file__).parent;source=W/'history/r2-before-edge-repair/fish.blend';O=W/'candidate'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def accessors(p):
 b=p.read_bytes();n=struct.unpack_from('<I',b,12)[0];g=json.loads(b[20:20+n]);binary=b[28+n:];rows=[]
 for a in g['accessors']:
  v=g['bufferViews'][a['bufferView']];unit={'SCALAR':1,'VEC2':2,'VEC3':3,'VEC4':4,'MAT4':16}[a['type']]*{5120:1,5121:1,5122:2,5123:2,5125:4,5126:4}[a['componentType']];stride=v.get('byteStride',unit);offset=v.get('byteOffset',0)+a.get('byteOffset',0);raw=b''.join(binary[offset+i*stride:offset+i*stride+unit]for i in range(a['count']));rows.append([a['type'],a['componentType'],a['count'],hashlib.sha256(raw).hexdigest()])
 return rows
bpy.ops.wm.open_mainfile(filepath=str(source));body=bpy.data.objects['Reference_head_body'];mat=body.data.materials[2]
im=bpy.data.images.load(str(W/'body-paint-r3.png'),check_existing=False);im.name='Great hammerhead R3 complete body color';im.pack()
nodes=[n for n in mat.node_tree.nodes if n.type=='TEX_IMAGE'];assert len(nodes)==1
nodes[0].image=im;nodes[0].interpolation='Closest'
bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(O/'fish.blend'))
bpy.ops.export_scene.gltf(filepath=str(O/'fish.glb'),export_format='GLB',export_animations=True,export_yup=True,export_skins=True)
before=accessors(W/'history/r2-before-edge-repair/fish.glb');after=accessors(O/'fish.glb');assert before==after
r={'ok':True,'base_source_sha256':sha(source),'base_model_sha256':sha(W/'history/r2-before-edge-repair/fish.glb'),'source_sha256':sha(O/'fish.blend'),'model_sha256':sha(O/'fish.glb'),'paint':{'path':str(W/'body-paint-r3.png'),'sha256':sha(W/'body-paint-r3.png'),'size':list(im.size)},'non_image_accessors_exact':len(after),'scope':'Entire body material color image replaced by one generated coherent atlas. No image patch, no geometry/UV/weight/normal/skeleton/animation accessor change. Other fin/eye/oral materials unchanged. Imagegen island alignment must be visually verified, not assumed pixel exact.','status':'candidate pending actual texture/geometry review'}
(W/'body-paint-r3.validation.json').write_text(json.dumps(r,indent=2));print(r)
