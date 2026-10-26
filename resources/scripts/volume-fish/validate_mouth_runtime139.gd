extends "preview_bound_mouth136.gd"
## Validate the actually installed139 resource path, not a preview-only mesh.
var selected_species:Array=[]
func bound_arrays(node:MeshInstance3D)->Dictionary:
    var skeleton=node.get_node(node.skeleton) as Skeleton3D;var names=[];var parts=[]
    for i in node.skin.get_bind_count():
        var name=String(node.skin.get_bind_name(i))
        if name.is_empty():name=skeleton.get_bone_name(node.skin.get_bind_bone(i))
        names.append(name)
    for si in node.mesh.get_surface_count():
        var arrays=node.mesh.surface_get_arrays(si);var vertices=[]
        for p in arrays[Mesh.ARRAY_VERTEX]:vertices.append([p.x,p.y,p.z])
        parts.append({"vertices":vertices,"triangles":Array(arrays[Mesh.ARRAY_INDEX]),"bones":Array(arrays[Mesh.ARRAY_BONES]),"weights":Array(arrays[Mesh.ARRAY_WEIGHTS])})
    return {"skin_bind_names":names,"parts":parts}
func runtime_hashes(directory:String)->Dictionary:
    var result={}
    for name in DirAccess.get_files_at(directory):
        if name.get_extension() in ["gd","gdshader","gdshaderinc","json","png","res"]:
            var path=directory.path_join(name);result[path]=FileAccess.get_sha256(path)
    for name in DirAccess.get_directories_at(directory):result.merge(runtime_hashes(directory.path_join(name)))
    return result
func material_inventory(body:MeshInstance3D)->Array:
    var result=[]
    for si in body.mesh.get_surface_count():
        var mat=body.get_active_material(si)
        if mat is StandardMaterial3D:
            assert(mat.transparency==BaseMaterial3D.TRANSPARENCY_DISABLED)
            var texture_record={}
            if mat.albedo_texture!=null:
                var im:Image=mat.albedo_texture.get_image().duplicate()
                assert(im!=null and not im.is_empty())
                if im.is_compressed():assert(im.decompress()==OK)
                im.clear_mipmaps();im.convert(Image.FORMAT_RGBA8)
                var ctx=HashingContext.new();ctx.start(HashingContext.HASH_SHA256);ctx.update(im.get_data())
                texture_record={"size":[im.get_width(),im.get_height()],"base_data_sha256":ctx.finish().hex_encode()}
            result.append({"surface":si,"kind":"opaque_standard","transparency_disabled":true,"albedo_alpha":mat.albedo_color.a,"texture_present":mat.albedo_texture!=null,"texture":texture_record})
            continue
        assert(mat is ShaderMaterial)
        var code_path=out+"/body-surface-%d.gdshader"%si
        var f=FileAccess.open(code_path,FileAccess.WRITE);f.store_string(mat.shader.code);f.close()
        var textures=[]
        for uniform in mat.shader.get_shader_uniform_list():
            var tex=mat.get_shader_parameter(uniform.name)
            if not tex is Texture2D:continue
            var im:Image=tex.get_image().duplicate();assert(im!=null and not im.is_empty())
            if im.is_compressed():assert(im.decompress()==OK)
            im.clear_mipmaps();var size=im.get_size()
            var ctx=HashingContext.new();ctx.start(HashingContext.HASH_SHA256);ctx.update(im.get_data());var hash=ctx.finish().hex_encode()
            var opaque=true
            if String(uniform.name) in ["opaque_skin","original_opaque"]:
                im.convert(Image.FORMAT_RGBA8);var data=im.get_data()
                for at in range(3,data.size(),4):
                    if data[at]!=255:opaque=false;break
                assert(opaque,"Transparent actual body donor")
            textures.append({"name":String(uniform.name),"size":[size.x,size.y],"base_data_sha256":hash,"opaque_checked":String(uniform.name) in ["opaque_skin","original_opaque"],"opaque":opaque})
        result.append({"surface":si,"kind":"opaque_shader","shader":code_path,"shader_sha256":FileAccess.get_sha256(code_path),"textures":textures})
    return result
