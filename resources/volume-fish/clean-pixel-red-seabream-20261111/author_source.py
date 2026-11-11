"""Guarded image-only authoring in the current source, with independent export."""
from pathlib import Path
import sys,json,hashlib,argparse
import bpy
E=Path(__file__).resolve().parent;R=E.parents[1];sys.path[:0]=[str(R/'resources/scripts/volume-fish/portable'),str(R/'resources/scripts/volume-fish')]
from export_packed_fish_source import geometry_signature,normal_attribute_signature,float_uv_signature,part_signature,material_signature
from export_source import export_source
from source_snapshot import rig_action_snapshot
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
p=argparse.ArgumentParser()
for k in ['blend','bake','output']:p.add_argument('--'+k,type=Path,required=True)
a=p.parse_args(sys.argv[sys.argv.index('--')+1:]);proof=json.loads((a.bake/'bake.validation.json').read_text());assert proof['ok']and proof['stage']=='fins'and proof['body_before_fins_rgba_sha256']==proof['body_after_fins_rgba_sha256']
out=a.output.resolve();assert out.is_relative_to(E)and not out.exists();source=a.blend.resolve();before_source=sha(source)
bpy.ops.wm.open_mainfile(filepath=str(source));ob=next(o for o in bpy.data.objects if o.type=='MESH');mesh=ob.data;mat=mesh.materials[0]
def frozen():return [geometry_signature(ob),normal_attribute_signature(ob),float_uv_signature(mesh),part_signature(mesh),rig_action_snapshot()]
assert geometry_signature(ob)==mesh['foundry_normal_geometry_sha256'];assert normal_attribute_signature(ob)==mesh['foundry_exact_normal_sha256'];assert float_uv_signature(mesh)==mesh['foundry_exact_uv_sha256'];assert part_signature(mesh)==mesh['foundry_part_signature_sha256'];assert material_signature(mat)==mat['foundry_material_signature_sha256'];before=frozen()
atlas=a.bake/'atlas.png';assert sha(atlas)==proof['atlas_sha256'];node=next(n for n in mat.node_tree.nodes if n.type=='TEX_IMAGE');im=bpy.data.images.load(str(atlas.resolve()),check_existing=False);im.alpha_mode='STRAIGHT';im.colorspace_settings.name='sRGB';im.pack();node.image=im;assert frozen()==before;mat['foundry_material_signature_sha256']=material_signature(mat)
out.mkdir();bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(out/'fish.blend'));export=export_source(out/'fish.glb');assert frozen()==before and sha(source)==before_source
result={'ok':True,'kind':'source_owned_material_only_authoring','input_source_sha256':before_source,'bake_report_sha256':sha(a.bake/'bake.validation.json'),'model_sha256':sha(out/'fish.glb'),'source_sha256':sha(out/'fish.blend'),'geometry_UV_normals_ownership_rig_actions_exact':True,'export':export,'scope':'Material image only; current source guard verified before/after. Independent cold export and visual checks separate.'};(out/'source-authoring.validation.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'ok':True,'model_sha256':result['model_sha256']}))
