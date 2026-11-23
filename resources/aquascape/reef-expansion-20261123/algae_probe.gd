extends SceneTree

const Interior = preload("res://scripts/aquarium/tank_design/ShellInterior.gd")
const Contents = preload("res://scripts/aquarium/tank_design/ShellContentsView.gd")
const Store = preload("res://scripts/aquarium/hall/HallLayoutStore.gd")
const Rules = preload("res://scripts/aquarium/hall/HallLayoutRules.gd")

func _initialize() -> void:
    audit.call_deferred()

func audit() -> void:
    var items: Array = []
    var rule := Rules.new()
    var supported: Array = Interior.assets().keys().filter(Interior.supports_algae)
    var columns := 6
    var rows := ceili(float(supported.size()) / columns)
    var i := 0
    for id: String in supported:
        var selected := {"id": id, "u": 0.15 + float(i % columns) * 0.12, "v": (floorf(float(i) / columns) + 0.5) / rows, "algae": true}
        items.append(selected)
        var plain: Dictionary = selected.duplicate()
        plain.erase("algae")
        plain.u += 0.035
        items.append(plain)
        i+=1
    var bed := {"substrate": "fine_sand", "depth_cm": 12, "props": items}
    var design := {"kind":"rect","width":15.0,"depth":8.0,"height":5.1,"radii":[0,0,0,0]}
    var shell := {"id":"algae-probe","kind":"shell","name":"覆藻存档验证","at":[0,0],"yaw":0,"scale":1,"design":design,"interior":bed}
    var layout := {"schema_version":1,"floor_style":0,"wall_style":0,"objects":[shell]}
    var out_path: String = OS.get_cmdline_user_args()[0]
    var temp := out_path.get_base_dir().path_join("algae-save-tmp.json")
    var saved := Store.write_layout(temp, layout, rule)
    var readback: Variant = Store.read_layout(temp, rule)
    var persisted: Array = readback.objects[0].interior.props if readback is Dictionary else []
    var roundtrip := persisted.size()==items.size()
    for index in persisted.size():
        var orig: Dictionary = items[index]
        var restored: Dictionary = persisted[index]
        roundtrip=roundtrip and restored.id==orig.id and restored.get("algae",false)==orig.get("algae",false)
        roundtrip=roundtrip and is_equal_approx(float(restored.u),float(orig.u)) and is_equal_approx(float(restored.v),float(orig.v))
    if saved: DirAccess.remove_absolute(temp)
    var wrong_type := not Interior.valid({"props":[{"id":"rock","u":0.4,"v":0.4,"algae":"yes"}]})
    var wrong_item := not Interior.valid({"props":[{"id":"java_fern","u":0.4,"v":0.4,"algae":true}]})
    var base := MeshInstance3D.new()
    var contents := Contents.new()
    root.add_child(base)
    base.add_child(contents)
    contents.sync(shell, readback.objects[0].interior if roundtrip else bed)
    var pairs := 0
    var surfaces := 0
    for index in range(0, contents.props.size(), 2):
        var coated: Node3D = contents.props[index].root
        var clean: Node3D = contents.props[index + 1].root
        var a := coated.find_children("*", "MeshInstance3D", true, false)[0] as MeshInstance3D
        var b := clean.find_children("*", "MeshInstance3D", true, false)[0] as MeshInstance3D
        var good := a.mesh == b.mesh
        for surface in a.mesh.get_surface_count():
            var variant := a.get_surface_override_material(surface) as ShaderMaterial
            var original := b.get_active_material(surface) as StandardMaterial3D
            if variant == null or original == null:
                good=false
                continue
            var same_texture: bool = variant.get_shader_parameter("stone_art") == original.albedo_texture
            good=good and same_texture and b.get_surface_override_material(surface)==null and variant.next_pass==null
            surfaces+=1
        pairs+=int(good)
    var ok := saved and roundtrip and wrong_type and wrong_item and pairs==supported.size()
    var info := {"ok": ok, "instances": contents.props.size(), "pairs_same_mesh_and_base_texture":pairs,
        "single_pass_surfaces":surfaces, "saved":saved, "roundtrip":roundtrip,
        "invalid_type_rejected":wrong_type, "unsupported_asset_rejected":wrong_item,
        "supported_ids":supported, "engine":Engine.get_version_info().string}
    var f := FileAccess.open(out_path, FileAccess.WRITE)
    f.store_string(JSON.stringify(info, "  ") + "\n")
    f.close()
    base.free()
    quit(0 if ok else 1)