func _initialize():
    var args=OS.get_cmdline_user_args();out=args[0]
    for i in range(1,args.size()):selected_species.append(args[i])
    call_deferred("run")
func run():
    DirAccess.make_dir_recursive_absolute(out)
    hall=load("res://scripts/aquarium/VolumeFishExhibit.gd").new();root.add_child(hall)
    hall.set_process(false);hall.paused=true;hall.header.hide();hall.footer.hide()
    hall.viewport.size=Vector2i(1200,800);hall.viewport.render_target_update_mode=SubViewport.UPDATE_ALWAYS
    var profiles=JSON.parse_string(FileAccess.get_file_as_string("res://assets/models/fish/motion/mouth-repair139.json")).profiles
    if selected_species.is_empty():selected_species=profiles.keys()
    var all_records=[]
    var root_out=out
    var intrinsic_visibility={}
    for node in hall.world.find_children("*","MeshInstance3D",true,false):intrinsic_visibility[node.get_instance_id()]=node.visible
    var dependencies=runtime_hashes("res://scripts/aquarium")
    dependencies.merge(runtime_hashes("res://assets/models/fish/motion"))
    var checker_dependencies={};var script=get_script()
    while script!=null:
        checker_dependencies[script.resource_path]=FileAccess.get_sha256(script.resource_path)
        script=script.get_base_script()
    for species in selected_species:
        assert(profiles.has(species));out=root_out.path_join(species);DirAccess.make_dir_recursive_absolute(out)
        hall._select_display(species);e=hall._selected()
        for tank in hall.tanks:tank.root.visible=tank.species==species
        for mesh in hall.world.find_children("*","MeshInstance3D",true,false):
            mesh.visible=e.model.is_ancestor_of(mesh) and intrinsic_visibility.get(mesh.get_instance_id(),false)
        for label in hall.world.find_children("*","Label3D",true,false):label.hide()
        var helper=load("res://scripts/aquarium/MouthRepair139.gd").new()
        var check=helper.validate(e.model,species)
        var body=e.model.find_child("Closed_body",true,false) as MeshInstance3D
        assert(body.visible)
        var material_receipts=material_inventory(body)
        var bind_names=[]
        for i in body.skin.get_bind_count():
            var name=String(body.skin.get_bind_name(i))
            if name.is_empty():name=e.skeleton.get_bone_name(body.skin.get_bind_bone(i))
            bind_names.append(name)
        var exported={"parts":[],"skin_bind_names":bind_names}
        var actual_lods=[]
        for si in body.mesh.get_surface_count():
            var a=body.mesh.surface_get_arrays(si);var vertices=[]
            for p in a[Mesh.ARRAY_VERTEX]:vertices.append([p.x,p.y,p.z])
            exported.parts.append({"vertices":vertices,"triangles":Array(a[Mesh.ARRAY_INDEX]),"bones":Array(a[Mesh.ARRAY_BONES]),"weights":Array(a[Mesh.ARRAY_WEIGHTS])})
            actual_lods.append(body.mesh.get("_surfaces")[si].get("lods",[]).size())
        var file=FileAccess.open(out+"/runtime-body.mesh.json",FileAccess.WRITE);file.store_string(JSON.stringify(exported));file.close()
        var fin_binding_sha=""
        if profiles[species].has("fins"):
            var fin_arrays={}
            for name in profiles[species].fins:fin_arrays[name]=bound_arrays(e.model.find_child(name,true,false))
            file=FileAccess.open(out+"/runtime-fins.mesh.json",FileAccess.WRITE);file.store_string(JSON.stringify(fin_arrays));file.close()
            fin_binding_sha=FileAccess.get_sha256(out+"/runtime-fins.mesh.json")
        e.controller.set_motion_controls({"body_amplitude":0.,"fin_amplitude":0.},true)
        e.controller.set_action("Swim",true);e.controller.step(0.);e.controller.seek(0.)
        # Same fixed native head domain as the earlier source-material audit.
        for view in ["side","front","top","oblique"]:
            camera(view,false);await shot(out+"/head-"+view+"-texture.png")
        var samples=[]
        for action in ["Swim","Turn","Ascend","Dive"]:
            e.controller.set_motion_controls({"body_amplitude":1.,"body_frequency":1.,"fin_amplitude":1.,"fin_frequency":1.},true)
            assert(e.controller.set_action(action,true));e.controller.step(0.)
            for t in [0.,.35,.75,1.25]:
                e.controller.seek(t);camera("oblique",false)
                var path=out+"/motion-%s-%.2f.png"%[action,t];await shot(path)
                samples.append({"action":action,"seconds":t,"file":path,"sha256":FileAccess.get_sha256(path),"snapshot":e.controller.snapshot()})
        var transitions=[]
        for start in ["Swim","Turn","Ascend","Dive"]:
            for target in ["Swim","Turn","Ascend","Dive"]:
                if start==target:continue
                e.controller.set_action(start,true);e.controller.step(.5);e.controller.set_action(target,false)
                for dt in [.05,.15,.35]:
                    e.controller.step(dt);camera("oblique",false)
                    var path=out+"/transition-%s-%s-%.2f.png"%[start,target,dt];await shot(path)
                    transitions.append({"from":start,"to":target,"delta_seconds":dt,"snapshot":e.controller.snapshot(),"file":path,"sha256":FileAccess.get_sha256(path)})
        var distances=[]
        for distance in [1.,2.6,5.]:
            var tr:Transform3D=e.carrier.global_transform
            hall.camera.global_position=tr.origin+tr.basis.orthonormalized()*Vector3(.5,.2,1.).normalized()*e.length_m*distance
            hall.camera.look_at(tr.origin,tr.basis.orthonormalized()*Vector3.UP)
            var path=out+"/distance-%.1f.png"%distance;await shot(path)
            distances.append({"length_multiple":distance,"actual_body_lod_counts":actual_lods,"file":path,"sha256":FileAccess.get_sha256(path)})
        var coverage=await body_coverage(body)
        assert(coverage.size()==16 and material_receipts.size()==body.mesh.get_surface_count())
        check.merge({"model_sha256":FileAccess.get_sha256("res://assets/models/fish/"+species+".glb"),"coverage":coverage,"samples":samples,"transitions":transitions,"distances":distances,"actual_body_lod_counts":actual_lods,
            "runtime_body_sha256":FileAccess.get_sha256(out+"/runtime-body.mesh.json"),"runtime_fin_binding_sha256":fin_binding_sha,"materials":material_receipts})
        all_records.append(check)
        print("MOUTH_RUNTIME139 ",species," coverage=",coverage.size()," samples=",samples.size()," transitions=",transitions.size())
    for path in dependencies:assert(FileAccess.get_sha256(path)==dependencies[path],"Runtime changed during capture")
    for path in checker_dependencies:assert(FileAccess.get_sha256(path)==checker_dependencies[path],"Checker changed during capture")
    var file=FileAccess.open(root_out+"/runtime.validation.json",FileAccess.WRITE)
    file.store_string(JSON.stringify({"ok":all_records.size()==selected_species.size(),"checks":all_records,"config_sha256":FileAccess.get_sha256("res://assets/models/fish/motion/mouth-repair139.json"),
        "helper_sha256":FileAccess.get_sha256("res://scripts/aquarium/MouthRepair139.gd"),"checker_sha256":FileAccess.get_sha256(get_script().resource_path),
        "runtime_dependencies":dependencies,
        "checker_dependencies":checker_dependencies,
        "scope":"Actual configured139 resources: body alpha coverage in16 views/poses, four actions,12 real transition pairs,3 distances and all present body LODs. Geometric closure and full posed fin contact are separate. Captures still require visual review; discrete samples do not prove continuous time."}));file.close()
    hall.queue_free();await process_frame;quit()
