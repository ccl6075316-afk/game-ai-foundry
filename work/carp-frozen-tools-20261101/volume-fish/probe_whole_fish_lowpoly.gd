extends SceneTree
## Inspect the actual assembled fish and legal simplification floor, read-only.
var output=""
func _initialize():
    for arg in OS.get_cmdline_user_args():
        if arg.begins_with("--output="):output=arg.trim_prefix("--output=")
    assert(output.is_absolute_path() and output.simplify_path().begins_with(ProjectSettings.globalize_path("res://../plans/reviews/").simplify_path()))
    DirAccess.make_dir_recursive_absolute(output);call_deferred("run")
func run():
    var holder=Node3D.new();root.add_child(holder)
    var factory=load("res://scripts/aquarium/VolumeFishExhibit.gd").new();factory._load_profiles()
    preload("res://scripts/aquarium/FishAppearanceCache.gd").begin_entry()
    var profile:Dictionary=factory.profiles.zander
    factory._add_fish(holder,"zander",float(profile.real_length_cm)/100.,profile)
    var model:Node3D=factory.fish[-1].model
    var rows=[]
    for node in model.find_children("*","MeshInstance3D",true,false):
        if not node.visible:continue
        for si in node.mesh.get_surface_count():
            var a=node.mesh.surface_get_arrays(si);var importer=ImporterMesh.new()
            importer.add_surface(Mesh.PRIMITIVE_TRIANGLES,a);importer.generate_lods(60,60,[])
            var counts=[]
            for li in importer.get_surface_lod_count(0):counts.append(importer.get_surface_lod_indices(0,li).size()/3)
            var mat=node.get_active_material(si);var uniforms=[];var snippets=[]
            if mat is ShaderMaterial:
                for line in mat.shader.code.split("\n"):
                    if "VERTEX_ID" in line:snippets.append(line)
                for u in mat.shader.get_shader_uniform_list():
                    var value=mat.get_shader_parameter(u.name)
                    if value is Texture2D:uniforms.append({"name":u.name,"size":[value.get_width(),value.get_height()]})
                    elif "count" in u.name or "size" in u.name:uniforms.append({"name":u.name,"value":str(value)})
            var row={"node":str(model.get_path_to(node)),"surface":si,"vertices":a[Mesh.ARRAY_VERTEX].size(),"triangles":a[Mesh.ARRAY_INDEX].size()/3,"lods":counts,"uniforms":uniforms,"vertex_id_lines":snippets}
            rows.append(row);print("WHOLE_LOD ",JSON.stringify(row))
    var f=FileAccess.open(output.path_join("floors.validation.json"),FileAccess.WRITE);f.store_string(JSON.stringify({"species":"zander","production_changed":false,"surfaces":rows},"  "));f.close()
    factory.free();preload("res://scripts/aquarium/FishAppearanceCache.gd").clear();quit()
