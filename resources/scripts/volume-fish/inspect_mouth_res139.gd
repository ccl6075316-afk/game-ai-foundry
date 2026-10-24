extends SceneTree
func _initialize():
    var args=OS.get_cmdline_user_args();var mesh=load(args[0]) as ArrayMesh
    for si in mesh.get_surface_count():
        var mat=mesh.surface_get_material(si)
        print("RESOURCE_MATERIAL ",si," ",mat.get_class())
        if mat is ShaderMaterial:
            print("CODE_LENGTH ",mat.shader.code.length())
            for line in mat.shader.code.split("\n"):
                if line.contains("rest_position=VERTEX;"):print("POSED_REFERENCE ",line)
            for key in ["head_source_repair","source_eye","eye_gap_native","eye_donor_u","eye_donor_v","secondary_feature_enabled","rim_local_source","head_blend","chart112_eye_rect_native"]:
                print("PARAMETER ",key," ",mat.get_shader_parameter(key))
            for row in mat.shader.get_shader_uniform_list():
                var value=mat.get_shader_parameter(row.name)
                if value is Texture2D:
                    var im=value.get_image()
                    print("TEXTURE ",row.name," ",value.get_class()," ",value.resource_path," ",im.get_size() if im else Vector2i.ZERO)
        elif mat is StandardMaterial3D:print("ALBEDO ",mat.albedo_color)
    quit()
