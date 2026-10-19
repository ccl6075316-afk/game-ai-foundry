extends SceneTree
## Fixed-camera actual GPU comparisons, with source-local eyes and per-species finite behavior.
var hall
var out:String
var config:Dictionary
var requested:Array=[]
const FPS=12
const FRAMES=192
var friendly=preload("res://scripts/aquarium/FriendlyFishPresentation.gd")
func _initialize():
    var args=OS.get_cmdline_user_args();out=args[0]
    for i in range(1,args.size()):requested.append(args[i])
    call_deferred("run")
func save_image(path:String):
    await process_frame
    await RenderingServer.frame_post_draw
    assert(hall.viewport.get_texture().get_image().save_png(path)==OK)
func eye_setting(entry:Dictionary, settings:Dictionary, enabled:bool):
    for node in entry.model.find_children("*","MeshInstance3D",true,false):
        for surface in node.mesh.get_surface_count():
            var material=node.get_active_material(surface)
            if material is ShaderMaterial and material.shader.resource_path.ends_with("FishBodyOpaque.gdshader"):
                material.set_shader_parameter("friendly_eye_scale",float(settings.eye_scale) if enabled else 1.0)
func camera_pose(entry:Dictionary, anchor:Vector3, yaw:float=.28, pitch:float=.10, distance:float=1.18):
    hall.target=anchor;hall.yaw=yaw;hall.pitch=pitch;hall.distance=entry.length_m*distance;hall._update_camera()
