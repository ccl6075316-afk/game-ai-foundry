extends SceneTree
## Test the actual hall's material installation and independent control UI.
var output: String
func _initialize() -> void:
    var args:=OS.get_cmdline_user_args();assert(args.size()==1,"Expected absolute report JSON path")
    output=args[0];call_deferred("run")
func run() -> void:
    var hall=load("res://scripts/aquarium/VolumeFishExhibit.gd").new();root.add_child(hall);hall.set_process(false)
    var data: Dictionary=JSON.parse_string(FileAccess.get_file_as_string("res://assets/models/fish/motion/surface-ownership.json"))
    var mouth_profiles: Dictionary=JSON.parse_string(FileAccess.get_file_as_string("res://assets/models/fish/motion/mouth-pigment.json")).profiles
    var head_profiles: Dictionary=JSON.parse_string(FileAccess.get_file_as_string("res://assets/models/fish/motion/head-source.json")).profiles
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
        if head_profiles.has(species):
            var h:Dictionary=head_profiles[species]
            assert(h.model_sha256==profile.model_sha256,"Stale head/source binding")
            var hm=entry.model.find_child(h.mesh,true,false) as MeshInstance3D
            var hs=hm.get_active_material(0) as ShaderMaterial
            assert(hs.get_shader_parameter("head_source_repair")==true)
            assert(hs.get_shader_parameter("mouth_source_projection")==h.mouth_enabled)
            assert(hs.get_shader_parameter("eye_gap_native").is_equal_approx(Vector2(h.eye_gap_native[0],h.eye_gap_native[1])))
            assert(h.eye_gap_native[0]>0.0 and h.eye_gap_native[1]>h.eye_gap_native[0],"No eye separation band")
            var e:Dictionary=h.eye
            assert(hs.get_shader_parameter("source_eye").is_equal_approx(Vector4(e.center[0],e.center[1],e.radius[0],e.radius[1])))
            var image:Image=hs.get_shader_parameter("source_texture").get_image()
            if image.is_compressed():assert(image.decompress()==OK)
            image.convert(Image.FORMAT_RGBA8)
            image.clear_mipmaps()
            var pixels=image.get_data()
            # Godot fixes RGB under transparent borders during import. Preserve
            # and verify every alpha byte and every opaque source RGB byte.
            for i in range(0,pixels.size(),4):
                if pixels[i+3]<243:pixels[i]=0;pixels[i+1]=0;pixels[i+2]=0
            var digest=HashingContext.new();assert(digest.start(HashingContext.HASH_SHA256)==OK);assert(digest.update(pixels)==OK)
            assert(digest.finish().hex_encode()==e.opaque_rgb_and_alpha_sha256,"Head shader uses different opaque source pixels or alpha")
            var donor=image.get_pixel(int(e.donor_u*image.get_width()),int(e.donor_v*image.get_height()))
            assert(donor.a>0.95,"Eye repair donor is transparent")
            assert(abs(e.donor_u-e.center[0])>e.radius[0]*1.25,"Eye donor samples the eye again")
            if h.mouth_enabled:
                var ho=hm.get_active_material(1) as ShaderMaterial
                for key in ["mouth_path","mouth_tangents","source_width_path","mouth_path_count","source_width_count","mouth_donor_window","mouth_source_edges","mouth_edge_count","model_path","model_tangents","model_path_count","model_aspect","model_gap","model_lip_roll","upper_skin_patch","lower_skin_patch"]:
                    assert(hs.get_shader_parameter(key)==ho.get_shader_parameter(key),"Lip seam uses two different source projections")
        if mouth_profiles.has(species):
            var p:Dictionary=mouth_profiles[species]
            assert(p.model_sha256==profile.model_sha256,"Stale mouth pigment model")
            var mouth_mesh=entry.model.find_child(p.mesh,true,false) as MeshInstance3D
            var skin=mouth_mesh.get_active_material(p.skin_surface) as ShaderMaterial
            var oral=mouth_mesh.get_active_material(p.oral_surface) as ShaderMaterial
            assert(skin.get_shader_parameter("mouth_source_projection")==true)
            assert(oral.shader.resource_path=="res://scripts/aquarium/FishMouthPigment.gdshader")
            assert(oral.get_shader_parameter("source_texture")==skin.get_shader_parameter("source_texture"),"Oral pigment has wrong source image")
            var donor_image: Image=skin.get_shader_parameter("source_texture").get_image()
            assert(donor_image.get_size()==Vector2i(p.source_size[0],p.source_size[1]),"Mouth source canvas mismatch")
            for key in ["pigment_top_uv","pigment_bottom_uv"]:
                var uv=p[key];var donor=donor_image.get_pixel(int(uv[0]*donor_image.get_width()),int(uv[1]*donor_image.get_height()))
                assert(donor.a>0.99 and max(donor.r,max(donor.g,donor.b))>60.0/255.0,"Transparent or black-outline mouth donor")
            for mat in [skin,oral]:
                assert(mat.get_shader_parameter("head_source_repair")==true)
                assert(mat.get_shader_parameter("mouth_source_projection")==true)
            var rim: PackedVector2Array=mouth_mesh.mesh.surface_get_arrays(p.oral_surface)[Mesh.ARRAY_TEX_UV2]
            var oral_arrays=mouth_mesh.mesh.surface_get_arrays(p.oral_surface)
            var oral_positions: PackedVector3Array=oral_arrays[Mesh.ARRAY_VERTEX]
            var oral_indices: PackedInt32Array=oral_arrays[Mesh.ARRAY_INDEX]
            assert(rim.size()>20,"Missing measured oral rim")
            var near_count=0;var deep_count=0;var upper_count=0;var lower_count=0
            for i in rim.size():
                var uv=rim[i]
                if abs(uv.x-abs(oral_positions[i].z))<0.0001:near_count+=1
                if uv.y>0.5:upper_count+=1
                else:lower_count+=1
            for i in range(0,oral_indices.size(),3):
                var z=0.0;var width=0.0
                for j in 3:
                    var ix=oral_indices[i+j];z+=oral_positions[ix].z/3.0;width+=rim[ix].x/3.0
                if width-abs(z)>p.rim_width_native:deep_count+=1
            assert(near_count>10 and deep_count>10 and upper_count>10 and lower_count>10,"Incomplete mouth rim/recess coordinates")
            for key in ["rim_width_native","recess_width_native"]:assert(is_equal_approx(oral.get_shader_parameter(key),p[key]))
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
    for file in ["scripts/aquarium/FishHeadSource.gd","scripts/aquarium/FishHeadSource.gdshaderinc","assets/models/fish/motion/head-source.json","scripts/aquarium/VolumeFishExhibit.gd","scripts/aquarium/FoundryFishMotion.gd","scripts/aquarium/FishSurfaceOwnership.gd","scripts/aquarium/FishSurfaceOwnership.gdshader","scripts/aquarium/FishBodyOpaque.gdshader","scripts/aquarium/FishMouthPigment.gd","scripts/aquarium/FishMouthPigment.gdshader","assets/models/fish/motion/mouth-pigment.json","assets/models/fish/motion/body-opacity.json","assets/models/fish/motion/surface-ownership.json","assets/models/fish/motion/motion.json"]:files[file]=FileAccess.get_sha256("res://"+file)
    var f:=FileAccess.open(output,FileAccess.WRITE);assert(f!=null);f.store_string(JSON.stringify({"ok":true,"checks":records,"files":files,"limit":"Structural material ownership and UI contract; GPU compile, hidden-fin visual review and comparison with source are separate checks."}));f.close()
    hall.queue_free();await process_frame;quit()
