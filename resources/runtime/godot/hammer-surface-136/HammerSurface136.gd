extends RefCounted
const PROJECTIONS={
    "scalloped_hammerhead":[Vector4(1.0675961537,.4694641970,3.0659579557,.4992548435),3.3564013841,Vector4(.9642,.1341,.0130,.0447)],
    "great_hammerhead":[Vector4(1.2326625138,.3911223218,3.3244534464,.4985569986),2.51464968,Vector4(.9695,.0956,.0118,.0346)],
    "smooth_hammerhead":[Vector4(1.0670410439,.4669227319,2.9670941911,.5),2.8926470588,Vector4(.9752,.1196,.0100,.0337)]
}
const MOUTHS={
    "scalloped_hammerhead":[Vector4(-24.2945616,-4.1699026,2.0368421,.77),Vector4(1.5505411,-4.3567552,1.5139614,.851),Vector4(-10.3262319,-1.4910652,1.0899149,.916)],
    "great_hammerhead":[Vector4(-3.6471037,2.6202600,.95614035,.77),Vector4(-41.1460301,4.6611496,1.1698076,.818),Vector4(.59152486,.39127127,1.3273273,.883)],
    "smooth_hammerhead":[Vector4(-87.7025972,-7.3984124,2.8883041,.77),Vector4(-37.3971648,-5.9232158,1.6896537,.877),Vector4(-34.2186574,-.68053472,.81685339,.942)]
}
## Candidate continuous source projection. Geometry and original pixels stay intact.
func retain_reviewed_detail(model:Node3D,species:String)->void:
    var config=JSON.parse_string(FileAccess.get_file_as_string("res://assets/models/fish/motion/hammer-lods137.json")).profiles[species]
    assert(config.model_sha256==preload("res://scripts/aquarium/FishRuntimeData.gd").sha256(model.scene_file_path))
    var rest=load("res://scripts/aquarium/RestSurface114.gd").new();var receipts=[]
    for mesh in model.find_children("*","MeshInstance3D",true,false):
        var before=rest.snapshot(mesh);assert(before==config.meshes[str(mesh.name)],"137 imported mesh changed; repeat LOD review")
        var source=mesh.mesh as ArrayMesh;var raw=source.get("_surfaces").duplicate(true);var removed=[]
        for surface in raw:removed.append(surface.get("lods",[]).size()/2);surface.erase("lods")
        var copy=source.duplicate(false) as ArrayMesh;copy.clear_surfaces();copy.set("_surfaces",raw);mesh.mesh=copy
        var after=rest.snapshot(mesh);assert(before.all_surface_arrays_sha256==after.all_surface_arrays_sha256)
        receipts.append({"mesh":str(mesh.name),"before":before,"after":after,"removed_lods_per_surface":removed,"base_arrays_identical":true})
    model.set_meta("hammer_lod137_receipt",{"model_sha256":config.model_sha256,"config_sha256":preload("res://scripts/aquarium/FishRuntimeData.gd").sha256("res://assets/models/fish/motion/hammer-lods137.json"),"meshes":receipts})

func wrap_source(original:String)->String:
    var include=FileAccess.get_file_as_string(get_script().resource_path.get_base_dir()+"/HammerSurface136.gdshaderinc")
    var code=original.replace("void vertex()",include+"\nvoid vertex()")
    var at=code.find("{",code.find("void vertex()"))
    code=code.insert(at+1,"chart112_rest_position=VERTEX;chart112_rest_normal=NORMAL;")
    code=code.replace("ALBEDO=color.rgb;","ALBEDO=hammer136_color(color.rgb);")
    return load("res://scripts/aquarium/RestSurface114.gd").new().wrap_chart(code)

