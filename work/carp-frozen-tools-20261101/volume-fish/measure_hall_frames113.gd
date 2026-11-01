extends SceneTree
func _initialize() -> void:call_deferred("run")
func run() -> void:
    root.size=Vector2i(1600,1000)
    var hall=load("res://scripts/aquarium/VolumeFishExhibit.gd").new();root.add_child(hall)
    var results: Array=[]
    for species in ["black_seabream","zander","arapaima"]:
        hall._select_display(species)
        hall._close_view()
        var modes: Array=["all_tanks","selected_tank"] if "--visibility-ab" in OS.get_cmdline_user_args() else ["runtime_selection"]
        for mode in modes:
            if "--visibility-ab" in OS.get_cmdline_user_args():
                for tank in hall.tanks:tank.root.visible=mode=="all_tanks" or tank.species==species
            for i in 30:await process_frame
            var values: Array=[]
            var before:=Time.get_ticks_usec()
            for i in 120:
                await process_frame
                var now:=Time.get_ticks_usec();values.append(float(now-before)/1000.);before=now
            values.sort()
            var entry: Dictionary=hall._selected()
            results.append({"species":species,"visibility":mode,"present":not entry.is_empty(),"sample_frames":values.size(),"frame_p50_ms":values[60],"frame_p95_ms":values[114],"max_ms":values[-1],"fps_monitor":Performance.get_monitor(Performance.TIME_FPS),"draw_calls":Performance.get_monitor(Performance.RENDER_TOTAL_DRAW_CALLS_IN_FRAME),"process_seconds":Performance.get_monitor(Performance.TIME_PROCESS)})
    var f:=FileAccess.open(OS.get_cmdline_user_args()[0],FileAccess.WRITE)
    f.store_string(JSON.stringify({"schema_version":1,"ok":true,"command":"fish.review113.live-frame-times","status":"done","next_action":"human_review","items":results,"engine":Engine.get_version_info().string,"renderer":RenderingServer.get_video_adapter_name(),"limits":"Current machine, normal full23-fish simulation and warm shaders; no claim about another machine or cold compilation."},"  ")+"\n")
    quit()
