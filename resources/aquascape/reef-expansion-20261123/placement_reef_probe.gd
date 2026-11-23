extends SceneTree

const Interior = preload("res://scripts/aquarium/tank_design/ShellInterior.gd")
const Design = preload("res://scripts/aquarium/tank_design/ShellDesign.gd")
const Contents = preload("res://scripts/aquarium/tank_design/ShellContentsView.gd")

const Store = preload("res://scripts/aquarium/hall/HallLayoutStore.gd")
const Rules = preload("res://scripts/aquarium/hall/HallLayoutRules.gd")

func _initialize() -> void:
    call_deferred("_audit")

func _audit() -> void:
    var catalogs: Array = []
    for path in ["res://assets/aquascape-v5/catalog.json", "res://assets/aquascape-decor-v1/catalog.json", "res://assets/aquascape-reef-foundation-v1/catalog.json", "res://assets/aquascape-expansion-v1/catalog.json"]:
        if not FileAccess.file_exists(path):
            continue
        var doc: Dictionary = JSON.parse_string(FileAccess.get_file_as_string(path))
        catalogs.append(doc.assets)
    var items: Array = []
    var expected_ids: Array = []
    var native_rows: Dictionary = {}
    var grid_rows := ceili(float(Interior.assets().size()) / 10.0)
    var new_positions := {
        "reef_backwall":Vector2(-3.3,-2.15),
        "reef_through_arch":Vector2(2.0,0.2),
        "reef_blind_grotto":Vector2(-4.45,1.45),
        "reef_shelf_terrace":Vector2(-0.5,-2.8),
        "reef_pinnacle":Vector2(5.0,-2.9),
        "reef_rubble_apron":Vector2(-0.9,2.5),
    }
    for catalog: Array in catalogs:
        for row: Dictionary in catalog:
            var id: String = row.id
            var index := items.size()
            expected_ids.append(id)
            var packed := load(row.model) as PackedScene
            var shader_variant: String = row.get("shader_model", "")
            native_rows[id] = {
                "packed_scene_loadable": packed != null,
                "sha_source": row.model,
                "shader_scene_loadable": ResourceLoader.exists(shader_variant, "PackedScene") if not shader_variant.is_empty() else null,
            }
            var location := Vector2((float(index % 10) + 0.5) / 10.0,
                (float(floori(index / 10.0)) + 0.5) / grid_rows)
            if new_positions.has(id):
                location=Vector2(0.5,0.5)+new_positions[id]/Vector2(15,8)
            items.append({"id": id, "u":location.x, "v":location.y})
    var design := {"kind":"rect","width":15.0,"depth":8.0,"height":5.1,"radii":[0,0,0,0]}
    var selection := {"substrate": "fine_sand", "depth_cm": 12.0, "props": items}
    var report_path: String = OS.get_cmdline_user_args()[0]
    var snapshot_path := report_path.get_base_dir().path_join("temporary-placement.json")
    var exhibit := {"id":"reef-registry-probe","kind":"shell","name":"饰物目录验证","at":[0,0],"yaw":0,"scale":1,"design":design,"interior":selection}
    var layout := {"schema_version":1,"floor_style":0,"wall_style":0,"objects":[exhibit]}
    var rules := Rules.new()
    var saved := Store.write_layout(snapshot_path, layout, rules)
    var loaded: Variant = Store.read_layout(snapshot_path, rules)
    if saved:
        DirAccess.remove_absolute(snapshot_path)
    var readback: Dictionary = loaded.objects[0].interior if loaded is Dictionary else {}
    var selection_valid := Interior.valid(selection)
    var restored_valid := loaded is Dictionary and Interior.valid(readback)
    var registry_order := Interior.assets().keys() == expected_ids
    var base := MeshInstance3D.new()
    var primary := Contents.new()
    var restored := Contents.new()
    root.add_child(base)
    base.add_child(primary)
    base.add_child(restored)
    primary.sync({"design":design}, selection)
    restored.sync({"design":design}, readback)
    var fits_count := 0
    var attached_count := 0
    var restored_count := 0
    var floating_count := 0
    var placed_floating := 0
    var new_large := 0
    var contour := Design.contour(design)
    for i: int in primary.props.size():
        var entry: Dictionary = primary.props[i]
        var node: Node3D = entry.root
        var extent: AABB = entry.bounds
        var id: String = entry.item.id
        var fits: bool = Interior.prop_fits(node.transform, extent, contour, design.height)
        var attached := absf(extent.position.y) < 0.0001
        if Interior.assets()[id].get("placement_anchor") == "water_surface":
            floating_count += 1
            var world_bounds: AABB = node.transform * extent
            placed_floating += int(absf(world_bounds.end.y - Interior.waterline(design.height) + .004) < .0001)
        var matched: bool = restored.props.size() > i and restored.props[i].item.id == id and restored.props[i].root.transform.is_equal_approx(node.transform)
        fits_count += int(fits)
        attached_count += int(attached)
        restored_count += int(matched)
        var size: float = node.transform.basis.get_scale().x
        if new_positions.has(id) and size > 1.0: new_large+=1
        native_rows[id].merge({"fits_tank":fits,"normalized_base":attached,"restored_same_transform":matched,"longest_dimension_m":size})
    var count := items.size()
    var ok := new_large == new_positions.size() and saved and registry_order and selection_valid and restored_valid and count == primary.props.size() and count == restored_count and count == attached_count and count == fits_count and floating_count == placed_floating
    var result := {"command":"aquascape.exhibit-prop-registry","ok":ok,"status":"done" if ok else "failed","catalog_count":count,"new_meter_scale":new_large,"registry_order_matches_source":registry_order,"save_ok":saved,"valid_input":selection_valid,"valid_readback":restored_valid,"created":primary.props.size(),"contained":fits_count,"normalized_base":attached_count,"floating_on_waterline":placed_floating,"restored_same_transform":restored_count,"rows":native_rows,"scope":"Headless placement through ShellContentsView and temporary HallLayoutStore save/reload; no player save accessed."}
    var out := FileAccess.open(report_path, FileAccess.WRITE)
    out.store_string(JSON.stringify(result, "  ") + "\n")
    out.close()
    base.free()
    quit(0 if ok else 1)
