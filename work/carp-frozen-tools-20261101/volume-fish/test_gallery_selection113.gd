extends SceneTree
var failures: Array=[]
var checks:=0
func _initialize() -> void:call_deferred("run")
func expect(value: bool,message: String) -> void:
    checks+=1
    if not value:failures.append({"kind":"validation","code":"gallery_selection","message":message})
func times(hall) -> Dictionary:
    var result: Dictionary={}
    for entry in hall.fish:result[entry.species]=entry.controller.snapshot().time
    return result
func check_advance(hall,expected: Array,label: String) -> void:
    var before:=times(hall)
    hall._process(1./60.)
    var after:=times(hall)
    for species in before:
        expect((after[species]>before[species])==(species in expected),label+" advances "+species)
func run() -> void:
    var script=load("res://scripts/aquarium/VolumeFishExhibit.gd")
    var hall=script.new();root.add_child(hall);hall.set_process(false)
    expect(hall._selected().species=="black_seabream","Initial selected fish")
    for species in hall.SPECIES:
        hall._select_display(species)
        for tank in hall.tanks:expect(tank.root.visible==(tank.species==species),"Selected "+species+" visible tank "+tank.species)
        check_advance(hall,hall.SPECIES,"Selected preserves all clocks "+species)
        for action in ["Swim","Turn","Ascend","Dive"]:
            hall._select_action(action);hall._process(.1)
            expect(hall._selected().controller.snapshot().action==action,"Selected action "+species+" "+action)
    hall._show_overview()
    for tank in hall.tanks:expect(tank.root.visible,"Overview restores "+tank.species)
    check_advance(hall,hall.SPECIES,"Overview")
    hall._close_view()
    for tank in hall.tanks:expect(tank.root.visible==(tank.species==hall.display),"Close view restores selected tank "+tank.species)
    hall._select_display("zander");hall.paused=true
    hall._select_display("black_seabream")
    for tank in hall.tanks:expect(tank.root.visible==(tank.species=="black_seabream"),"Paused selection visible "+tank.species)
    check_advance(hall,[],"Paused")
    hall.paused=false;hall.hide();check_advance(hall,[],"Hidden gallery")
    hall.queue_free();await process_frame
    var shared=script.new();shared.shared_tank=true;root.add_child(shared);shared.set_process(false)
    shared._select_display("zander")
    expect(shared.tanks.size()==1 and shared.tanks[0].root.visible,"Shared tank stays visible")
    check_advance(shared,shared.SPECIES,"Shared selected")
    shared._show_overview()
    expect(shared.tanks[0].root.visible,"Shared overview visible")
    var report: Dictionary={"schema_version":1,"ok":failures.is_empty(),"command":"fish.review113.gallery-regression","status":"done" if failures.is_empty() else "failed","next_action":"human_review" if failures.is_empty() else "fix_input","checks":checks,"failures":failures,"exhibit_sha256":FileAccess.get_sha256("res://scripts/aquarium/VolumeFishExhibit.gd")}
    var f:=FileAccess.open(OS.get_cmdline_user_args()[0],FileAccess.WRITE);f.store_string(JSON.stringify(report,"  ")+"\n")
    print("GALLERY_SELECTION "+JSON.stringify({"ok":report.ok,"checks":checks,"failures":failures.size()}))
    quit(0 if report.ok else 1)
