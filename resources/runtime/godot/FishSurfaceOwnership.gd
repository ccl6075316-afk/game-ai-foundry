extends RefCounted
## Per-mesh ownership. Never replace source textures or edit skin/bone geometry.
var _profiles: Dictionary = {}
var _body_profiles: Dictionary = {}

func apply(model: Node3D, species: String) -> Dictionary:
    if _profiles.is_empty():
        _profiles=JSON.parse_string(FileAccess.get_file_as_string("res://assets/models/fish/motion/surface-ownership.json")).profiles
    assert(_profiles.has(species),"Missing fish surface ownership: "+species)
    var profile: Dictionary=_profiles[species]
    if _body_profiles.is_empty():
        _body_profiles=JSON.parse_string(FileAccess.get_file_as_string("res://assets/models/fish/motion/body-opacity.json")).profiles
    assert(_body_profiles.has(species),"Missing body opacity data: "+species)
    var body_profile: Dictionary=_body_profiles[species]
    var path := "res://assets/models/fish/"+species+".glb"
    assert(FileAccess.get_sha256(path)==profile.model_sha256,"Stale fish surface ownership: "+species)
    assert(FileAccess.get_sha256(path)==body_profile.model_sha256,"Stale body opacity data: "+species)
    var changed := {"skin_surfaces":0,"fin_surfaces":0}
    for mesh in model.find_children("*","MeshInstance3D",true,false):
        if str(mesh.name) in body_profile.suppressed_auxiliary:
            assert(str(mesh.name).begins_with("Textured_eye"),"Unexpected hidden body component")
            mesh.hide() # Existing disabled duplicate eye proxy; complete skin remains underneath.
            continue
        if body_profile.get("decorative_overlays",{}).has(str(mesh.name)):
            assert(str(mesh.name)=="Frontal_head_overlay" and species=="arapaima","Unexpected decorative overlay")
            assert(model.find_child(body_profile.decorative_overlays[str(mesh.name)].underlying_body,true,false)!=null,"Missing underlying opaque body")
            continue # Preserve authored alpha fusion above the separately tested opaque shell.
        var is_fin: bool=profile.fins.has(str(mesh.name))
        var records: Dictionary=profile.fins.get(str(mesh.name),{}) if is_fin else profile.skins.get(str(mesh.name),{})
        for surface in mesh.mesh.get_surface_count():
            var opaque_record: Dictionary=body_profile.surfaces.get(str(mesh.name),{}).get(str(surface),{})
            if not records.has(str(surface)) and (is_fin or opaque_record.is_empty()):continue
            var source=mesh.get_active_material(surface)
            assert(source is StandardMaterial3D and source.albedo_texture!=null,"Missing fish source material")
            var record: Dictionary=records.get(str(surface),{})
            var material:=ShaderMaterial.new()
            material.shader=load("res://scripts/aquarium/FishSurfaceOwnership.gdshader" if is_fin else "res://scripts/aquarium/FishBodyOpaque.gdshader")
            material.set_shader_parameter("source_texture",source.albedo_texture)
            material.set_shader_parameter("tint",source.albedo_color)
            material.set_shader_parameter("source_size",Vector2(source.albedo_texture.get_size()))
            material.set_shader_parameter("fin",is_fin)
            if is_fin:
                var edge_array:=PackedVector4Array()
                for e in record.edges:edge_array.append(Vector4(e[0],e[1],e[2],e[3]))
                edge_array.resize(128)
                material.set_shader_parameter("edges",edge_array)
                material.set_shader_parameter("edge_count",record.edges.size())
                material.set_shader_parameter("ink",Color(record.ink[0],record.ink[1],record.ink[2]))
                material.set_shader_parameter("ink_width",record.width_px)
                changed.fin_surfaces+=1
            else:
                assert(not opaque_record.is_empty(),"Missing opaque skin donor")
                assert(FileAccess.get_sha256(opaque_record.texture)==opaque_record.texture_sha256,"Stale opaque skin donor")
                material.set_shader_parameter("opaque_skin",load(opaque_record.texture))
                var projection: Dictionary=body_profile.get("head_projection",{})
                if projection.get("mesh","")==str(mesh.name):
                    material.set_shader_parameter("head_blend",true)
                    for channel in ["side","front"]:
                        var donor_record: Dictionary=body_profile.surfaces[str(mesh.name)][str(int(projection[channel+"_surface"]))]
                        assert(FileAccess.get_sha256(donor_record.texture)==donor_record.texture_sha256)
                        material.set_shader_parameter(channel+"_head",load(donor_record.texture))
                    material.set_shader_parameter("head_start",projection.start_x)
                    material.set_shader_parameter("head_blend_x",Vector2(projection.blend_x[0],projection.blend_x[1]))
                    var a: Array=projection.side_uv;var b: Array=projection.front_uv
                    material.set_shader_parameter("head_side_uv",Vector4(a[0],a[1],a[2],a[3]))
                    material.set_shader_parameter("head_front_uv",Vector4(b[0],b[1],b[2],b[3]))
                    material.set_shader_parameter("head_front_x",b[4])
                var meta:=PackedVector4Array();var rects:=PackedVector4Array();var points:=PackedVector2Array()
                for patch in record.get("patches",[]):
                    meta.append(Vector4(points.size(),patch.polygon.size(),patch.donor_u[0],patch.donor_u[1]))
                    var r: Array=patch.rect;rects.append(Vector4(r[0],r[1],r[2],r[3]))
                    for point in patch.polygon:points.append(Vector2(point[0],point[1]))
                meta.resize(8);rects.resize(8);points.resize(512)
                material.set_shader_parameter("patch_count",record.get("patches",[]).size())
                material.set_shader_parameter("patch_meta",meta)
                material.set_shader_parameter("patch_rect",rects)
                material.set_shader_parameter("patch_points",points)
                if records.has(str(surface)):changed.skin_surfaces+=1
            mesh.set_surface_override_material(surface,material)
    return changed
