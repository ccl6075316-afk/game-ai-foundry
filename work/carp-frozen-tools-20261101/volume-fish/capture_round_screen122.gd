extends "./capture_head_screen117.gd"
## Same world-space camera from the frozen pre-round head, including old native scale.
func camera(entry:Dictionary,r:Dictionary,close:bool,yaw:float,pitch:float):
    if not close:
        super.camera(entry,r,close,yaw,pitch)
        return
    var cfg:Dictionary=JSON.parse_string(FileAccess.get_file_as_string(out.get_base_dir()+"/inputs/camera119.json"))
    var p:Dictionary=cfg[entry.species]
    var a:Array=p.head_position
    var b:Array=p.head_size
    var pos:=Vector3(a[0],a[1],a[2])
    var size:=Vector3(b[0],b[1],b[2])
    var scale:float=entry.length_m/float(p.native_length)
    var direction:Basis=entry.carrier.global_transform.basis.orthonormalized()
    var center:Vector3=entry.model.global_transform.origin+entry.model.global_transform.basis.orthonormalized()*(pos+size*.5)*scale
    var distance:float=maxf(maxf(size.x,maxf(size.y,size.z))*scale*1.9,entry.length_m*.20)
    hall.camera.near=.0005
    hall.camera.global_position=center+direction*Vector3(sin(yaw)*cos(pitch),sin(pitch),cos(yaw)*cos(pitch))*distance
    hall.camera.look_at(center,direction*Vector3.UP)
