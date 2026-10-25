extends RefCounted
## Independent original-source fin resources; apply before preserved mouth/body layers.
const CONFIG="res://assets/models/fish/motion/fin-source141.json"
func apply(model:Node3D,species:String)->int:
    if not FileAccess.file_exists(CONFIG):return 0
    var cfg=JSON.parse_string(FileAccess.get_file_as_string(CONFIG))
    if not cfg.profiles.has(species):return 0
    assert(not species.ends_with("hammerhead"))
    var p:Dictionary=cfg.profiles[species];assert(preload("res://scripts/aquarium/FishRuntimeData.gd").sha256(model.scene_file_path)==p.source_model_sha256)
    var stored={}
    if p.has("body"):
        var body=model.find_child(p.body.get("node","Closed_body"),true,false) as MeshInstance3D;assert(body!=null and body.skin!=null);assert(preload("res://scripts/aquarium/FishRuntimeData.gd").sha256(p.body.path)==p.body.sha256);var body_mesh=load(p.body.path) as ArrayMesh;assert(body_mesh!=null);body.mesh=body_mesh
        for si in body_mesh.get_surface_count():body.set_surface_override_material(si,null)
    for name in p.fins:
        var node=model.find_child(name,true,false) as MeshInstance3D;assert(node!=null and node.skin!=null)
        var skin=node.skin;var skeleton=node.skeleton;var r:Dictionary=p.fins[name];assert(preload("res://scripts/aquarium/FishRuntimeData.gd").sha256(r.path)==r.sha256)
        var mesh=load(r.path) as ArrayMesh;assert(mesh!=null and mesh.get_surface_count()>0);node.mesh=mesh
        for si in mesh.get_surface_count():node.set_surface_override_material(si,null)
        assert(node.skin==skin and node.skeleton==skeleton);stored[name]={"skin_id":skin.get_instance_id(),"skeleton":str(skeleton),"sha256":r.sha256}
    model.set_meta("fin_source141",{"species":species,"config_sha256":preload("res://scripts/aquarium/FishRuntimeData.gd").sha256(CONFIG),"fins":stored})
    return p.fins.size()
func validate(model:Node3D,species:String)->Dictionary:
    var cfg=JSON.parse_string(FileAccess.get_file_as_string(CONFIG));var p:Dictionary=cfg.profiles[species];var receipt:Dictionary=model.get_meta("fin_source141",{});assert(receipt.species==species and receipt.config_sha256==preload("res://scripts/aquarium/FishRuntimeData.gd").sha256(CONFIG))
    if p.has("body"):
        var body=model.find_child(p.body.get("node","Closed_body"),true,false) as MeshInstance3D;assert(body!=null and preload("res://scripts/aquarium/FishRuntimeData.gd").sha256(p.body.path)==p.body.sha256 and body.mesh==load(p.body.path))
        for si in body.mesh.get_surface_count():assert(body.get_surface_override_material(si)==null)
    for name in p.fins:
        var node=model.find_child(name,true,false) as MeshInstance3D;var r:Dictionary=p.fins[name];assert(preload("res://scripts/aquarium/FishRuntimeData.gd").sha256(r.path)==r.sha256 and node.mesh==load(r.path));assert(node.skin.get_instance_id()==receipt.fins[name].skin_id and str(node.skeleton)==receipt.fins[name].skeleton)
        for si in node.mesh.get_surface_count():assert(node.get_surface_override_material(si)==null and node.get_active_material(si)==node.mesh.surface_get_material(si))
    return {"ok":true,"species":species,"fins":p.fins.keys(),"config_sha256":receipt.config_sha256,"scope":"Frozen new fin resource/skin binding. Source silhouette, contact, visibility and motion are separate gates."}
