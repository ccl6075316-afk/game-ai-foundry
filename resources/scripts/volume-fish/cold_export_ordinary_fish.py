"""Fresh-process ordinary editable-source export; no geometry construction.

Reject guarded packed sources, which require their existing exact exporter.
The reference comparison covers all decoded geometry/UV/skin/normals/animation
arrays and imported document bindings; visual approval remains separate.
"""
import bpy,sys,json,hashlib
from pathlib import Path
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE/'portable'))
from glb_io import read_glb,arrays,sha
sys.path.insert(0,str(HERE));from restore_fin_source_normals import EXACT_NORMAL_ATTRIBUTE
import numpy as np
args=sys.argv[sys.argv.index('--')+1:];source=Path(args[0]).resolve();reference=Path(args[1]).resolve();out=Path(args[2]).resolve();assert not out.exists()and'/experiments/'in out.as_posix();out.mkdir();source_hash=sha(source);bpy.ops.wm.open_mainfile(filepath=str(source));objects=[o for o in bpy.context.scene.objects if o.type in['MESH','ARMATURE']];assert objects and not any(o.type=='MESH'and EXACT_NORMAL_ATTRIBUTE in o.data.attributes for o in objects);bpy.ops.object.select_all(action='DESELECT')
for o in objects:o.select_set(True)
model=out/'fish.glb';bpy.ops.export_scene.gltf(filepath=str(model),export_format='GLB',use_selection=True,export_animations=True,export_yup=True,export_def_bones=False);assert sha(source)==source_hash;a,ab=read_glb(reference);b,bb=read_glb(model);assert len(a['accessors'])==len(b['accessors']);errors=[]
for i in range(len(a['accessors'])):
 x=arrays(a,ab,i);y=arrays(b,bb,i);assert x.shape==y.shape and np.isfinite(y).all();error=float(np.max(abs(x.astype(float)-y)))if x.size else 0;assert error<=1e-6,(i,error);errors.append(error)
for k in['nodes','skins','animations','meshes','materials','textures']:assert a.get(k)==b.get(k),k
assert a.get('samplers')==b.get('samplers'),'Unexpected source sampler change'
sampler_before=[dict(s)for s in b.get('samplers',[])]
for s in b.get('samplers',[]):s.update(magFilter=9728,minFilter=9728)
sys.path.insert(0,str(HERE));from patch_existing_fin_meshes import write
write(model,b,bytearray(bb))
for x,y in zip(a['images'],b['images']):
 av=a['bufferViews'][x['bufferView']];bv=b['bufferViews'][y['bufferView']];xx=ab[av.get('byteOffset',0):av.get('byteOffset',0)+av['byteLength']];yy=bb[bv.get('byteOffset',0):bv.get('byteOffset',0)+bv['byteLength']];assert xx==yy,'Embedded pixels changed'
(out/'fish.blend').write_bytes(source.read_bytes());(out/'fin-authoring.json').write_bytes((source.parent/'fin-authoring.json').read_bytes());r=dict(ok=True,kind='ordinary_fish_source_cold_export_parity',fresh_process=True,static_builders_disabled=True,runtime_static_build_calls=0,source=str(source),source_sha256=source_hash,reference=str(reference),reference_sha256=sha(reference),model_sha256=sha(model),maximum_array_error=max(errors),decoded_arrays_checked=len(errors),image_payloads_exact=True,rig_material_animations_document_bindings_exact=True,formal_acceptance=False,sampler_finalization={'before':sampler_before,'after':b.get('samplers',[]),'policy':'Explicit Closest source to nearest GLB without mip selection; no pixel change'});(out/'cold-export.validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
