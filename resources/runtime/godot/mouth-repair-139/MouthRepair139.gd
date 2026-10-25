extends RefCounted
## Frozen source-matched, rigged mouth resources. GLB remains the rig/fin donor.
const CONFIG="res://assets/models/fish/motion/mouth-repair139.json"
func digest(value:Variant)->String:
    var ctx=HashingContext.new();ctx.start(HashingContext.HASH_SHA256);ctx.update(var_to_bytes(value));return ctx.finish().hex_encode()
func fin_state(model:Node3D,species:String)->Dictionary:
    var p=JSON.parse_string(FileAccess.get_file_as_string("res://assets/models/fish/motion/surface-ownership.json")).profiles[species]
    var result={}
    for name in p.fins:
        var node=model.find_child(name,true,false) as MeshInstance3D;assert(node!=null)
        var arrays=[]
        for si in node.mesh.get_surface_count():arrays.append(node.mesh.surface_get_arrays(si))
        result[name]={"arrays":digest(arrays),"skin":node.skin.get_instance_id(),"skeleton":str(node.skeleton)}
    return result
func auxiliary_state(model:Node3D,species:String)->Dictionary:
    var fins=JSON.parse_string(FileAccess.get_file_as_string("res://assets/models/fish/motion/surface-ownership.json")).profiles[species].fins
    var result={}
    for node in model.find_children("*","MeshInstance3D",true,false):
        if String(node.name) in ["Closed_body","Source_lips139"] or fins.has(String(node.name)):continue
        var arrays=[];var materials=[]
        for si in node.mesh.get_surface_count():
            arrays.append(node.mesh.surface_get_arrays(si))
            var mat=node.get_active_material(si)
            materials.append([mat.get_instance_id(),mat.shader.code.sha256_text() if mat is ShaderMaterial else ""])
        result[String(node.name)]={"arrays":digest(arrays),"materials":materials,"skin":node.skin.get_instance_id() if node.skin else 0,"skeleton":str(node.skeleton)}
    return result
func apply(model:Node3D,species:String)->int:
    if not FileAccess.file_exists(CONFIG):return 0
    var cfg=JSON.parse_string(FileAccess.get_file_as_string(CONFIG))
    if not cfg.profiles.has(species):return 0
    assert(not species.ends_with("hammerhead"),"Hammerheads excluded by user")
    var p:Dictionary=cfg.profiles[species]
    assert(preload("res://scripts/aquarium/FishRuntimeData.gd").sha256(model.scene_file_path)==p.source_model_sha256,"Stale rig/fin donor")
    var before=fin_state(model,species)
    var auxiliary_before=auxiliary_state(model,species)
    var body=model.find_child("Closed_body",true,false) as MeshInstance3D;assert(body!=null and body.skin!=null)
    var skin=body.skin;var skel=body.skeleton
    for kind in ["body","lips"]:
        if not p.has(kind):continue
        assert(preload("res://scripts/aquarium/FishRuntimeData.gd").sha256(p[kind].path)==p[kind].sha256,"Stale139 resource: "+kind)
        var mesh=load(p[kind].path) as ArrayMesh;assert(mesh!=null and mesh.get_surface_count()>0)
        var target=body
        if kind=="lips":
            target=MeshInstance3D.new();target.name="Source_lips139";body.add_child(target)
            target.skin=skin;target.skeleton=target.get_path_to(body.get_node(skel))
            target.set_meta("decorative_lip139",{"underlying_body":"Closed_body","resource_sha256":p[kind].sha256})
        target.mesh=mesh
        for si in mesh.get_surface_count():
            target.set_surface_override_material(si,null)
            var arrays=mesh.surface_get_arrays(si)
            assert(arrays[Mesh.ARRAY_BONES].size()==arrays[Mesh.ARRAY_VERTEX].size()*4)
            assert(arrays[Mesh.ARRAY_WEIGHTS].size()==arrays[Mesh.ARRAY_BONES].size())
    assert(body.skin==skin and body.skeleton==skel and fin_state(model,species)==before)
    for name in p.get("fins",{}):
        assert(species=="peacock_bass" and before.has(name),"Unreviewed fin replacement")
        var target=model.find_child(name,true,false) as MeshInstance3D
        var old_skin=target.skin;var old_skeleton=target.skeleton;var resource:Dictionary=p.fins[name]
        assert(preload("res://scripts/aquarium/FishRuntimeData.gd").sha256(resource.path)==resource.sha256)
        var mesh=load(resource.path) as ArrayMesh;assert(mesh!=null and mesh.get_surface_count()>0)
        target.mesh=mesh
        for si in mesh.get_surface_count():target.set_surface_override_material(si,null)
        assert(target.skin==old_skin and target.skeleton==old_skeleton)
    var active_fins=fin_state(model,species)
    for name in before:
        if not p.get("fins",{}).has(name):assert(active_fins[name]==before[name])
    assert(auxiliary_state(model,species)==auxiliary_before,"Independent jaw/eye/other body changed")
    for name in p.get("retired_runtime_auxiliaries",[]):
        assert(species=="peacock_bass" and String(name).begins_with("Eye_relief112_"),"Unreviewed auxiliary retirement")
        var node=model.find_child(name,true,false) as MeshInstance3D;assert(node!=null)
        node.hide()
    for name in p.get("preserved_visible_auxiliaries",[]):
        var node=model.find_child(name,true,false) as MeshInstance3D;assert(node!=null and node.visible,"Missing actual eye")
    model.set_meta("mouth_repair139_receipt",{"species":species,"source_model_sha256":p.source_model_sha256,"config_sha256":preload("res://scripts/aquarium/FishRuntimeData.gd").sha256(CONFIG),
        "helper_sha256":preload("res://scripts/aquarium/FishRuntimeData.gd").sha256(get_script().resource_path),"body_sha256":p.body.sha256,"lips_sha256":p.get("lips",{}).get("sha256",""),
        "source_reference_semantics":"Original material reference coordinates transported to new geometry; not asserted equal to the new geometric rest positions.","fins_original":before,"fins_active":active_fins,"auxiliary_unchanged":auxiliary_before})
    return 1
