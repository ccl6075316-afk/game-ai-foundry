extends SceneTree
func _initialize():call_deferred("run")
func run():
    var args=OS.get_cmdline_user_args();var hall=load("res://scripts/aquarium/VolumeFishExhibit.gd").new();root.add_child(hall);hall.set_process(false);hall.paused=true;var profiles=JSON.parse_string(FileAccess.get_file_as_string("res://assets/models/fish/motion/motion.json")).profiles;var rows={}
    for species in args.slice(1):
        hall._select_display(species);var e:Dictionary=hall._selected();var scale:float=e.model.scale.x;rows[species]={"model_scale_m_per_native":scale,"length_native":float(profiles[species].real_length_cm)/100./scale,"controller_script":e.controller.get_script().resource_path,"controller_sha256":FileAccess.get_sha256(e.controller.get_script().resource_path)}
    var f=FileAccess.open(args[0],FileAccess.WRITE);f.store_string(JSON.stringify({"ok":rows.size()==args.size()-1,"records":rows,"exhibit_sha256":FileAccess.get_sha256("res://scripts/aquarium/VolumeFishExhibit.gd")}));f.close();hall.queue_free();await process_frame;quit()
