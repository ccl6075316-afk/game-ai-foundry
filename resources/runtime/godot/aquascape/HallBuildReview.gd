extends "res://scripts/aquarium/AquariumHall3DReview.gd"
## Exercise the actual canvas tools and physical doors before the V1 regression.

func _click_world(at: Vector3) -> void:
    var event := InputEventMouseButton.new();event.button_index=MOUSE_BUTTON_LEFT
    event.position=editor_camera.unproject_position(at)*canvas.size/Vector2(viewport.size)
    event.pressed=true;canvas.gui_input.emit(event)
    event.pressed=false;canvas.gui_input.emit(event)

func _ray(from: Vector3,to: Vector3,mask: int=1) -> Dictionary:
    return world.get_world_3d().direct_space_state.intersect_ray(PhysicsRayQueryParameters3D.create(from,to,mask))

func _capture() -> void:
    for i in 15:await get_tree().process_frame
    _check("six_initial_standard_parcels",parcels.size()==6 and Footprint.valid(parcels))
    _check("initial_floor_area_252m2",Footprint.extent(parcels).get_area()==252)
    _check("reject_diagonal_parcel",not _expand_at(Vector3(12,0,10.5)))
    _check("reject_owned_parcel",not _expand_at(Vector3(0,0,0)))
    _set_tool("parcel")
    _check("only_neighbor_expansion_hints",parcel_hints.get_child_count()==Footprint.candidates(parcels).size()*2)
    _preview(Vector3(12,0,-3.5))
    await _image("06-parcel-expansion-preview")
    _click_world(Vector3(12,0,-3.5))
    _check("mouse_expands_one_fixed_parcel",parcels.size()==7 and Footprint.has(parcels,[3,0]))
    _undo();_check("undo_removes_expansion",parcels.size()==6)
    _redo();_check("redo_restores_expansion",parcels.size()==7)
    for i in 3:await get_tree().physics_frame
    _check("former_exterior_wall_removed",_ray(Vector3(8,1,-3),Vector3(10,1,-3)).is_empty())
    _check("new_exterior_wall_has_collision",not _ray(Vector3(14,1,-3),Vector3(16,1,-3)).is_empty())
    _check("new_parcel_has_floor",not _ray(Vector3(12,1,-3),Vector3(12,-1,-3)).is_empty())
    _check("unowned_notch_rejected",not _valid_placement(_candidate("bench",Vector3(12,0,3.5)),objects))
    _check("placement_across_owned_seam_allowed",_valid_placement(_candidate("bench",Vector3(9,0,-1)),objects))
    for index in 3:
        tank_size_choice.select(index)
        _check("tank_size_preset_%d" % index,absf(_candidate("tank",Vector3.ZERO).scale-[.5,.65,1.0][index])<.00001)
    tank_size_choice.select(1)
    _set_tool("tank");_preview(Vector3(12,0,-3.5))
    _check("tank_preview_exists",build_preview.get_child_count()==1)
    var turn := InputEventKey.new();turn.keycode=KEY_E;turn.pressed=true;_unhandled_key_input(turn)
    _check("pending_tank_keyboard_rotates_preview",absf(pending_yaw-deg_to_rad(15))<.00001)
    turn.keycode=KEY_Q;_unhandled_key_input(turn)
    var bad := _state();_click_world(Vector3(12,0,3.5))
    _check("invalid_mouse_tank_placement_does_not_mutate",_same(_state(),bad))
    _click_world(Vector3(12,0,-3.5))
    _check("mouse_places_real_tank_on_expansion",objects.size()==5 and objects[-1].data.kind=="tank" and objects[-1].tank!=null)
    _check("new_tank_starts_without_inventory_fish",objects[-1].tank.fish.is_empty())
    _set_tool("wall");wall_with_door=false
    _click_world(Vector3(4,0,0));_check("first_wall_click_sets_anchor",wall_anchor!=null)
    _preview(Vector3(8,0,.15));_click_world(Vector3(8,0,.15))
    _check("second_click_builds_orthogonal_wall",objects.size()==6 and objects[-1].data.kind=="wall" and objects[-1].data.length==4 and objects[-1].data.at[1]==0)
    var solid_id: String=objects[-1].data.id
    var before := _state()
    _check("reject_wall_through_existing_tank",not _commit_wall(Vector3(-2,0,-4.5),Vector3(2,0,-4.5)) and _same(_state(),before))
    _check("reject_overlapping_parallel_walls",not _commit_wall(Vector3(5,0,0),Vector3(7,0,0)))
    _set_tool("wall");wall_with_door=true
    _click_world(Vector3(-2,0,3));_click_world(Vector3(2,0,3))
    _check("doorway_is_real_wall_object",objects.size()==7 and objects[-1].data.get("door",false))
    _set_tool("")
    _set_tool("wall");wall_anchor=Vector3.ZERO
    var cancel := InputEventKey.new();cancel.keycode=KEY_ESCAPE;cancel.pressed=true;_input(cancel)
    _check("escape_cancels_wall_and_preview",pending_kind=="" and wall_anchor==null and build_preview.get_child_count()==0)
    panning=true
    var release := InputEventMouseButton.new();release.button_index=MOUSE_BUTTON_MIDDLE;release.pressed=false;_input(release)
    _check("middle_release_over_inspector_stops_pan",not panning)
    var door_id: String=objects[-1].data.id
    for i in 3:await get_tree().physics_frame
    _check("doorway_center_open_at_eye_height",_ray(Vector3(0,1.6,4),Vector3(0,1.6,2),2).is_empty())
    _check("doorway_header_collides",not _ray(Vector3(0,2.7,4),Vector3(0,2.7,2),2).is_empty())
    _mode(false)
    player.position=Vector3(6,.88,1.8);player.rotation.y=0;player.velocity=Vector3.ZERO
    Input.action_press("hall_forward")
    for i in 60:await get_tree().physics_frame
    Input.action_release("hall_forward")
    _check("solid_partition_blocks_walk",player.position.z>.31 and player.position.z<.6)
    player.position=Vector3(0,.88,5);player.velocity=Vector3.ZERO
    Input.action_press("hall_forward")
    for i in 65:await get_tree().physics_frame
    Input.action_release("hall_forward")
    _check("character_walks_through_real_door",player.position.z<2.6)
    player.position=Vector3(1.4,.88,5);player.velocity=Vector3.ZERO
    Input.action_press("hall_forward")
    for i in 65:await get_tree().physics_frame
    Input.action_release("hall_forward")
    _check("doorway_side_blocks_walk",player.position.z>3.25 and player.position.z<3.6)
    player.position=Vector3(0,.88,5.6);player.velocity=Vector3.ZERO
    notice="门洞保留真实通道，两侧隔墙阻挡行走。"
    await _image("07-partition-door-walk")
    _mode(true);selected=objects.size()-1
    _check("door_wall_length_edit",_resize_selected(5) and objects[selected].data.length==5)
    _undo();_check("wall_length_undo",objects[-1].data.id==door_id and objects[-1].data.length==4)
    _redo();_check("wall_length_redo",objects[-1].data.length==5)
    for i in objects.size():
        if objects[i].data.id==solid_id:selected=i
    _check("wall_rotates_in_right_angles",_rotate_selected(1) and absf(objects[selected].data.yaw-PI/2)<.00001)
    _check("wall_moves_on_floor",_move_selected(Vector3(6.5,0,.5)))
    _delete_selected();_check("wall_delete",objects.size()==6)
    _undo();_check("wall_delete_undo",objects.size()==7)
    var built := _state()
    _check("schema2_validates_parcels_and_partitions",built.schema_version==2 and _valid_state(built))
    _check("schema2_atomic_save",_write_layout(directory+"/build-layout.json"))
    _restore(_default_state());_check("schema2_load_restores_all_building",_load_layout(directory+"/build-layout.json") and _same(_state(),built))
    var invalid: Dictionary=built.duplicate(true);invalid.parcels.append([4,3])
    _check("disconnected_parcel_save_rejected",not _valid_state(invalid))
    invalid=built.duplicate(true);invalid.parcels.append([0,0])
    _check("duplicate_parcel_save_rejected",not _valid_state(invalid))
    invalid=built.duplicate(true);invalid.parcels[0]=[false,0]
    _check("nonnumeric_parcel_save_rejected",not _valid_state(invalid))
    invalid=built.duplicate(true);invalid.objects[-1].length=.1
    _check("too_short_door_save_rejected",not _valid_state(invalid))
    invalid=built.duplicate(true);invalid.objects[-1].yaw=.3
    _check("diagonal_wall_save_rejected",not _valid_state(invalid))
    invalid=built.duplicate(true);invalid.parcels=Footprint.initial()
    _check("object_on_unowned_land_save_rejected",not _valid_state(invalid))
    var legacy := _default_state();legacy.schema_version=1;legacy.erase("parcels")
    _check("legacy_schema1_is_accepted",_valid_state(legacy))
    var file := FileAccess.open(directory+"/legacy-layout.json",FileAccess.WRITE);file.store_string(JSON.stringify(legacy));file.close()
    _check("legacy_load_gives_six_parcels",_load_layout(directory+"/legacy-layout.json") and parcels.size()==6)
    _check("legacy_file_not_rewritten_on_load",JSON.parse_string(FileAccess.get_file_as_string(directory+"/legacy-layout.json")).schema_version==1)
    _restore(built);_fit_hall();pitch=1.15;yaw=.10;_camera();selected=-1;_sync_panel()
    notice="已扩至 7 块 / 294 m²：新增展缸、实墙、可穿行门洞；支持撤销和保存。"
    await _image("08-expanded-hall-build")
    _set_tool("tank");_preview(Vector3(12,0,4))
    await _image("09-invalid-placement-preview")
    _set_tool("");_restore(_default_state());history.clear();future.clear();_fit_hall();pitch=.83;yaw=.48;_camera()
    await super._capture()