func validate(model:Node3D,species:String)->Dictionary:
    var cfg=JSON.parse_string(FileAccess.get_file_as_string(CONFIG));assert(cfg.profiles.has(species))
    var p:Dictionary=cfg.profiles[species];var r:Dictionary=model.get_meta("mouth_repair139_receipt",{})
    assert(not r.is_empty() and r.species==species and r.source_model_sha256==preload("res://scripts/aquarium/FishRuntimeData.gd").sha256(model.scene_file_path))
    assert(r.config_sha256==preload("res://scripts/aquarium/FishRuntimeData.gd").sha256(CONFIG) and r.helper_sha256==preload("res://scripts/aquarium/FishRuntimeData.gd").sha256(get_script().resource_path))
    assert(fin_state(model,species)==r.fins_active)
    for name in p.get("fins",{}):
        var resource:Dictionary=p.fins[name];var node=model.find_child(name,true,false) as MeshInstance3D
        assert(preload("res://scripts/aquarium/FishRuntimeData.gd").sha256(resource.path)==resource.sha256 and node.mesh==load(resource.path))
        for si in node.mesh.get_surface_count():assert(node.get_surface_override_material(si)==null)
    assert(auxiliary_state(model,species)==r.auxiliary_unchanged)
    for name in p.get("retired_runtime_auxiliaries",[]):assert(not model.find_child(name,true,false).visible)
    for name in p.get("preserved_visible_auxiliaries",[]):assert(model.find_child(name,true,false).visible)
    for kind in ["body","lips"]:
        if not p.has(kind):continue
        assert(preload("res://scripts/aquarium/FishRuntimeData.gd").sha256(p[kind].path)==p[kind].sha256)
        var node=model.find_child("Closed_body" if kind=="body" else "Source_lips139",true,false) as MeshInstance3D
        assert(node!=null and node.mesh==load(p[kind].path) and node.skin!=null)
        for si in node.mesh.get_surface_count():
            assert(node.get_surface_override_material(si)==null)
            assert(node.get_active_material(si)==node.mesh.surface_get_material(si))
            var material=node.get_active_material(si)
            if material is ShaderMaterial:
                var uniforms=[]
                for uniform in material.shader.get_shader_uniform_list():uniforms.append(String(uniform.name))
                for key in ["source_texture","opaque_skin","chart112_dorsal","chart112_ventral","original_source","original_opaque","continuation"]:
                    if key in uniforms:assert(material.get_shader_parameter(key) is Texture2D,"Missing139 native source texture: "+key)
    return {"ok":true,"species":species,"body_sha256":p.body.sha256,"lips_sha256":r.lips_sha256,"fins_unchanged":p.get("fins",{}).is_empty(),"fin_resources_verified":true,"auxiliary_unchanged":true,"scope":"Exact frozen resources and original skin binding; fins either unchanged or explicitly frozen replacement resources. Independent jaw/real eyes retained; named redundant relief caps retired separately. GPU, posed contact and visual review remain separate."}
