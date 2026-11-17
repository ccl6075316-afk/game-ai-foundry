extends "smooth/live_viewer.gd"

const ScallopedGait = preload("scalloped/Gait.gd")
const ScallopedPrey = preload("scalloped/Prey.gd")
var fish_choice: OptionButton

func run() -> void:
    await super.run()
    if closing:
        return

    root.title = "路氏双髻鲨与无沟双髻鲨 · 捕食预览"
    var sidebar := pause_button.get_parent()
    var heading := sidebar.get_child(0) as Label
    heading.text = "双髻鲨"
    fish_choice = OptionButton.new()
    for entry in catalog.entries:
        fish_choice.add_item(str(entry.label))
    sidebar.add_child(fish_choice)
    sidebar.move_child(fish_choice, heading.get_index() + 1)
    fish_choice.item_selected.connect(show_species)

    fish_choice.select(1)
    show_species(1)
    if "--background-preview" not in OS.get_cmdline_user_args():
        root.grab_focus()
    if "--joint-test" in OS.get_cmdline_user_args():
        await verify_both()
        _finish()
        return

    await _save_capture("joint-window")
    write("joint-startup.validation.json", {
        "ok": ready_for_input and checks.all(func(item): return item.passed),
        "pid": OS.get_process_id(),
        "startup_species": config.species,
        "models": catalog.entries.map(func(entry): return FileAccess.get_sha256(entry.viewer.model)),
        "captures": captures,
    })

func show_species(index: int) -> void:
    playing = false
    stamp = 0.
    prey.free()
    live_controls = false
    _select_fish(index)
    live_controls = true
    if not ready_for_input:
        return
    gait = ScallopedGait.new() if index == 1 else Gait.new()
    prey = ScallopedPrey.new() if index == 1 else Prey.new()
    gait.bind(carrier, skeleton, controller)
    world.add_child(prey)
    info.text = "捕食回放"
    sync_frame()

func verify_both() -> void:
    for index in range(fish_choice.item_count):
        fish_choice.select(index)
        fish_choice.item_selected.emit(index)
        var species: String = config.species
        _check(species + "_actual_model_loaded", ready_for_input
            and skeleton.get_bone_count() == 22
            and FileAccess.get_sha256(config.model) == config.model_sha256)
        _check(species + "_fins_and_material", meshes.size() == config.inventory.mesh_count)
        for prey_index in range(branch.item_count):
            branch.select(prey_index)
            branch.item_selected.emit(prey_index)
            var label := species + ("-large" if large else "-small")
            var contact := ScallopedGait.BITE_TIME if index == 1 else Gait.CONTACT
            var events: Array[Dictionary] = []
            var max_gap := 0.
            var max_grip_error := 0.
            for frame in range(241):
                var t := float(frame) / 60.
                var sample := frame_at(t, large)
                max_gap = maxf(max_gap, sample.mouth_gap_m)
                if sample.has("upper_grip_m"):
                    max_grip_error = maxf(max_grip_error, maxf(sample.upper_grip_m, sample.lower_grip_m))
                if frame in [0, 76, int(round(contact * 60.)), 138, 240]:
                    events.append(sample)
            var final_state: Dictionary = events.back()
            var recovery_ok: bool = final_state.gape < .001 and final_state.inside_progress > .999
            if large:
                recovery_ok = max_grip_error < .000002 and final_state.gape > .25
            _check(label + "_pose_contact_and_recovery", max_gap > .03 and recovery_ok)
            write(label + ".validation.json", {
                "model_sha256": FileAccess.get_sha256(config.model),
                "max_mouth_gap_m": max_gap, "max_grip_error_m": max_grip_error,
                "pose_samples": 241, "events": events,
            })
            close_button.pressed.emit()
            _view(27., -39.)
            if index == 1:
                stamp = 1.25
                playing = true
                sync_frame()
                await _save_capture(label + "-open")
            stamp = contact
            playing = true
            sync_frame()
            await _save_capture(label + "-bite")
            if index == 1:
                stamp = 2.29
                sync_frame()
                await _save_capture(label + "-recovery")
            whole_button.pressed.emit()
            top_button.pressed.emit()
            record_playback_view(label + "_top", Vector3.UP)
            await _save_capture(label + "-playing-top")
    playing = false
    write("joint-controls.validation.json", {
        "ok": checks.all(func(item): return item.passed),
        "checks": checks, "captures": captures,
    })
