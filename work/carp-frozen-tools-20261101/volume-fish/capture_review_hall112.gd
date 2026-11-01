extends SceneTree
var hall
var out: String
var records: Array=[]
func _initialize():
    out=OS.get_cmdline_user_args()[0]
    call_deferred("run")
func shot(path: String):
    await process_frame
    RenderingServer.force_draw()
    await process_frame
    RenderingServer.force_draw()
    assert(root.get_texture().get_image().save_png(path)==OK)
func run():
    DirAccess.make_dir_recursive_absolute(out)
    root.size=Vector2i(1600,1000)
    hall=load("res://scripts/aquarium/VolumeFishExhibit.gd").new()
    root.add_child(hall)
    hall.paused=true
    hall.set_process(false)
    await process_frame
    for species in hall.SPECIES:
        var folder: String=out+"/"+species
        DirAccess.make_dir_recursive_absolute(folder)
        hall._select_display(species)
        var entry: Dictionary=hall._selected()
        assert(entry.controller.set_action("Swim",true))
        entry.controller.step(0.)
        entry.controller.seek(0.)
        hall._focus_selected(false,2.2)
        await shot(folder+"/side.png")
        hall._close_view()
        hall.pitch=1.3
        hall._update_camera()
        await shot(folder+"/top.png")
        hall._close_view()
        await shot(folder+"/oblique.png")
        var actions: Array=[]
        for action in ["Swim","Turn","Ascend","Dive"]:
            hall._select_action(action)
            entry.controller.step(0.)
            entry.controller.seek(.35)
            var snapshot: Dictionary=entry.controller.snapshot()
            assert(str(snapshot.action)==action)
            hall._focus_selected(true,1.9)
            var file: String=folder+"/action-"+action+".png"
            await shot(file)
            actions.append({"action":action,"snapshot":snapshot,"sha256":FileAccess.get_sha256(file)})
        var meshes: Array=[]
        for node in entry.model.find_children("*","MeshInstance3D",true,false):
            var surfaces: Array=[]
            for i in node.mesh.get_surface_count():
                var mat: Material=node.get_active_material(i)
                surfaces.append({"surface":i,"shader":mat.shader.resource_path if mat is ShaderMaterial else "StandardMaterial3D"})
            meshes.append({"mesh":str(node.name),"surfaces":surfaces})
        var controller_path: String=entry.controller.get_script().resource_path
        records.append({"species":species,"model_sha256":FileAccess.get_sha256("res://assets/models/fish/"+species+".glb"),"controller":controller_path,"controller_sha256":FileAccess.get_sha256(controller_path),"actions":actions,"meshes":meshes,"eye106":entry.model.get_meta("eye_ownership_106_receipt",{}),"eye107":entry.model.get_meta("eye_ownership_107_receipt",{}),"lod106":entry.model.get_meta("eye_lod_106_receipt",{}),"lod107":entry.model.get_meta("eye_lod_107_receipt",{})})
        print("REVIEW_HALL "+species)
    var f=FileAccess.open(out+"/completion.validation.json",FileAccess.WRITE)
    f.store_string(JSON.stringify({"schema_version":1,"ok":records.size()==23,"status":"done","next_action":"human_review","species":records.size(),"images":records.size()*7,"records":records,"exhibit_sha256":FileAccess.get_sha256("res://scripts/aquarium/VolumeFishExhibit.gd"),"scope":"Actual installed23-species gallery with UI/tanks,3camera views and4action samples. No visual/anatomical/fin-contact acceptance implied."},"  "))
    f.close()
    hall.queue_free()
    await process_frame
    quit()
