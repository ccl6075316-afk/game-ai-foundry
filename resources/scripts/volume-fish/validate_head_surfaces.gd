extends SceneTree
## Regression: retain authored color-overlay blending and share the same head
## projection across material boundaries. Visual/source review remains separate.
func _initialize():call_deferred("run")
func overlay_preserved(mesh) -> bool:
    for si in mesh.mesh.get_surface_count():
        var original=mesh.mesh.surface_get_material(si)
        var active=mesh.get_active_material(si)
        if not active is StandardMaterial3D:return false
        if active.transparency!=original.transparency or active.albedo_color!=original.albedo_color or active.albedo_texture!=original.albedo_texture:return false
    return true
func run():
    var hall=load("res://scripts/aquarium/VolumeFishExhibit.gd").new();root.add_child(hall);hall.set_process(false)
    var config=JSON.parse_string(FileAccess.get_file_as_string("res://assets/models/fish/motion/body-opacity.json"))
    var checks: Array=[]
    for species in hall.SPECIES:
        hall._select_display(species)
        var entry: Dictionary=hall._selected()
        if species=="arapaima":
            var overlay=entry.model.find_child("Frontal_head_overlay",true,false)
            assert(overlay_preserved(overlay))
            var old=overlay.get_surface_override_material(0)
            var wrong:=ShaderMaterial.new();wrong.shader=load("res://scripts/aquarium/FishBodyOpaque.gdshader")
            overlay.set_surface_override_material(0,wrong)
            assert(not overlay_preserved(overlay),"Opaque overlay negative escaped")
            overlay.set_surface_override_material(0,old)
            checks.append({"species":species,"authored_overlay_surfaces":overlay.mesh.get_surface_count(),"opaque_overlay_negative_rejected":true})
        for mesh in entry.model.find_children("*","MeshInstance3D",true,false):
            for si in mesh.mesh.get_surface_count():
                var mat=mesh.get_active_material(si)
                if not mat is ShaderMaterial or not mat.shader.resource_path.ends_with("FishBodyOpaque.gdshader"):continue
                var expected: bool=species=="mahi_mahi" and str(mesh.name)=="Closed_body"
                assert((mat.get_shader_parameter("head_blend")==true)==expected,"Head projection leaked or missing")
                if expected:
                    var p: Dictionary=config.profiles[species].head_projection
                    assert(mat.get_shader_parameter("side_head")!=null and mat.get_shader_parameter("front_head")!=null)
                    assert(mat.get_shader_parameter("head_blend_x")==Vector2(p.blend_x[0],p.blend_x[1]))
                    assert(is_equal_approx(mat.get_shader_parameter("head_start"),p.start_x))
                    checks.append({"species":species,"mesh":str(mesh.name),"surface":si,"shared_continuous_projection":true})
    assert(checks.size()==5,"Missing head surfaces")
    var files: Dictionary={}
    for file in ["scripts/aquarium/FishSurfaceOwnership.gd","scripts/aquarium/FishBodyOpaque.gdshader","assets/models/fish/motion/body-opacity.json"]:files[file]=FileAccess.get_sha256("res://"+file)
    var f=FileAccess.open(OS.get_cmdline_user_args()[0],FileAccess.WRITE);f.store_string(JSON.stringify({"ok":true,"checks":checks,"files":files}));f.close();print("HEAD_SURFACES_OK");quit()
