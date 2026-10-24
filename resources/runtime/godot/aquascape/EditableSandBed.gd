extends Node3D
## Persistent substrate is one height array and sixteen shared-material chunks.
const NX := 129
const NZ := 65
const WIDTH := 1.2
const DEPTH := .6
const MAX_HEIGHT := .24
const DX := WIDTH/(NX-1)
const DZ := DEPTH/(NZ-1)
const CHUNK_X := 32
const CHUNK_Z := 16
var heights := PackedFloat32Array()
var chunks: Array[MeshInstance3D]=[]
var side: MeshInstance3D
var paint: StandardMaterial3D
var mesh_updates := 0
var last_update_ms := 0.0
var last_brush_ms := 0.0

func setup(texture: Texture2D) -> void:
    paint=StandardMaterial3D.new()
    paint.albedo_texture=texture
    paint.texture_filter=BaseMaterial3D.TEXTURE_FILTER_NEAREST
    paint.roughness=1.0
    paint.metallic_specular=0.0
    for i in 16:
        var piece := MeshInstance3D.new()
        piece.name="SandChunk%02d" % i
        piece.material_override=paint
        add_child(piece)
        chunks.append(piece)
    side=MeshInstance3D.new()
    side.name="SandThickness"
    side.material_override=paint
    add_child(side)
    reset(.025)

func reset(value: float) -> void:
    heights.resize(NX*NZ)
    heights.fill(clampf(value,0,MAX_HEIGHT))
    rebuild_all()

func sample(x: float,z: float) -> float:
    var u: float=clampf((x+WIDTH*.5)/DX,0,NX-1.00001)
    var v: float=clampf((z+DEPTH*.5)/DZ,0,NZ-1.00001)
    var ix := int(u)
    var iz := int(v)
    return lerpf(lerpf(heights[iz*NX+ix],heights[iz*NX+ix+1],u-ix),lerpf(heights[(iz+1)*NX+ix],heights[(iz+1)*NX+ix+1],u-ix),v-iz)

func volume() -> float:
    var sum := 0.0
    # Trapezoidal integration weights the boundary samples correctly.
    for z in NZ:
        for x in NX:
            var weight: float=(.5 if x==0 or x==NX-1 else 1.0)*(.5 if z==0 or z==NZ-1 else 1.0)
            sum+=heights[z*NX+x]*weight
    return sum*DX*DZ

func brush(at: Vector3,radius: float,seconds: float,operation: String) -> void:
    var started := Time.get_ticks_usec()
    var x0 := maxi(0,int(floor((at.x-radius+WIDTH*.5)/DX))-2)
    var x1 := mini(NX-1,int(ceil((at.x+radius+WIDTH*.5)/DX))+2)
    var z0 := maxi(0,int(floor((at.z-radius+DEPTH*.5)/DZ))-2)
    var z1 := mini(NZ-1,int(ceil((at.z+radius+DEPTH*.5)/DZ))+2)
    var previous := heights.duplicate() if operation=="smooth" else PackedFloat32Array()
    for z in range(z0,z1+1):
        for x in range(x0,x1+1):
            var d2 := Vector2(x*DX-WIDTH*.5-at.x,z*DZ-DEPTH*.5-at.z).length_squared()/(radius*radius)
            if d2>=1.0:continue
            var weight := (1.0-d2)*(1.0-d2)
            var i := z*NX+x
            if operation=="smooth":
                var average := 0.0
                var count := 0
                for zz in range(maxi(0,z-1),mini(NZ,z+2)):
                    for xx in range(maxi(0,x-1),mini(NX,x+2)):
                        average+=previous[zz*NX+xx]
                        count+=1
                heights[i]=lerpf(previous[i],average/count,minf(1.0,seconds*12.0*weight))
            else:
                heights[i]=clampf(heights[i]+(.11 if operation=="pour" else -.14)*seconds*weight,0,MAX_HEIGHT)
    # Finite local relaxation; no terrain solver runs after the edit finishes.
    for iteration in 3:
        for z in range(z0,z1):
            for x in range(x0,x1):
                _slide(z*NX+x,z*NX+x+1,DX*.65)
                _slide(z*NX+x,(z+1)*NX+x,DZ*.65)
    rebuild_region(x0,x1,z0,z1)
    last_brush_ms=(Time.get_ticks_usec()-started)/1000.0

