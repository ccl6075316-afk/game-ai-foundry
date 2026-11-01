extends SceneTree
var hall
var out: String
var profiles: Dictionary
var opaque_profiles: Dictionary
static func validate_dynamic_106_shader(model: Node3D, species: String, mesh: MeshInstance3D, surface: int, material: ShaderMaterial) -> Dictionary:
    if species!="black_seabream" or model==null or mesh==null or str(mesh.name)!="Closed_body" or surface!=0 or not model.is_ancestor_of(mesh):
        return {"ok":false,"reason":"Unknown dynamic body shader identity"}
    if material==null or material.shader==null or not material.shader.resource_path.is_empty():
        return {"ok":false,"reason":"Expected106 generated shader"}
    if mesh.mesh==null or mesh.get_active_material(surface)!=material:
        return {"ok":false,"reason":"106 material is not active on actual body surface"}
    var eye: Dictionary=model.get_meta("eye_ownership_106_receipt",{})
    var lod: Dictionary=model.get_meta("eye_lod_106_receipt",{})
    if eye.is_empty() or lod.is_empty():return {"ok":false,"reason":"Missing106 eye/LOD receipt"}
    var paths: Dictionary={"model_sha256":"res://assets/models/fish/black_seabream.glb",
        "helper_sha256":"res://scripts/aquarium/FishEyeOwnership.gd","template_sha256":"res://scripts/aquarium/FishEyeOwnership.gdshaderinc",
        "profile_sha256":"res://assets/models/fish/motion/eye-ownership-106.json"}
    var digests: Dictionary={}
    for key in paths:
        if not FileAccess.file_exists(paths[key]):return {"ok":false,"reason":"Missing mandatory106 dependency: "+paths[key]}
        digests[key]=FileAccess.get_sha256(paths[key])
        if eye.get(key,"")!=digests[key]:return {"ok":false,"reason":"Stale106 receipt hash: "+key}
    var lod_path: String="res://scripts/aquarium/FishEyeLod106.gd"
    if not FileAccess.file_exists(lod_path):return {"ok":false,"reason":"Missing mandatory106 LODhelper"}
    var lod_sha:=FileAccess.get_sha256(lod_path)
    if lod.get("helper_sha256","")!=lod_sha or lod.get("config_sha256","")!=digests.profile_sha256 or lod.get("model_sha256","")!=digests.model_sha256 or eye.get("lod_exception_receipt")!=lod:
        return {"ok":false,"reason":"Stale106 LODhelper/config/model receipt"}
    if model.scene_file_path!=paths.model_sha256 or not eye.get("mesh_after") is Dictionary or eye.mesh_after.get("mesh_resource_id",-1)!=mesh.mesh.get_instance_id():
        return {"ok":false,"reason":"Receipt does not own actual106 mesh/model"}
    var generated: String=material.shader.code.sha256_text()
    if eye.get("generated_shader_sha256","")!=generated:return {"ok":false,"reason":"Generated106 shader code hash differs from install receipt"}
    var template: String=FileAccess.get_file_as_string(paths.template_sha256)
    if template.is_empty() or not material.shader.code.contains(template):return {"ok":false,"reason":"Generated106 code lacks complete current template"}
    # Ignore comments, then reject all coverage-changing shader identifiers.
    var tokens:=RegEx.new()
    tokens.compile('(?s)//[^\\n]*|/\\*.*?\\*/|[A-Za-z_][A-Za-z_0-9]*|[^\\s]')
    for item in tokens.search_all(material.shader.code):
        var token: String=item.get_string()
        if token.begins_with("//") or token.begins_with("/*"):continue
        if token=="ALPHA" or token.begins_with("ALPHA_") or token=="discard":return {"ok":false,"reason":"Forbidden coverage token in106 code: "+token}
    var config=JSON.parse_string(FileAccess.get_file_as_string(paths.profile_sha256))
    if not config is Dictionary or not config.get("profiles") is Dictionary or not config.profiles.get(species) is Dictionary:return {"ok":false,"reason":"Invalid106 config"}
    var profile: Dictionary=config.profiles[species]
    if not profile.get("opaque_skin") is Dictionary:return {"ok":false,"reason":"Missing frozen106 opaque donor"}
    var donor: Dictionary=profile.opaque_skin
    if not FileAccess.file_exists(donor.get("path","")):return {"ok":false,"reason":"Missing106 donor file"}
    if FileAccess.get_sha256(donor.path)!=donor.get("sha256","") or eye.get("fallback_texture_sha256","")!=donor.sha256:return {"ok":false,"reason":"Stale106 donor file"}
    var actual:=material.get_shader_parameter("opaque_skin") as Texture2D
    if actual==null or actual.get_size()!=Vector2(profile.source_size[0],profile.source_size[1]):return {"ok":false,"reason":"Invalid106 actual opaque_skin texture"}
    var expected:=Image.new()
    if expected.load_png_from_buffer(FileAccess.get_file_as_bytes(donor.path))!=OK:return {"ok":false,"reason":"Cannot decode106 opaque donor"}
    expected.convert(Image.FORMAT_RGBA8)
    var image:=actual.get_image()
    if image==null:return {"ok":false,"reason":"Cannot read106 actual opaque donor"}
    if image.is_compressed() and image.decompress()!=OK:return {"ok":false,"reason":"Cannot decompress106 actual opaque donor"}
    image.convert(Image.FORMAT_RGBA8)
    if image.has_mipmaps():image.clear_mipmaps()
    if image.get_data()!=expected.get_data():return {"ok":false,"reason":"Actual106 opaque donor differs from frozenRGBA"}
    return {"ok":true,"species":species,"mesh":"Closed_body","surface":0,"generated_shader_sha256":generated,
        "model_sha256":digests.model_sha256,"helper_sha256":digests.helper_sha256,"template_sha256":digests.template_sha256,
        "config_sha256":digests.profile_sha256,"lod_helper_sha256":lod_sha,"fallback_sha256":donor.sha256}
