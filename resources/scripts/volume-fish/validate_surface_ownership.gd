extends SceneTree
## Test the actual hall's material installation and independent control UI.
var output: String
func _initialize() -> void:
    var args:=OS.get_cmdline_user_args();assert(args.size()==1,"Expected absolute report JSON path")
    output=args[0];call_deferred("run")
func run() -> void:
    var hall=load("res://scripts/aquarium/VolumeFishExhibit.gd").new();root.add_child(hall);hall.set_process(false)
    var data: Dictionary=JSON.parse_string(FileAccess.get_file_as_string("res://assets/models/fish/motion/surface-ownership.json"))
    var records: Array=[]
    for species in hall.SPECIES:
        hall._select_display(species)
        var entry: Dictionary=hall._selected();var profile: Dictionary=data.profiles[species]
        assert(FileAccess.get_sha256("res://assets/models/fish/"+species+".glb")==profile.model_sha256,"Stale model ownership")
        var fin_count:=0;var skin_count:=0
        for mesh in entry.model.find_children("*","MeshInstance3D",true,false):
            var label: String=str(mesh.name);var is_fin: bool=profile.fins.has(label)
            if not is_fin and not profile.skins.has(label):continue
            var surfaces: Dictionary=profile.fins[label] if is_fin else profile.skins[label]
            for key in surfaces:
                var material=mesh.get_active_material(int(key));assert(material is ShaderMaterial,"Fin source leaked onto body or outline missing")
                assert(material.shader.resource_path==("res://scripts/aquarium/FishSurfaceOwnership.gdshader" if is_fin else "res://scripts/aquarium/FishBodyOpaque.gdshader"))
                assert(material.get_shader_parameter("fin")==is_fin)
                if is_fin:
                    assert(material.get_shader_parameter("edge_count")>0,"Empty fin outline")
                    assert(material.get_shader_parameter("ink_width")>0,"Invisible fin outline")
                    fin_count+=1
                else:
                    assert(material.get_shader_parameter("patch_count")>0,"Empty skin cleanup mask")
                    skin_count+=1
        assert(fin_count==profile.fins.size(),"Incomplete fin material inventory")
        assert(skin_count>0 or profile.skin_status=="existing_separate_clean_body_texture","Skin cleanup unverified")
        for preset in ["舒缓","常速","快速","大幅展示"]:
            hall._motion_preset(preset)
            var selected: Dictionary=entry.controller.motion_controls()
            for key in selected:assert(is_equal_approx(float(hall.motion_sliders[key].value),float(selected[key])),"UI and controller disagree")
        hall.motion_sliders.fin_amplitude.value=0.0
        assert(entry.controller.motion_controls().fin_amplitude==0.0)
        assert(entry.controller.motion_controls().body_amplitude==2.5,"Fin slider modifies body amplitude")
        records.append({"species":species,"ok":true,"fin_surfaces":fin_count,"skin_surfaces":skin_count,"skin_status":profile.skin_status,"four_presets_and_independent_slider":true,"model_sha256":profile.model_sha256})
        print("SURFACE_AND_UI_TEST ",species," ",fin_count," ",skin_count)
    var files: Dictionary={}
    for file in ["scripts/aquarium/VolumeFishExhibit.gd","scripts/aquarium/FoundryFishMotion.gd","scripts/aquarium/FishSurfaceOwnership.gd","scripts/aquarium/FishSurfaceOwnership.gdshader","scripts/aquarium/FishBodyOpaque.gdshader","assets/models/fish/motion/body-opacity.json","assets/models/fish/motion/surface-ownership.json","assets/models/fish/motion/motion.json"]:files[file]=FileAccess.get_sha256("res://"+file)
    var f:=FileAccess.open(output,FileAccess.WRITE);assert(f!=null);f.store_string(JSON.stringify({"ok":true,"checks":records,"files":files,"limit":"Structural material ownership and UI contract; GPU compile, hidden-fin visual review and comparison with source are separate checks."}));f.close()
    hall.queue_free();await process_frame;quit()