func _slide(a: int,b: int,limit: float) -> void:
    var gap := heights[a]-heights[b]
    if absf(gap)<=limit:return
    var move := (absf(gap)-limit)*.28*signf(gap)
    heights[a]-=move
    heights[b]+=move

func _vertex(x: int,z: int) -> Vector3:
    return Vector3(x*DX-WIDTH*.5,heights[z*NX+x],z*DZ-DEPTH*.5)

func _normal(x: int,z: int) -> Vector3:
    var left := maxi(0,x-1)
    var right := mini(NX-1,x+1)
    var back := maxi(0,z-1)
    var front := mini(NZ-1,z+1)
    return Vector3(-(heights[z*NX+right]-heights[z*NX+left])/((right-left)*DX),1.0,-(heights[front*NX+x]-heights[back*NX+x])/((front-back)*DZ)).normalized()

func _chunk(cx: int,cz: int) -> void:
    var verts := PackedVector3Array()
    var normals := PackedVector3Array()
    var uv := PackedVector2Array()
    var indices := PackedInt32Array()
    for z in range(cz*CHUNK_Z,(cz+1)*CHUNK_Z+1):
        for x in range(cx*CHUNK_X,(cx+1)*CHUNK_X+1):
            var p := _vertex(x,z)
            verts.append(p)
            normals.append(_normal(x,z))
            uv.append(Vector2(p.x,p.z)/.48)
    for z in CHUNK_Z:
        for x in CHUNK_X:
            var i := z*(CHUNK_X+1)+x
            # Godot front faces use clockwise winding; analytic normals face up.
            indices.append_array(PackedInt32Array([i,i+1,i+CHUNK_X+1,i+1,i+CHUNK_X+2,i+CHUNK_X+1]))
    var arrays: Array=[]
    arrays.resize(Mesh.ARRAY_MAX)
    arrays[Mesh.ARRAY_VERTEX]=verts
    arrays[Mesh.ARRAY_NORMAL]=normals
    arrays[Mesh.ARRAY_TEX_UV]=uv
    arrays[Mesh.ARRAY_INDEX]=indices
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
            if edge==0:a=_vertex(k,0);b=_vertex(k+1,0);normal=Vector3.BACK*-1
            elif edge==1:a=_vertex(k+1,NZ-1);b=_vertex(k,NZ-1);normal=Vector3.BACK
            elif edge==2:a=_vertex(0,k+1);b=_vertex(0,k);normal=Vector3.LEFT
            else:a=_vertex(NX-1,k);b=_vertex(NX-1,k+1);normal=Vector3.RIGHT
            var c := Vector3(a.x,-.002,a.z)
            var d := Vector3(b.x,-.002,b.z)
            for p in [a,c,b,b,c,d]:
                st.set_normal(normal)
                st.set_uv(Vector2(p.x+p.z,p.y)/.48)
                st.add_vertex(p)
    side.mesh=st.commit()

func rebuild_region(x0: int,x1: int,z0: int,z1: int) -> void:
    var started := Time.get_ticks_usec()
    for cz in 4:
        for cx in 4:
            if cx*CHUNK_X>x1+1 or (cx+1)*CHUNK_X<x0-1 or cz*CHUNK_Z>z1+1 or (cz+1)*CHUNK_Z<z0-1:continue
            _chunk(cx,cz)
    if x0<=1 or x1>=NX-2 or z0<=1 or z1>=NZ-2:_walls()
    last_update_ms=(Time.get_ticks_usec()-started)/1000.0

func rebuild_all() -> void:
    rebuild_region(0,NX-1,0,NZ-1)
