extends "./capture_hammer_review136.gd"
## Temporary forced actual imported index buffers, retaining original vertex IDs.
func run():
    DirAccess.make_dir_recursive_absolute(out)
    root.size=Vector2i(960,640)
    hall=load("res://scripts/aquarium/VolumeFishExhibit.gd").new();root.add_child(hall)
    hall.set_process(false);hall.paused=true;hall.header.hide();hall.footer.hide()
    hall.screen.set_anchors_and_offsets_preset(Control.PRESET_TOP_LEFT);hall.screen.size=Vector2(960,640)
    hall.viewport.size=Vector2i(960,640);hall.viewport.render_target_update_mode=SubViewport.UPDATE_ALWAYS
    ownership=JSON.parse_string(FileAccess.get_file_as_string("res://assets/models/fish/motion/surface-ownership.json")).profiles
    for mesh in hall.world.find_children("*","MeshInstance3D",true,false):intrinsic[mesh.get_instance_id()]=mesh.visible
    for label in hall.world.find_children("*","Label3D",true,false):label.hide()
    var rest=load("res://scripts/aquarium/RestSurface114.gd").new()
    for species in requested:
        hall._select_display(species);var entry:Dictionary=hall._selected()
        for tank in hall.tanks:tank.root.visible=tank.species==species
        for mesh in hall.world.find_children("*","MeshInstance3D",true,false):mesh.visible=entry.model.is_ancestor_of(mesh) and intrinsic[mesh.get_instance_id()]
        var originals=[];var levels=1;var base_arrays=[]
        for mesh in entry.model.find_children("*","MeshInstance3D",true,false):
            var source=mesh.mesh as ArrayMesh;assert(source!=null and source.get_blend_shape_count()==0)
            originals.append([mesh,source])
            base_arrays.append({"mesh":str(mesh.name),"snapshot":rest.snapshot(mesh)})
            for raw in source.get("_surfaces"):levels=maxi(levels,1+raw.get("lods",[]).size()/2)
        var r=region(entry);var rows=[];var folder=out+"/"+species;DirAccess.make_dir_recursive_absolute(folder)
        for level in levels:
            var buffers=[]
            for pair in originals:
                var mesh:MeshInstance3D=pair[0];var source:ArrayMesh=pair[1];var raw=source.get("_surfaces").duplicate(true)
                for si in raw.size():
                    var table=raw[si].get("lods",[]);var chosen=mini(level,table.size()/2)
                    if chosen>0:
                        raw[si].index_data=table[(chosen-1)*2+1]
                        raw[si].index_count=raw[si].index_data.size()/(2 if raw[si].vertex_count<=65536 else 4)
                    raw[si].erase("lods")
                    buffers.append({"mesh":str(mesh.name),"surface":si,"level":chosen,"indices":raw[si].index_count,"index_sha256":rest.digest(raw[si].index_data)})
                var copy=source.duplicate(false) as ArrayMesh;copy.clear_surfaces();copy.set("_surfaces",raw)
                for si in copy.get_surface_count():
                    var a=source.surface_get_arrays(si);var b=copy.surface_get_arrays(si)
                    for at in Mesh.ARRAY_MAX:
                        if at!=Mesh.ARRAY_INDEX:assert(a[at]==b[at],"LOD changed original vertex IDs/attributes")
                mesh.mesh=copy
            var frames=[]
            for action in ["Swim","Turn","Ascend","Dive"]:
                entry.controller.set_action(action,false);entry.controller.step(.35)
                camera(entry,r,true,.65,.20 if action in ["Swim","Turn"] else -.4)
                var file=folder+"/lod-%02d-%s.png"%[level,action];await shot(file)
                frames.append({"action":action,"file":file,"sha256":FileAccess.get_sha256(file)})
            rows.append({"level":level,"actual_index_buffers":buffers,"frames":frames})
        for pair in originals:pair[0].mesh=pair[1]
        records.append({"species":species,"model_sha256":FileAccess.get_sha256(entry.model.scene_file_path),"levels":rows,"base_arrays":base_arrays})
    var f=FileAccess.open(out+"/lod.validation.json",FileAccess.WRITE)
    f.store_string(JSON.stringify({"ok":true,"records":records,"checker_sha256":FileAccess.get_sha256(get_script().resource_path),"scope":"All actual imported LOD index buffers forced temporarily, keeping every original vertex attribute and ID. Four-action transition frames. Normal game LOD selection also shown in orbit video; this report is not visual approval."},"  "));f.close();quit()