static func validate_dynamic_107_shader(model: Node3D, species: String, mesh: MeshInstance3D, surface: int, material: ShaderMaterial) -> Dictionary:
    if species!="zander" or model==null or mesh==null or str(mesh.name)!="Closed_body" or surface!=0 or not model.is_ancestor_of(mesh):
        return {"ok":false,"reason":"Unknown107 dynamic body identity"}
    if material==null or material.shader==null or not material.shader.resource_path.is_empty() or mesh.mesh==null or mesh.get_active_material(surface)!=material:
        return {"ok":false,"reason":"Expected active107 generated body material"}
    var eye: Dictionary=model.get_meta("eye_ownership_107_receipt",{})
    if eye.is_empty():return {"ok":false,"reason":"Missing107 eye receipt"}
    var paths: Dictionary={"model_sha256":"res://assets/models/fish/zander.glb",
        "helper_sha256":"res://scripts/aquarium/FishEyeOwnership.gd","template_sha256":"res://scripts/aquarium/FishEyeOwnership.gdshaderinc",
        "profile_sha256":"res://assets/models/fish/motion/eye-ownership-107.json","original_shader_file_sha256":"res://scripts/aquarium/FishBodyOpaque.gdshader",
        "head_include_sha256":"res://scripts/aquarium/FishHeadSource.gdshaderinc","head_profile_sha256":"res://assets/models/fish/motion/head-source.json"}
    var digests: Dictionary={}
    for key in paths:
        if not FileAccess.file_exists(paths[key]):return {"ok":false,"reason":"Missing mandatory107 dependency: "+paths[key]}
        digests[key]=FileAccess.get_sha256(paths[key])
        if eye.get(key,"")!=digests[key]:return {"ok":false,"reason":"Stale107 receipt hash: "+key}
    var lod: Dictionary=model.get_meta("eye_lod_107_receipt",{})
    var repaired_lod: bool=not lod.is_empty()
    var expected_mesh_id=lod.get("runtime_mesh_resource_id",-1) if repaired_lod else eye.get("mesh_after",{}).get("mesh_resource_id",-1)
    if model.scene_file_path!=paths.model_sha256 or not eye.get("mesh_after") is Dictionary or expected_mesh_id!=mesh.mesh.get_instance_id() or eye.get("mesh_before")!=eye.mesh_after:
        return {"ok":false,"reason":"Receipt does not own unchanged actual107 mesh/model"}
    if mesh.mesh.get_surface_count()!=2 or eye.mesh_after.get("lod_counts")!=[6,2] or not eye.get("all_original_lods_retained",false) or eye.get("lod_geometry_gate",{}).get("status","")!="failed":
        return {"ok":false,"reason":"107 must retain original6/2LOD and failedLOD5 geometry gate"}
    #109 changes only the post-eye runtime LOD inventory. Preserve107's failed
    # originalLOD evidence and validate the separate, current packed-copy receipt.
    var expected_lod_hash: String=eye.mesh_after.get("all_lods_sha256","")
    if repaired_lod:
        var helper_path="res://scripts/aquarium/FishEyeLod107.gd"
        if not FileAccess.file_exists(helper_path) or lod.get("helper_sha256","")!=FileAccess.get_sha256(helper_path) or lod.get("config_sha256","")!=digests.profile_sha256 or lod.get("model_sha256","")!=digests.model_sha256:
            return {"ok":false,"reason":"Stale109 LOD helper/config/model receipt"}
        if lod.get("source_mesh_resource_id",-1)!=eye.mesh_after.mesh_resource_id or not lod.get("original_resource_raw_unchanged",false) or not lod.get("skin_same_object",false) or not lod.get("skeleton_path_unchanged",false):
            return {"ok":false,"reason":"109 original resource/binding not preserved"}
        var context=HashingContext.new();context.start(HashingContext.HASH_SHA256);context.update(var_to_bytes(mesh.mesh.get("_surfaces")))
        if context.finish().hex_encode()!=lod.get("actual_after_raw_surfaces_sha256","") or lod.get("expected_after_raw_surfaces_sha256","")!=lod.get("actual_after_raw_surfaces_sha256","") or lod.get("all_decoded_surface_arrays_before")!=lod.get("all_decoded_surface_arrays_after"):
            return {"ok":false,"reason":"109 actual packed mesh differs from preservation receipt"}
        var raw: Array=mesh.mesh.get("_surfaces")
        if raw[0].get("lods",[]).size()!=10 or raw[1].get("lods",[]).size()!=4 or lod.get("retired_lod",{}).get("triangles",0)!=439 or lod.get("retired_lod",{}).get("index",-1)!=5:
            return {"ok":false,"reason":"109 must retire exactly broken zanderLOD5"}
        expected_lod_hash=lod.get("runtime_lods_sha256","")
    var arrays_hash:=HashingContext.new();var lod_hash:=HashingContext.new()
    arrays_hash.start(HashingContext.HASH_SHA256);lod_hash.start(HashingContext.HASH_SHA256)
    for index in mesh.mesh.get_surface_count():
        arrays_hash.update(var_to_bytes(mesh.mesh.surface_get_arrays(index)))
        lod_hash.update(var_to_bytes(RenderingServer.mesh_get_surface(mesh.mesh.get_rid(),index).get("lods",[])))
    if arrays_hash.finish().hex_encode()!=eye.mesh_after.get("all_surface_arrays_sha256","") or lod_hash.finish().hex_encode()!=expected_lod_hash or str(mesh.skeleton)!=eye.mesh_after.get("skeleton_path","") or (mesh.skin.get_instance_id() if mesh.skin!=null else 0)!=eye.mesh_after.get("skin_resource_id",-1):
        return {"ok":false,"reason":"Actual107 arrays/LOD/binding differ from install"}
    var generated: String=material.shader.code.sha256_text()
    if eye.get("generated_shader_sha256","")!=generated:return {"ok":false,"reason":"Generated107 shader code differs from install receipt"}
    var template: String=FileAccess.get_file_as_string(paths.template_sha256)
    if template.is_empty() or not material.shader.code.contains(template):return {"ok":false,"reason":"Generated107 code lacks complete current template"}
    var tokens:=RegEx.new()
    tokens.compile('(?s)//[^\\n]*|/\\*.*?\\*/|[A-Za-z_][A-Za-z_0-9]*|[^\\s]')
    for item in tokens.search_all(material.shader.code):
        var token: String=item.get_string()
        if token.begins_with("//") or token.begins_with("/*"):continue
        if token=="ALPHA" or token.begins_with("ALPHA_") or token=="discard":return {"ok":false,"reason":"Forbidden coverage token in107 code: "+token}
    var config=JSON.parse_string(FileAccess.get_file_as_string(paths.profile_sha256))
    if not config is Dictionary or not config.get("profiles") is Dictionary or not config.profiles.get(species) is Dictionary:return {"ok":false,"reason":"Invalid107 config"}
    var p: Dictionary=config.profiles[species]
    if repaired_lod and lod.get("retired_lod",{})!=p.get("retired_lod",{}):
        return {"ok":false,"reason":"109 LOD retirement differs from frozen profile"}
    if p.get("mesh","")!="Closed_body" or p.get("surface",-1)!=0 or p.get("model_path","")!=paths.model_sha256 or p.get("model_sha256","")!=digests.model_sha256 or p.get("head_include_sha256","")!=digests.head_include_sha256 or p.get("head_profile_sha256","")!=digests.head_profile_sha256 or p.get("original_shader_file_sha256","")!=digests.original_shader_file_sha256 or p.get("original_shader_code_sha256","")!=eye.get("original_shader_code_sha256","") or p.get("original_uniforms_sha256","")!=eye.get("original_uniforms_sha256",""):
        return {"ok":false,"reason":"107 profile original assembly binding mismatch"}
    if p.get("all_lods_sha256","")!=eye.mesh_after.get("all_lods_sha256","") or p.get("all_surface_arrays_sha256","")!=eye.mesh_after.get("all_surface_arrays_sha256","") or p.get("vertex_order_sha256","")!=eye.get("vertex_order_sha256",""):
        return {"ok":false,"reason":"107 profile geometry binding mismatch"}
    var texture_bindings: Dictionary={"source":["source_texture","source_sha256"],"opaque_skin":["opaque_skin","fallback_texture_sha256"],"clean_source":["eye_clean_source","clean_source_sha256"],"clean_opaque":["eye_clean_opaque","clean_opaque_sha256"],"source_eye_mask":["eye_source_mask","source_eye_mask_sha256"],"fallback_eye_mask":["eye_fallback_mask","fallback_eye_mask_sha256"],"eye_layer_mask":["eye_layer_mask","eye_layer_mask_sha256"]}
    for key in texture_bindings:
        if not p.get(key) is Dictionary:return {"ok":false,"reason":"Missing107 frozen texture: "+key}
        var spec: Dictionary=p[key];var binding: Array=texture_bindings[key]
        if not FileAccess.file_exists(spec.get("path","")):return {"ok":false,"reason":"Missing107 texture file: "+key}
        if FileAccess.get_sha256(spec.path)!=spec.get("sha256","") or eye.get(binding[1],"")!=spec.sha256:return {"ok":false,"reason":"Stale107 frozen texture: "+key}
        var actual:=material.get_shader_parameter(binding[0]) as Texture2D
        if actual==null or actual.get_size()!=Vector2(p.source_size[0],p.source_size[1]):return {"ok":false,"reason":"Invalid107 actual texture: "+key}
        var expected:=Image.new()
        if expected.load_png_from_buffer(FileAccess.get_file_as_bytes(spec.path))!=OK:return {"ok":false,"reason":"Cannot decode107 texture: "+key}
        expected.convert(Image.FORMAT_RGBA8)
        var image:=actual.get_image()
        if image==null:return {"ok":false,"reason":"Cannot read107 actual texture: "+key}
        if image.is_compressed() and image.decompress()!=OK:return {"ok":false,"reason":"Cannot decode107 actual texture: "+key}
        image.convert(Image.FORMAT_RGBA8)
        if image.has_mipmaps():image.clear_mipmaps()
        if image.get_data()!=expected.get_data():return {"ok":false,"reason":"Actual107 textureRGBA differs: "+key}
    for field in ["mode","probe","retired_probe"]:
        var uniform: String="eye_mode" if field=="mode" else ("eye_probe" if field=="probe" else "eye_retired_probe")
        if material.get_shader_parameter(uniform)!=eye.get(field,-1):return {"ok":false,"reason":"Actual107 mode/probe mismatch"}
    var projection: Dictionary=p.projection
    var expected_uniforms: Dictionary={"eye_source_size":Vector2(p.source_size[0],p.source_size[1]),"eye_anchor_xy":Vector2(projection.anchor_rest_xy[0],projection.anchor_rest_xy[1]),"eye_pupil_uv":Vector2(projection.source_pupil_px[0]/p.source_size[0],projection.source_pupil_px[1]/p.source_size[1]),"eye_pixel_native":Vector2(projection.pixel_native_xy[0],projection.pixel_native_xy[1]),"eye_downshift_pixels":projection.downshift_native_pixels,"eye_z_gap":Vector2(projection.central_gap_abs_z,projection.full_owner_abs_z),"eye_vertex_count":p.surface0_vertices}
    for uniform in expected_uniforms:
        if material.get_shader_parameter(uniform)!=expected_uniforms[uniform]:return {"ok":false,"reason":"Actual107 projection uniform mismatch: "+uniform}
    return {"ok":true,"species":species,"mesh":"Closed_body","surface":0,"generated_shader_sha256":generated,"model_sha256":digests.model_sha256,"helper_sha256":digests.helper_sha256,"template_sha256":digests.template_sha256,"config_sha256":digests.profile_sha256,"original_shader_sha256":digests.original_shader_file_sha256,"head_include_sha256":digests.head_include_sha256,"head_profile_sha256":digests.head_profile_sha256,"fallback_sha256":p.opaque_skin.sha256,"all_original_lods_retained":not repaired_lod,"LOD5_geometry_gate":"failed","LOD5_excluded_by_109":repaired_lod,"scope":"Opaque coverage authorization only; not eye/LOD/wholefish acceptance"}

