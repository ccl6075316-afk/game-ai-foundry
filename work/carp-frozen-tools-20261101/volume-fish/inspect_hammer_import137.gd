extends SceneTree
func _initialize():
    var args=OS.get_cmdline_user_args()
    var model=load("res://assets/models/fish/scalloped_hammerhead.glb").instantiate()
    var mesh=model.find_child("Cephalofoil",true,false) as MeshInstance3D
    var rows=[]
    for si in mesh.mesh.get_surface_count():
        var a=mesh.mesh.surface_get_arrays(si);var pts=[]
        for v in a[Mesh.ARRAY_VERTEX]:pts.append([v.x,v.y,v.z])
        rows.append({"surface":si,"positions":pts,"triangles":Array(a[Mesh.ARRAY_INDEX])})
    var f=FileAccess.open(args[0],FileAccess.WRITE);f.store_string(JSON.stringify(rows));f.close();model.free();quit()
