extends "./capture_hammer_tail_audit.gd"
## Orthographic source-space crop anchored from the last small dorsal/anal fin.
func region(entry:Dictionary)->Dictionary:
    var aspect=2.5146496815 if entry.species=="great_hammerhead" else 2.8926470588
    var bounds=AABB(Vector3(-.5,-.5/aspect,-.025),Vector3(.425,1./aspect,.05))
    return {"body":bounds,"head":bounds,"extent_m":.425*entry.model.global_transform.basis.get_scale().x}
func camera(entry:Dictionary,r:Dictionary,close:bool,yaw:float,pitch:float):
    if absf(yaw-PI/2.)<.01:yaw=-PI/2.
    super.camera(entry,r,close,yaw,pitch)
    hall.camera.projection=Camera3D.PROJECTION_ORTHOGONAL
    hall.camera.size=r.body.size.y*entry.model.global_transform.basis.get_scale().x*1.08
