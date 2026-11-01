extends SceneTree
const Route=preload("res://scripts/aquarium/passage/PassageRoute.gd")
const Session=preload("res://scripts/aquarium/passage/PassageSession.gd")
var checks: Dictionary={}

func _initialize() -> void:
    var directory := ""
    for arg in OS.get_cmdline_user_args():
        if arg.begins_with("--report-dir="):directory=arg.trim_prefix("--report-dir=")
    if directory.is_empty():quit(2);return
    DirAccess.make_dir_recursive_absolute(directory)
    var route := Route.initial()
    checks.default_route_valid=Route.validate(route).is_empty()
    print("DEFAULT_ROUTE ",Route.validate(route))
    var path := Route.samples(route)
    checks.bounded_dry_segments=path.size()>5 and path.size()-1<=Route.MAX_SEGMENTS
    checks.endpoints_preserved=path[0].distance_to(Route.point(route.points[0]))<.001 and path[-1].distance_to(Route.point(route.points[-1]))<.001
    checks.nonuniform_elevations=path[-1].y-path[0].y>2.9
    var bad := route.duplicate(true);bad.points[1][1]=4.0
    checks.steep_route_rejected=not Route.validate(bad).is_empty()
    bad=route.duplicate(true);bad.width=20
    checks.invalid_dimensions_rejected=not Route.validate(bad).is_empty()
    bad=route.duplicate(true);bad.points[0][0]=0
    checks.missing_dry_platform_rejected=not Route.validate(bad).is_empty()
    bad=route.duplicate(true);bad.points[2][0]=NAN
    checks.nonfinite_point_rejected=not Route.validate(bad).is_empty()
    bad=route.duplicate(true);bad.extra=Node.new()
    checks.unknown_runtime_field_rejected=not Route.validate(bad).is_empty();bad.extra.free()
    var flat := route.duplicate(true);flat.points=[[-13.0,1.0,0.0],[13.0,1.0,0.0]]
    var straight := Route.samples(flat)
    checks.round_interior_is_dry=Route.contains(flat,straight,Vector3(0,2.6,0))
    checks.water_outside_stays_wet=not Route.contains(flat,straight,Vector3(0,2.6,4))
    checks.long_dry_ray_has_zero_water=Route.wet_length(flat,straight,Vector3(-8,2.6,0),Vector3.RIGHT,Vector2(0,16))<.0001
    var r := Route.radius(flat);var center: float=flat.height-r
    var expected := 6-sqrt(r*r-pow(1.6-center,2))
    checks.round_side_ray_keeps_water=absf(Route.wet_length(flat,straight,Vector3(0,2.6,0),Vector3.BACK,Vector2(0,6))-expected)<.001
    flat.section="arch"
    checks.arch_valid=Route.validate(flat).is_empty()
    checks.arch_floor_dry=Route.contains(flat,straight,Vector3(0,1.01,0))
    checks.arch_below_floor_wet=not Route.contains(flat,straight,Vector3(0,.9,0))
    checks.arch_side_water_length=absf(Route.wet_length(flat,straight,Vector3(0,2,0),Vector3.BACK,Vector2(0,6))-4.7)<.001
    var session=Session.new();var original := JSON.stringify(session.route)
    checks.rejected_edit_preserves_model=not session.commit(bad).is_empty() and JSON.stringify(session.route)==original
    flat=route.duplicate(true);flat.section="arch"
    checks.section_can_change=session.commit(flat).is_empty()
    checks.undo_section=session.undo() and session.route.section=="round"
    checks.redo_section=session.redo() and session.route.section=="arch"
    checks.save_valid_route=session.save(directory+"/route.json")
    var reloaded=Session.new()
    checks.cold_read_saved_route=reloaded.load_route(directory+"/route.json").is_empty() and reloaded.route.section=="arch"
    var file=FileAccess.open(directory+"/bad.json",FileAccess.WRITE);file.store_string("[]");file.close()
    original=JSON.stringify(reloaded.route)
    checks.invalid_load_preserves_model=not reloaded.load_route(directory+"/bad.json").is_empty() and JSON.stringify(reloaded.route)==original
    var okay := not checks.values().has(false)
    file=FileAccess.open(directory+"/route.validation.json",FileAccess.WRITE);file.store_string(JSON.stringify({"ok":okay,"checks":checks},"  "));file.close()
    print("PASSAGE_ROUTE ",okay," ",checks.size());quit(0 if okay else 1)
