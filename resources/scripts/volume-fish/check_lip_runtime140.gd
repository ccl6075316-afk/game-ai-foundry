extends "validate_mouth_runtime139.gd"
## Bind final lip resources to actual exhibit skin and UV arrays, including new points.
func run():
    DirAccess.make_dir_recursive_absolute(out);var base=out;hall=load("res://scripts/aquarium/VolumeFishExhibit.gd").new();root.add_child(hall);hall.set_process(false);hall.paused=true
    var rows=[];var helper=load("res://scripts/aquarium/MouthRepair139.gd").new()
    for species in ["bluegill","zander","grass_carp","nile_tilapia","peacock_bass"]:
        hall._select_display(species);var entry:Dictionary=hall._selected();helper.validate(entry.model,species)
        var body=entry.model.find_child("Closed_body",true,false) as MeshInstance3D;var lip=entry.model.find_child("Source_lips139",true,false) as MeshInstance3D;assert(lip!=null and lip.skin==body.skin and lip.get_node(lip.skeleton)==entry.skeleton)
        var data=bound_arrays(lip)
        for si in lip.mesh.get_surface_count():
            var arrays=lip.mesh.surface_get_arrays(si)
            for pair in [["uv",Mesh.ARRAY_TEX_UV],["uv2",Mesh.ARRAY_TEX_UV2]]:
                var points=[]
                if arrays[pair[1]]!=null:
                    for p in arrays[pair[1]]:points.append([p.x,p.y])
                data.parts[si][pair[0]]=points
        var path=base.path_join(species+".mesh.json");var f=FileAccess.open(path,FileAccess.WRITE);f.store_string(JSON.stringify(data));f.close();rows.append({"species":species,"path":path,"sha256":FileAccess.get_sha256(path),"same_original_skin_and_skeleton":true})
    var f=FileAccess.open(base+"/runtime.validation.json",FileAccess.WRITE);f.store_string(JSON.stringify({"ok":true,"rows":rows,"config_sha256":FileAccess.get_sha256("res://assets/models/fish/motion/mouth-repair139.json"),"checker_sha256":FileAccess.get_sha256(get_script().resource_path)},"  "));f.close();hall.queue_free();await process_frame;quit()
