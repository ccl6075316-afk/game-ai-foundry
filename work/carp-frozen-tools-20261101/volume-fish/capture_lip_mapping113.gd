extends SceneTree
## Temporary material annotation, preserving current production geometry/texels.
var hall
var out: String
func _initialize() -> void:call_deferred("run")
func shot(path: String) -> void:
    await process_frame;RenderingServer.force_draw()
    await process_frame;RenderingServer.force_draw()
    assert(hall.viewport.get_texture().get_image().save_png(path)==OK)
func region(entry: Dictionary) -> AABB:
    var mesh: MeshInstance3D=entry.model.find_child("Closed_body",true,false)
    var bounds:=mesh.get_aabb()
    var head:=AABB();var first:=true
    for surface in mesh.mesh.get_surface_count():
        for v in mesh.mesh.surface_get_arrays(surface)[Mesh.ARRAY_VERTEX]:
            if v.x<bounds.position.x+bounds.size.x*.80:continue
            if first:head=AABB(v,Vector3.ZERO);first=false
            else:head=head.expand(v)
    return head
func camera(entry: Dictionary,head: AABB,yaw: float,pitch: float) -> void:
    var basis: Basis=entry.carrier.global_transform.basis.orthonormalized()
    var center: Vector3=entry.model.global_transform*head.get_center()
    var size: Vector3=head.size*entry.model.global_transform.basis.get_scale()
    var distance: float=maxf(maxf(size.x,maxf(size.y,size.z))*1.9,entry.length_m*.20)
    hall.camera.near=.0005
    hall.camera.global_position=center+basis*Vector3(sin(yaw)*cos(pitch),sin(pitch),cos(yaw)*cos(pitch))*distance
    hall.camera.look_at(center,basis*Vector3.UP)
