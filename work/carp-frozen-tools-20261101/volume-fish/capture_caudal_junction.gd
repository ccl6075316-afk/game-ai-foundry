extends "./capture_hammer_tail_audit.gd"
var replaced:Dictionary={}
func region(entry:Dictionary)->Dictionary:
    if out.get_file().begins_with("candidate") and not replaced.has(entry.species):
        var folder=out.get_base_dir()+"/candidate/"+entry.species
        var doc=GLTFDocument.new();var state=GLTFState.new()
        assert(doc.append_from_file(folder+"/fish.glb",state)==OK)
        var model=doc.generate_scene(state)
        var source=model.find_child("Caudal",true,false) as MeshInstance3D
        var target=entry.model.find_child("Caudal",true,false) as MeshInstance3D
        target.mesh=source.mesh;model.free();replaced[entry.species]=true
    var body=entry.model.find_child("Closed_body",true,false) as MeshInstance3D
    var box: AABB=body.mesh.get_aabb();var rear=box.position.x
    var tail=entry.model.find_child("Caudal",true,false) as MeshInstance3D
    var points=tail.mesh.surface_get_arrays(0)[Mesh.ARRAY_VERTEX];var ymin=1.;var ymax=-1.
    for v in points:
        if absf(v.x-rear)<.0001:ymin=minf(ymin,v.y);ymax=maxf(ymax,v.y)
    assert(ymax>ymin)
    var center=(ymin+ymax)*.5;var bounds=AABB(Vector3(rear-.065,center-.04,-.025),Vector3(.135,.08,.05))
    return {"body":bounds,"head":bounds,"extent_m":.135*entry.model.global_transform.basis.get_scale().x}
func camera(entry:Dictionary,r:Dictionary,close:bool,yaw:float,pitch:float):
    # Look forward from behind the tail; +X would put the camera inside body.
    if absf(yaw-PI/2.)<.01:yaw=-PI/2.
    super.camera(entry,r,close,yaw,pitch)
