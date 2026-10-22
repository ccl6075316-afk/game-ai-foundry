extends SceneTree
## Runtime-only, single-variable comparison of exact section search methods.
var hall
var cases: Array=[]
func _initialize() -> void:
    call_deferred("run")
func search_code() -> String:
    return """vec4 chart112_section(float x){
    int lo=0;int hi=chart112_section_count-1;
    for(int search=0;search<7;search++){
        if(hi-lo<=1)break;
        int mid=(lo+hi)/2;
        if(x<=chart112_sections[mid].x)hi=mid;else lo=mid;
    }
    vec4 a=chart112_sections[lo];vec4 b=chart112_sections[hi];
    return mix(a,b,clamp((x-a.x)/max(b.x-a.x,1e-8),0.,1.));
}
"""
func shot(path: String) -> Image:
    await process_frame
    RenderingServer.force_draw()
    await process_frame
    RenderingServer.force_draw()
    var image: Image=hall.viewport.get_texture().get_image()
    image.save_png(path)
    return image
func frames(count: int) -> Array:
    var values: Array=[]
    for i in count:
        await process_frame
        var t:=Time.get_ticks_usec()
        RenderingServer.force_draw()
        values.append(float(Time.get_ticks_usec()-t)/1000.)
    values.sort()
    return values
func run() -> void:
    var out: String=OS.get_cmdline_user_args()[0]
    DirAccess.make_dir_recursive_absolute(out)
    root.size=Vector2i(1200,800)
    hall=load("res://scripts/aquarium/VolumeFishExhibit.gd").new();root.add_child(hall)
    hall.set_process(false);hall.paused=true;hall.header.hide();hall.footer.hide()
    hall.screen.set_anchors_and_offsets_preset(Control.PRESET_TOP_LEFT)
    hall.screen.position=Vector2.ZERO;hall.screen.size=Vector2(1200,800)
    hall.viewport.size=Vector2i(1200,800);hall.viewport.render_target_update_mode=SubViewport.UPDATE_ALWAYS
    for species in ["black_seabream","zander","sea_bass"]:
        hall._select_display(species)
        for tank in hall.tanks:tank.root.visible=tank.species==species
        var entry: Dictionary=hall._selected()
        entry.controller.set_motion_controls({"body_amplitude":0.,"fin_amplitude":0.},true)
        entry.controller.step(0.);entry.controller.seek(0.)
        hall._focus_selected(true,1.65)
        var receipt: Dictionary=entry.model.get_meta("surface_chart_112_receipt")
        var body=entry.model.find_child(receipt.mesh,true,false)
        var material: ShaderMaterial=body.get_active_material(int(receipt.surface))
        var old_shader: Shader=material.shader
        var code: String=old_shader.code
        var start:=code.find("vec4 chart112_section(float x){")
        var end:=code.find("vec3 chart112_color",start)
        assert(start>=0 and end>start)
        var shader:=Shader.new();shader.code=code.substr(0,start)+search_code()+code.substr(end)
        var results: Dictionary={"species":species,"methods":[]}
        var before: Image
        for method in ["linear","binary","linear","binary"]:
            material.shader=old_shader if method=="linear" else shader
            await frames(15)
            var image: Image=await shot(out+"/"+species+"-"+method+".png")
            if before==null:before=image
            var timings: Array=await frames(50)
            results.methods.append({"method":method,"draw_wall_p50_ms":timings[25],"draw_wall_p95_ms":timings[47],"pixels_equal_to_linear":image.get_data()==before.get_data()})
        material.shader=old_shader
        cases.append(results)
    var report: Dictionary={"schema_version":1,"command":"fish.review113.section-benchmark","ok":true,"status":"done","next_action":"human_review","items":cases,"limits":"force_draw wall time includes graphics driver and CPU, not a pure GPU timestamp; fixed paused scene and warmed shaders."}
    var f:=FileAccess.open(out+"/benchmark.validation.json",FileAccess.WRITE);f.store_string(JSON.stringify(report,"  ")+"\n")
    quit()
