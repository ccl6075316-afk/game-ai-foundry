extends SceneTree
## Native pre-inked GLB fin charts: do not require a second procedural outline.
func base_pixels(texture:Texture2D)->PackedByteArray:
    var im=texture.get_image().duplicate()
    if im.is_compressed():assert(im.decompress()==OK)
    im.clear_mipmaps();im.convert(Image.FORMAT_RGBA8);return im.get_data()
func _initialize():call_deferred("run")
func run():
    var args=OS.get_cmdline_user_args();assert(args.size()>=2);var plan=JSON.parse_string(FileAccess.get_file_as_string(args[0]));assert(not plan.items.is_empty());var mutated=false
    var hall=load("res://scripts/aquarium/VolumeFishExhibit.gd").new();root.add_child(hall);hall.set_process(false);hall.paused=true;var rows=[]
    var ownership=JSON.parse_string(FileAccess.get_file_as_string("res://assets/models/fish/motion/surface-ownership.json")).profiles
    for spec in plan.items:
        var species:String=spec.species;hall._select_display(species);var e:Dictionary=hall._selected();assert(FileAccess.get_sha256(e.model.scene_file_path)==spec.model_sha256);var p:Dictionary=ownership[species];assert(p.fins.size()==spec.fins.size());var fins=[]
        for name in spec.fins:
            var node=e.model.find_child(name,true,false) as MeshInstance3D;assert(node!=null and node.visible and node.skin!=null)
            var definition:Dictionary=spec.fins[name]
            for si in node.mesh.get_surface_count():
                var original=node.mesh.surface_get_material(si) as StandardMaterial3D;var actual=node.get_active_material(si) as ShaderMaterial
                assert(original!=null and actual!=null)
                if e.model.has_meta("final_asset157_receipt"):
                    var frozen:Dictionary=e.model.get_meta("final_asset157_receipt");assert(frozen.static_builders_disabled and frozen.static_build_calls==0)
                    if "--mutate-native-pixel" in args and not mutated:
                        var im=(actual.get_shader_parameter("source_texture")as Texture2D).get_image().duplicate();im.clear_mipmaps();im.convert(Image.FORMAT_RGBA8);im.set_pixel(0,0,Color(1,0,1,1));actual.set_shader_parameter("source_texture",ImageTexture.create_from_image(im));mutated=true
                    assert(base_pixels(actual.get_shader_parameter("source_texture"))==base_pixels(original.albedo_texture),"Final portable native pixels changed")
                    assert(actual.shader.code==load("res://scripts/aquarium/FishSurfaceOwnership.gdshader").code,"Final portable fin shader changed")
                else:
                    assert(actual.get_shader_parameter("source_texture")==original.albedo_texture,"Native fin chart rebound")
                    assert(actual.shader.resource_path=="res://scripts/aquarium/FishSurfaceOwnership.gdshader")
                assert(actual.get_shader_parameter("fin")==true)
                assert(actual.get_shader_parameter("edge_count")==0 and is_zero_approx(actual.get_shader_parameter("ink_width")),"Native ink must not receive an extra contour")
                assert(original.albedo_texture.get_size()==Vector2(definition.native_size[0],definition.native_size[1]),"Native fin resampled")
                assert(node.mesh.get("_surfaces")[si].get("lods",[]).is_empty(),"This native full-detail branch cannot select rejected coarse fin geometry")
            fins.append({"name":name,"native_size":definition.native_size,"bound_to_original_glb_chart":true})
        var body=e.model.find_child(spec.body,true,false) as MeshInstance3D;assert(body!=null and body.visible)
        var native=body.mesh.surface_get_material(0) as StandardMaterial3D;var current=body.get_active_material(0) as ShaderMaterial;var source_copy:Node3D
        assert(current!=null)
        if native==null:
            # A declared139 replacement owns a frozen ShaderMaterial rather
            # than the original imported StandardMaterial. Verify that exact
            # replacement, then compare full native pixels with the rig GLB.
            assert(e.model.has_meta("mouth_repair139_receipt"))
            assert(load("res://scripts/aquarium/MouthRepair139.gd").new().validate(e.model,species).ok)
            source_copy=(load(e.model.scene_file_path) as PackedScene).instantiate()
            native=(source_copy.find_child(spec.body,true,false) as MeshInstance3D).mesh.surface_get_material(0) as StandardMaterial3D
            assert(native!=null and base_pixels(current.get_shader_parameter("source_texture"))==base_pixels(native.albedo_texture),"Portable body pixels differ from native GLB source")
        else:assert(current.get_shader_parameter("source_texture")==native.albedo_texture)
        assert(native.albedo_texture.get_size()==Vector2(spec.body_native_size[0],spec.body_native_size[1]))
        assert(current.shader.code.contains("chart112_rest_position=rest114_position;chart112_rest_normal=rest114_normal;"))
        assert(not current.shader.code.contains("front112_rest=VERTEX;front112_normal=NORMAL;"),"Front colour reads posed coordinates")
        for si in body.mesh.get_surface_count():assert(body.mesh.get("_surfaces")[si].get("lods",[]).is_empty())
        rows.append({"species":species,"ok":true,"model_sha256":spec.model_sha256,"fins":fins,"body_native_size":spec.body_native_size,"body_shader_sha256":current.shader.code.sha256_text(),"lod_branch":"full_detail_only","chart_rest114":true})
        if source_copy!=null:source_copy.free()
    var f=FileAccess.open(args[1],FileAccess.WRITE);f.store_string(JSON.stringify({"ok":rows.size()==plan.items.size(),"checks":rows,"checker_sha256":FileAccess.get_sha256(get_script().resource_path),"ownership_sha256":FileAccess.get_sha256("res://assets/models/fish/motion/surface-ownership.json"),"motion_config_sha256":FileAccess.get_sha256("res://assets/models/fish/motion/motion.json"),"scope":"Cold actual hall: complete native GLB fin texture/size/skin/visibility, pre-inked contours without extra outline, original derived-body binding and immutable material coordinates, explicit full-detail LOD. Anatomy, complete contact, image RGB provenance and GPU coverage checked separately."}));f.close();quit()
