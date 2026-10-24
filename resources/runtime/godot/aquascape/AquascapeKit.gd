extends RefCounted
## Reusable deterministic geometry. Units are meters. Source PNGs remain native size.
var rng := RandomNumberGenerator.new()
var materials: Array[ShaderMaterial] = []
var triangle_count := 0
var failures: Array[String] = []
var source_dir := "res://assets/aquascape/"
const CODE = """
shader_type spatial;
render_mode diffuse_lambert, cull_back;
uniform sampler2D source_tex : source_color, filter_nearest, repeat_disable;
uniform int mapping = 0;
uniform int review_mode = 0;
uniform vec3 tint : source_color = vec3(1.0);
uniform vec2 pixel_grid = vec2(0.0);
varying vec3 local_pos;
varying vec3 local_normal;
vec2 mirror_uv(vec2 p) {return 1.0-abs(mod(p,2.0)-1.0);}
void vertex(){local_pos=VERTEX; local_normal=NORMAL;}
void fragment(){
 vec2 uv=UV;
 if(pixel_grid.x>0.0)uv=(floor(UV*pixel_grid)+0.5)/pixel_grid;
 vec3 col=texture(source_tex,clamp(uv,vec2(0.002),vec2(0.998))).rgb;
 if(mapping==1){
   vec3 w=pow(abs(normalize(local_normal)),vec3(6.0));w/=max(w.x+w.y+w.z,0.001);
   vec3 p=local_pos*3.0;
   col=texture(source_tex,mirror_uv(p.yz)).rgb*w.x+texture(source_tex,mirror_uv(p.xz)).rgb*w.y+texture(source_tex,mirror_uv(p.xy)).rgb*w.z;
 }
 if(mapping==2){col=texture(source_tex,vec2(mirror_uv(UV).x,clamp(UV.y,0.002,0.998))).rgb;}
 if(mapping==3){
   vec2 q=(floor(UV*100.0)+0.5)/100.0-0.5;
   float r=length(q*vec2(1.0,1.15));
   float rings=step(.70,fract(r*24.0+sin(atan(q.y,q.x)*4.0)*.16));
   col=mix(vec3(.28,.20,.12),vec3(.16,.11,.065),rings);
 }
 ALBEDO=col*tint;
 if(review_mode==1) ALBEDO=vec3(0.57,0.61,0.60);
 if(review_mode==2){
   vec2 p=UV*12.0;
   if(mapping==1){vec3 n=abs(local_normal);p=(n.x>n.y&&n.x>n.z?local_pos.yz:(n.y>n.z?local_pos.xz:local_pos.xy))*40.0;}
   float q=mod(floor(p.x)+floor(p.y),2.0);
   ALBEDO=mix(vec3(0.05,0.22,0.30),vec3(0.95,0.65,0.25),q);
 }
 ROUGHNESS=1.0;SPECULAR=0.0;
}
"""

func material(tex: String, mapping: int = 0, tint := Color.WHITE) -> ShaderMaterial:
    var m := ShaderMaterial.new()
    var shader := Shader.new()
    shader.code = CODE
    m.shader = shader
    m.set_shader_parameter("source_tex",load(source_dir+tex+".png"))
    m.set_shader_parameter("mapping",mapping)
    m.set_shader_parameter("tint",Vector3(tint.r,tint.g,tint.b))
    materials.append(m)
    return m

func set_mode(mode: int) -> void:
    for m in materials: m.set_shader_parameter("review_mode",mode)

func triangle(s: SurfaceTool,a: Vector3,b: Vector3,c: Vector3,ua: Vector2,ub: Vector2,uc: Vector2) -> void:
    var cross := (b-a).cross(c-a)
    if cross.length_squared()<1e-17:
        failures.append("degenerate triangle")
        return
    var n := cross.normalized()
    # Godot uses clockwise faces. Store outward normals explicitly.
    for pair in [[a,ua],[c,uc],[b,ub]]:
        s.set_normal(n)
        s.set_uv(pair[1])
        s.add_vertex(pair[0])
    triangle_count+=1

func quad(s: SurfaceTool,a: Vector3,b: Vector3,c: Vector3,d: Vector3,ua: Vector2,ub: Vector2,uc: Vector2,ud: Vector2) -> void:
    triangle(s,a,b,c,ua,ub,uc)
    triangle(s,a,c,d,ua,uc,ud)

func finish(s: SurfaceTool, mat: Material, title: String) -> MeshInstance3D:
    var n := MeshInstance3D.new()
    n.name=title
    n.mesh=s.commit()
    n.mesh.surface_set_material(0,mat)
    return n

