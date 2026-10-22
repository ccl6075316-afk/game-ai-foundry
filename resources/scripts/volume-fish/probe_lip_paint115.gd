extends "./capture_source_fit115.gd"
func run():
    DirAccess.make_dir_recursive_absolute(out)
    var plan:Dictionary=JSON.parse_string(FileAccess.get_file_as_string(OS.get_cmdline_user_args()[2]))
    var frozen:Dictionary=JSON.parse_string(FileAccess.get_file_as_string(OS.get_cmdline_user_args()[3]))
    root.size=Vector2i(1000,700);hall=load("res://scripts/aquarium/VolumeFishExhibit.gd").new();root.add_child(hall);hall.set_process(false);hall.paused=true;hall.header.hide();hall.footer.hide()
    hall.screen.set_anchors_and_offsets_preset(Control.PRESET_TOP_LEFT);hall.screen.position=Vector2.ZERO;hall.screen.size=Vector2(1000,700);hall.viewport.size=Vector2i(1000,700);hall.viewport.render_target_update_mode=SubViewport.UPDATE_ALWAYS
    ownership=JSON.parse_string(FileAccess.get_file_as_string("res://assets/models/fish/motion/surface-ownership.json")).profiles
    for mesh in hall.world.find_children("*","MeshInstance3D",true,false):intrinsic[mesh.get_instance_id()]=mesh.visible
    for label in hall.world.find_children("*","Label3D",true,false):label.hide()
    var failures:Array=[];var parser=load("res://scripts/aquarium/FishEyeOwnership.gd").new()
    for p in plan.items:
        var species:String=p.species;hall._select_display(species);var entry:Dictionary=hall._selected();var body=entry.model.find_child("Closed_body",true,false) as MeshInstance3D
        for mesh in hall.world.find_children("*","MeshInstance3D",true,false):mesh.visible=mesh==body
        var production=body.get_active_material(0) as ShaderMaterial;var diagnostic=production.duplicate() as ShaderMaterial
        var code:String=production.shader.code.replace("render_mode","render_mode unshaded,")
        var declaration="""
uniform vec2 probe115_lower[32];uniform int probe115_count;uniform float probe115_pixel;
uniform vec3 probe115_bounds[32];uniform int probe115_bounds_count;uniform int probe115_outside=0;
"""
        code=code.replace("void vertex()",declaration+"\nvoid vertex()")
        var fragment:Dictionary=parser._stage_braces(code,"fragment")
        var color:String="chart112_color(vec3(0.,1.,0.))"
        if code.contains("vec3 lip115_color("):color="lip115_color(vec3(0.,1.,0.),"+color+")"
        var tail="""
    vec3 q=rest114_position;
    if(q.x<probe115_lower[0].x||q.x>probe115_lower[probe115_count-1].x){discard;}
    float y=probe115_lower[probe115_count-1].y;
    for(int i=1;i<probe115_count;i++){if(q.x<=probe115_lower[i].x){vec2 a=probe115_lower[i-1];vec2 b=probe115_lower[i];y=mix(a.y,b.y,clamp((q.x-a.x)/(b.x-a.x),0.,1.));break;}}
    if(abs(q.y-y)>1.5*probe115_pixel){discard;}
"""
        var outside="""
    float upper=probe115_bounds[probe115_bounds_count-1].y;float lower=probe115_bounds[probe115_bounds_count-1].z;
    for(int i=1;i<probe115_bounds_count;i++){if(q.x<=probe115_bounds[i].x){vec3 a=probe115_bounds[i-1];vec3 b=probe115_bounds[i];vec2 yy=mix(a.yz,b.yz,clamp((q.x-a.x)/(b.x-a.x),0.,1.));upper=yy.x;lower=yy.y;break;}}
    bool safe=(probe115_outside==1&&q.x<=probe115_bounds[0].x)||(probe115_outside==2&&q.x>=probe115_bounds[0].x&&q.y>=upper+5.01*probe115_pixel)||(probe115_outside==3&&q.x>=probe115_bounds[0].x&&q.y<=lower-5.01*probe115_pixel);
    if(!safe){discard;}
"""
        var selected="vec3(0.,1.,0.)" if not code.contains("vec3 lip115_color(") else color
        var tail_code="\nif(rest114_error>.001){ALBEDO=vec3(1.,0.,1.);}else{vec3 q=rest114_position;\nif(probe115_outside==0){"+tail.replace("    vec3 q=rest114_position;","")+"\nALBEDO="+color+";}else{"+outside+"\nALBEDO=distance("+selected+",chart112_color(vec3(0.,1.,0.)))<.000001?vec3(0.,1.,0.):vec3(1.,0.,0.); }}\n"
        code=code.insert(fragment.close,tail_code)
        var shader=Shader.new();shader.code=code;diagnostic.shader=shader
        var width:float=p.source_size[0];var height:float=p.source_size[1];var points=PackedVector2Array()
        for point in p.material_lower_line_source_px:points.append(Vector2(point[0]/width-.5,(height*.5-point[1])/width))
        var bounds=PackedVector3Array()
        for item in frozen.items:
            if item.species==species:
                for row in item.lip_pixels:bounds.append(Vector3(row[0]/width-.5,(height*.5-row[1])/width,(height*.5-row[2])/width))
        diagnostic.set_shader_parameter("probe115_bounds_count",bounds.size());bounds.resize(32);diagnostic.set_shader_parameter("probe115_bounds",bounds)
        diagnostic.set_shader_parameter("probe115_count",points.size());points.resize(32);diagnostic.set_shader_parameter("probe115_lower",points);diagnostic.set_shader_parameter("probe115_pixel",1./width)
        var red=Image.create(1,1,false,Image.FORMAT_RGBA8);red.fill(Color.RED)
        for kind in ["dorsal","ventral"]:diagnostic.set_shader_parameter("chart112_"+kind,ImageTexture.create_from_image(red))
        var hidden=ShaderMaterial.new();var hs=Shader.new();hs.code="shader_type spatial;void fragment(){discard;}";hidden.shader=hs
        body.set_surface_override_material(0,diagnostic);body.set_surface_override_material(1,hidden)
        var r=region(entry);var folder=out+"/"+species;DirAccess.make_dir_recursive_absolute(folder)
        for action in ["Swim","Turn","Ascend","Dive"]:
            entry.controller.set_action(action,true);entry.controller.step(0.)
            for phase in [0.,.33]:
                entry.controller.seek(float(entry.profile.period_seconds)*phase);camera(entry,r,true,0.,0.)
                var file=folder+"/"+action+"-"+str(phase)+".png";await shot(file)
                var data=hall.viewport.get_texture().get_image().get_data();var coverage=0;var painted=0;var faults=0
                for i in range(0,data.size(),4):
                    if data[i]>240 and data[i+2]>240 and data[i+1]<10:faults+=1
                    if data[i+2]<4 and (data[i]>10 or data[i+1]>10):
                        coverage+=1
                        if data[i]>2:painted+=1
                var row={"species":species,"action":action,"phase":phase,"visible_lip_pixels":coverage,"chart_replaced_lip_pixels":painted,"rest_lut_fault_pixels":faults,"image":file};records.append(row)
                if coverage<30 or painted>0 or faults>0:failures.append(row)
        for zone in [1,2,3]:
            diagnostic.set_shader_parameter("probe115_outside",zone)
            camera(entry,r,true,0.,0.);var file=folder+"/outside-"+str(zone)+".png";await shot(file)
            var data=hall.viewport.get_texture().get_image().get_data();var coverage=0;var changed=0;var faults=0
            for i in range(0,data.size(),4):
                if data[i]>240 and data[i+2]>240 and data[i+1]<10:faults+=1
                if data[i+2]<4 and (data[i]>10 or data[i+1]>10):
                    coverage+=1
                    if data[i]>2:changed+=1
            var row={"species":species,"scope":"outside_protection","zone":["posterior","above","below"][zone-1],"visible_pixels":coverage,"changed_pixels":changed,"rest_lut_fault_pixels":faults,"image":file};records.append(row)
            if coverage<1000 or changed>0 or faults>0:failures.append(row)
        body.set_surface_override_material(0,production)
    var report={"ok":failures.is_empty(),"status":"done" if failures.is_empty() else "failed","next_action":"human_review" if failures.is_empty() else "fix_input","records":records,"failures":failures,"probe_sha256":FileAccess.get_sha256(OS.get_cmdline_args()[OS.get_cmdline_args().find("--script")+1]),"models":{},"runtime_files":{},"scope":"Actual production chart and optional lip wrapper, fixed RGB base green/donor red at actual posed surface fragments within1.5 native pixels of confirmed lower curve; nonempty coverage required."}
    for name in runtime_files("res://scripts/aquarium")+runtime_files("res://assets/models/fish/motion"):report.runtime_files[name]=FileAccess.get_sha256("res://"+name)
    for p in plan.items:report.models[p.species]=FileAccess.get_sha256("res://assets/models/fish/"+p.species+".glb")
    var file=FileAccess.open(out+"/paint.validation.json",FileAccess.WRITE);file.store_string(JSON.stringify(report,"  "));print("LIP_PAINT115 ",report.ok," ",failures.size());quit(0 if report.ok else 1)