func validate(model:Node3D,species:String,mesh:MeshInstance3D,si:int,material:ShaderMaterial)->Dictionary:
    if not PROJECTIONS.has(species) or str(mesh.name) not in ["Closed_body","Cephalofoil"] or si not in [0,1,2]:return {"ok":false,"reason":"Not a137 target"}
    if mesh.get_active_material(si)!=material or not model.is_ancestor_of(mesh):return {"ok":false,"reason":"136 inactive material"}
    var base=FileAccess.get_file_as_string("res://scripts/aquarium/FishBodyOpaque.gdshader")
    if material.shader.code!=wrap_source(base):return {"ok":false,"reason":"136 generated code differs from current template"}
    var body=model.find_child("Closed_body",true,false) as MeshInstance3D
    if material.get_shader_parameter("hammer136_top")!=body.mesh.surface_get_material(1).albedo_texture:return {"ok":false,"reason":"136 top source changed"}
    if material.get_shader_parameter("hammer136_side")!=body.mesh.surface_get_material(0).albedo_texture:return {"ok":false,"reason":"136 side source changed"}
    if material.get_shader_parameter("hammer136_wing")!=(str(mesh.name)=="Cephalofoil"):return {"ok":false,"reason":"136 wrong mesh projection"}
    if material.get_shader_parameter("hammer137_projection")!=PROJECTIONS[species][0] or absf(material.get_shader_parameter("hammer137_side_aspect")-PROJECTIONS[species][1])>.00001:return {"ok":false,"reason":"137 wrong source coordinates"}
    if material.get_shader_parameter("hammer137_top_eye")!=PROJECTIONS[species][2]:return {"ok":false,"reason":"137 wrong eye footprint"}
    if material.get_shader_parameter("hammer137_ventral")!=(si==2) or material.get_shader_parameter("hammer137_mouth_curve")!=PackedVector4Array(MOUTHS[species]):return {"ok":false,"reason":"137 wrong mouth chart"}
    if material.get_shader_parameter("hammer137_bottom")!=body.mesh.surface_get_material(2).albedo_texture:return {"ok":false,"reason":"137 bottom source changed"}
    var lod_receipt:Dictionary=model.get_meta("hammer_lod137_receipt",{})
    if lod_receipt.get("model_sha256","")!=preload("res://scripts/aquarium/FishRuntimeData.gd").sha256(model.scene_file_path) or lod_receipt.get("config_sha256","")!=preload("res://scripts/aquarium/FishRuntimeData.gd").sha256("res://assets/models/fish/motion/hammer-lods137.json"):return {"ok":false,"reason":"137 stale full-detail policy"}
    for item in lod_receipt.meshes:
        var target=model.find_child(item.mesh,true,false) as MeshInstance3D
        if load("res://scripts/aquarium/RestSurface114.gd").new().snapshot(target)!=item.after:return {"ok":false,"reason":"137 mesh or LOD table changed"}
        for raw in target.mesh.get("_surfaces"):
            if not raw.get("lods",[]).is_empty():return {"ok":false,"reason":"137 rejected generated LOD active"}
    var rest=load("res://scripts/aquarium/RestSurface114.gd").new().validate(model,mesh,si,material)
    return {"ok":true,"species":species,"mesh":str(mesh.name),"surface":si,"model_sha256":rest.model_sha256,"helper_sha256":preload("res://scripts/aquarium/FishRuntimeData.gd").sha256(get_script().resource_path),"template_sha256":preload("res://scripts/aquarium/FishRuntimeData.gd").sha256(get_script().resource_path.get_base_dir()+"/HammerSurface136.gdshaderinc"),"generated_shader_sha256":material.shader.code.sha256_text(),"rest_tables":rest.tables_sha256}

func apply(model:Node3D,species:String)->int:
    if not PROJECTIONS.has(species):return 0
    retain_reviewed_detail(model,species)
    var body=model.find_child("Closed_body",true,false) as MeshInstance3D
    var wing=model.find_child("Cephalofoil",true,false) as MeshInstance3D
    var top=body.get_active_material(1).get_shader_parameter("source_texture")
    var side=body.get_active_material(0).get_shader_parameter("source_texture")
    var opaque=body.get_active_material(0).get_shader_parameter("opaque_skin")
    var bottom=body.get_active_material(2).get_shader_parameter("source_texture")
    var bottom_opaque=body.get_active_material(2).get_shader_parameter("opaque_skin")
    var rest=load("res://scripts/aquarium/RestSurface114.gd").new()
    var count=0
    for mesh in [body,wing]:
        for si in mesh.mesh.get_surface_count():
            if mesh==body and species!="great_hammerhead" and si!=2:continue
            var material=mesh.get_active_material(si).duplicate() as ShaderMaterial
            var code:String=wrap_source(material.shader.code)
            var shader=Shader.new();shader.code=code;material.shader=shader
            material.set_shader_parameter("hammer136_top",top)
            material.set_shader_parameter("hammer136_side",side)
            material.set_shader_parameter("hammer136_opaque",opaque)
            material.set_shader_parameter("hammer136_wing",mesh==wing)
            material.set_shader_parameter("hammer137_projection",PROJECTIONS[species][0])
            material.set_shader_parameter("hammer137_side_aspect",PROJECTIONS[species][1])
            material.set_shader_parameter("hammer137_top_eye",PROJECTIONS[species][2])
            material.set_shader_parameter("hammer137_ventral",si==2)
            material.set_shader_parameter("hammer137_bottom",bottom)
            material.set_shader_parameter("hammer137_bottom_opaque",bottom_opaque)
            material.set_shader_parameter("hammer137_mouth_curve",PackedVector4Array(MOUTHS[species]))
            rest.bind(model,mesh,si,material)
            mesh.set_surface_override_material(si,material)
            rest.validate(model,mesh,si,material)
            count+=1
    return count
