## The maintained complete surface/LBS schedule plus native cap arrays in the SAME pose.
extends "../../../scripts/volume-fish/portable/export_fin_poses_merged.gd"
var cap_entry: Dictionary = {}
var cap_rows: Array = []
var cap_ready := false
var cap_inventory: Dictionary = {}
func prepare(entry: Dictionary, spec: Dictionary) -> void:
    cap_ready=false
    cap_rows=[]
    cap_inventory={}
    cap_entry=entry
    super.prepare(entry,spec)
    if not merge_inventory_ready:return
    var declaration: Dictionary=spec.get("native_eye_caps_inventory",{})
    if declaration.get("model_sha256","")!=spec.model_sha256:return
    var logical: Dictionary=PACKED_PARTS.surfaces(entry,spec)
    if not logical.get("ok",false):return
    for row in logical.surfaces:
        if not declaration.get("caps",{}).has(row.name):continue
        var expected: Dictionary=declaration.caps[row.name]
        if cap_inventory.has(row.name):return
        var arrays: Array=row.arrays
        if arrays[Mesh.ARRAY_VERTEX].size()!=int(expected.vertices) or arrays[Mesh.ARRAY_INDEX].size()!=int(expected.triangles)*3:return
        cap_rows.append(row)
        cap_inventory[row.name]={"vertices":arrays[Mesh.ARRAY_VERTEX].size(),"triangles":arrays[Mesh.ARRAY_INDEX].size()/3,"mesh_path":str(entry.model.get_path_to(row.mesh))}
    cap_ready=cap_rows.size()==declaration.caps.size() and cap_rows.size()>0
    if not cap_ready:push_error("Actual native cap inventory incomplete");quit(1)
func sample(entry: Dictionary,label: String,seconds: float) -> void:
    if not cap_ready:return
    super.sample(entry,label,seconds)
func save_json(path: String,value: Variant) -> void:
    if path.get_file().begins_with("sample-") and value is Dictionary and value.has("body_vertices_m"):
        var skeleton: Skeleton3D=cap_entry.skeleton
        var relative: Transform3D=cap_entry.carrier.global_transform.affine_inverse()*skeleton.global_transform
        var caps: Dictionary={}
        for row in cap_rows:
            var mesh: MeshInstance3D=row.mesh
            var transforms: Array[Transform3D]=[]
            for j in mesh.skin.get_bind_count():
                var bone: int=mesh.skin.get_bind_bone(j)
                if bone<0:bone=skeleton.find_bone(mesh.skin.get_bind_name(j))
                assert(bone>=0)
                transforms.append(relative*skeleton.get_bone_global_pose(bone)*mesh.skin.get_bind_pose(j))
            var arrays: Array=row.arrays
            var vertices: PackedVector3Array=arrays[Mesh.ARRAY_VERTEX]
            var joints: PackedInt32Array=arrays[Mesh.ARRAY_BONES]
            var weights: PackedFloat32Array=arrays[Mesh.ARRAY_WEIGHTS]
            var slots: int=joints.size()/vertices.size()
            var posed: Array=[]
            var rest: Array=[]
            for i in vertices.size():
                var p:=Vector3.ZERO
                for j in slots:
                    var at: int=i*slots+j
                    p+=(transforms[joints[at]]*vertices[i])*weights[at]
                posed.append([p.x,p.y,p.z])
                rest.append([vertices[i].x,vertices[i].y,vertices[i].z])
            caps[row.name]={"vertices_m":posed,"rest_vertices_native":rest,"triangles":Array(arrays[Mesh.ARRAY_INDEX])}
        value["native_eye_caps"]=caps
    if path.ends_with("export.validation.json"):
        value["actual_packed_helper_path"]=(PACKED_PARTS as Script).resource_path
        value["packed_helper_sha256"]=FileAccess.get_sha256((PACKED_PARTS as Script).resource_path)
        value["native_eye_caps_revision"]=1
        value["native_eye_caps_inventory"]=cap_inventory
        value["native_eye_caps_same_pose_body"]=cap_ready
        if not cap_ready:value["ok"]=false
    super.save_json(path,value)
