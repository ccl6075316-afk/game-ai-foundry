extends "export_runtime_fin_roots112.gd"
## Actual installed layer chain, unchanged pose/check kernels and exact matching.
func cell150(point:Vector3,epsilon:float)->Vector3i:
    return Vector3i(floori(point.x/epsilon),floori(point.y/epsilon),floori(point.z/epsilon))
func matches150(point:Vector3,bins:Dictionary,epsilon:float)->bool:
    var key=cell150(point,epsilon)
    for x in [-1,0,1]:
        for y in [-1,0,1]:
            for z in [-1,0,1]:
                for raw in bins.get(key+Vector3i(x,y,z),[]):
                    if point.distance_to(raw)<epsilon:return true
    return false
func matcher_selftest150():
    var epsilon=.00002;var points=[];var bins={}
    for i in 53:
        var q=Vector3(sin(i*1.7)*.001,cos(i*.3)*.001,sin(i*.7)*.001);points.append(q)
        var key=cell150(q,epsilon)
        if not bins.has(key):bins[key]=[]
        bins[key].append(q)
    for q in points:
        for delta in [Vector3.ZERO,Vector3(.999*epsilon,0,0),Vector3(1.001*epsilon,0,0),Vector3(-epsilon*.57,epsilon*.57,epsilon*.57)]:
            var query=q+delta;var exact=false
            for raw in points:
                if query.distance_to(raw)<epsilon:exact=true;break
            assert(matches150(query,bins,epsilon)==exact,"Root selector changed strict matching semantics")
func prepare(entry:Dictionary,spec:Dictionary)->void:
    matcher_selftest150()
    for path in spec.current_inputs:
        assert(FileAccess.get_sha256(path)==spec.current_inputs[path],"Stale150 runtime input "+path)
    load("res://scripts/aquarium/FishSurfaceOwnership.gd").new().apply(entry.model,spec.species)
    surfaces=[];faces=[];var offset=0;var found={};var skeleton:Skeleton3D=entry.skeleton
    for node in entry.model.find_children("*","MeshInstance3D",true,false):
        var name:String=str(node.name);var is_body=name==spec.body
        for token in ["Dorsal","Anal","Caudal","Pectoral","Pelvic","Tail_Fin","Adipose"]:
            assert(not(token in name)or spec.fins.has(name),"Fin omitted from150 gate: "+name)
        if not is_body and not spec.fins.has(name):continue
        found[name]=true;var bindings:Array[int]=[]
        for j in node.skin.get_bind_count():
            var index=node.skin.get_bind_bone(j)
            if index<0:index=skeleton.find_bone(node.skin.get_bind_name(j))
            assert(index>=0);bindings.append(index)
        var epsilon=float(spec.length_native)*.00002;var bins={}
        if not is_body:
            for raw in spec.fins[name].rest_points_gltf:
                var q=Vector3(raw[0],raw[1],raw[2]);var key=cell150(q,epsilon)
                if not bins.has(key):bins[key]=[]
                bins[key].append(q)
        for si in node.mesh.get_surface_count():
            var a=node.mesh.surface_get_arrays(si);var vertices:PackedVector3Array=a[Mesh.ARRAY_VERTEX];var joints:PackedInt32Array=a[Mesh.ARRAY_BONES];var weights:PackedFloat32Array=a[Mesh.ARRAY_WEIGHTS];var triangles:PackedInt32Array=a[Mesh.ARRAY_INDEX];var count:int=joints.size()/vertices.size();var ids:Array[int]=[];var edges:Array=[]
            if is_body:
                for i in range(0,triangles.size(),3):faces.append([offset+triangles[i],offset+triangles[i+1],offset+triangles[i+2]])
                offset+=vertices.size()
            else:
                var transforms:Array[Transform3D]=[]
                for j in bindings.size():transforms.append(skeleton.global_transform*skeleton.get_bone_global_rest(bindings[j])*node.skin.get_bind_pose(j))
                var selected={}
                for i in vertices.size():
                    var point=Vector3.ZERO
                    for j in count:
                        var at=i*count+j;point+=(transforms[joints[at]]*vertices[i])*weights[at]
                    if matches150(point,bins,epsilon):ids.append(i);selected[i]=true
                var seen={}
                for i in range(0,triangles.size(),3):
                    for pair in [[triangles[i],triangles[i+1]],[triangles[i+1],triangles[i+2]],[triangles[i+2],triangles[i]]]:
                        var key="%d:%d"%[mini(pair[0],pair[1]),maxi(pair[0],pair[1])]
                        if selected.has(pair[0])and selected.has(pair[1])and not seen.has(key):edges.append(pair);seen[key]=true
                assert(not ids.is_empty(),"Unmapped complete150 basal selection: "+spec.species+"/"+name)
            surfaces.append({"name":name,"body":is_body,"mesh":node,"vertices":vertices,"joints":joints,"weights":weights,"bindings":bindings,"count":count,"ids":ids,"edges":edges})
    assert(found.size()==spec.fins.size()+1,"Incomplete150 fin inventory")
func save_json(path:String,value:Variant)->void:
    if path.ends_with("export.validation.json"):
        value["parent_exporter_sha256"]=FileAccess.get_sha256(get_script().get_base_script().resource_path)
        value["root_selector150"]="Same strict distance predicate and27 neighboring exact cells; boundary brute-force self-test passed. Frozen full basal points unchanged."
    super.save_json(path,value)
