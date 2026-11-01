extends "./capture_hammer_review136.gd"
## Labeled readability stress simulation, not an actual underwater renderer.
func run():
    DirAccess.make_dir_recursive_absolute(out);root.size=Vector2i(960,640)
    hall=load("res://scripts/aquarium/VolumeFishExhibit.gd").new();root.add_child(hall)
    hall.set_process(false);hall.paused=true;hall.header.hide();hall.footer.hide()
    hall.screen.set_anchors_and_offsets_preset(Control.PRESET_TOP_LEFT);hall.screen.size=Vector2(960,640)
    hall.viewport.size=Vector2i(960,640);hall.viewport.render_target_update_mode=SubViewport.UPDATE_ALWAYS
    ownership=JSON.parse_string(FileAccess.get_file_as_string("res://assets/models/fish/motion/surface-ownership.json")).profiles
    for mesh in hall.world.find_children("*","MeshInstance3D",true,false):intrinsic[mesh.get_instance_id()]=mesh.visible
    for label in hall.world.find_children("*","Label3D",true,false):label.hide()
    var layer=CanvasLayer.new();hall.viewport.add_child(layer)
    var tint=ColorRect.new();tint.size=Vector2(960,640);tint.color=Color(.04,.18,.25,.18);layer.add_child(tint)
    var label=Label.new();label.text="READABILITY STRESS SIMULATION / blue veil 18% / not actual water";label.position=Vector2(16,16);label.add_theme_font_size_override("font_size",16);layer.add_child(label)
    for species in requested:
        hall._select_display(species);var entry:Dictionary=hall._selected()
        for tank in hall.tanks:tank.root.visible=tank.species==species
        for mesh in hall.world.find_children("*","MeshInstance3D",true,false):mesh.visible=entry.model.is_ancestor_of(mesh) and intrinsic[mesh.get_instance_id()]
        var r=region(entry)
        for close in [false,true]:
            camera(entry,r,close,.65,-.4 if close else .2)
            await shot(out+"/"+species+("-close.png" if close else "-normal.png"))
    quit()
