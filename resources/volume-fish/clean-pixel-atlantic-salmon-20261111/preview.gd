extends "E:/game-ai-foundry/resources/scripts/volume-fish/portable/FishAssetViewer.gd"
func run() -> void:
    await super.run()
    if config.get("mode", "") != "interactive":return
    var lamps=root.find_children("*","DirectionalLight3D",true,false);assert(lamps.size()==1);lamps[0].light_energy=.65;lamps[0].rotation_degrees=Vector3(-45,-35,0)
    root.title="Atlantic salmon R3 color candidate"
    _apply_camera(config.get("camera",{}))
    for i in 4:await process_frame
    await RenderingServer.frame_post_draw
    assert(root.get_texture().get_image().save_png(str(config.output).path_join("live-preview.png"))==OK)
    FileAccess.open(str(config.output).path_join("live-ready.validation.json"),FileAccess.WRITE).store_string(JSON.stringify({"ok":true,"model_sha256":FileAccess.get_sha256(config.model),"light_energy":lamps[0].light_energy,"scope":"Actual interactive R3 cold read; reference light, no static model patch."},"  "))
    var help=Label.new();help.text="1 Swim   2 Turn   3 Ascend   4 Dive   |   Drag: orbit   Wheel: zoom   Space: pause   G: clay";help.position=Vector2(12,715);root.add_child(help)
func _input(event: InputEvent) -> bool:
    if ready_for_input and controller!=null and event is InputEventKey and event.pressed and not event.echo:
        var actions={KEY_1:"Swim",KEY_2:"Turn",KEY_3:"Ascend",KEY_4:"Dive"}
        if actions.has(event.keycode):
            assert(controller.set_action(actions[event.keycode],true));controller.step(0.)
    return super._input(event)

func _advance(delta: float) -> void:
    var previous_position=carrier.global_position
    super._advance(delta)
    target+=carrier.global_position-previous_position
    _update_camera()
