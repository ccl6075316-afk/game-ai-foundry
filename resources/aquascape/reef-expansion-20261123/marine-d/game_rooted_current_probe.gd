extends SceneTree

const Interior=preload("res://scripts/aquarium/tank_design/ShellInterior.gd")
const Contents=preload("res://scripts/aquarium/tank_design/ShellContentsView.gd")
const Current=preload("res://scripts/aquarium/tank_design/RootedCurrent.gd")
var camera: Camera3D
var prop_view: Node3D
var bed_holder: MeshInstance3D
var out: String
var rows: Array=[]
var failures: Array[String]=[]

func _initialize() -> void:
    run.call_deferred()

func run() -> void:
    var args:=OS.get_cmdline_user_args()
    out=args[0]
    DirAccess.make_dir_recursive_absolute(out)
    root.set_flag(Window.FLAG_NO_FOCUS,true)
    var index:=DisplayServer.get_primary_screen()
    var frame:=DisplayServer.screen_get_usable_rect(index)
    root.current_screen=index
    root.size=Vector2i(Vector2(940,624)*minf(frame.size.x*.8/940,frame.size.y*.8/624))
    root.position=frame.position+(frame.size-root.size)/2
    root.title="潮汐馆 · 缸体定制原型 · 造景水流验证"
    root.show()
    GDExtensionManager.load_extension(args[1])
    var center:=Node3D.new()
    root.add_child(center)
    var env := Environment.new()
    env.background_mode=Environment.BG_COLOR
    env.background_color=Color("#253840")
    env.ambient_light_source=Environment.AMBIENT_SOURCE_COLOR
    env.ambient_light_color=Color("#e8f9fb")
    env.ambient_light_energy=.46
    var atmosphere := WorldEnvironment.new()
    atmosphere.environment=env
    center.add_child(atmosphere)
    var light:=DirectionalLight3D.new()
    light.rotation=Vector3(-.62,-.45,0)
    light.light_energy=.64
    center.add_child(light)
    camera=Camera3D.new()
    camera.projection=Camera3D.PROJECTION_ORTHOGONAL
    center.add_child(camera)
    camera.make_current()
    bed_holder=MeshInstance3D.new()
    var plane:=PlaneMesh.new()
    plane.size=Vector2(15,8)
    var substrate:=StandardMaterial3D.new()
    substrate.albedo_color=Color("#9e9870")
    bed_holder.mesh=plane
    bed_holder.material_override=substrate
    center.add_child(bed_holder)
    bed_holder.position.y=.1195
    prop_view=Contents.new()
    var layout_bed:=MeshInstance3D.new()
    center.add_child(layout_bed)
    # The production view expects a MeshInstance3D parent. Use an independent
    # plane for the fixture so the fixture never offsets production anchors.
    layout_bed.add_child(prop_view)
    var assets: Dictionary=Interior.assets()
    var ids: Array=assets.keys().filter(func(id):return assets[id].has("rooted_current"))
    ids.append("reef_rubble_apron")
    for value: Variant in ids:
        await capture(String(value),assets[value])
    var pass_value:=failures.is_empty() and ids.has("giant_kelp") and ids.has("eelgrass_meadow")
    var output:=FileAccess.open(out.path_join("game-review.json"),FileAccess.WRITE)
    output.store_string(JSON.stringify({"ok":pass_value,"engine":Engine.get_version_info(),"catalog_count":assets.size(),
        "shader_path":Current.PAINT.resource_path,"rows":rows,"failures":failures}, "  ")+"\n")
    output.close()
    quit(0 if pass_value else 1)

