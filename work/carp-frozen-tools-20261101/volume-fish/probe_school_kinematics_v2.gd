extends SceneTree
## Read-only phase-1 evidence: no rig loading, tuning, asset writes or GPU claims.
var output := ""
var rows: Array = []
var roster: Array = []
var profiles: Dictionary = {}
var bindings: Dictionary = {}

func _initialize() -> void:
    for arg in OS.get_cmdline_user_args():
        if arg.begins_with("--output="): output = arg.trim_prefix("--output=")
    var safe_root := ProjectSettings.globalize_path("res://../plans/reviews/fish-school-motion-v2").simplify_path()
    if not output.is_absolute_path() or output != output.simplify_path() or not output.begins_with(safe_root + "/"):
        push_error("Output must be an absolute child of fish-school-motion-v2"); quit(2); return
    var directory := DirAccess.open("/")
    var cursor := "/"
    for part in output.split("/", false):
        cursor = cursor.path_join(part)
        if directory.is_link(cursor): push_error("Symlink output ancestor rejected"); quit(2); return
    DirAccess.make_dir_recursive_absolute(output)
    var expression := RegEx.new()
    expression.compile("const SPECIES := (\\[[^\\r\\n]+\\])")
    var text := FileAccess.get_file_as_string("res://scripts/aquarium/VolumeFishExhibit.gd")
    var match := expression.search(text)
    if match == null: push_error("Species roster missing"); quit(2); return
    for species in JSON.parse_string(match.get_string(1)):
        if species not in ["scalloped_hammerhead", "great_hammerhead", "smooth_hammerhead"]: roster.append(species)
    profiles = JSON.parse_string(FileAccess.get_file_as_string("res://assets/models/fish/motion/motion.json")).profiles
    for path in ["res://scripts/aquarium/fish_school/FishSchoolSimulation.gd", "res://scripts/aquarium/fish_school/FishSchoolReview.gd", "res://scripts/aquarium/FoundryFishMotion.gd", "res://scripts/aquarium/VolumeFishExhibit.gd", "res://assets/models/fish/motion/motion.json", get_script().resource_path]:
        bindings[path] = FileAccess.get_sha256(path)
    call_deferred("run")

func summary(values: Array) -> Dictionary:
    values.sort()
    var total := 0.0
    for value in values: total += float(value)
    return {"min": values[0], "mean": total / values.size(), "median": values[values.size() / 2], "p95": values[mini(values.size() - 1, ceili(values.size() * 0.95) - 1)], "max": values[-1]}

