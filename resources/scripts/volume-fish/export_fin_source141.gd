extends SceneTree
## Audit actual configured fin arrays at original skeleton rest, before any edit.
func _initialize():call_deferred("run")
func is_body_mesh(_species:String,name:String)->bool:return name=="Closed_body"
func write_json(path:String,value:Variant):
    var f=FileAccess.open(path,FileAccess.WRITE);assert(f!=null);f.store_string(JSON.stringify(value));f.close()
func run():
    var args=OS.get_cmdline_user_args();var out=args[0];DirAccess.make_dir_recursive_absolute(out)
    var hall=load("res://scripts/aquarium/VolumeFishExhibit.gd").new();root.add_child(hall);hall.set_process(false);hall.paused=true
    var ownership=JSON.parse_string(FileAccess.get_file_as_string("res://assets/models/fish/motion/surface-ownership.json")).profiles
    var rows=[]
    for species in ownership:
        if species.ends_with("hammerhead"):continue
        if args.size()>1 and not species in args.slice(1):continue
        hall._select_display(species);var e:Dictionary=hall._selected();e.player.stop();e.skeleton.reset_bone_poses();e.skeleton.force_update_all_bone_transforms()
        var data={"species":species,"source_model_sha256":FileAccess.get_sha256("res://assets/models/fish/"+species+".glb"),"fins":[],"body":[]}
        for node in e.model.find_children("*","MeshInstance3D",true,false):
            var is_fin=ownership[species].fins.has(String(node.name))
            if not is_fin and not is_body_mesh(species,String(node.name)):continue
            var record={"name":String(node.name),"parts":[],"skin_joint_names":[]}
            var transforms=[];var skin:Skin=node.skin
            assert(skin!=null)
            for j in skin.get_bind_count():
                var bi=skin.get_bind_bone(j)
                if bi<0:bi=e.skeleton.find_bone(skin.get_bind_name(j))
                assert(bi>=0);record.skin_joint_names.append(String(e.skeleton.get_bone_name(bi)))
                transforms.append(e.model.global_transform.affine_inverse()*e.skeleton.global_transform*e.skeleton.get_bone_global_rest(bi)*skin.get_bind_pose(j))
            for si in node.mesh.get_surface_count():
                var a=node.mesh.surface_get_arrays(si);var vertices:PackedVector3Array=a[Mesh.ARRAY_VERTEX];var uv:PackedVector2Array=a[Mesh.ARRAY_TEX_UV];var bones:PackedInt32Array=a[Mesh.ARRAY_BONES];var weights:PackedFloat32Array=a[Mesh.ARRAY_WEIGHTS];var normals:PackedVector3Array=a[Mesh.ARRAY_NORMAL]
                var part={"surface":si,"vertices":[],"rest_vertices":[],"normals":[],"uv":[],"joints":[],"weights":[],"triangles":Array(a[Mesh.ARRAY_INDEX])}
                for i in vertices.size():
                    var p=Vector3.ZERO;var jj=[];var ww=[]
                    for k in 4:
                        var j=bones[i*4+k];var w=weights[i*4+k];p+=(transforms[j]*vertices[i])*w;jj.append(j);ww.append(w)
                    part.vertices.append([vertices[i].x,vertices[i].y,vertices[i].z]);part.rest_vertices.append([p.x,p.y,p.z]);part.normals.append([normals[i].x,normals[i].y,normals[i].z]);part.joints.append(jj);part.weights.append(ww)
                    if i<uv.size():part.uv.append([uv[i].x,uv[i].y])
                if is_fin:
                    var mat=node.get_active_material(si);assert(mat!=null)
                    var image:Image
                    if mat is ShaderMaterial:image=(mat.get_shader_parameter("source_texture") as Texture2D).get_image();part.shader_sha256=mat.shader.code.sha256_text()
                    elif mat is StandardMaterial3D:image=mat.albedo_texture.get_image()
                    assert(image!=null);var folder=out.path_join(species);DirAccess.make_dir_recursive_absolute(folder)
                    var path=folder.path_join(String(node.name)+"-"+str(si)+"-source.png");assert(image.save_png(path)==OK);part.texture={"path":path,"sha256":FileAccess.get_sha256(path),"size":[image.get_width(),image.get_height()]}
                record.parts.append(part)
            if is_fin:data.fins.append(record)
            else:data.body.append(record)
        assert(data.fins.size()==ownership[species].fins.size());write_json(out.path_join(species+".mesh.json"),data);rows.append({"species":species,"fins":data.fins.size(),"path":out.path_join(species+".mesh.json"),"sha256":FileAccess.get_sha256(out.path_join(species+".mesh.json"))});print("FIN_SOURCE141 ",species," ",data.fins.size())
    write_json(out.path_join("export.validation.json"),{"ok":not rows.is_empty(),"records":rows,"scope":"Actual configured original-rest arrays/material source. This export does not assert source silhouette/complete area match.","exporter_sha256":FileAccess.get_sha256(get_script().resource_path),"mouth_config_sha256":FileAccess.get_sha256("res://assets/models/fish/motion/mouth-repair139.json")});hall.queue_free();await process_frame;quit()
