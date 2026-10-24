extends "./capture_caudal_delivery.gd"
## Same validated native/four-action movie, framed around the entire joint.
func region(entry:Dictionary)->Dictionary:
    var body=entry.model.find_child("Closed_body",true,false) as MeshInstance3D
    var box=body.mesh.get_aabb();var rear=box.position.x
    var points=entry.model.find_child("Caudal",true,false).mesh.surface_get_arrays(0)[Mesh.ARRAY_VERTEX]
    var low=1.;var high=-1.
    for v in points:
        if absf(v.x-rear)<.0001:low=minf(low,v.y);high=maxf(high,v.y)
    assert(high>low)
    var bounds=AABB(Vector3(rear-.065,(high+low)*.5-.04,-.025),Vector3(.135,.08,.05))
    return {"body":bounds,"head":bounds,"extent_m":.135*entry.model.global_transform.basis.get_scale().x}