func rock(seed_value: int, size: Vector3) -> Node3D:
    rng.seed=seed_value
    var s := SurfaceTool.new()
    s.begin(Mesh.PRIMITIVE_TRIANGLES)
    var rings: Array = []
    var count := 15
    var sizes := [0.64,0.99,1.0,0.79,0.47]
    var levels := [0.0,0.12,0.47,0.78,0.98]
    var irregular: Array[float]=[]
    for j in count: irregular.append(rng.randf_range(.82,1.12))
    for i in sizes.size():
        var row: Array[Vector3]=[]
        for j in count:
            var a := TAU*j/count
            var r: float=sizes[i]*irregular[j]
            row.append(Vector3(cos(a)*r*.5*size.x+size.x*.10*levels[i], levels[i]*size.y+sin(a*3.0+i)*size.y*.035,sin(a)*r*.5*size.z))
        rings.append(row)
    for i in rings.size()-1:
        for j in count:
            var k: int=(j+1)%count
            quad(s,rings[i][j],rings[i+1][j],rings[i+1][k],rings[i][k],Vector2(float(j)/count,float(i)/4),Vector2(float(j)/count,float(i+1)/4),Vector2(float(j+1)/count,float(i+1)/4),Vector2(float(j+1)/count,float(i)/4))
    var top := Vector3(size.x*.1,size.y*1.01,0)
    var bottom := Vector3(0,-size.y*.035,0)
    for j in count:
        var k: int=(j+1)%count
        triangle(s,top,rings[-1][k],rings[-1][j],Vector2(.5,.5),Vector2(0,0),Vector2(1,1))
        triangle(s,bottom,rings[0][j],rings[0][k],Vector2(.5,.5),Vector2(0,0),Vector2(1,1))
    return finish(s,material("rock",1),"RiverRock")

func tube(points: Array[Vector3], radii: Array[float], mat: Material, title: String, sides: int = 12, ridges: float = 0.1) -> MeshInstance3D:
    var s := SurfaceTool.new()
    s.begin(Mesh.PRIMITIVE_TRIANGLES)
    var rings: Array=[]
    var distance: Array[float]=[0.0]
    for i in points.size():
        if i>0:distance.append(distance[-1]+points[i].distance_to(points[i-1]))
        var tangent: Vector3=(points[mini(i+1,points.size()-1)]-points[maxi(0,i-1)]).normalized()
        var axis := Vector3.FORWARD if absf(tangent.dot(Vector3.FORWARD))<.9 else Vector3.RIGHT
        var x := tangent.cross(axis).normalized()
        var z := x.cross(tangent).normalized()
        var row: Array[Vector3]=[]
        for j in sides:
            var a := TAU*j/sides
            var r: float=radii[i]*(1.0+ridges*sin(j*2.7+i*.4))
            row.append(points[i]+(x*cos(a)+z*sin(a))*r)
        rings.append(row)
    for i in points.size()-1:
        for j in sides:
            var k: int=(j+1)%sides
            var u0 := float(j)/sides
            var u1 := float(j+1)/sides
            var v0 := distance[i]/distance[-1]
            var v1 := distance[i+1]/distance[-1]
            quad(s,rings[i][j],rings[i+1][j],rings[i+1][k],rings[i][k],Vector2(u0,v0),Vector2(u0,v1),Vector2(u1,v1),Vector2(u1,v0))
    var cap := SurfaceTool.new()
    cap.begin(Mesh.PRIMITIVE_TRIANGLES)
    var is_wood: bool=mat is ShaderMaterial and mat.get_shader_parameter("mapping")==2
    var cap_target: SurfaceTool=cap if is_wood else s
    for j in sides:
        var k: int=(j+1)%sides
        var uj := Vector2(.5,.5)+Vector2(cos(TAU*j/sides),sin(TAU*j/sides))*.49
        var uk := Vector2(.5,.5)+Vector2(cos(TAU*k/sides),sin(TAU*k/sides))*.49
        triangle(cap_target,points[0],rings[0][j],rings[0][k],Vector2(.5,.5),uj,uk)
        triangle(cap_target,points[-1],rings[-1][k],rings[-1][j],Vector2(.5,.5),uk,uj)
    var node := finish(s,mat,title)
    if is_wood:
        cap.commit(node.mesh)
        node.mesh.surface_set_material(1,material("wood",3))
    return node

func wood() -> Node3D:
    var root := Node3D.new()
    root.name="ForkedDriftwood"
    var m := material("wood",2,Color("8a8274"))
    root.add_child(tube([Vector3(-.32,.07,.04),Vector3(-.19,.09,.01),Vector3(-.03,.13,0),Vector3(.13,.16,-.025),Vector3(.29,.20,-.06),Vector3(.43,.27,-.09)],[.071,.067,.056,.040,.022,.003],m,"Trunk",18,.17))
    root.add_child(tube([Vector3(-.075,.112,.005),Vector3(.015,.20,.015),Vector3(.085,.28,.02),Vector3(.20,.40,.035)],[.043,.032,.018,.0025],m,"RisingFork",16,.17))
    root.add_child(tube([Vector3(-.19,.082,.015),Vector3(-.13,.06,.09),Vector3(.02,.038,.15),Vector3(.23,.018,.18)],[.04,.032,.018,.0025],m,"RootFork",14,.17))
    root.add_child(tube([Vector3(-.24,.07,.04),Vector3(-.31,.035,.12),Vector3(-.37,.015,.19)],[.035,.022,.003],m,"RearRoot",12,.15))
    return root

