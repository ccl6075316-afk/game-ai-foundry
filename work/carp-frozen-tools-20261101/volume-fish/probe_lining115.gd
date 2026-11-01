extends "./capture_source_fit115.gd"
func run():
    DirAccess.make_dir_recursive_absolute(out)
    var plan:Dictionary=JSON.parse_string(FileAccess.get_file_as_string(OS.get_cmdline_user_args()[2]))
    root.size=Vector2i(1000,700);hall=load("res://scripts/aquarium/VolumeFishExhibit.gd").new();root.add_child(hall);hall.set_process(false);hall.paused=true;hall.header.hide();hall.footer.hide()
    hall.screen.set_anchors_and_offsets_preset(Control.PRESET_TOP_LEFT);hall.screen.position=Vector2.ZERO;hall.screen.size=Vector2(1000,700);hall.viewport.size=Vector2i(1000,700);hall.viewport.render_target_update_mode=SubViewport.UPDATE_ALWAYS
    for label in hall.world.find_children("*","Label3D",true,false):label.hide()
    var failures:Array=[];var parser=load("res://scripts/aquarium/FishEyeOwnership.gd").new()
    for p in plan.items:
        hall._select_display(p.species);var entry:Dictionary=hall._selected();var body=entry.model.find_child("Closed_body",true,false) as MeshInstance3D
        for mesh in hall.world.find_children("*","MeshInstance3D",true,false):mesh.visible=mesh==body
        body.extra_cull_margin=1000.
        var production=body.get_active_material(1) as ShaderMaterial
        var diagnostic=ShaderMaterial.new();var code:String=production.shader.code.replace("render_mode","render_mode unshaded,depth_test_disabled,depth_draw_never,")
        if "--legacy" in OS.get_cmdline_user_args():code=FileAccess.get_file_as_string("res://scripts/aquarium/SourceJaw112.gdshader").replace("render_mode","render_mode unshaded,depth_test_disabled,depth_draw_never,")
        code=code.replace("#include \"RestSurface114.gdshaderinc\"",FileAccess.get_file_as_string("res://scripts/aquarium/RestSurface114.gdshaderinc"))
        var declaration="""
uniform sampler2D probe115_positions:filter_nearest,repeat_disable;
uniform ivec2 probe115_size;uniform int probe115_count;
uniform vec4 probe115_rect;uniform vec3 probe115_bounds;uniform int probe115_mode=0;
varying vec3 probe115_p;varying float probe115_error;
"""
        code=code.replace("void vertex()",declaration+"\nvoid vertex()")
        var vb:Dictionary=parser._stage_braces(code,"vertex")
        var prefix="""
    int index=clamp(VERTEX_ID,0,probe115_count-1);vec4 p=texelFetch(probe115_positions,ivec2(index%probe115_size.x,index/probe115_size.x),0);
    probe115_p=p.xyz;probe115_error=(VERTEX_ID>=probe115_count||p.w<.5)?1.:0.;
"""
        var suffix="""
    float cx=(probe115_p.x-probe115_bounds.x)/(probe115_bounds.y-probe115_bounds.x)*1.9-.95;
    float cy=probe115_p.z/probe115_bounds.z*.44+(UV2.y>.5?.5:-.5);
    POSITION=vec4(cx,cy,0.,1.);
"""
        code=code.insert(vb.close,suffix);code=code.insert(vb.open,prefix)
        var fb:Dictionary=parser._stage_braces(code,"fragment")
        var actual="cavity115_uv(rest114_position)" if code.contains("vec2 cavity115_uv(") else "UV"
        var guard="||rest114_error>.001" if code.contains("rest114_error") else ""
        var fragment="""
    vec2 span=probe115_rect.zw-probe115_rect.xy;
    vec2 pixel=floor(vec2(probe115_p.x+.5,probe115_p.z)*source_size.x);
    ivec2 expected=ivec2(probe115_rect.xy+mod(pixel,span));
    ivec2 actual=ivec2(floor(ACTUAL*source_size));
    ALBEDO=all(equal(actual,expected))?vec3(0.,1.,0.):vec3(1.,0.,0.);
    if(probe115_mode==1){ALBEDO=vec3(mod(float(actual.x),251.)/250.,mod(float(actual.y),251.)/250.,.5);}
    if(probe115_error>.001GUARD){ALBEDO=vec3(1.,0.,1.);}
""".replace("ACTUAL",actual).replace("GUARD",guard)
        code=code.substr(0,fb.open)+fragment+code.substr(fb.close)
        var shader=Shader.new();shader.code=code;diagnostic.shader=shader
        for u in production.shader.get_shader_uniform_list():diagnostic.set_shader_parameter(u.name,production.get_shader_parameter(u.name))
        var arrays=body.mesh.surface_get_arrays(1);var positions:PackedVector3Array=arrays[Mesh.ARRAY_VERTEX]
        var count:int=positions.size();var size=Vector2i(256,ceili(float(count)/256));var lookup=Image.create(size.x,size.y,false,Image.FORMAT_RGBAF)
        var minx=INF;var maxx=-INF;var maxz=0.
        for i in count:
            var v=positions[i];lookup.set_pixel(i%256,i/256,Color(v.x,v.y,v.z,1.));minx=minf(minx,v.x);maxx=maxf(maxx,v.x);maxz=maxf(maxz,abs(v.z))
        diagnostic.set_shader_parameter("probe115_positions",ImageTexture.create_from_image(lookup));diagnostic.set_shader_parameter("probe115_count",count);diagnostic.set_shader_parameter("probe115_size",size)
        var rect:Array=p.cavity_rect_native_px;diagnostic.set_shader_parameter("probe115_rect",Vector4(rect[0],rect[1],rect[2],rect[3]));diagnostic.set_shader_parameter("probe115_bounds",Vector3(minx,maxx,maxz))
        var hidden=ShaderMaterial.new();var hs=Shader.new();hs.code="shader_type spatial;void fragment(){discard;}";hidden.shader=hs
        var skin=body.get_surface_override_material(0);body.set_surface_override_material(0,hidden);body.set_surface_override_material(1,diagnostic)
        var folder=out+"/"+p.species;DirAccess.make_dir_recursive_absolute(folder)
        var samples:Array=[]
        for action in ["Swim","Turn","Ascend","Dive"]:
            for phase in [0.,.33]:samples.append({"action":action,"phase":phase})
        for pair in [["Swim","Turn"],["Turn","Ascend"],["Ascend","Dive"],["Dive","Swim"]]:samples.append({"from":pair[0],"to":pair[1],"fraction":.5})
        for sample in samples:
            if sample.has("from"):
                entry.controller.set_action(sample.from,true);entry.controller.step(0.);entry.controller.seek(.75);entry.controller.set_action(sample.to,false);entry.controller.step(float(entry.profile.transition_seconds)*.5)
            else:
                entry.controller.set_action(sample.action,true);entry.controller.step(0.);entry.controller.seek(float(entry.profile.period_seconds)*sample.phase)
            var file=folder+"/sample-%02d.png"%records.size();await shot(file)
            var data=hall.viewport.get_texture().get_image().get_data();var coverage=0;var mismatch=0;var faults=0
            for i in range(0,data.size(),4):
                if data[i]>240 and data[i+2]>240 and data[i+1]<10:faults+=1
                if data[i+2]<4 and (data[i]>10 or data[i+1]>10):
                    coverage+=1
                    if data[i]>2:mismatch+=1
            var row={"species":p.species,"sample":sample,"visible_cavity_pixels":coverage,"mismatched_native_texels":mismatch,"lookup_fault_pixels":faults,"production_shader_sha256":production.shader.code.sha256_text(),"diagnostic_shader_sha256":code.sha256_text(),"model_sha256":FileAccess.get_sha256(entry.model.scene_file_path)};records.append(row)
            if coverage<10000 or mismatch>0 or faults>0:failures.append(row)
        diagnostic.set_shader_parameter("probe115_mode",1);await shot(folder+"/native-coordinates.png")
        var img=hall.viewport.get_texture().get_image();var columns:Dictionary={};var rows:Dictionary={}
        for y in img.get_height():
            for x in img.get_width():
                var c:Color=img.get_pixel(x,y)
                if c.b<.49 or c.b>.51:continue
                if not columns.has(x):columns[x]={}
                if not rows.has(y):rows[y]={}
                columns[x][roundi(c.g*255.)]=true;rows[y][roundi(c.r*255.)]=true
        var max_column=0;var max_row=0
        for values in columns.values():max_column=maxi(max_column,values.size())
        for values in rows.values():max_row=maxi(max_row,values.size())
        var axes={"species":p.species,"scope":"native_texel_axes","max_distinct_y_texels_at_fixed_x":max_column,"max_distinct_x_texels_at_fixed_z":max_row};records.append(axes)
        if max_column<3 or max_row<3:failures.append(axes)
        body.set_surface_override_material(0,skin);body.set_surface_override_material(1,production)
    var report={"ok":failures.is_empty(),"status":"done" if failures.is_empty() else "failed","next_action":"human_review" if failures.is_empty() else "fix_input","records":records,"failures":failures,"probe_sha256":FileAccess.get_sha256(get_script().resource_path),"runtime_files":{},"plan_sha256":FileAccess.get_sha256(OS.get_cmdline_user_args()[2]),"scope":"Actual production cavity donor coordinate against separate static surface1 table/oracle; nondegenerate restXZ roof/floor canvas, 8 actual four-action phases each species. Material appearance and continuous-time proof separate."}
    for name in runtime_files("res://scripts/aquarium")+runtime_files("res://assets/models/fish/motion"):report.runtime_files[name]=FileAccess.get_sha256("res://"+name)
    var file=FileAccess.open(out+"/lining.validation.json",FileAccess.WRITE);file.store_string(JSON.stringify(report,"  "));print("LINING115 ",report.ok," ",failures.size());quit(0 if report.ok else 1)
