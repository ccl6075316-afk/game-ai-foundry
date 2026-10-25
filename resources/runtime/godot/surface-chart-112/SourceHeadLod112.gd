extends RefCounted
var last_error:String=""
var last_receipt:Dictionary={}
func sha(value:Variant)->String:
    var ctx=HashingContext.new();ctx.start(HashingContext.HASH_SHA256);ctx.update(value if value is PackedByteArray else var_to_bytes(value));return ctx.finish().hex_encode()
func apply(model:Node3D,species:String)->int:
    var config="res://assets/models/fish/motion/head-lods112.json"
    var cfg=JSON.parse_string(FileAccess.get_file_as_string(config));assert(cfg.profiles.has(species))
    var p:Dictionary=cfg.profiles[species]
    assert(preload("res://scripts/aquarium/FishRuntimeData.gd").sha256("res://assets/models/fish/"+species+".glb")==p.model_sha256)
    var body=model.find_child("Closed_body",true,false) as MeshInstance3D
    var original=body.mesh as ArrayMesh;assert(original!=null and original.get_blend_shape_count()==0)
    var frozen=original.get("_surfaces").duplicate(true);var lod_hash=HashingContext.new();lod_hash.start(HashingContext.HASH_SHA256)
    for si in original.get_surface_count():lod_hash.update(var_to_bytes(RenderingServer.mesh_get_surface(original.get_rid(),si).get("lods",[])))
    assert(lod_hash.finish().hex_encode()==p.all_lods_sha256,"New112 native LOD table differs from frozen import")
    var before_arrays:Array=[]
    for si in original.get_surface_count():before_arrays.append(sha(original.surface_get_arrays(si)))
    var expected=frozen.duplicate(true);var counts:Array=[]
    for surface in expected:counts.append(surface.get("lods",[]).size()/2);surface.erase("lods")
    var copy=original.duplicate(false) as ArrayMesh;copy.resource_scene_unique_id=original.resource_scene_unique_id;copy.clear_surfaces();copy.set("_surfaces",expected)
    assert(copy.get("_surfaces")==expected and original.get("_surfaces")==frozen)
    var after_arrays:Array=[]
    for si in copy.get_surface_count():after_arrays.append(sha(copy.surface_get_arrays(si)))
    assert(before_arrays==after_arrays,"LOD suppression changed full-detail arrays")
    body.mesh=copy
    last_receipt={"species":species,"model_sha256":p.model_sha256,"helper_sha256":preload("res://scripts/aquarium/FishRuntimeData.gd").sha256(get_script().resource_path),"config_sha256":preload("res://scripts/aquarium/FishRuntimeData.gd").sha256(config),"exception":"All regenerated head/body LOD tables are unreviewed and excluded; full-detail geometry retained. No LOD passed.","before_lod_counts":counts,"after_lod_counts":[0,0],"all_decoded_surface_arrays_before":before_arrays,"all_decoded_surface_arrays_after":after_arrays,"original_raw_surfaces_sha256":sha(frozen),"actual_after_raw_surfaces_sha256":sha(copy.get("_surfaces")),"source_mesh_resource_id":original.get_instance_id(),"runtime_mesh_resource_id":copy.get_instance_id(),"fin_objects_touched":false}
    model.set_meta("head_lods112_receipt",last_receipt)
    if species=="black_seabream":model.set_meta("eye_lod_106_receipt",last_receipt)
    if species=="zander":model.set_meta("eye_lod_107_receipt",last_receipt)
    return 1
