extends "E:/game-ai-foundry/resources/scripts/volume-fish/portable/FishAssetViewer.gd"
func run() -> void:
    await super.run()
    if config.get("mode", "") != "interactive":return
    root.title="Brown trout R2 material candidate"
    var help=Label.new();help.text="1 Swim   2 Turn   3 Ascend   4 Dive   |   Drag: orbit   Wheel: zoom   Space: pause   G: clay";help.position=Vector2(12,715);root.add_child(help)
func _input(event: InputEvent) -> bool:
    if ready_for_input and controller!=null and event is InputEventKey and event.pressed and not event.echo:
        var actions={KEY_1:"Swim",KEY_2:"Turn",KEY_3:"Ascend",KEY_4:"Dive"}
        if actions.has(event.keycode):
            assert(controller.set_action(actions[event.keycode],true));controller.step(0.)
    return super._input(event)
