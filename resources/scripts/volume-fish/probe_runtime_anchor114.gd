extends "./capture_surface_mouth_audit.gd"
## Real posed geometry and runtime LODs; UV rasterization is never substituted.
func pixels(image:Image)->Dictionary:
    var bytes=image.get_data();var faults=0;var covered=0;var background=image.get_pixel(0,0)
    for i in range(0,bytes.size(),4):
        if bytes[i]>245 and bytes[i+1]<10 and bytes[i+2]>245:faults+=1
        if Color8(bytes[i],bytes[i+1],bytes[i+2],bytes[i+3])!=background:covered+=1
    return {"lookup_fault_pixels":faults,"body_pixels":covered}
func run():
    DirAccess.make_dir_recursive_absolute(out)
    for file in runtime_files("res://scripts/aquarium")+runtime_files("res://assets/models/fish/motion"):starting_bindings[file]=FileAccess.get_sha256("res://"+file)
    root.size=Vector2i(640,480);hall=load("res://scripts/aquarium/VolumeFishExhibit.gd").new();root.add_child(hall);hall.set_process(false);hall.paused=true;hall.header.hide();hall.footer.hide()
    hall.screen.set_anchors_and_offsets_preset(Control.PRESET_TOP_LEFT);hall.screen.position=Vector2.ZERO;hall.screen.size=Vector2(640,480);hall.viewport.size=Vector2i(640,480);hall.viewport.render_target_update_mode=SubViewport.UPDATE_ALWAYS
    ownership=JSON.parse_string(FileAccess.get_file_as_string("res://assets/models/fish/motion/surface-ownership.json")).profiles
    for mesh in hall.world.find_children("*","MeshInstance3D",true,false):intrinsic[mesh.get_instance_id()]=mesh.visible
    for label in hall.world.find_children("*","Label3D",true,false):label.hide()
    var charts=JSON.parse_string(FileAccess.get_file_as_string("res://assets/models/fish/motion/surface-charts112.json")).profiles
    var validator=load("res://scripts/aquarium/ValidateSurface112.gd").new();var parser=load("res://scripts/aquarium/FishEyeOwnership.gd").new()
    var unique:Dictionary={};var failures:Array=[]
    for species in charts:
        hall._select_display(species);var entry:Dictionary=hall._selected();var p:Dictionary=charts[species]
        var body=entry.model.find_child(p.mesh,true,false) as MeshInstance3D;var si=int(p.surface);var material=body.get_active_material(si) as ShaderMaterial
        assert(not unique.has(material.get_instance_id()),"Shared chart material");unique[material.get_instance_id()]=true
        if material.shader.code.contains("front112_color"):assert(validator.validate_front(entry.model,species,body,si,material).ok)
        else:assert(validator.validate_chart(entry.model,species,body,si,material).ok)
        var raw_hash=validator.digest(body.mesh.get("_surfaces"));var arrays_hash=validator.digest(body.mesh.surface_get_arrays(si))
        for mesh in hall.world.find_children("*","MeshInstance3D",true,false):mesh.visible=mesh==body
        var r:Dictionary=region(entry);var folder=out+"/"+species;DirAccess.make_dir_recursive_absolute(folder)
        var guard=material.duplicate() as ShaderMaterial;var shader=Shader.new();var code:String=material.shader.code.replace("render_mode","render_mode unshaded,")
        var fragment:Dictionary=parser._stage_braces(code,"fragment")
        code=code.substr(0,fragment.open)+"ALBEDO=rest114_error>.001?vec3(1.,0.,1.):vec3(.5);"+code.substr(fragment.close);shader.code=code;guard.shader=shader
        var stored:Array=[];var hidden=ShaderMaterial.new();var discard_shader=Shader.new();discard_shader.code="shader_type spatial;void fragment(){discard;}";hidden.shader=discard_shader
        for surface in body.mesh.get_surface_count():
            stored.append(body.get_surface_override_material(surface))
            if surface!=si:body.set_surface_override_material(surface,hidden)
        entry.controller.set_motion_controls({"body_amplitude":1.,"body_frequency":1.,"fin_amplitude":1.,"fin_frequency":1.},true)
        var shots:Array=[]
        for action in ["Swim","Turn","Ascend","Dive"]:
            entry.controller.set_action(action,true);entry.controller.step(0.);entry.controller.seek(float(entry.profile.period_seconds)*.21)
            for distance_factor in [1.,3.,8.]:
                camera(entry,r,false,.4,.85)
                var center:Vector3=entry.model.global_transform*r.body.get_center();hall.camera.global_position=center+(hall.camera.global_position-center)*distance_factor;hall.camera.look_at(center)
                var stem=folder+"/"+action+"-distance-"+str(distance_factor)
                body.set_surface_override_material(si,material);await shot(stem+"-actual.png")
                body.set_surface_override_material(si,guard);await shot(stem+"-lookup.png")
                var stats=pixels(hall.viewport.get_texture().get_image());stats.merge({"action":action,"distance_factor":distance_factor,"image":stem+"-lookup.png","snapshot":entry.controller.snapshot()});shots.append(stats)
                if stats.lookup_fault_pixels>0 or stats.body_pixels<30:failures.append({"species":species,"sample":stats})
        for pair in [["Swim","Turn"],["Turn","Ascend"],["Ascend","Dive"],["Dive","Swim"]]:
            entry.controller.set_action(pair[0],true);entry.controller.step(0.);entry.controller.seek(.75);entry.controller.set_action(pair[1],false);entry.controller.step(float(entry.profile.transition_seconds)*.5)
            camera(entry,r,false,.4,.85);var stem=folder+"/"+pair[0]+"-to-"+pair[1]
            body.set_surface_override_material(si,material);await shot(stem+"-actual.png")
            body.set_surface_override_material(si,guard);await shot(stem+"-lookup.png")
            var stats=pixels(hall.viewport.get_texture().get_image());stats.merge({"transition":pair,"fraction":.5,"image":stem+"-lookup.png","snapshot":entry.controller.snapshot()});shots.append(stats)
            if stats.lookup_fault_pixels>0 or stats.body_pixels<30:failures.append({"species":species,"sample":stats})
        for surface in body.mesh.get_surface_count():body.set_surface_override_material(surface,stored[surface])
        assert(raw_hash==validator.digest(body.mesh.get("_surfaces")) and arrays_hash==validator.digest(body.mesh.surface_get_arrays(si)),"Runtime geometry changed")
        records.append({"species":species,"model_sha256":FileAccess.get_sha256(entry.model.scene_file_path),"shader_sha256":material.shader.code.sha256_text(),"runtime_lods_sha256":load("res://scripts/aquarium/RestSurface114.gd").new().snapshot(body).lods_sha256,"shots":shots})
        print("ANCHOR_RUNTIME114 ",species," ",shots.size())
    for file in starting_bindings:assert(starting_bindings[file]==FileAccess.get_sha256("res://"+file))
    var report={"ok":failures.is_empty() and records.size()==charts.size(),"records":records,"failures":failures,"files":starting_bindings,"scope":"Actual runtime full-detail/LOD distance renders, four actions and four midpoint transitions; exact wrapper and current position/normal/UV table validation. Guard probe uses actual production vertex code and actual geometry; discrete samples are not continuous-time or artistic acceptance."}
    var f=FileAccess.open(out+"/runtime-anchor.validation.json",FileAccess.WRITE);f.store_string(JSON.stringify(report,"  ")+"\n");print("ANCHOR_RUNTIME114_DONE ",report.ok," ",failures.size());quit(0 if report.ok else 1)
