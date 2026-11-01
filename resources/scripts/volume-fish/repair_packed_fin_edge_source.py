"""Save a bounded fin-edge image repair in an otherwise exact packed fish source."""
import argparse,hashlib,json,sys
from pathlib import Path
import bpy
ROOT=Path(__file__).resolve().parents[3]
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
p=argparse.ArgumentParser(description=__doc__)
for k in ['blend','repair','output','tool-root']:p.add_argument('--'+k,type=Path,required=True)
a=p.parse_args(sys.argv[sys.argv.index('--')+1:]);tool=a.tool_root.resolve();sys.path[:0]=[str(tool/'portable'),str(tool)]
from export_packed_fish_source import geometry_signature,normal_attribute_signature,float_uv_signature,part_signature,material_signature
from export_source import export_source
from source_snapshot import rig_action_snapshot
report=json.loads(a.repair.read_text(encoding='utf8'));assert report['ok'] and report['alpha_exact'] and (report.get('pixels_outside_declared_fin_edge_bands_exact') or report.get('pixels_outside_declared_edit_mask_exact'));out=a.output.resolve();assert out.is_relative_to(ROOT/'projects/fishing-2d/experiments') and not out.exists()
bpy.ops.wm.open_mainfile(filepath=str(a.blend.resolve()));ob=next(o for o in bpy.data.objects if o.type=='MESH');mesh=ob.data;mat=mesh.materials[0]
def frozen():return [geometry_signature(ob),normal_attribute_signature(ob),float_uv_signature(mesh),part_signature(mesh),rig_action_snapshot()]
assert geometry_signature(ob)==mesh['foundry_normal_geometry_sha256'];assert normal_attribute_signature(ob)==mesh['foundry_exact_normal_sha256'];assert float_uv_signature(mesh)==mesh['foundry_exact_uv_sha256'];assert part_signature(mesh)==mesh['foundry_part_signature_sha256'];assert material_signature(mat)==mat['foundry_material_signature_sha256'];before=frozen()
atlas=Path(report['atlas']);assert sha(atlas)==report['atlas_sha256'];node=next(n for n in mat.node_tree.nodes if n.type=='TEX_IMAGE');old=node.image;image=bpy.data.images.load(str(atlas),check_existing=False);image.alpha_mode='STRAIGHT';image.colorspace_settings.name='sRGB';image.pack();node.image=image
assert frozen()==before
mat['foundry_material_signature_sha256']=material_signature(mat)
out.mkdir(parents=True);bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(out/'fish.blend'));proof=export_source(out/'fish.glb');assert frozen()==before
data={'ok':True,'kind':'source_owned_fin_edge_material_repair','input_blend_sha256':sha(a.blend),'repair_report_sha256':sha(a.repair),'output_blend_sha256':sha(out/'fish.blend'),'output_model_sha256':sha(out/'fish.glb'),'geometry_normals_UV_part_ownership_rig_actions_exact':True,'old_material_signature_validated_before_edit':True,'new_material_signature_after_bounded_image_only_change':True,'export_proof':proof,'scope':'Material image edit only; static fix packed in editable source. Separate fresh-process cold export and final gates required.'};(out/'source-repair.validation.json').write_text(json.dumps(data,indent=2)+'\n',encoding='utf8');print(json.dumps({'ok':True,'model_sha256':data['output_model_sha256']}))
