extends SceneTree
## Isolated investigation only. Never writes runtime assets or acceptance state.
var output := ""
var meshes: Array[ArrayMesh] = []
var report: Dictionary = {"schema_version":1,"species":"zander","production_changed":false,"accepted":false,"surfaces":[],"candidates":[],"inputs":{}}

func _initialize() -> void:
    for arg in OS.get_cmdline_user_args():
        if arg.begins_with("--output="):output=arg.trim_prefix("--output=")
    var allowed=ProjectSettings.globalize_path("res://../plans/reviews/").simplify_path()
    assert(output.is_absolute_path() and output.simplify_path().begins_with(allowed),"Explicit project review directory required")
    DirAccess.make_dir_recursive_absolute(output)
    call_deferred("run")

func bind(path:String) -> void:
    report.inputs[path]=FileAccess.get_sha256(path)

func compact(a:Array,indices:PackedInt32Array) -> Array:
    var count=a[Mesh.ARRAY_VERTEX].size()
    var used:Dictionary={};var order: Array[int]=[];var mapped=PackedInt32Array()
    for id in indices:
        assert(id>=0 and id<count)
        if not used.has(id):used[id]=used.size();order.append(id)
        mapped.append(used[id])
    var result=a.duplicate(true)
    for slot in Mesh.ARRAY_MAX:
        if slot==Mesh.ARRAY_INDEX or a[slot]==null or a[slot].is_empty():continue
        assert(slot not in [Mesh.ARRAY_CUSTOM0,Mesh.ARRAY_CUSTOM1,Mesh.ARRAY_CUSTOM2,Mesh.ARRAY_CUSTOM3],"Custom bytes require explicit layout")
        assert(a[slot].size()%count==0)
        var stride=a[slot].size()/count
        var values=a[slot].duplicate();values.resize(order.size()*stride)
        for i in order.size():
            for j in stride:values[i*stride+j]=a[slot][order[i]*stride+j]
        result[slot]=values
    result[Mesh.ARRAY_INDEX]=mapped
    return result

func dump_geometry(mesh:Mesh,name:String) -> void:
    var surfaces=[]
    for si in mesh.get_surface_count():
        var a=mesh.surface_get_arrays(si);var prefix=name+"-"+str(si)
        for pair in [["positions",a[Mesh.ARRAY_VERTEX].to_byte_array()],["indices",a[Mesh.ARRAY_INDEX].to_byte_array()]]:
            var path=output.path_join(prefix+"-"+pair[0]+".bin")
            var f=FileAccess.open(path,FileAccess.WRITE);f.store_buffer(pair[1]);f.close()
        surfaces.append({"prefix":prefix,"vertices":a[Mesh.ARRAY_VERTEX].size(),"triangles":a[Mesh.ARRAY_INDEX].size()/3})
    report[name+"_geometry"]=surfaces

func run() -> void:
    bind(get_script().resource_path)
    var config="res://assets/models/fish/motion/mouth-repair139.json";bind(config)
    var cfg=JSON.parse_string(FileAccess.get_file_as_string(config)).profiles.zander
    bind(cfg.body.path);bind(cfg.lips.path)
    var source=load(cfg.lips.path) as ArrayMesh
    var generated: Array=[]
    for si in source.get_surface_count():
        var a=source.surface_get_arrays(si)
        var material=source.surface_get_material(si)
        assert(not (material is ShaderMaterial) or not material.shader.code.contains("VERTEX_ID"),"Index-based shader cannot use compaction")
        var importer=ImporterMesh.new()
        importer.add_surface(Mesh.PRIMITIVE_TRIANGLES,a,[],{},material)
        importer.generate_lods(60.0,60.0,[])
        var base=importer.get_surface_arrays(0)
        for slot in Mesh.ARRAY_MAX:
            if slot!=Mesh.ARRAY_INDEX:assert(a[slot]==base[slot],"Importer changed attribute correspondence")
        var levels=[]
        for li in importer.get_surface_lod_count(0):
            levels.append({"indices":importer.get_surface_lod_indices(0,li),"error":importer.get_surface_lod_size(0,li)})
        generated.append(levels)
        var counts=[]
        for level in levels:counts.append(level.indices.size()/3)
        report.surfaces.append({"surface":si,"original_triangles":a[Mesh.ARRAY_INDEX].size()/3,"lod_triangles":counts,"attributes_unchanged_before_compaction":true})
    var freezer=load("E:/game-ai-foundry/resources/runtime/godot/mouth-repair-139/PortableMaterial139.gd")
    for ratio in [.25,.1,.03]:
        var mesh=ArrayMesh.new();var total=0;var rows=[]
        for si in source.get_surface_count():
            var a=source.surface_get_arrays(si);var original:PackedInt32Array=a[Mesh.ARRAY_INDEX]
            var chosen=original;var error=0.0;var best=INF
            for level in generated[si]:
                var distance=absf(float(level.indices.size())/original.size()-ratio)
                if distance<best:best=distance;chosen=level.indices;error=level.error
            var compacted=compact(a,chosen)
            mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES,compacted)
            mesh.surface_set_material(si,freezer.freeze(source.surface_get_material(si)))
            total+=chosen.size()/3
            rows.append({"surface":si,"triangles":chosen.size()/3,"vertices":compacted[Mesh.ARRAY_VERTEX].size(),"lod_error_native":error})
        var name="lips-"+str(int(ratio*100));var path=output.path_join(name+".res")
        assert(ResourceSaver.save(mesh,path)==OK)
        report.candidates.append({"name":name,"path":path,"sha256":FileAccess.get_sha256(path),"triangles":total,"surfaces":rows,"cold_loaded":false})
        meshes.append(mesh)
        dump_geometry(mesh,name)
    dump_geometry(source,"baseline")
    dump_geometry(load(cfg.body.path),"body")
    var f=FileAccess.open(output.path_join("probe.validation.json"),FileAccess.WRITE)
    f.store_string(JSON.stringify(report,"  "));f.close()
    print("LIP_REDUCTION ",JSON.stringify(report.candidates))
    quit()