static func validate_dynamic_body_shader(model: Node3D, species: String, mesh: MeshInstance3D, surface: int, material: ShaderMaterial) -> Dictionary:
    if species in ["scalloped_hammerhead","great_hammerhead","smooth_hammerhead"] and FileAccess.file_exists("res://scripts/aquarium/HammerSurface136.gd"):
        return load("res://scripts/aquarium/HammerSurface136.gd").new().validate(model,species,mesh,surface,material)
    if model.get_meta("front_skin112_receipts",{}).has(str(mesh.name)+":"+str(surface)):
        return load("res://scripts/aquarium/ValidateSurface112.gd").new().validate_front(model,species,mesh,surface,material)
    if model.has_meta("surface_chart_112_receipt"):
        return load("res://scripts/aquarium/ValidateSurface112.gd").new().validate_chart(model,species,mesh,surface,material)
    if species=="black_seabream":return validate_dynamic_106_shader(model,species,mesh,surface,material)
    if species=="zander":return validate_dynamic_107_shader(model,species,mesh,surface,material)
    return {"ok":false,"reason":"Unknown dynamic body shader"}

func authorize_body_shader(model:Node3D,species:String,mesh:MeshInstance3D,surface:int,material:ShaderMaterial)->Dictionary:return validate_dynamic_body_shader(model,species,mesh,surface,material)
func authorize_relief(model:Node3D,mesh:MeshInstance3D):load("res://scripts/aquarium/ValidateSurface112.gd").new().validate_relief(model,mesh)
func extra_capture_bindings()->Dictionary:return {}

