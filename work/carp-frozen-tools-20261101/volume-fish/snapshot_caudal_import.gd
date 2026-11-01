extends SceneTree
func _initialize():
    var args=OS.get_cmdline_user_args();var records={}
    var rest=load("res://scripts/aquarium/RestSurface114.gd").new()
    for species in ["great_hammerhead","smooth_hammerhead"]:
        var path="res://assets/models/fish/"+species+".glb"
        var model=load(path).instantiate();var meshes={}
        for mesh in model.find_children("*","MeshInstance3D",true,false):meshes[str(mesh.name)]=rest.snapshot(mesh)
        records[species]={"model_sha256":FileAccess.get_sha256(path),"meshes":meshes};model.free()
    var f=FileAccess.open(args[0],FileAccess.WRITE);f.store_string(JSON.stringify(records,"  "));f.close();quit()
