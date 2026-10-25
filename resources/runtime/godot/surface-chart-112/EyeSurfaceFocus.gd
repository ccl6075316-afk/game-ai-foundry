extends RefCounted
## Source-matched relief caps use vertex0 as the pupil center. Focus the actual
## posed surface, not the centerline hidden inside a broad fish's head.
static var first_vertex_cache:Dictionary={}
static func center(model:Node3D,side:float)->Vector3:
    for node in model.find_children("Eye_relief112*","MeshInstance3D",true,false):
        if not node.visible:continue
        var key=node.mesh.get_instance_id()
        if not first_vertex_cache.has(key):
            var a=node.mesh.surface_get_arrays(0)
            assert(a[Mesh.ARRAY_VERTEX].size()>0 and a[Mesh.ARRAY_BONES].size()==a[Mesh.ARRAY_VERTEX].size()*4)
            first_vertex_cache[key]={"v":a[Mesh.ARRAY_VERTEX][0],"j":Array(a[Mesh.ARRAY_BONES].slice(0,4)),"w":Array(a[Mesh.ARRAY_WEIGHTS].slice(0,4))}
        var p:Dictionary=first_vertex_cache[key]
        if p.v.z*side<=0.:continue
        var skeleton=node.get_node(node.skeleton) as Skeleton3D;assert(skeleton!=null and node.skin!=null)
        skeleton.force_update_all_bone_transforms();var point=Vector3.ZERO
        for k in 4:
            if p.w[k]<=0.:continue
            var bind=int(p.j[k]);var bone=node.skin.get_bind_bone(bind)
            if bone<0:bone=skeleton.find_bone(node.skin.get_bind_name(bind))
            assert(bone>=0)
            point+=(skeleton.global_transform*skeleton.get_bone_global_pose(bone)*node.skin.get_bind_pose(bind)*p.v)*p.w[k]
        return point
    assert(false,"No visible shallow eye on requested side")
    return Vector3.ZERO