func _initialize():
    out=OS.get_cmdline_user_args()[0]
    call_deferred("run")
func runtime_files(directory:String)->Array:
    var files:Array=[]
    for name in DirAccess.get_files_at(directory):
        if name.get_extension() in ["gd","gdshader","gdshaderinc","json"]:files.append(directory.path_join(name).trim_prefix("res://"))
    for name in DirAccess.get_directories_at(directory):files.append_array(runtime_files(directory.path_join(name)))
    return files
func capture(path: String):
    await process_frame
    if OS.get_environment("FOUNDRY_MANUAL_RENDER")=="1":
        RenderingServer.force_draw()
    else:
        await RenderingServer.frame_post_draw
    assert(hall.viewport.get_texture().get_image().save_png(path)==OK)
func run():
    DirAccess.make_dir_recursive_absolute(out)
    root.size=Vector2i(800,600);root.content_scale_size=Vector2i(800,600)
    hall=load("res://scripts/aquarium/VolumeFishExhibit.gd").new();root.add_child(hall);hall.set_process(false);hall.paused=true;hall.header.hide();hall.footer.hide()
    hall.screen.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT);hall.viewport.size=Vector2i(800,600);hall.viewport.transparent_bg=true
    hall.viewport.render_target_update_mode=SubViewport.UPDATE_ALWAYS
    profiles=JSON.parse_string(FileAccess.get_file_as_string("res://assets/models/fish/motion/surface-ownership.json")).profiles
    opaque_profiles=JSON.parse_string(FileAccess.get_file_as_string("res://assets/models/fish/motion/body-opacity.json")).profiles
    for env in hall.world.find_children("*","WorldEnvironment",true,false):
        env.environment.background_mode=Environment.BG_CLEAR_COLOR
    var reference:=StandardMaterial3D.new();reference.shading_mode=BaseMaterial3D.SHADING_MODE_UNSHADED;reference.cull_mode=BaseMaterial3D.CULL_DISABLED;reference.albedo_color=Color.WHITE
    var records: Array=[]
    var dynamic_shaders: Array=[]
    var dynamic_checks: Array=[]
    var uses_head: bool=false
    var uses_mouth: bool=false
    var views=[[0.,0.],[PI,0.],[PI/2.,0.],[-PI/2.,0.],[.5,.85],[.5,-.85],[PI+.5,.65],[PI+.5,-.65]]
    var requested: Array=[]
    var arguments=OS.get_cmdline_user_args()
    for i in range(1,arguments.size()):
        assert(arguments[i] in hall.SPECIES and not arguments[i] in requested,"Unknown/duplicate body capture species")
        requested.append(arguments[i])
    for species in hall.SPECIES:
        if not requested.is_empty() and not species in requested:continue
        hall._select_display(species)
        var entry: Dictionary=hall._selected()
        for mesh in hall.world.find_children("*","MeshInstance3D",true,false):mesh.visible=entry.model.is_ancestor_of(mesh) and not profiles[species].fins.has(str(mesh.name)) and not str(mesh.name) in opaque_profiles[species].suppressed_auxiliary and not opaque_profiles[species].get("decorative_overlays",{}).has(str(mesh.name))
        for mesh in entry.model.find_children("*","MeshInstance3D",true,false):
            if mesh.has_meta("decorative_relief112"):
                authorize_relief(entry.model,mesh)
                mesh.hide()
                continue
            if opaque_profiles[species].get("decorative_overlays",{}).has(str(mesh.name)):
                if species=="zander" and str(mesh.name) in ["Eye_relief112_-1_0","Eye_relief112_1_0"]:
                    var frozen:Dictionary=entry.model.get_meta("final_asset160_receipt",{})
                    var body=entry.model.find_child("Closed_body",true,false) as MeshInstance3D
                    var eye_material=mesh.get_active_material(0) as StandardMaterial3D
                    assert(frozen.get("static_build_calls",-1)==0 and body!=null and mesh.skin==body.skin and mesh.skeleton==body.skeleton)
                    assert(eye_material!=null and eye_material.transparency==BaseMaterial3D.TRANSPARENCY_DISABLED and eye_material.albedo_texture!=null)
                    continue
                for si in mesh.mesh.get_surface_count():
                    var original=mesh.mesh.surface_get_material(si)
                    var active=mesh.get_active_material(si)
                    if entry.model.has_meta("feature_overlay112_receipt"):
                        assert(active is ShaderMaterial and active.shader.resource_path=="res://scripts/aquarium/FeatureOverlay112.gdshader")
                        assert(active.get_shader_parameter("tint")==original.albedo_color and active.get_shader_parameter("source_texture")==original.albedo_texture,"112 overlay fusion differs")
                    else:
                        assert(active is StandardMaterial3D and active.transparency==original.transparency and active.albedo_color==original.albedo_color and active.albedo_texture==original.albedo_texture,"Authored head fusion overwritten")
        var bodies: Array=[]
        for mesh in entry.model.find_children("*","MeshInstance3D",true,false):
            if mesh.has_meta("decorative_relief112"):continue # Test complete skin independently under the decorative eye cap.
            if not profiles[species].fins.has(str(mesh.name)) and not str(mesh.name) in opaque_profiles[species].suppressed_auxiliary and not opaque_profiles[species].get("decorative_overlays",{}).has(str(mesh.name)):
                var originals: Array=[]
                for s in mesh.mesh.get_surface_count():
                    var material=mesh.get_active_material(s)
                    if material is ShaderMaterial:
                        if material.shader.resource_path=="res://scripts/aquarium/SourceJaw112.gdshader":
                            load("res://scripts/aquarium/ValidateSurface112.gd").new().validate_lining(entry.model,species,mesh,s,material)
                        elif material.shader.resource_path in ["res://scripts/aquarium/FishMouthPigment.gdshader","res://scripts/aquarium/review_candidates/yellow_croaker/FishMouthPigment.gdshader"]:
                            uses_mouth=true
                            var mouth_profiles:Dictionary=JSON.parse_string(FileAccess.get_file_as_string("res://assets/models/fish/motion/mouth-pigment.json")).profiles
                            assert(mouth_profiles.has(species),"Unregistered oral pigment")
                            var p:Dictionary=mouth_profiles[species]
                            assert(p.mesh==str(mesh.name) and int(p.oral_surface)==s,"Wrong oral pigment surface")
                            assert(p.model_sha256==FileAccess.get_sha256("res://assets/models/fish/"+species+".glb"))
                            assert(material.get_shader_parameter("source_texture")!=null,"Missing oral palette")
                        else:
                            if material.shader.resource_path!="res://scripts/aquarium/FishBodyOpaque.gdshader":
                                var authorization:=authorize_body_shader(entry.model,species,mesh,s,material)
                                assert(authorization.ok,str(authorization.get("reason","Unexpected body shader")))
                                dynamic_shaders.append(authorization)
                                dynamic_checks.append([entry.model,species,mesh,s,material])
                            uses_head=uses_head or material.get_shader_parameter("head_source_repair")==true or material.get_shader_parameter("head_blend")==true
                            assert(material.get_shader_parameter("opaque_skin")!=null,"Missing body donor")
                    else:
                        assert(material is StandardMaterial3D and material.transparency==BaseMaterial3D.TRANSPARENCY_DISABLED,"Nonopaque body surface")
                    originals.append(material)
                bodies.append({"mesh":mesh,"materials":originals})
        var folder=out+"/"+species;DirAccess.make_dir_recursive_absolute(folder)
        for pose in 2:
            entry.controller.set_motion_controls({"body_amplitude":0. if pose==0 else 2.5,"fin_amplitude":0. if pose==0 else 2.5},true);entry.controller.seek(1.17)
            await process_frame
            await process_frame
            for v in views.size():
                var tr: Transform3D=entry.carrier.global_transform;var yaw: float=views[v][0];var pitch: float=views[v][1]
                hall.camera.global_position=tr.origin+tr.basis.orthonormalized()*Vector3(sin(yaw)*cos(pitch),sin(pitch),cos(yaw)*cos(pitch))*entry.length_m*1.4
                hall.camera.look_at(tr.origin,tr.basis.orthonormalized()*Vector3.UP)
                var stem=folder+"/p%d-v%d"%[pose,v]
                for b in bodies:
                    for s in b.materials.size():b.mesh.set_surface_override_material(s,b.materials[s])
                # A hidden manual render loop must submit the new skeleton
                # pose once before comparing actual and reference coverage.
                # Otherwise view0 can compare the previous GPU bone buffer
                # against the current one, producing a false silhouette gap.
                if v==0 and OS.get_environment("FOUNDRY_MANUAL_RENDER")=="1":
                    RenderingServer.force_draw()
                    await process_frame
                await capture(stem+"-actual.png")
                for b in bodies:
                    for s in b.materials.size():b.mesh.set_surface_override_material(s,reference)
                await capture(stem+"-closed.png")
            records.append({"species":species,"pose":pose,"views":views.size(),"model_sha256":FileAccess.get_sha256("res://assets/models/fish/"+species+".glb")})
        for b in bodies:
            for s in b.materials.size():b.mesh.set_surface_override_material(s,b.materials[s])
        print("BODY_COVERAGE ",species)
    var bindings: Dictionary={}
    var required: Array=["scripts/aquarium/FishSurfaceOwnership.gd","scripts/aquarium/FishSurfaceOwnership.gdshader","scripts/aquarium/FishBodyOpaque.gdshader","scripts/aquarium/FoundryFishMotion.gd","assets/models/fish/motion/body-opacity.json","assets/models/fish/motion/motion.json","assets/models/fish/motion/surface-ownership.json"]
    var head_files: Array=["scripts/aquarium/FishHeadSource.gd","scripts/aquarium/FishHeadSource.gdshaderinc","assets/models/fish/motion/head-source.json"]
    var mouth_files: Array=["scripts/aquarium/FishMouthPigment.gd","scripts/aquarium/FishMouthPigment.gdshader","assets/models/fish/motion/mouth-pigment.json"]
    var optional: Array=[]
    if FileAccess.file_exists("res://scripts/aquarium/ValidateSurface112.gd"):
        required.append_array(runtime_files("res://scripts/aquarium"));required.append_array(runtime_files("res://assets/models/fish/motion"))
        required.append_array(["scripts/aquarium/ValidateSurface112.gd","scripts/aquarium/BodyChart112.gd","scripts/aquarium/BodyChart112.gdshaderinc","scripts/aquarium/EyeRelief112.gd","scripts/aquarium/SourceJaw112.gd","scripts/aquarium/SourceJaw112.gdshader","scripts/aquarium/SourceHeadLod112.gd","scripts/aquarium/FeatureOverlay112.gd","scripts/aquarium/FeatureOverlay112.gdshader","assets/models/fish/motion/eye-relief112.json","assets/models/fish/motion/source-jaw112.json","assets/models/fish/motion/surface-charts112.json","assets/models/fish/motion/head-lods112.json"])
    var only_106: bool=hall.SPECIES.size()==1 and hall.SPECIES[0]=="black_seabream" and not dynamic_shaders.is_empty()
    if only_106:
        required.append_array(["scripts/aquarium/FishEyeOwnership.gd","scripts/aquarium/FishEyeOwnership.gdshaderinc","scripts/aquarium/FishEyeLod106.gd","assets/models/fish/motion/eye-ownership-106.json"])
        if uses_head:required.append_array(head_files)
        else:optional.append_array(head_files)
        if uses_mouth:required.append_array(mouth_files)
        else:optional.append_array(mouth_files)
    else:
        required.append_array(head_files);required.append_array(mouth_files)
    if hall.SPECIES.size()==1 and hall.SPECIES[0]=="zander" and not dynamic_shaders.is_empty():
        required.append_array(["scripts/aquarium/FishEyeOwnership.gd","scripts/aquarium/FishEyeOwnership.gdshaderinc","assets/models/fish/motion/eye-ownership-107.json"])
    for check in dynamic_checks:
        var current:=authorize_body_shader(check[0],check[1],check[2],check[3],check[4])
        assert(current.ok,str(current.get("reason","106 changed during capture")))
    for file in required:
        assert(FileAccess.file_exists("res://"+file),"Missing mandatory capture dependency: "+file)
        bindings[file]=FileAccess.get_sha256("res://"+file)
    var missing_optional: Array=[]
    for file in optional:
        if FileAccess.file_exists("res://"+file):bindings[file]=FileAccess.get_sha256("res://"+file)
        else:missing_optional.append(file)
    bindings.merge(extra_capture_bindings())
    var f=FileAccess.open(out+"/capture.validation.json",FileAccess.WRITE);f.store_string(JSON.stringify({"records":records,"files":bindings,"dynamic_body_shaders":dynamic_shaders,"missing_optional_unused_106_files":missing_optional}));f.close()
    hall.queue_free()
    await process_frame
    if RenderingServer.has_method("force_sync"):RenderingServer.force_sync()
    await process_frame
    quit()
