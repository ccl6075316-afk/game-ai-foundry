extends "./capture_hammer_tail_audit.gd"
var replaced:Dictionary={}
func region(entry:Dictionary)->Dictionary:
    if not replaced.has(entry.species):
        var folder=out.get_base_dir()+"/candidate/"+entry.species
        var doc=GLTFDocument.new();var state=GLTFState.new()
        assert(doc.append_from_file(folder+"/fish.glb",state)==OK)
        var candidate=doc.generate_scene(state)
        var source=candidate.find_child("Caudal",true,false) as MeshInstance3D
        var target=entry.model.find_child("Caudal",true,false) as MeshInstance3D
        assert(source!=null and target!=null)
        target.mesh=source.mesh
        var profile=JSON.parse_string(FileAccess.get_file_as_string(folder+"/caudal-material.json"))
        var material=target.get_surface_override_material(0).duplicate() as ShaderMaterial
        var edges=PackedVector4Array()
        for e in profile.edges:edges.append(Vector4(e[0],e[1],e[2],e[3]))
        material.set_shader_parameter("edges",edges);material.set_shader_parameter("edge_count",edges.size())
        target.set_surface_override_material(0,material)
        candidate.free();replaced[entry.species]=true
    return super.region(entry)
