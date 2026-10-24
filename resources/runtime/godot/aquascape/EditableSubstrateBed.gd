extends "res://scripts/aquarium/EditableSandBed.gd"
const MATERIAL_IDS := ["fine_sand","quartz_white","aquasoil_dark","river_gravel","slate_chips"]
var material_ids := PackedByteArray()
var active_material := 0
var blend_paint: ShaderMaterial
var gravel

func setup(texture: Texture2D) -> void:
    material_ids.resize(NX*NZ)
    material_ids.fill(0)
    super.setup(texture)
    blend_paint=ShaderMaterial.new()
    blend_paint.shader=load("res://scripts/aquarium/SubstrateBlend.gdshader")
    for i in 5:
        var path: String="res://assets/aquascape-sand-v1/fine-sand.png" if i==0 else "res://assets/aquascape-substrates-v2/"+MATERIAL_IDS[i]+".png"
        blend_paint.set_shader_parameter("substrate_"+str(i),load(path))
    for piece in chunks:piece.material_override=blend_paint
    side.material_override=blend_paint
    gravel=preload("res://scripts/aquarium/SubstrateGravel.gd").new()
    gravel.name="BatchedSurfaceGravel"
    add_child(gravel)
    gravel.setup(self)
    for cz in 4:
        for cx in 4:gravel.refresh(cx,cz)

func reset(value: float) -> void:
    material_ids.resize(NX*NZ)
    material_ids.fill(active_material)
    super.reset(value)

func material_at(x: float,z: float) -> int:
    var ix: int=clampi(roundi((x+WIDTH*.5)/DX),0,NX-1)
    var iz: int=clampi(roundi((z+DEPTH*.5)/DZ),0,NZ-1)
    return material_ids[iz*NX+ix]

func _coverage(id: int) -> Color:
    match id:
        0:return Color(1,0,0,0)
        1:return Color(0,1,0,0)
        2:return Color(0,0,1,0)
        3:return Color(0,0,0,1)
    return Color(0,0,0,0)

func brush(at: Vector3,radius: float,seconds: float,operation: String) -> void:
    if operation in ["pour","paint"]:
        var x0: int=maxi(0,int(floor((at.x-radius+WIDTH*.5)/DX)))
        var x1: int=mini(NX-1,int(ceil((at.x+radius+WIDTH*.5)/DX)))
        var z0: int=maxi(0,int(floor((at.z-radius+DEPTH*.5)/DZ)))
        var z1: int=mini(NZ-1,int(ceil((at.z+radius+DEPTH*.5)/DZ)))
        for z in range(z0,z1+1):
            for x in range(x0,x1+1):
                if Vector2(x*DX-WIDTH*.5-at.x,z*DZ-DEPTH*.5-at.z).length_squared()<radius*radius*.88:material_ids[z*NX+x]=active_material
        if operation=="paint":
            var started := Time.get_ticks_usec()
            rebuild_region(x0,x1,z0,z1)
            last_brush_ms=(Time.get_ticks_usec()-started)/1000.0
            return
    super.brush(at,radius,seconds,operation)

func _chunk(cx: int,cz: int) -> void:
    var verts := PackedVector3Array()
    var normals := PackedVector3Array()
    var uv := PackedVector2Array()
    var colors := PackedColorArray()
    var indices := PackedInt32Array()
    for z in range(cz*CHUNK_Z,(cz+1)*CHUNK_Z+1):
        for x in range(cx*CHUNK_X,(cx+1)*CHUNK_X+1):
            var p := _vertex(x,z)
            verts.append(p);normals.append(_normal(x,z));uv.append(Vector2(p.x,p.z)/.48)
            colors.append(_coverage(material_ids[z*NX+x]))
    for z in CHUNK_Z:
        for x in CHUNK_X:
            var i := z*(CHUNK_X+1)+x
            indices.append_array(PackedInt32Array([i,i+1,i+CHUNK_X+1,i+1,i+CHUNK_X+2,i+CHUNK_X+1]))
    var arrays: Array=[]
    arrays.resize(Mesh.ARRAY_MAX)
    arrays[Mesh.ARRAY_VERTEX]=verts;arrays[Mesh.ARRAY_NORMAL]=normals;arrays[Mesh.ARRAY_TEX_UV]=uv;arrays[Mesh.ARRAY_COLOR]=colors;arrays[Mesh.ARRAY_INDEX]=indices
    var mesh := ArrayMesh.new()
    mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES,arrays)
    chunks[cz*4+cx].mesh=mesh
    mesh_updates+=1

func _walls() -> void:
    var st := SurfaceTool.new()
    st.begin(Mesh.PRIMITIVE_TRIANGLES)
    for edge in 4:
        var count: int=NX if edge<2 else NZ
        for k in count-1:
            var a: Vector3
            var b: Vector3
            var normal: Vector3
            if edge==0:a=_vertex(k,0);b=_vertex(k+1,0);normal=Vector3.FORWARD
            elif edge==1:a=_vertex(k+1,NZ-1);b=_vertex(k,NZ-1);normal=Vector3.BACK
            elif edge==2:a=_vertex(0,k+1);b=_vertex(0,k);normal=Vector3.LEFT
            else:a=_vertex(NX-1,k);b=_vertex(NX-1,k+1);normal=Vector3.RIGHT
            var c := Vector3(a.x,-.002,a.z)
            var d := Vector3(b.x,-.002,b.z)
            for p in [a,c,b,b,c,d]:
                st.set_normal(normal)
                st.set_uv(Vector2(p.x+p.z,p.y)/.48)
                st.set_color(_coverage(material_at(p.x,p.z)))
                st.add_vertex(p)
    side.mesh=st.commit()

func rebuild_region(x0: int,x1: int,z0: int,z1: int) -> void:
    super.rebuild_region(x0,x1,z0,z1)
    if not is_instance_valid(gravel):return
    for cz in 4:
        for cx in 4:
            if cx*CHUNK_X>x1+1 or (cx+1)*CHUNK_X<x0-1 or cz*CHUNK_Z>z1+1 or (cz+1)*CHUNK_Z<z0-1:continue
            gravel.refresh(cx,cz)