func run():
    root.size=Vector2i(1280,720);root.content_scale_size=Vector2i(1280,720)
    DirAccess.make_dir_recursive_absolute(out)
    config=JSON.parse_string(FileAccess.get_file_as_string("res://assets/models/fish/motion/presentation.json"))
    if requested.is_empty():requested=config.species
    var original_profiles:Dictionary=JSON.parse_string(FileAccess.get_file_as_string("res://original-motion.json")).profiles
    hall=load("res://scripts/aquarium/VolumeFishExhibit.gd").new();root.add_child(hall);hall.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
    await process_frame
    hall.set_process(false);hall.paused=true
    var layer=CanvasLayer.new();hall.viewport.add_child(layer)
    var label=Label.new();layer.add_child(label);label.position=Vector2(16,12);label.add_theme_font_size_override("font_size",22);label.add_theme_color_override("font_outline_color",Color.BLACK);label.add_theme_constant_override("outline_size",5)
    for species in requested:
        var settings:Dictionary=config.profiles[species];assert(friendly.validate(settings))
        hall._select_display(species);var entry:Dictionary=hall._selected()
        for tank in hall.tanks:tank.root.visible=tank.species==species
        var origin:Vector3=entry.controller._origin
        var anchor:Vector3=entry.origin
        var target:Vector3=anchor+Vector3(.075*entry.length_m,float(settings.height_tl)*entry.length_m,0.)
        var records:Array=[]
        var folder:String=out+"/"+species;DirAccess.make_dir_recursive_absolute(folder)
        for variant in ["before","after"]:
            var profile:Dictionary=original_profiles[species].duplicate(true) if variant=="before" else entry.profile.duplicate(true)
            assert(entry.controller.configure(entry.carrier,entry.model,entry.player,entry.skeleton,profile,origin).ok)
            eye_setting(entry,settings,variant=="after")
            entry.controller.set_action("Swim",true);entry.controller.seek(0.)
            entry.controller.set_motion_controls({"body_amplitude":1.,"body_frequency":1.,"fin_amplitude":1.,"fin_frequency":1.},true)
            var path:String=folder+"/"+variant;DirAccess.make_dir_recursive_absolute(path+"/frames")
            entry.controller.step(0.);entry.controller.seek(.6)
            entry.carrier.global_position=anchor;entry.carrier.rotation=Vector3.ZERO
            label.text=settings.name+(" · 原版" if variant=="before" else " · 轻调试作")
            for view in [["neutral",.28,.10,1.18],["side",0.,0.,1.18],["front",PI/2.,.04,1.18],["top",0.,1.30,1.18],["opposite",PI+.28,.10,1.18]]:
                camera_pose(entry,anchor,view[1],view[2],view[3]);await save_image(path+"/"+view[0]+".png")
            if variant=="after":
                var stored:Array=[]
                for node in entry.model.find_children("*","MeshInstance3D",true,false):
                    for surface in node.mesh.get_surface_count():
                        stored.append([node,surface,node.get_surface_override_material(surface)])
                        var grey=StandardMaterial3D.new();grey.albedo_color=Color(.55,.57,.59);grey.roughness=1.;grey.cull_mode=BaseMaterial3D.CULL_DISABLED
                        node.set_surface_override_material(surface,grey)
                camera_pose(entry,anchor);await save_image(path+"/grey.png")
                for item in stored:item[0].set_surface_override_material(item[1],item[2])
            entry.controller.set_action("Swim",true);entry.controller.seek(0.)
            var samples:Array=[]
            for frame in FRAMES:
                var t:float=float(frame)/FPS;var state:Dictionary=friendly.state(t,settings,entry.length_m)
                if variant=="after":entry.controller.set_motion_controls(state.controls)
                entry.controller.step(1./FPS)
                var offset:Vector3=state.offset if variant=="after" else Vector3(lerpf(-.20,.40,t/16.),float(settings.height_tl),0.)*entry.length_m
                var yaw:float=state.yaw if variant=="after" else 0.
                entry.carrier.global_position=anchor+offset;entry.carrier.rotation=Vector3(0.,yaw,0.)
                camera_pose(entry,target)
                label.text=settings.name+(" · "+state.label if variant=="after" else " · 原版匀速对照")
                await save_image(path+"/frames/frame-%04d.png"%frame)
                var snapshot:Dictionary=entry.controller.snapshot();assert(snapshot.ready and snapshot.inside_envelope)
                var raw:Array=snapshot.head_world;var head:Vector3=Vector3(raw[0],raw[1],raw[2])-anchor
                var half:Vector3=Vector3(profile.tank_size_m[0],profile.tank_size_m[1],profile.tank_size_m[2])*.5
                var envelope:float=snapshot.computed_skin_envelope_m
                var manual_inside:bool=absf(head.x)+envelope<=half.x and absf(head.y)+envelope<=half.y and absf(head.z)+envelope<=half.z
                assert(manual_inside,"Manual authored path exceeds conservative fish envelope: "+species)
                samples.append({"time":t,"stage":state.stage,"phase":state.label,"offset_m":[offset.x,offset.y,offset.z],"yaw":yaw,"actual_controls":snapshot.motion_controls,"manual_path_inside":manual_inside,"snapshot":snapshot})
                if frame in [18,48,84,108,138,174]:await save_image(path+"/key-%03d.png"%frame)
            records.append({"variant":variant,"frames":FRAMES,"fps":FPS,"shape_scale":profile.get("presentation_shape_scale",[1.,1.,1.]),"eye_scale":settings.eye_scale if variant=="after" else 1.,"samples":samples})
        var result={"schema_version":1,"ok":records.size()==2,"species":species,"settings":settings,"records":records,"model_sha256":FileAccess.get_sha256("res://assets/models/fish/"+species+".glb"),"presentation_sha256":FileAccess.get_sha256("res://assets/models/fish/motion/presentation.json"),"behavior_sha256":FileAccess.get_sha256("res://scripts/aquarium/FriendlyFishPresentation.gd"),"scope":"Two actual-Godot source-preserving variants. Before is uniform comparison movement, not the original full exhibit path. Four standard actions and authored behavior need independent geometry checks."}
        var file=FileAccess.open(folder+"/presentation.validation.json",FileAccess.WRITE);file.store_string(JSON.stringify(result,"  "));file.close()
        print("CAPTURE_DONE "+species)
    quit()
