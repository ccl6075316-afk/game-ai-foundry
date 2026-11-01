extends SceneTree
func _initialize():call_deferred("run")
func run():
    var args=OS.get_cmdline_user_args();var out:String=args[0];DirAccess.make_dir_recursive_absolute(out);var records:Array=[]
    for species in ["black_seabream","red_seabream","zander"]:
        var path="res://assets/models/fish/"+species+".glb";var model=load(path).instantiate();root.add_child(model)
        var body=model.find_child("Closed_body",true,false) as MeshInstance3D
        var h=load("res://scripts/aquarium/FishEyeOwnership.gd").new();var snapshot:Dictionary=h._mesh_snapshot(body)
        snapshot["species"]=species;snapshot["model_sha256"]=FileAccess.get_sha256(path);snapshot["vertex_order_sha256"]=h._vertex_order_hash(body.mesh.surface_get_arrays(0));snapshot["surface0_vertices"]=body.mesh.surface_get_arrays(0)[Mesh.ARRAY_VERTEX].size()
        records.append(snapshot);model.queue_free();await process_frame
    var f=FileAccess.open(out+"/import.validation.json",FileAccess.WRITE);f.store_string(JSON.stringify({"ok":true,"items":records},"  "));quit()
