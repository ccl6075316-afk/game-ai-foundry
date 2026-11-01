extends SceneTree
## Same-pose GPU comparisons, including actual transported material tables.
var output=""
var species=""
var entries=[]
var cameras=[]
var factory
func _initialize():
    for arg in OS.get_cmdline_user_args():
        if arg.begins_with("--output="):output=arg.trim_prefix("--output=")
        if arg.begins_with("--species="):species=arg.trim_prefix("--species=")
    assert(output.is_absolute_path() and output.simplify_path().begins_with(ProjectSettings.globalize_path("res://../plans/reviews/").simplify_path()+"/"))
    call_deferred("run")
func run():
    var config=JSON.parse_string(FileAccess.get_file_as_string("E:/game-ai-foundry/resources/volume-fish/volume-budget-study-v3.json"))
    var source=JSON.parse_string(FileAccess.get_file_as_string(output.path_join("source.validation.json")))
    assert(source.species==species)
    for path in source.inputs:assert(FileAccess.get_sha256(path)==source.inputs[path],"Baseline dependency changed: "+path)
    var budgets=[0];budgets.append_array(config.species[species].whole_fish_triangle_budgets)
    root.size=Vector2i(2048,720);root.title="Fish budget experiment: "+species
    var layout=HBoxContainer.new();layout.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT);root.add_child(layout)
    factory=load("res://scripts/aquarium/VolumeFishExhibit.gd").new();factory._load_profiles()
    preload("res://scripts/aquarium/FishAppearanceCache.gd").begin_entry()
    var transport=load("E:/game-ai-foundry/resources/scripts/volume-fish/LowPolyFishTransport.gd").new()
    var report={"schema_version":1,"species":species,"production_changed":false,"accepted":false,"source_sha256":FileAccess.get_sha256(output.path_join("source.validation.json")),"candidates":[],"images":[],"pose_probes":[],"renderer_sha256":FileAccess.get_sha256(get_script().resource_path),"transport_sha256":FileAccess.get_sha256("E:/game-ai-foundry/resources/scripts/volume-fish/LowPolyFishTransport.gd")}
    var labels=[]
    for budget in budgets:
        var column=VBoxContainer.new();column.size_flags_horizontal=Control.SIZE_EXPAND_FILL;layout.add_child(column)
        var label=Label.new();label.text=config.species[species].label+" · ";column.add_child(label);labels.append(label)
        var container=SubViewportContainer.new();container.stretch=true;container.size_flags_vertical=Control.SIZE_EXPAND_FILL;column.add_child(container)
        var viewport=SubViewport.new();viewport.own_world_3d=true;viewport.size=Vector2i(512,690);container.add_child(viewport)
        var world=Node3D.new();viewport.add_child(world)
        var env=WorldEnvironment.new();env.environment=Environment.new();env.environment.background_mode=Environment.BG_COLOR;env.environment.background_color=Color("183b4a");env.environment.ambient_light_source=Environment.AMBIENT_SOURCE_COLOR;env.environment.ambient_light_color=Color.WHITE;env.environment.ambient_light_energy=.8;world.add_child(env)
        var light=DirectionalLight3D.new();light.rotation_degrees=Vector3(-35,-30,0);world.add_child(light)
        var camera=Camera3D.new();camera.projection=Camera3D.PROJECTION_ORTHOGONAL;camera.near=.001;camera.far=100;world.add_child(camera);camera.current=true;cameras.append(camera)
        factory._add_fish(world,species,float(factory.profiles[species].real_length_cm)/100.,factory.profiles[species])
        var entry=factory.fish[-1];entries.append(entry);entry.player.pause();entry.carrier.transform=Transform3D.IDENTITY
        # Actual current arrays must match the frozen exporter order/bytes,
        # not merely a shared filename or historic GLB hash.
        for node in source.nodes:
            var mesh=entry.model.get_node(node.path)
            for part in node.surfaces:
                var arrays=mesh.mesh.surface_get_arrays(int(part.surface))
                for slot in part.attributes:
                    var ctx=HashingContext.new();ctx.start(HashingContext.HASH_SHA256);ctx.update(arrays[int(slot)].to_byte_array())
                    assert(ctx.finish().hex_encode()==source.binary_sha256[part.attributes[slot]],"Actual source arrays changed")
                var mat=mesh.get_active_material(int(part.surface))
                if part.has("shader_sha256"):assert(mat.shader.code.sha256_text()==part.shader_sha256,"Actual shader changed")
        var recipe_sha=""
        if budget>0:
            var json_path=output.path_join("low-"+str(int(budget))+".json");var data=JSON.parse_string(FileAccess.get_file_as_string(json_path))
            assert(data.source_sha256==report.source_sha256 and data.species==species)
            transport.apply(entry.model,data);recipe_sha=FileAccess.get_sha256(json_path)
        var total=0;var vertices=0;var surfaces=0;var lookup_errors=0;var tables=0
        for node in entry.model.find_children("*","MeshInstance3D",true,false):
            if not node.is_visible_in_tree():continue
            for si in node.mesh.get_surface_count():
                var a=node.mesh.surface_get_arrays(si);total+=a[Mesh.ARRAY_INDEX].size()/3;vertices+=a[Mesh.ARRAY_VERTEX].size();surfaces+=1
                var mat=node.get_active_material(si)
                if mat is ShaderMaterial and budget>0:
                    for key in ["rest114_uvs","eye_uv_lookup"]:
                        var tex=mat.get_shader_parameter(key)
                        if not tex is Texture2D:continue
                        tables+=1;var img=tex.get_image()
                        for vi in a[Mesh.ARRAY_VERTEX].size():
                            var v=img.get_pixel(vi%img.get_width(),vi/img.get_width());var uv=a[Mesh.ARRAY_TEX_UV][vi]
                            if absf(uv.x-v.r)>1e-6 or absf(uv.y-v.g)>1e-6 or v.a<.5:lookup_errors+=1
        assert(lookup_errors==0)
        report.candidates.append({"budget":budget,"triangles":total,"vertices":vertices,"surfaces":surfaces,"bones":entry.skeleton.get_bone_count(),"uv_lookup_errors":lookup_errors,"uv_tables_checked":tables,"recipe_sha256":recipe_sha})
        label.text+=("原版" if budget==0 else "实验")+" · "+str(total)+" 三角面"
    var length_m=float(entries[0].length_m)
    var head=entries[0].model.find_child("Source_lips139",true,false) as MeshInstance3D
    if head==null:head=entries[0].model.find_child("Cephalofoil",true,false) as MeshInstance3D
    assert(head!=null)
    var head_box=head.global_transform*head.get_aabb()
    var tail=entries[0].model.find_child("Caudal",true,false) as MeshInstance3D
    var tail_box=tail.global_transform*tail.get_aabb()
    for shot in ["whole","whole-oblique","head-side","head-front","head-oblique","tail-oblique","Turn"]:
        for i in entries.size():
            var entry=entries[i];var controller=entry.controller
            controller.set_action("Turn" if shot=="Turn" else "Swim",true);controller.step(0);controller.seek(1.25 if shot=="Turn" else 0.0);entry.carrier.transform=Transform3D.IDENTITY
            var direction=Vector3(0,0,1);var center=Vector3.ZERO;var size=length_m*1.55
            if shot=="whole-oblique" or shot=="Turn":direction=Vector3(.7,.3,1).normalized()
            if shot.begins_with("head"):
                center=head_box.get_center();size=maxf(head_box.size.length()*1.65,length_m*.10)
                if shot=="head-front":direction=Vector3(1,0,0)
                if shot=="head-oblique":direction=Vector3(1,.35,1).normalized()
            if shot=="tail-oblique":
                center=tail_box.get_center();size=tail_box.size.length()*1.6;direction=Vector3(.7,.25,1).normalized()
            cameras[i].size=size;cameras[i].position=center+direction*maxf(length_m*3.,2.);cameras[i].look_at(center)
            var finite=true
            for bi in entry.skeleton.get_bone_count():finite=finite and entry.skeleton.get_bone_global_pose(bi).origin.is_finite()
            report.pose_probes.append({"budget":budgets[i],"shot":shot,"finite_bone_origins":finite})
        for frame in 8:await process_frame
        await RenderingServer.frame_post_draw
        var path=output.path_join(shot+".png");assert(root.get_texture().get_image().save_png(path)==OK)
        report.images.append({"path":path,"sha256":FileAccess.get_sha256(path)})
    var f=FileAccess.open(output.path_join("render.validation.json"),FileAccess.WRITE);f.store_string(JSON.stringify(report,"  "));f.close()
    print("BUDGET_RENDER ",species," ",report.candidates)
    layout.queue_free();await process_frame;factory.free();preload("res://scripts/aquarium/FishAppearanceCache.gd").clear();quit()
