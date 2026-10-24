extends Node3D
## 32 fixed MultiMesh nodes, <=4608 deterministic visible stones, no grain nodes.
var batches: Array=[]
var bounds: Array=[]
var locations: Array=[]
var templates: Array=[]
var refreshes := 0
var bed

func setup(surface) -> void:
    bed=surface
    var catalog: Array=JSON.parse_string(FileAccess.get_file_as_string("res://assets/aquascape-v5/catalog.json")).assets
    var sources: Array=[]
    for id in ["river_boulder","rock"]:
        var spec: Dictionary={}
        for row in catalog:
            if row.id==id:spec=row
        var model: Node3D=(load("res://assets/aquascape-substrates-v2/"+id+"-gravel.glb") as PackedScene).instantiate()
        var mesh: Mesh=(model.find_children("*","MeshInstance3D",true,false)[0] as MeshInstance3D).mesh
        var paint := ShaderMaterial.new()
        paint.shader=load("res://scripts/aquarium/ThreeViewArtwork.gdshader")
        for view in ["front","right","top"]:paint.set_shader_parameter(view+"_art",load(spec.material_dir+"/"+id+"-"+view+".png"))
        var d: Dictionary=spec.projection_bounds
        paint.set_shader_parameter("projection_size",Vector3(d.width,d.height,d.depth))
        sources.append({"mesh":mesh,"paint":paint})
        bounds.append(mesh.get_aabb())
        model.free()
    for chunk in 16:
        var pair: Array=[]
        for kind in 2:
            var node := MultiMeshInstance3D.new()
            node.name="Gravel_%02d_%d" % [chunk,kind]
            node.multimesh=MultiMesh.new()
            node.multimesh.transform_format=MultiMesh.TRANSFORM_3D
            node.multimesh.mesh=sources[kind].mesh
            node.multimesh.instance_count=288
            node.multimesh.visible_instance_count=0
            node.material_override=sources[kind].paint
            node.custom_aabb=AABB(Vector3(-.62+(chunk%4)*.3,-.01,-.32+(chunk/4)*.15),Vector3(.34,.28,.19))
            add_child(node)
            pair.append(node)
        batches.append(pair)
        var points := PackedVector2Array()
        var transforms: Array=[[],[]]
        for iz in 12:
            for ix in 24:
                var seed: int=((chunk/4)*12+iz)*96+(chunk%4)*24+ix
                var x: float=-.6+((chunk%4)*24+ix+.5+(_hash(seed)-.5)*.55)*.0125
                var z: float=-.3+((chunk/4)*12+iz+.5+(_hash(seed+8000)-.5)*.55)*.0125
                points.append(Vector2(x,z))
                for kind in 2:
                    var box: AABB=bounds[kind]
                    var width: float=lerpf(.010,.015,_hash(seed+16000))
                    var factor: float=width/box.size.x
                    var basis := Basis.from_euler(Vector3((_hash(seed+24000)-.5)*.25,_hash(seed+32000)*TAU,(_hash(seed+40000)-.5)*.25))
                    basis=Basis(basis.x*factor,basis.y*factor*lerpf(.65,1.1,_hash(seed+48000)),basis.z*factor)
                    transforms[kind].append(Transform3D(basis,Vector3(x,-box.size.y*factor*.38-box.position.y*factor,z)))
        locations.append(points)
        templates.append(transforms)

func _hash(value: int) -> float:
    return fposmod(sin(float(value)*12.9898+78.233)*43758.5453,1.0)

func refresh(cx: int,cz: int) -> void:
    var counts := [0,0]
    var chunk: int=cz*4+cx
    for i in 288:
        var at: Vector2=locations[chunk][i]
        var material: int=bed.material_at(at.x,at.y)
        if material<3:continue
        var height: float=bed.sample(at.x,at.y)
        if height<.002:continue
        var kind: int=0 if material==3 else 1
        var transform: Transform3D=templates[chunk][kind][i]
        transform.origin.y+=height
        batches[chunk][kind].multimesh.set_instance_transform(counts[kind],transform)
        counts[kind]+=1
    for kind in 2:batches[cz*4+cx][kind].multimesh.visible_instance_count=counts[kind]
    refreshes+=1

func visible_count() -> int:
    var count := 0
    for pair in batches:
        for node in pair:count+=node.multimesh.visible_instance_count
    return count