func run() -> void:
    var script = load("res://scripts/aquarium/fish_school/FishSchoolSimulation.gd")
    for count in [50, 200]:
        for tiered in [false, true]:
            var simulation = script.new()
            simulation.configure(count, 731, roster.size())
            var species_rows: Array = []
            for species in roster:
                species_rows.append({"species": species, "length_m": float(profiles[species].real_length_cm) / 100.0,
                    "speed": [], "actual_speed": [], "turn": [], "acceleration": [], "turning_radius": [],
                    "path_distance_m": 0.0, "projection_affected_steps": 0, "sample_count": 0})
            var contacts := 0
            var boundaries := 0
            var truncations := 0
            for tick in 1200:
                var old_positions: PackedVector3Array = simulation.positions.duplicate()
                var old_velocities: PackedVector3Array = simulation.velocities.duplicate()
                var metrics: Dictionary = simulation.step(1.0 / 60.0, tiered)
                contacts += metrics.obstacle_contacts; boundaries += metrics.boundary_contacts
                truncations += metrics.neighbor_truncations
                for i in count:
                    var row: Dictionary = species_rows[simulation.species_ids[i]]
                    var velocity: Vector3 = simulation.velocities[i]
                    var speed := velocity.length()
                    var actual_delta: Vector3 = simulation.positions[i] - old_positions[i]
                    var turn: float = old_velocities[i].angle_to(velocity) * 60.0
                    row.speed.append(speed); row.actual_speed.append(actual_delta.length() * 60.0)
                    row.turn.append(turn); row.acceleration.append(old_velocities[i].distance_to(velocity) * 60.0)
                    if turn > 0.05: row.turning_radius.append(speed / turn)
                    row.path_distance_m += actual_delta.length(); row.sample_count += 1
                    if actual_delta.distance_to(velocity / 60.0) > 0.0001: row.projection_affected_steps += 1
            for row in species_rows:
                var species: String = row.species
                var profile: Dictionary = profiles[species]
                var length_m: float = row.length_m
                var fish_count := int(count / roster.size())
                var normalized: Array = []
                for speed in row.speed: normalized.append(float(speed) / length_m)
                var normalized_radii: Array = []
                for radius in row.turning_radius: normalized_radii.append(float(radius) / length_m)
                var speed_stats := summary(row.speed)
                var path_radii: Array = profile.path_radii_m
                var native_rate := TAU / float(profile.period_seconds) * float(profile.actions.Swim.radius_scale)
                rows.append({"count": count, "tiered": tiered, "species": species, "length_m": length_m,
                    "first_two_member_tier_ids": [simulation.tier_ids[roster.find(species)], simulation.tier_ids[roster.find(species) + roster.size()]],
                    "speed_m_s": speed_stats, "speed_body_lengths_s": summary(normalized), "actual_point_displacement_speed_m_s": summary(row.actual_speed),
                    "heading_turn_rad_s": summary(row.turn), "vector_acceleration_m_s2": summary(row.acceleration),
                    "nonstraight_center_path_radius_m": summary(row.turning_radius) if not row.turning_radius.is_empty() else {},
                    "nonstraight_center_path_radius_body_lengths": summary(normalized_radii) if not normalized_radii.is_empty() else {},
                    "average_20s_center_path_distance_m": row.path_distance_m / fish_count,
                    "average_20s_center_path_distance_body_lengths": row.path_distance_m / fish_count / length_m,
                    "projection_affected_steps": row.projection_affected_steps,
                    "native_Swim_head_ellipse_speed_m_s_range": [native_rate * minf(path_radii[0], path_radii[1]), native_rate * maxf(path_radii[0], path_radii[1])],
                    "native_Swim_head_ellipse_speed_body_lengths_s_range": [native_rate * minf(path_radii[0], path_radii[1]) / length_m, native_rate * maxf(path_radii[0], path_radii[1]) / length_m]})
                rows[-1]["native_Swim_head_ellipse_turn_rad_s_range"] = [TAU / float(profile.period_seconds) * minf(path_radii[0], path_radii[1]) / maxf(path_radii[0], path_radii[1]), TAU / float(profile.period_seconds) * maxf(path_radii[0], path_radii[1]) / minf(path_radii[0], path_radii[1])]
                rows[-1]["native_Swim_head_ellipse_radius_m_range"] = [pow(minf(path_radii[0], path_radii[1]), 2) / maxf(path_radii[0], path_radii[1]), pow(maxf(path_radii[0], path_radii[1]), 2) / minf(path_radii[0], path_radii[1])]
            rows.append({"count": count, "tiered": tiered, "aggregate": true, "obstacle_projection_events": contacts, "boundary_clamp_events": boundaries, "neighbor_truncation_events": truncations})
    var changed: Array = []
    for path in bindings:
        if FileAccess.get_sha256(path) != bindings[path]: changed.append(path)
    var report := {"schema_version": 1, "command": "fish.school.kinematics-probe-v2", "ok": changed.is_empty(), "status": "done" if changed.is_empty() else "failed", "next_action": "human_review",
        "phase": "root_cause_investigation_only", "inputs": {"bindings_sha256": bindings, "changed_during_run": changed, "roster": roster, "seed": 731, "fixed_delta_s": 1.0 / 60.0, "ticks_per_case": 1200},
        "rows": rows, "limits": {"min_speed_m_s": script.MIN_SPEED, "max_speed_m_s": script.MAX_SPEED, "max_vector_acceleration_m_s2": script.MAX_ACCELERATION, "max_turn_rad_s": script.MAX_TURN_RATE, "point_radius_m": script.FISH_RADIUS},
        "limitations": ["World center path sampled, no meshes/bones loaded or GPU visual validation", "Native comparator is profile Swim head ellipse analytical speed range, a different reference point from school model-center path", "m/s divided by current authored length gives body lengths/s, not a biological target or measured species calibration", "Twenty simulated seconds at fixed tick; no inference about wall-time interactive playback or benchmark FPS", "Point projections can differ from velocity integration and do not represent full-body/fin clearance", "Native profile and 132 gait numeric settings are authored illustrative/experimental settings, not measured biology", "No source tuning or fix performed; previous v1 evidence remains historical"], "failures": changed}
    var file := FileAccess.open(output.path_join("kinematics.validation.json"), FileAccess.WRITE)
    file.store_string(JSON.stringify(report, "  ") + "\n")
    print(JSON.stringify({"ok": report.ok, "rows": rows.size(), "report": output.path_join("kinematics.validation.json")}))
    quit(0 if report.ok else 1)
