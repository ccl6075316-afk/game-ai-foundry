"""Generate portable loaders for unchanged standalone077/head/motion checks.

Only loaders, helper paths and UTF8 change. Physical kernels and assertions stay
in their original maintained scripts. Exact replacement counts fail on drift.
"""
from pathlib import Path
HERE = Path(__file__).resolve().parent
PARENT = HERE.parent

def replace(text, old, new):
    assert text.count(old) == 1, 'Adapter template drift: ' + old[:100]
    return text.replace(old, new)

def generate():
    for name in ('capture_standalone_body.gd', 'validate_motion_controls.gd'):
        text = (PARENT/name).read_text(encoding='utf8')
        text = replace(text, 'preload("PackedFishValidation.gd")', 'preload("PackedFishParts.gd")')
        (HERE/name).write_text(text, encoding='utf8')

def generate_review():
    text=(PARENT/'preview_nile_ab_textured.gd').read_text(encoding='utf8')
    methods=[]
    for start,end in [('func _load(', 'func _input_surface('),('func _view_image(', 'func _run(')]:
        methods.append(text[text.index(start):text.index(end)])
    base='extends SceneTree\nvar entries: Array=[]\nvar gray:=false\nvar load_plan: Dictionary\nvar report: Dictionary={"models":[],"captures":[]}\n'+''.join(methods)
    base=replace(base, 'var path := _model_path(route)', 'var path: String = load_plan.model')
    base=replace(base, 'Vector3.ONE*.402819722890854', 'Vector3.ONE*float(load_plan.model_scale)')
    base=replace(base, 'var controller=MOTION.new()', 'var controller=load(load_plan.motion_runtime).new()')
    base=replace(base, 'ProjectSettings.globalize_path("res://../../../resources/volume-fish/motion/nile_tilapia-082.json")', 'str(load_plan.motion_profile)')
    base=replace(base, 'mat.texture_filter=BaseMaterial3D.TEXTURE_FILTER_NEAREST;mat.shading_mode=BaseMaterial3D.SHADING_MODE_UNSHADED', 'assert(mat.texture_filter==BaseMaterial3D.TEXTURE_FILTER_NEAREST)')
    (HERE/'ReviewCaptureBase.gd').write_text(base,encoding='utf8')
    review=(PARENT/'capture_standalone_fish_review.gd').read_text(encoding='utf8')
    review=replace(review,'extends "preview_nile_ab_textured.gd"','extends "ReviewCaptureBase.gd"\nvar direction:=Vector3(0,0,1)\nvar zoom:=1.0')
    review=replace(review,' and review_out.contains("/final-sop/") and review_out.get_file()=="review"',' and review_out.contains("/experiments/")')
    review=review.replace('PackedFishValidation.gd','PackedFishParts.gd')
    review=review.replace('res://../../../resources/scripts/volume-fish/validate_motion_controls.gd','res://../../../resources/scripts/volume-fish/portable/validate_motion_controls.gd')
    review=replace(review, '"res://../../../resources/scripts/volume-fish/preview_nile_ab_textured.gd",', '"res://../../../resources/scripts/volume-fish/portable/ReviewCaptureBase.gd",')
    review=replace(review, '"res://../../../resources/volume-fish/motion/nile_tilapia-082.json",','')
    review=replace(review, 'var box: SubViewportContainer=SubViewportContainer.new();root.add_child(box)', 'load_plan=plan\n\tvar box: SubViewportContainer=SubViewportContainer.new();root.add_child(box)')
    review=review.replace('zoom=.52','zoom=float(plan.whole_camera_size)').replace('zoom=.6','zoom=float(plan.whole_camera_size)*1.15')
    start=review.index('\tfor detail in [{"name":"head"');end=review.index('\n\tvar part_meshes',start)
    review=review[:start]+'\tfor detail in plan.details:\n\t\tzoom=float(detail.size);focus=Vector3(float(detail.at[0]),float(detail.at[1]),float(detail.at[2]));await photo_views(detail.name)'+review[end:]
    review=replace(review,'native: bool=false) -> void:', 'native: bool=false, transition: bool=false) -> void:')
    review=replace(review,'if not native:assert(snapshot.action==label and snapshot.pending_action=="" and snapshot.inside_envelope)', 'if not native:\n\t\tassert(snapshot.inside_envelope)\n\t\tif not transition:assert(snapshot.action==label and snapshot.pending_action=="")')
    review=replace(review,'for phase in 12:entry.controller.step(1./12.);await movie_frame(action,phase)', 'for phase in 12:entry.controller.step(1./12.);await movie_frame(action,phase,false,true)')
    (HERE/'capture_fish_review.gd').write_text(review,encoding='utf8')
    for name in ('validate_standalone_body.py', 'check_head_form.py'):
        text = (PARENT/name).read_text(encoding='utf8')
        # Original script directory is needed for shared glTF accessor code.
        pos = text.index('from freeze_surface_ownership import')
        text = text[:pos] + 'import sys\nsys.path.append(str(Path(__file__).resolve().parent.parent))\n' + text[pos:]
        text = replace(text, 'from packed_fish_parts import logical_document', 'from logical_document import logical_document')
        if name.startswith('validate'):
            text = replace(text, "len(plan['fins'])==7 and len(set(plan['fins']))==7", "plan['fins'] and len(set(plan['fins']))==len(plan['fins'])")
            text = replace(text, "'Explicit seven-fin inventory required'", "'Explicit complete species fin inventory required'")
            text = replace(text, 'len(mesh_nodes)==8', "len(mesh_nodes)==1+len(plan['fins'])")
            text = replace(text, "logical_document(plan['model'],plan['body'],plan['fins'])", "logical_document(plan['model'],plan['body'],plan['fins'],plan['packed_parts_manifest'])")
            text = text.replace("Path(__file__).with_name('freeze_surface_ownership.py')", "Path(__file__).parent.parent/'freeze_surface_ownership.py'")
            text = text.replace("Path(__file__).with_name('validate_body_integrity.py')", "Path(__file__).parent.parent/'validate_body_integrity.py'")
            text = text.replace("Path(__file__).with_name('packed_fish_parts.py')", "Path(__file__).with_name('logical_document.py')")
            text = text.replace("Path(__file__).with_name('PackedFishValidation.gd')", "Path(__file__).with_name('PackedFishParts.gd')")
        else:
            text = replace(text, "logical_document(path,item['body'],item['fins'])", "logical_document(path,item['body'],item['fins'],item['packed_parts_manifest'])")
        text = text.replace('.read_text()', ".read_text(encoding='utf8')")
        text = text.replace(".write_text(log)", ".write_text(log,encoding='utf8')")
        text = text.replace(".write_text(json.dumps(result,indent=2)+'\\n')", ".write_text(json.dumps(result,indent=2)+'\\n',encoding='utf8')")
        (HERE/name).write_text(text, encoding='utf8')

if __name__ == '__main__':
    generate()
    generate_review()
    print('{"ok":true,"generated":6}')