func leaf(length_m: float, width_ratio: float, bend: float, fern: bool, mat: Material) -> MeshInstance3D:
    var s := SurfaceTool.new()
    s.begin(Mesh.PRIMITIVE_TRIANGLES)
    var rows := 16
    var columns := 6
    var top: Array=[]
    var back: Array=[]
    var thick := .00065 if fern else .0008
    for i in rows+1:
        var t := float(i)/rows
        # Broad oval Anubias, long tapering entire lanceolate fern. No serrated leaflets.
        var outline := pow(maxf(.008,sin(PI*t)), .68 if fern else .73)
        if not fern: outline*=1.0+.18*sin(PI*t)
        var width := length_m*width_ratio*.5*outline
        var rr: Array[Vector3]=[]
        var bb: Array[Vector3]=[]
        for j in columns+1:
            var x := float(j)/columns*2.0-1.0
            var ripple := sin(t*PI*5.0)*pow(absf(x),3)*length_m*(.012 if fern else .004)
            var z := bend*t*t*length_m + (1.0-x*x)*length_m*.035*sin(PI*t)+ripple
            var p := Vector3(x*width,length_m*t,z)
            rr.append(p+Vector3(0,0,thick*.5))
            bb.append(p-Vector3(0,0,thick*.5))
        top.append(rr)
        back.append(bb)
    for i in rows:
        for j in columns:
            var a := Vector2(float(j)/columns,1.0-float(i)/rows)
            var b := Vector2(float(j+1)/columns,a.y)
            var c := Vector2(b.x,1.0-float(i+1)/rows)
            var d := Vector2(a.x,c.y)
            quad(s,top[i][j],top[i][j+1],top[i+1][j+1],top[i+1][j],a,b,c,d)
            quad(s,back[i][j+1],back[i][j],back[i+1][j],back[i+1][j+1],b,a,d,c)
        for j in [0,columns]:
            if j==0:
                quad(s,top[i][j],top[i+1][j],back[i+1][j],back[i][j],Vector2(0,0),Vector2(0,1),Vector2(0,1),Vector2(0,0))
            else:
                quad(s,top[i+1][j],top[i][j],back[i][j],back[i+1][j],Vector2(1,1),Vector2(1,0),Vector2(1,0),Vector2(1,1))
    for j in columns:
        quad(s,top[0][j+1],top[0][j],back[0][j],back[0][j+1],Vector2(.5,1),Vector2(.5,1),Vector2(.5,1),Vector2(.5,1))
        quad(s,top[-1][j],top[-1][j+1],back[-1][j+1],back[-1][j],Vector2(.5,0),Vector2(.5,0),Vector2(.5,0),Vector2(.5,0))
    var leaf_mat: ShaderMaterial=mat.duplicate()
    leaf_mat.set_shader_parameter("pixel_grid",Vector2(32,128) if fern else Vector2(40,64))
    materials.append(leaf_mat)
    return finish(s,leaf_mat,"FernLeaf" if fern else "AnubiasLeaf")

func plant(fern: bool, seed_value: int) -> Node3D:
    rng.seed=seed_value
    var root := Node3D.new()
    root.name="Microsorum_pteropus" if fern else "Anubias_barteri_var_nana"
    root.set_meta("scientific_name","Microsorum pteropus" if fern else "Anubias barteri var. nana")
    var m := material("fern" if fern else "anubias",0,Color("b1bd91") if fern else Color("c3c9ad"))
    var stem := material("anubias",0,Color("8e9474"))
    root.add_child(tube([Vector3(-.045,0,0),Vector3(0,.004,0),Vector3(.05,.003,.01)],[.006,.006,.0045],stem,"ExposedRhizome",10,0.07))
    var count := 12 if fern else 10
    for i in count:
        var base := Vector3(lerpf(-.04,.045,float(i)/count),.003,0)
        var pivot := Node3D.new()
        pivot.position=base
        pivot.rotation=Vector3(rng.randf_range(.24,.80) if fern else rng.randf_range(.65,1.24),float(i)*2.399,.0)
        root.add_child(pivot)
        var petiole := rng.randf_range(.015,.035) if fern else rng.randf_range(.025,.060)
        var length_m := rng.randf_range(.16,.28) if fern else rng.randf_range(.045,.072)
        pivot.add_child(tube([Vector3.ZERO,Vector3(0,petiole,0)],[.0013,.0009],stem,"Petiole",6,0.0))
        var blade := leaf(length_m,.18 if fern else .56,rng.randf_range(.08,.32),fern,m)
        blade.position.y=petiole
        pivot.add_child(blade)
        var rbase := base+Vector3(0,-.002,0)
        root.add_child(tube([rbase,rbase+Vector3(.003,-.010,.006),rbase+Vector3(.008,-.018,.009)],[.0009,.0007,.00025],stem,"AttachmentRoot",5,0))
    return root

func own_recursive(n: Node, root: Node) -> void:
    for child in n.get_children():
        child.owner=root
        own_recursive(child,root)

func save_asset(n: Node3D, path: String) -> int:
    own_recursive(n,n)
    var packed := PackedScene.new()
    var error := packed.pack(n)
    if error != OK:return error
    return ResourceSaver.save(packed,path)
