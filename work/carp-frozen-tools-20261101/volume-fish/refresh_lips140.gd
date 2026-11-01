extends SceneTree
## Export contact-corrected lips only. Frozen body resources remain untouched.
func _initialize():call_deferred("run")
func run():
    var base=OS.get_cmdline_user_args()[0];var rows=[]
    var plan=JSON.parse_string(FileAccess.get_file_as_string(base+"/final-lips.plan.json"))
    for item in plan.items:
        var species:String=item.species;var folder=base.path_join(species);var path:String=item.lips;var data=JSON.parse_string(FileAccess.get_file_as_string(path));var source=load(item.material_resource) as ArrayMesh;assert(source!=null and source.get_surface_count()==data.parts.size())
        var names:Array=JSON.parse_string(FileAccess.get_file_as_string(folder+"/geometry/skinning.validation.json")).summary.skin_joint_names
        var actual:Array=JSON.parse_string(FileAccess.get_file_as_string(base+"/runtime-final/"+species+"/runtime-body.mesh.json")).skin_bind_names;var mapping=[]
        for name in names:
            var found=-1
            for i in actual.size():
                if actual[i]==name or actual[i]==name+"_2":assert(found<0);found=i
            assert(found>=0);mapping.append(found)
        var next=ArrayMesh.new()
        for si in data.parts.size():
            var p:Dictionary=data.parts[si];var arrays=[];arrays.resize(Mesh.ARRAY_MAX);var vertices=PackedVector3Array();var normals=PackedVector3Array();var uv=PackedVector2Array();var uv2=PackedVector2Array();var colors=PackedColorArray();var bones=PackedInt32Array();var weights=PackedFloat32Array()
            for q in p.vertices:vertices.append(Vector3(q[0],q[1],q[2]))
            for q in p.normals:normals.append(Vector3(q[0],q[1],q[2]))
            for q in p.uv:uv.append(Vector2(q[0],q[1]))
            for q in p.uv2:uv2.append(Vector2(q[0],q[1]))
            for q in p.colors:colors.append(Color(q[0],q[1],q[2],q[3]))
            for i in p.joints.size():
                for k in 4:bones.append(mapping[int(p.joints[i][k])]);weights.append(p.weights[i][k])
            arrays[Mesh.ARRAY_VERTEX]=vertices;arrays[Mesh.ARRAY_NORMAL]=normals;arrays[Mesh.ARRAY_TEX_UV]=uv;arrays[Mesh.ARRAY_TEX_UV2]=uv2;arrays[Mesh.ARRAY_COLOR]=colors;arrays[Mesh.ARRAY_BONES]=bones;arrays[Mesh.ARRAY_WEIGHTS]=weights;arrays[Mesh.ARRAY_INDEX]=PackedInt32Array(p.triangles)
            var material=source.surface_get_material(si)
            if si==1 and item.has("retained_lower_material_resource"):material=(load(item.retained_lower_material_resource) as ArrayMesh).surface_get_material(1)
            next.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES,arrays);next.surface_set_material(si,material)
        var output=folder+"/lips/final-lips.res";assert(ResourceSaver.save(next,output,ResourceSaver.FLAG_BUNDLE_RESOURCES)==OK)
        rows.append({"species":species,"source_mesh_sha256":FileAccess.get_sha256(path),"material_source_resource_sha256":FileAccess.get_sha256(folder+"/preview-v3/lips.res"),"resource":output,"resource_sha256":FileAccess.get_sha256(output)})
        if item.has("body_resource"):
            var body=load(item.body_resource) as ArrayMesh;var portable=load(get_script().resource_path.get_base_dir().path_join("../../runtime/godot/mouth-repair-139/PortableMaterial139.gd"));var mat=portable.freeze(body.surface_get_material(0)) as ShaderMaterial
            var table=JSON.parse_string(FileAccess.get_file_as_string(item.skin_records));var width=256;var height=ceili(table.size()/256.);var image=Image.create(width,height,false,Image.FORMAT_RGBAF)
            for i in table.size():var p=table[i];image.set_pixel(i%width,i/width,Color(p[0],p[1],p[2],p[3]))
            mat.set_shader_parameter("mouth136_records",ImageTexture.create_from_image(image));mat.set_shader_parameter("mouth136_size",Vector2i(width,height));mat.set_shader_parameter("mouth136_skin",ImageTexture.create_from_image(Image.load_from_file(item.skin_atlas)));body.surface_set_material(0,mat)
            assert(ResourceSaver.save(body,item.body_output,ResourceSaver.FLAG_BUNDLE_RESOURCES)==OK);rows[-1]["body_resource"]=item.body_output;rows[-1]["body_resource_sha256"]=FileAccess.get_sha256(item.body_output)
    var f=FileAccess.open(base+"/lip-export140.validation.json",FileAccess.WRITE);f.store_string(JSON.stringify({"ok":true,"rows":rows,"scope":"Contact-refined lip geometry and exact normalized rig binding; native existing portable materials preserved. Body files unchanged; fresh actual runtime check required."},"  "));f.close();quit()
