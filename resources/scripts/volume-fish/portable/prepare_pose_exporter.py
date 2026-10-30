"""Create the portable adapter of the established unchanged177/490 pose schedule.

Only resource/partition/profile loading differs. Physical checks and all poses
are retained. This generator is an explicit development step, never game code.
"""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4]
source=ROOT/'resources/scripts/volume-fish/export_runtime_fin_roots.gd'
target=Path(__file__).with_name('export_fin_poses.gd')
code=source.read_text(encoding='utf8')
def replace(old,new):
    global code
    assert code.count(old)==1,old
    code=code.replace(old,new)
replace('preload("PackedFishValidation.gd")','preload("PackedFishParts.gd")')
replace('var logical: Dictionary=PACKED_PARTS.surfaces(entry,spec)','var logical: Dictionary=PACKED_PARTS.surfaces(entry,spec) if spec.get("packed_parts_manifest","")!="" else {"ok":true,"packed":false,"surfaces":PACKED_PARTS.ordinary_surfaces(entry)}\n    assert(logical.get("ok",false),"Portable actual partition rejected")')
old='''        var resource_path=ProjectSettings.localize_path(path.replace("\\\\","/"))
        if resource_path.begins_with("res://"):
            # Installed assets use precisely the imported resource the game loads.
            var packed=load(resource_path) as PackedScene;assert(packed!=null);model=packed.instantiate()
        else:
            var document=GLTFDocument.new();var state=GLTFState.new();assert(document.append_from_file(path,state)==OK);model=document.generate_scene(state)'''
replace(old,'''        # Explicit standalone candidate: exactly the reviewed portable loader.
        var document=GLTFDocument.new();var state=GLTFState.new();assert(document.append_from_file(path,state)==OK);model=document.generate_scene(state)''')
replace('var profile: Dictionary=profiles[spec.species];model.scale','var profile: Dictionary=JSON.parse_string(FileAccess.get_file_as_string(spec.motion_profile));assert(FileAccess.get_sha256(spec.motion_profile)==spec.motion_profile_sha256 and profile.species==spec.species);model.scale')
replace('get_base_dir().path_join("PackedFishValidation.gd")','get_base_dir().path_join("PackedFishParts.gd")')
replace('        report["motion_range_revision"]=1','        report["actual_motion_profile"]=spec.motion_profile\n        report["actual_motion_profile_sha256"]=FileAccess.get_sha256(spec.motion_profile)\n        report["loader_scope"]="Explicit standalone GLB and native profile; game config/exhibit hashes are context snapshots, no canonical fish is replaced."\n        report["motion_range_revision"]=1')
replace('"ids":ids,"edges":edges}', '"ids":ids,"edges":edges,"outward_axis":spec.fins.get(name,{}).get("diagnostic_outward_axis",[0,0,0])}')
replace('    var s: Skeleton3D=entry.skeleton;s.force_update_all_bone_transforms();', '''    if variant=="envelope":
        var selected := label=="Static"
        for row in plan.items[0].get("diagnostic_pose_filter",[]):
            if row.action==label and is_equal_approx(float(row.seconds),seconds):selected=true
        if not selected:return
    var s: Skeleton3D=entry.skeleton;s.force_update_all_bone_transforms();''')
replace('            membranes[surface.name]={"vertices_m":membrane_points,"triangles":Array(triangles)}','''            membranes[surface.name]={"vertices_m":membrane_points,"triangles":Array(triangles)}
            var axis := Vector3(surface.outward_axis[0],surface.outward_axis[1],surface.outward_axis[2])
            if axis.length_squared()>0:
                var gains := [];var rest := []
                for vi in surface.vertices.size():
                    var gain := Vector3.ZERO
                    for slot in surface.count:
                        var at: int=vi*int(surface.count)+slot
                        gain+=(transforms[surface.joints[at]].basis*axis)*surface.weights[at]
                    gains.append([gain.x,gain.y,gain.z]);var v: Vector3=surface.vertices[vi];rest.append([v.x,v.y,v.z])
                membranes[surface.name]["outward_gain_m_per_native_unit"]=gains
                membranes[surface.name]["rest_vertices_native"]=rest''')
replace('        save_json(out+"/export.validation.json",report);','        if variant=="envelope":report["diagnostic_only"]=true;report["sample_limit"]="Frozen failed-pose subset and Static for actual displacement gains; not a177/490 delivery gate."\n        save_json(out+"/export.validation.json",report);')
code='# Portable loading adapter; pose schedule copied without geometric or coverage changes.\n'+code
if target.exists():assert target.read_text(encoding='utf8')==code,'Refuse overwriting changed adapter'
else:target.write_text(code,encoding='utf8')
print(target)