func run() -> void:
    var args:=OS.get_cmdline_user_args();out=args[0]
    var plan: Dictionary=JSON.parse_string(FileAccess.get_file_as_string(args[1]))
    DirAccess.make_dir_recursive_absolute(out)
    root.size=Vector2i(1400,900)
    hall=load("res://scripts/aquarium/VolumeFishExhibit.gd").new();root.add_child(hall)
    hall.set_process(false);hall.paused=true;hall.header.hide();hall.footer.hide()
    hall.screen.set_anchors_and_offsets_preset(Control.PRESET_TOP_LEFT);hall.screen.position=Vector2.ZERO;hall.screen.size=Vector2(1400,900)
    hall.viewport.size=Vector2i(1400,900);hall.viewport.render_target_update_mode=SubViewport.UPDATE_ALWAYS
    var results: Array=[]
    for p in plan.items:
        hall._select_display(p.species)
        for tank in hall.tanks:tank.root.visible=tank.species==p.species
        var entry: Dictionary=hall._selected()
        entry.controller.set_motion_controls({"body_amplitude":0.,"fin_amplitude":0.},true)
        entry.controller.step(0.);entry.controller.seek(0.)
        var body: MeshInstance3D=entry.model.find_child("Closed_body",true,false)
        var material: ShaderMaterial=body.get_active_material(0)
        var original: Shader=material.shader
        var code: String=original.code
        var include: String="""
uniform vec2 lip113_material_line[32];
uniform int lip113_material_count;
uniform vec3 lip113_geometry_line[64];
uniform int lip113_geometry_count;
uniform vec2 lip113_source_size;
uniform bool lip113_marks=false;
varying vec3 lip113_rest;
float lip113_segment(vec2 p,vec2 a,vec2 b){vec2 d=b-a;return length(p-a-d*clamp(dot(p-a,d)/max(dot(d,d),1e-12),0.,1.));}
float lip113_segment3(vec3 p,vec3 a,vec3 b){vec3 d=b-a;return length(p-a-d*clamp(dot(p-a,d)/max(dot(d,d),1e-12),0.,1.));}
vec3 lip113_annotate(vec3 c,vec2 uv){
    if(!lip113_marks)return c;
    vec2 pixel=uv*lip113_source_size;float material_distance=1e8;
    for(int i=1;i<lip113_material_count;i++)material_distance=min(material_distance,lip113_segment(pixel,lip113_material_line[i-1],lip113_material_line[i]));
    float geometry_distance=1e8;
    for(int i=1;i<lip113_geometry_count;i++)geometry_distance=min(geometry_distance,lip113_segment3(lip113_rest,lip113_geometry_line[i-1],lip113_geometry_line[i])*lip113_source_size.x);
    if(material_distance<1.4)c=vec3(.05,1.,.2);
    if(geometry_distance<1.1)c=vec3(.05,.5,1.);
    return c;
}
"""
        code=code.replace("void vertex()",include+"\nvoid vertex()")
        var vertex_open:=code.find("{",code.find("void vertex()"));code=code.insert(vertex_open+1,"lip113_rest=VERTEX;")
        var assignment:=code.find("ALBEDO=")
        var assignment_end:=code.find(";",assignment)
        assert(assignment>=0 and assignment_end>assignment)
        code=code.insert(assignment_end+1,"ALBEDO=lip113_annotate(ALBEDO,UV);")
        var annotated:=Shader.new();annotated.code=code
        assert(not annotated.get_shader_uniform_list().is_empty(),"Diagnostic shader failed")
        material.shader=annotated
        var points:=PackedVector2Array()
        for v in p.material_lower_line_source_px:points.append(Vector2(v[0],v[1]))
        material.set_shader_parameter("lip113_material_count",points.size());points.resize(32);material.set_shader_parameter("lip113_material_line",points)
        var geometry:=PackedVector3Array()
        for v in p.current_geometry_lower_rim:geometry.append(Vector3(v[0],v[1],v[2]))
        material.set_shader_parameter("lip113_geometry_count",geometry.size());geometry.resize(64);material.set_shader_parameter("lip113_geometry_line",geometry)
        material.set_shader_parameter("lip113_source_size",Vector2(p.source_size[0],p.source_size[1]))
        var head:=region(entry)
        var folder: String=out+"/"+str(p.species);DirAccess.make_dir_recursive_absolute(folder)
        for view in [["side",0.,0.],["oblique",.55,.12],["front",PI/2.,0.]]:
            camera(entry,head,view[1],view[2])
            material.set_shader_parameter("lip113_marks",false);await shot(folder+"/"+view[0]+"-current.png")
            material.set_shader_parameter("lip113_marks",true);await shot(folder+"/"+view[0]+"-marked.png")
        material.shader=original
        if "--surface-diagnosis" in args:
            var lining: Material=body.get_active_material(1)
            var highlight:=StandardMaterial3D.new();highlight.shading_mode=BaseMaterial3D.SHADING_MODE_UNSHADED
            highlight.cull_mode=BaseMaterial3D.CULL_DISABLED;highlight.albedo_color=Color(1.,0.,1.)
            for view in [["front",PI/2.,0.],["oblique",.55,.12]]:
                camera(entry,head,view[1],view[2])
                body.set_surface_override_material(1,highlight)
                await shot(folder+"/"+view[0]+"-lining-highlight.png")
                body.set_surface_override_material(1,lining)
                body.set_surface_override_material(0,highlight)
                await shot(folder+"/"+view[0]+"-skin-highlight.png")
                body.set_surface_override_material(0,material)
        results.append({"species":p.species,"model_sha256":FileAccess.get_sha256("res://assets/models/fish/"+p.species+".glb"),"green":"operator-identified visible material lower-line candidate, source texels retained","blue":"actual existing skin/oral lower boundary projected from current mesh","limits":"Material-line identity and rear jawbone fold require review before cutting; annotations are diagnostic and production model unchanged."})
    var f:=FileAccess.open(out+"/annotation.validation.json",FileAccess.WRITE)
    f.store_string(JSON.stringify({"schema_version":1,"ok":true,"command":"fish.review113.lip-annotation","status":"done","next_action":"human_review","items":results,"plan_sha256":FileAccess.get_sha256(args[1])},"  ")+"\n")
    quit()
