extends SceneTree
## Render the actual skinned body in its fixed source UV canvas.
## Only raster POSITION is unwrapped; vertex input remains actual GPU skinned data.
var hall
func _initialize() -> void:call_deferred("run")
func shot() -> Image:
    await process_frame;RenderingServer.force_draw();await process_frame;RenderingServer.force_draw()
    return hall.viewport.get_texture().get_image()
func run() -> void:
    var args:=OS.get_cmdline_user_args();var out: String=args[0]
    var species: String=args[1] if args.size()>1 else "arapaima"
    var domain: String=args[2] if args.size()>2 else "chart"
    var legacy:bool=args.size()>3 and args[3]=="legacy"
    var surface:=1 if domain=="jaw" else 0
    DirAccess.make_dir_recursive_absolute(out)
    root.size=Vector2i(1024,512)
    hall=load("res://scripts/aquarium/VolumeFishExhibit.gd").new();root.add_child(hall)
    hall.set_process(false);hall.paused=true;hall.header.hide();hall.footer.hide()
    hall.screen.set_anchors_and_offsets_preset(Control.PRESET_TOP_LEFT);hall.screen.position=Vector2.ZERO;hall.screen.size=Vector2(1024,512)
    hall.viewport.size=Vector2i(1024,512);hall.viewport.render_target_update_mode=SubViewport.UPDATE_ALWAYS
    hall._select_display(species)
    var entry: Dictionary=hall._selected()
    var mesh_name:String="Closed_body"
    if domain=="chart":
        var chart:Dictionary=JSON.parse_string(FileAccess.get_file_as_string("res://assets/models/fish/motion/surface-charts112.json")).profiles[species]
        mesh_name=chart.mesh;surface=int(chart.surface)
    var body: MeshInstance3D=entry.model.find_child(mesh_name,true,false)
    assert(body!=null,"Probe target mesh missing: "+mesh_name)
    # UV rasterization bypasses normal clip positions, but culling/LOD still
    # use the posed 3D bounds. Freeze the triangle set for this coordinate test.
    var source_mesh: ArrayMesh=body.mesh
    var raw_surfaces: Array=source_mesh.get("_surfaces").duplicate(true)
    for raw in raw_surfaces:raw.erase("lods")
    var fixed_mesh:=source_mesh.duplicate(false) as ArrayMesh
    fixed_mesh.clear_surfaces();fixed_mesh.set("_surfaces",raw_surfaces)
    for si in source_mesh.get_surface_count():assert(var_to_bytes(source_mesh.surface_get_arrays(si))==var_to_bytes(fixed_mesh.surface_get_arrays(si)))
    body.mesh=fixed_mesh;body.extra_cull_margin=1000.
    for mesh in hall.world.find_children("*","MeshInstance3D",true,false):mesh.visible=mesh==body
    for label in hall.world.find_children("*","Label3D",true,false):label.hide()
    var material: ShaderMaterial=body.get_active_material(surface)
    var production: Shader=material.shader
    var arrays: Array=body.mesh.surface_get_arrays(surface)
    var positions: PackedVector3Array=arrays[Mesh.ARRAY_VERTEX]
    var normals: PackedVector3Array=arrays[Mesh.ARRAY_NORMAL]
    var uv: PackedVector2Array=arrays[Mesh.ARRAY_TEX_UV]
    var width:=256;var height:=ceili(float(positions.size())/width)
    var rest:=Image.create(width,height,false,Image.FORMAT_RGBAF)
    var nr:=Image.create(width,height,false,Image.FORMAT_RGBAF)
    var expected_uv:=Image.create(width,height,false,Image.FORMAT_RGBAF)
    for i in positions.size():
        var at:=Vector2i(i%width,i/width);var p:=positions[i];var n:=normals[i]
        rest.set_pixelv(at,Color(p.x,p.y,p.z,1.));nr.set_pixelv(at,Color(n.x,n.y,n.z,1.));expected_uv.set_pixelv(at,Color(uv[i].x,uv[i].y,0.,1.))
    var shader:=Shader.new()
    var declaration: String="""
uniform sampler2D probe114_rest:filter_nearest,repeat_disable;
uniform sampler2D probe114_normals:filter_nearest,repeat_disable;
uniform sampler2D probe114_uv:filter_nearest,repeat_disable;
uniform vec2 probe114_size;
uniform int probe114_count;
uniform int probe114_mode=0;
varying float probe114_error;
"""
    var prefix: String="""
    int safe_index=clamp(VERTEX_ID,0,probe114_count-1);
    vec2 at=(vec2(float(safe_index%int(probe114_size.x)),float(safe_index/int(probe114_size.x)))+vec2(.5))/probe114_size;
    vec4 p=textureLod(probe114_rest,at,0.);vec4 n=textureLod(probe114_normals,at,0.);vec4 reference_uv=textureLod(probe114_uv,at,0.);
    probe114_error=(VERTEX_ID>=probe114_count||p.w<.5||n.w<.5||reference_uv.w<.5||any(greaterThan(abs(UV-reference_uv.xy),vec2(.000001))))?1.:0.;
"""
    var code: String=production.code.replace("render_mode","render_mode unshaded,depth_test_disabled,depth_draw_never,")
    if legacy:
        var stable:String={"chart":"chart112_rest_position=rest114_position;chart112_rest_normal=rest114_normal;","front":"front112_rest=rest114_position;front112_normal=rest114_normal;","directional":"skin152_p=rest114_position;skin152_n=rest114_normal;"}.get(domain,"")
        var posed:String={"chart":"chart112_rest_position=VERTEX;chart112_rest_normal=NORMAL;","front":"front112_rest=VERTEX;front112_normal=NORMAL;","directional":"skin152_p=VERTEX;skin152_n=NORMAL;"}.get(domain,"")
        assert(not stable.is_empty() and code.count(stable)==1)
        code=code.replace(stable,posed)
    code=code.replace("void vertex()",declaration+"\nvoid vertex()")
    var parser=load("res://scripts/aquarium/FishEyeOwnership.gd").new()
    var vertex: Dictionary=parser._stage_braces(code,"vertex")
    var override: String={"chart":"chart112_rest_position=p.xyz;chart112_rest_normal=n.xyz;","front":"front112_rest=p.xyz;front112_normal=n.xyz;","jaw":"jaw112_rest=p.xyz;","directional":"skin152_p=p.xyz;skin152_n=n.xyz;"}[domain]
    var suffix: String="\nif(probe114_mode==1){"+override+"}\nPOSITION=vec4(UV.x*2.-1.,1.-UV.y*2.,0.,1.);\n"
    code=code.insert(vertex.close,suffix);code=code.insert(vertex.open,prefix)
    var fragment: Dictionary=parser._stage_braces(code,"fragment")
    var body_code: String=code.substr(fragment.open,fragment.close-fragment.open) if domain=="jaw" else "ALBEDO="+domain+"112_color(vec3(.15));"
    if domain=="directional":body_code="ALBEDO=skin152_color(vec3(.15),UV);"
    code=code.substr(0,fragment.open)+body_code+"\nif(probe114_error>.5){ALBEDO=vec3(1.,0.,1.);}\n"+code.substr(fragment.close)
    shader.code=code;assert(not shader.get_shader_uniform_list().is_empty())
    var diagnostic:=ShaderMaterial.new();diagnostic.shader=shader
    for uniform in production.get_shader_uniform_list():
        var name: String=uniform.name
        diagnostic.set_shader_parameter(name,material.get_shader_parameter(name))
    diagnostic.set_shader_parameter("probe114_rest",ImageTexture.create_from_image(rest));diagnostic.set_shader_parameter("probe114_normals",ImageTexture.create_from_image(nr));diagnostic.set_shader_parameter("probe114_uv",ImageTexture.create_from_image(expected_uv))
    diagnostic.set_shader_parameter("probe114_size",Vector2(width,height));diagnostic.set_shader_parameter("probe114_count",positions.size())
    body.set_surface_override_material(surface,diagnostic)
    # The UV canvas contains only the target surface, not a posed oral surface
    # still rendered by the regular 3D camera.
    var hidden:=ShaderMaterial.new();var hidden_shader:=Shader.new()
    hidden_shader.code="shader_type spatial;void fragment(){discard;}";hidden.shader=hidden_shader
    for si in body.mesh.get_surface_count():
        if si!=surface:body.set_surface_override_material(si,hidden)
    # A deterministic nonuniform donor rules out flat colors hiding UV motion.
    var donor:=Image.create(512,256,false,Image.FORMAT_RGBA8)
    for y in 256:
        for x in 512:donor.set_pixel(x,y,Color(.15+.55*float((x/3)%2),.2+.5*float((y/3)%2),.3+.3*float(((x/3)+(y/3))%2)))
    for parameter in {"chart":["chart112_dorsal","chart112_ventral"],"front":["front112_source"],"jaw":["source_texture"],"directional":["skin152_top","skin152_bottom"]}[domain]:diagnostic.set_shader_parameter(parameter,ImageTexture.create_from_image(donor))
    #153 adds a real flat surface-distance field; test it with the same nonuniform
    #diagnostic donor while retaining its numeric arc LUT (not colour artwork).
    if domain=="directional" and production.code.contains("uniform sampler2D skin153_flat"):
        diagnostic.set_shader_parameter("skin153_flat",ImageTexture.create_from_image(donor))
    var records: Array=[]
    var references: Dictionary={}
    var failures: Array=[]
    for mode in [0,1]:
        diagnostic.set_shader_parameter("probe114_mode",mode)
        var reference: Image
        for action in ["Swim","Turn","Ascend","Dive"]:
            entry.controller.set_action(action,true);entry.controller.step(0.)
            for phase in [0.,.21,.48]:
                entry.controller.seek(float(entry.profile.period_seconds)*phase)
                var image: Image=await shot()
                var path: String=out+"/"+species+"-"+str(mode)+"-"+action+"-"+str(phase)+".png";image.save_png(path)
                var bytes: PackedByteArray=image.get_data()
                var magenta:=0
                var donor_coverage:=0
                var background:=image.get_pixel(0,0)
                for at in range(0,bytes.size(),4):
                    if bytes[at]>245 and bytes[at+1]<10 and bytes[at+2]>245:magenta+=1
                    var color:=Color8(bytes[at],bytes[at+1],bytes[at+2],bytes[at+3])
                    if color!=background and maxi(bytes[at],maxi(bytes[at+1],bytes[at+2]))-mini(bytes[at],mini(bytes[at+1],bytes[at+2]))>20:donor_coverage+=1
                if reference==null:reference=image
                var ref: PackedByteArray=reference.get_data();var changed:=0
                for at in range(0,bytes.size(),4):
                    if bytes[at]!=ref[at] or bytes[at+1]!=ref[at+1] or bytes[at+2]!=ref[at+2]:changed+=1
                records.append({"mode":"production_coordinates" if mode==0 else "independent_rest_oracle","action":action,"phase":phase,"changed_canvas_pixels":changed,"lookup_fault_pixels":magenta,"donor_coverage_pixels":donor_coverage,"image":path})
                if donor_coverage<1000:failures.append({"kind":"validation","code":"insufficient_probe_coverage","message":str(donor_coverage)+" < 1000; result inconclusive"})
                if magenta>0:failures.append({"kind":"validation","code":"vertex_lookup_fault","message":str(magenta)})
                if changed>0 and mode==1:failures.append({"kind":"validation","code":"oracle_drift","message":action+" "+str(phase)})
    body.set_surface_override_material(surface,material)
    var drift:=false
    for r in records:drift=drift or (r.mode=="production_coordinates" and r.changed_canvas_pixels>0)
    var report: Dictionary={"schema_version":1,"ok":not drift and failures.is_empty(),"command":"fish.review114.material-anchor-negative","status":"failed" if drift or not failures.is_empty() else "done","next_action":"fix_input" if drift or not failures.is_empty() else "human_review","species":species,"current_chart_drifts":drift,"records":records,"failures":failures,"model_sha256":FileAccess.get_sha256(entry.model.scene_file_path),"template_sha256":FileAccess.get_sha256("res://scripts/aquarium/BodyChart112.gdshaderinc"),"limits":"Fixed full-detail triangle set in same UV canvas, widened cull bounds. Actual imported vertex/rig/UV data preserved. Nonuniform temporary donor, not production art or LOD acceptance."}
    report["domain"]=domain
    report["legacy_coordinate_counterfactual"]=legacy
    report["body_helper_sha256"]=FileAccess.get_sha256("res://scripts/aquarium/BodyChart112.gd")
    report["production_shader_sha256"]=production.code.sha256_text()
    report["probe_sha256"]=FileAccess.get_sha256(OS.get_cmdline_args()[OS.get_cmdline_args().find("--script")+1])
    var f:=FileAccess.open(out+"/anchor.validation.json",FileAccess.WRITE);f.store_string(JSON.stringify(report,"  ")+"\n")
    print("ANCHOR114 "+JSON.stringify({"drift":drift,"failures":failures.size()}));quit(1 if not report.ok else 0)