func capture(id: String, row: Dictionary) -> void:
    var design: Dictionary={"kind":"rect","width":15.0,"depth":8.0,"height":5.1,"radii":[0,0,0,0]}
    var bed: Dictionary={"substrate":"fine_sand","depth_cm":12.0,"props":[{"id":id,"u":.5,"v":.5}],"fish":[]}
    prop_view.sync({"design":design},bed)
    if prop_view.props.size()!=1:
        failures.append(id+": production sync gave no prop")
        return
    var entry: Dictionary=prop_view.props[0]
    var node: Node3D=entry.root
    var extent: AABB=node.global_transform*entry.bounds
    var meshes:=node.find_children("*","MeshInstance3D",true,false)
    var rooted:=row.has("rooted_current")
    var bound_surfaces:=0
    var surface_count:=0
    var native_mount_vertices:=0
    var native_mount_weight:=0.0
    var native_tip_weight:=0.0
    for mesh: MeshInstance3D in meshes:
        for surface: int in mesh.mesh.get_surface_count():
            surface_count+=1
            var material:=mesh.get_surface_override_material(surface) as ShaderMaterial
            if material==null:continue
            if material.shader!=Current.PAINT:continue
            bound_surfaces+=1
            if material.get_shader_parameter("artwork")==null:failures.append(id+": no imported artwork")
            if mesh.extra_cull_margin<=0.:failures.append(id+": existing cull margin not expanded")
            var arrays: Array=mesh.mesh.surface_get_arrays(surface)
            var position: PackedVector3Array=arrays[Mesh.ARRAY_VERTEX]
            var uv2: PackedVector2Array=arrays[Mesh.ARRAY_TEX_UV2]
            var colors: PackedColorArray=arrays[Mesh.ARRAY_COLOR]
            if position.size()!=uv2.size() or position.size()!=colors.size():
                failures.append(id+": missing native deformation streams")
                continue
            var box:=mesh.get_aabb()
            for vertex in position.size():
                var weight:=smoothstep(.08,1.,uv2[vertex].x)*colors[vertex].a
                native_tip_weight=maxf(native_tip_weight,weight)
                if position[vertex].y<=box.position.y+box.size.y*.022:
                    native_mount_vertices+=1
                    native_mount_weight=maxf(native_mount_weight,weight)
    if ((rooted and bound_surfaces!=surface_count) or (not rooted and bound_surfaces!=0)):
        failures.append(id+": wrong active shader count")
    if rooted and (native_mount_vertices==0 or native_mount_weight!=0. or native_tip_weight<=0.):
        failures.append(id+": imported mesh has no fixed substrate contact or no moving tip")
    if not is_equal_approx(extent.position.y,.12):
        failures.append(id+": global bounds do not begin on shaped tank substrate")
    var center:=extent.get_center()
    var ratio:=float(root.size.x)/float(root.size.y)
    camera.size=1.32*maxf(extent.size.y,extent.size.x/ratio)
    camera.look_at_from_position(center+Vector3(.14,0.0,4.4),center)
    var point:=camera.unproject_position(Vector3(center.x,extent.position.y,center.z))
    rows.append({"id":id,"rooted":rooted,"expected_q_depth":.12,"model":row.model,
        "placed_root_y":extent.position.y,"all_surfaces":surface_count,"official_shader_surfaces":bound_surfaces,
        "native_mount_vertices":native_mount_vertices,"native_max_mount_sway_weight":native_mount_weight,
        "native_max_tip_sway_weight":native_tip_weight,
        "root_row_logical_px":point.y,"one_m_logical_px":point.y-camera.unproject_position(Vector3(center.x,extent.position.y+1.,center.z)).y,
        "logical_height_px":root.size.y,"bounds_size":[extent.size.x,extent.size.y,extent.size.z]})
    set_enabled(meshes,1.)
    await frame_to(id+"-real-time-a.png")
    await create_timer(.45).timeout
    await frame_to(id+"-real-time-b.png")
    set_enabled(meshes,0.)
    await frame_to(id+"-held-a.png")
    await create_timer(.41).timeout
    await frame_to(id+"-held-b.png")
    set_enabled(meshes,1.)
    await create_timer(.32).timeout
    await frame_to(id+"-resumed.png")

func set_enabled(meshes: Array[Node], enabled: float) -> void:
    for mesh: MeshInstance3D in meshes:
        for surface: int in mesh.mesh.get_surface_count():
            var p:=mesh.get_surface_override_material(surface) as ShaderMaterial
            if p != null and p.shader==Current.PAINT:
                p.set_shader_parameter("enabled",enabled)

func frame_to(name: String) -> void:
    for i: int in range(2):await process_frame
    RenderingServer.force_draw(false,.11)
    assert(root.get_texture().get_image().save_png(out.path_join(name))==OK)
