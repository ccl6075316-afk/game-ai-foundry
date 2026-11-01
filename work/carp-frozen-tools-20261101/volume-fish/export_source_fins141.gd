extends SceneTree
func portable_material(source:Material)->Material:
    var material=source.duplicate()
    if material is ShaderMaterial:
        var shader=Shader.new();shader.code=source.shader.code;material.shader=shader
        for uniform in source.shader.get_shader_uniform_list():
            var value=source.get_shader_parameter(uniform.name)
            if value is Texture2D:
                var im=value.get_image().duplicate()
                if im.is_compressed():assert(im.decompress()==OK)
                material.set_shader_parameter(uniform.name,ImageTexture.create_from_image(im))
    return material
func _initialize():call_deferred("run")
func run():
    var args=OS.get_cmdline_user_args();var data=JSON.parse_string(FileAccess.get_file_as_string(args[0]));var out=args[1];DirAccess.make_dir_recursive_absolute(out)
    var path_glb="res://assets/models/fish/"+data.species+".glb";assert(FileAccess.get_sha256(path_glb)==data.source_model_sha256);var model=(load(path_glb) as PackedScene).instantiate();root.add_child(model);var e={"model":model,"skeleton":model.find_children("*","Skeleton3D",true,false)[0]};var rows=[]
    for fin in data.fins:
        var node=e.model.find_child(fin.name,true,false) as MeshInstance3D;assert(node!=null);var mapping=[]
        for name in fin.skin_joint_names:
            var bi=e.skeleton.find_bone(name);assert(bi>=0);var found=-1
            for j in node.skin.get_bind_count():
                var actual=node.skin.get_bind_bone(j)
                if actual<0:actual=e.skeleton.find_bone(node.skin.get_bind_name(j))
                if actual==bi:assert(found<0);found=j
            assert(found>=0);mapping.append(found)
        var mesh=ArrayMesh.new();var retained:ArrayMesh=null
        if fin.has("retained_material_source"):
            var ref:Dictionary=fin.retained_material_source;assert(FileAccess.get_sha256(ref.path)==ref.sha256);retained=load(ref.path)as ArrayMesh;assert(retained.get_surface_count()==fin.parts.size())
        for part in fin.parts:
            var arrays=[];arrays.resize(Mesh.ARRAY_MAX);var v=PackedVector3Array();var n=PackedVector3Array();var uv=PackedVector2Array();var jj=PackedInt32Array();var ww=PackedFloat32Array()
            for q in part.vertices:v.append(Vector3(q[0],q[1],q[2]))
            for q in part.normals:n.append(Vector3(q[0],q[1],q[2]))
            for q in part.uv:uv.append(Vector2(q[0],q[1]))
            for i in part.joints.size():
                for k in 4:jj.append(mapping[int(part.joints[i][k])]);ww.append(part.weights[i][k])
            arrays[Mesh.ARRAY_VERTEX]=v;arrays[Mesh.ARRAY_NORMAL]=n;arrays[Mesh.ARRAY_TEX_UV]=uv;arrays[Mesh.ARRAY_BONES]=jj;arrays[Mesh.ARRAY_WEIGHTS]=ww;arrays[Mesh.ARRAY_INDEX]=PackedInt32Array(part.triangles);mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES,arrays)
            var im=Image.load_from_file(fin.texture);assert(im!=null and FileAccess.get_sha256(fin.texture)==fin.texture_sha256);var mat=ShaderMaterial.new();var shader=Shader.new();shader.code="shader_type spatial;\nrender_mode cull_disabled,diffuse_lambert,specular_disabled;\nuniform sampler2D source_texture : source_color,filter_nearest,repeat_disable;\nvoid fragment(){vec4 c=texture(source_texture,UV);ALBEDO=c.rgb;ALPHA=c.a;ALPHA_SCISSOR_THRESHOLD=.5;ROUGHNESS=1.;}\n";mat.shader=shader;mat.set_shader_parameter("source_texture",ImageTexture.create_from_image(im));mesh.surface_set_material(mesh.get_surface_count()-1,mat)
            if retained:
                var si=mesh.get_surface_count()-1;mesh.surface_set_material(si,portable_material(retained.surface_get_material(si)));var a=retained.surface_get_arrays(si);var b=mesh.surface_get_arrays(si)
                for field in Mesh.ARRAY_MAX:
                    if field!=Mesh.ARRAY_VERTEX:assert(a[field]==b[field],"Retained fin non-position stream changed")
        var path=out.path_join(String(fin.name)+".res");assert(ResourceSaver.save(mesh,path,ResourceSaver.FLAG_BUNDLE_RESOURCES)==OK);rows.append({"name":fin.name,"path":path,"sha256":FileAccess.get_sha256(path)})
    var f=FileAccess.open(out.path_join("resources.validation.json"),FileAccess.WRITE);f.store_string(JSON.stringify({"ok":rows.size()==data.fins.size(),"species":data.species,"input_sha256":FileAccess.get_sha256(args[0]),"fins":rows}));f.close();model.queue_free();await process_frame;quit()
