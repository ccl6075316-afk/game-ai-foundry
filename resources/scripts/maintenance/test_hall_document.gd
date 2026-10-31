extends SceneTree
const Document=preload("res://scripts/aquarium/hall/HallLayoutDocument.gd")
const Commands=preload("res://scripts/aquarium/hall/HallBuildCommands.gd")
const Rules=preload("res://scripts/aquarium/hall/HallLayoutRules.gd")
const History=preload("res://scripts/aquarium/hall/HallEditHistory.gd")
var checks: Dictionary={}

func _initialize() -> void:
    var directory := ""
    for arg in OS.get_cmdline_user_args():
        if arg.begins_with("--maintenance-dir="):directory=arg.trim_prefix("--maintenance-dir=")
    if directory.is_empty():quit(2);return
    DirAccess.make_dir_recursive_absolute(directory)
    var doc=Document.new();var rules=Rules.new();var history=History.new()
    var commands=Commands.new(doc,rules,history)
    var legacy := {"schema_version":1,"floor_style":0,"wall_style":0,"objects":[]}
    checks.legacy_normalized=doc.replace(legacy,rules) and doc.snapshot().schema_version==2 and doc.parcels().size()==6
    var snapshot: Dictionary=doc.snapshot();snapshot.parcels.clear()
    checks.snapshot_does_not_alias=doc.parcels().size()==6
    var bench := {"id":"bench","kind":"bench","name":"bench","at":[0,0],"yaw":0.0,"scale":1.0}
    var added: Dictionary=commands.execute("add",{"object":bench})
    checks.add_command=added.ok
    if not added.ok:print("ADD_FAILED ",added," ",doc.snapshot());quit(1);return
    bench.at[0]=99
    checks.command_payload_does_not_alias=doc.object_data("bench").at[0]==0
    var revision: int=doc.revision;var count: int=history.past.size()
    checks.invalid_placement_rejected=not commands.execute("patch",{"id":"bench","patch":{"at":[999,999]}}).ok
    checks.failed_command_preserves_revision_and_history=doc.revision==revision and history.past.size()==count and doc.object_data("bench").at[0]==0
    checks.duplicate_id_rejected=not commands.execute("add",{"object":doc.object_data("bench")}).ok
    checks.stale_preview_rejected=not commands.execute("remove",{"id":"bench"},true,revision-1).ok and not doc.object_data("bench").is_empty()
    checks.move_command=commands.execute("patch",{"id":"bench","patch":{"at":[2.0,2.25]}}).ok
    checks.undo_restores_model=commands.undo() and doc.object_data("bench").at[0]==0
    checks.redo_restores_model=commands.redo() and doc.object_data("bench").at[0]==2
    commands.undo();commands.execute("style",{"key":"floor_style","value":1})
    checks.branch_discards_redo=not commands.redo() and doc.style("floor_style")==1
    checks.expand_command=commands.execute("expand",{"cell":[3,0]}).ok and doc.parcels().size()==7
    checks.invalid_expansion_rejected=not commands.execute("expand",{"cell":[999,999]}).ok
    checks.malformed_expansion_rejected=not commands.execute("expand",{"cell":[]}).ok and not commands.execute("expand",{"cell":["a",0]}).ok
    checks.id_and_kind_immutable=not commands.execute("patch",{"id":"bench","patch":{"id":"other"}}).ok
    var tank := {"id":"tank","kind":"tank","name":"tank","at":[0,-4],"yaw":0.0,"scale":.5,"fish_count":0,"content":{}}
    checks.tank_add_checks_content=commands.execute("add",{"object":tank}).ok
    checks.changed_content_cannot_skip_validation=not commands.execute("patch",{"id":"tank","patch":{"content":{"invalid":true}}}).ok
    var injected := Node.new()
    checks.command_cannot_inject_runtime_nodes=not commands.execute("patch",{"id":"bench","patch":{"extra":injected}}).ok
    injected.free()
    snapshot=doc.snapshot();var node := Node.new();snapshot.extra=node
    checks.runtime_nodes_never_enter_document=not doc.replace(snapshot,rules);node.free()
    checks.remove_command=commands.execute("remove",{"id":"bench"}).ok and doc.object_data("bench").is_empty()
    checks.undo_recreates_document_object=commands.undo() and not doc.object_data("bench").is_empty()
    var copy: Dictionary=doc.object_data("bench");copy.at[0]=400
    checks.object_lookup_does_not_alias=doc.object_data("bench").at[0]!=400
    var okay := not checks.values().has(false)
    var file=FileAccess.open(directory+"/document.validation.json",FileAccess.WRITE)
    file.store_string(JSON.stringify({"ok":okay,"checks":checks},"  "));file.close()
    print("HALL_DOCUMENT ",okay," ",checks.size());quit(0 if okay else 1)
