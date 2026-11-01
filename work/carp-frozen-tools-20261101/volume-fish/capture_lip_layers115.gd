extends "./capture_source_fit115.gd"
func run():
    DirAccess.make_dir_recursive_absolute(out)
    root.size=Vector2i(1200,800)
    hall=load("res://scripts/aquarium/VolumeFishExhibit.gd").new();root.add_child(hall)
    hall.set_process(false);hall.paused=true;hall.header.hide();hall.footer.hide()
    hall.screen.set_anchors_and_offsets_preset(Control.PRESET_TOP_LEFT);hall.screen.position=Vector2.ZERO;hall.screen.size=Vector2(1200,800)
    hall.viewport.size=Vector2i(1200,800);hall.viewport.render_target_update_mode=SubViewport.UPDATE_ALWAYS
    for label in hall.world.find_children("*","Label3D",true,false):label.hide()
    var invisible=ShaderMaterial.new();var shader=Shader.new();shader.code="shader_type spatial;void fragment(){discard;}";invisible.shader=shader
    var pink=StandardMaterial3D.new();pink.shading_mode=BaseMaterial3D.SHADING_MODE_UNSHADED;pink.albedo_color=Color.MAGENTA;pink.cull_mode=BaseMaterial3D.CULL_DISABLED
    for species in requested:
        hall._select_display(species);var entry:Dictionary=hall._selected()
        for tank in hall.tanks:tank.root.visible=tank.species==species
        entry.controller.set_motion_controls({"body_amplitude":0.,"body_frequency":1.,"fin_amplitude":0.,"fin_frequency":1.},true)
        entry.controller.set_action("Swim",true);entry.controller.step(0.);entry.controller.seek(0.)
        var body=entry.model.find_child("Closed_body",true,false) as MeshInstance3D
        var lining=body.get_surface_override_material(1)
        var folder=out+"/"+species;DirAccess.make_dir_recursive_absolute(folder)
        for view in [["front",PI/2.,0.],["side",0.,0.],["oblique",.65,.20]]:
            camera(entry,region(entry),true,view[1],view[2])
            body.set_surface_override_material(1,lining);await shot(folder+"/"+view[0]+"-current.png")
            body.set_surface_override_material(1,invisible);await shot(folder+"/"+view[0]+"-no-lining.png")
            body.set_surface_override_material(1,pink);await shot(folder+"/"+view[0]+"-lining-region.png")
        body.set_surface_override_material(1,lining)
    quit()
