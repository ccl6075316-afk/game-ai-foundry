"""Bind a reviewed color-only atlas into the editable guarded source and export."""
import argparse,hashlib,json,sys
from pathlib import Path
import bpy
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2];sys.path[:0]=[str(HERE),str(HERE/'portable')]
from export_packed_fish_source import material_signature,export_packed_source,float_uv_signature,part_signature
from restore_fin_source_normals import geometry_signature,normal_attribute_signature
from source_snapshot import rig_action_snapshot
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def main(a):
    out=a.output.resolve();assert out.is_relative_to(ROOT/'projects/fishing-2d/experiments') and not out.exists();proof=json.loads(a.bake_report.read_text(encoding='utf8'));assert proof['ok'] and sha(a.atlas)==proof['atlas_sha256']
    bpy.ops.wm.open_mainfile(filepath=str(a.blend.resolve()));obs=[o for o in bpy.data.objects if o.type=='MESH'];assert len(obs)==1;ob=obs[0];m=ob.data
    before=(rig_action_snapshot(),geometry_signature(ob),normal_attribute_signature(ob),float_uv_signature(m),part_signature(m),[[(x.group,x.weight) for x in v.groups] for v in m.vertices])
    mat=m.materials[0];assert material_signature(mat)==mat['foundry_material_signature_sha256'];node=next(n for n in mat.node_tree.nodes if n.type=='TEX_IMAGE');old_image_hash=hashlib.sha256(node.image.packed_file.data).hexdigest();image=bpy.data.images.load(str(a.atlas.resolve()),check_existing=False);image.alpha_mode='STRAIGHT';image.colorspace_settings.name='sRGB';image.pack();node.image=image;mat['foundry_material_signature_sha256']=material_signature(mat)
    after=(rig_action_snapshot(),geometry_signature(ob),normal_attribute_signature(ob),float_uv_signature(m),part_signature(m),[[(x.group,x.weight) for x in v.groups] for v in m.vertices]);assert before==after
    out.mkdir();bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(out/'fish.blend'));export=export_packed_source(out/'fish.glb')
    result={'ok':True,'kind':'source_owned_color_only_atlas_revision','species':proof['species'],'source_input_sha256':sha(a.blend),'old_embedded_image_sha256':old_image_hash,'new_image_sha256':sha(a.atlas),'bake_report_sha256':sha(a.bake_report),'model_sha256':sha(out/'fish.glb'),'blend_sha256':sha(out/'fish.blend'),'same_geometry_normals_UV_parts_skin_rig_actions':True,'export':export,'formal_acceptance':False};(out/'source-authoring.validation.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'ok':True,'model_sha256':result['model_sha256']}))
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for k in ['blend','atlas','bake-report','output']:p.add_argument('--'+k,required=True,type=Path)
    main(p.parse_args(sys.argv[sys.argv.index('--')+1:]))
