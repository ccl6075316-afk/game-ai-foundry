extends RefCounted
## Build-mode input adapter. Issues host commands; owns no scene or persistence.

func canvas_input(host: Control,event: InputEvent) -> void:
    if event is InputEventMouseMotion:
        host.pointer=event.position*Vector2(host.viewport.size)/host.canvas.size
        if host.editor.panning:
            var right: Vector3=host.editor_camera.global_basis.x
            var forward := Vector3(right.z,0,-right.x)
            host.camera_target+=(-right*event.relative.x+forward*event.relative.y)*host.view_size/1080;host._camera()
        if host.editor.orbiting:host.yaw-=event.relative.x*.005;host.pitch=clampf(host.pitch+event.relative.y*.004,.4,PI/2);host._camera()
        if host.editor.dragging and host.selected>=0 and host.objects[host.selected].data.id==host.editor.move_selection_id:
            if not (event.button_mask & MOUSE_BUTTON_MASK_LEFT):
                host.editor.dragging=false
            elif host.editor.drag_moved or event.position.distance_to(host.editor.drag_press)>=host.editor.DRAG_SLOP:
                var at: Variant=host.editor._floor_hit(host.pointer)
                if at!=null and host.editor._move_selected(at+host.editor.drag_offset,not host.editor.drag_moved):
                    host.editor.drag_moved=true
        host.editor._preview(host.editor._floor_hit(host.pointer))
    if not event is InputEventMouseButton:return
    host.pointer=event.position*Vector2(host.viewport.size)/host.canvas.size
    if event.button_index==MOUSE_BUTTON_RIGHT:host.editor.orbiting=event.pressed
    if event.button_index==MOUSE_BUTTON_MIDDLE:host.editor.panning=event.pressed
    if event.pressed and event.button_index in [MOUSE_BUTTON_WHEEL_UP,MOUSE_BUTTON_WHEEL_DOWN]:
        host.view_size=maxf(host.view_size*(.9 if event.button_index==MOUSE_BUTTON_WHEEL_UP else 1.1),1.0 if host.build_editor.shells.session.mode=="interior" else 10.0);host._camera();host.editor._preview(host.editor._floor_hit(host.pointer))
    if event.button_index==MOUSE_BUTTON_LEFT:
        var at: Variant=host.editor._floor_hit(host.pointer)
        if host.editor.pending_kind in ["floor","floor_erase"]+host.editor.Architecture.REGION_TOOLS:
            if event.pressed:host.editor.floor_anchor=at;host.editor._preview(at)
            elif host.editor.floor_anchor!=null:
                if at!=null:host.editor._commit_floor(at)
                else:host.editor.floor_anchor=null;host.editor._preview(null)
            return
        if not event.pressed:host.editor.dragging=false;return
        if host.editor.pending_kind=="parcel":
            if at!=null:host.editor._expand_at(at);host.editor._preview(host.editor._floor_hit(host.pointer))
        elif host.editor.pending_kind=="wall":
            if at!=null:
                if host.editor.wall_anchor==null:
                    var marker := AABB(Vector3(at.x-.01,0,at.z-.01),Vector3(.02,.1,.02))
                    if host.Footprint.contains(host.parcels,marker):host.editor.wall_anchor=at;host.notice="已选起点，点击终点建墙；Esc 取消。"
                    else:host.notice="起点需要在已扩建地基内。"
                else:host.editor._commit_wall(host.editor.wall_anchor,at)
                host.editor._preview(at)
        elif host.editor.pending_kind!="":
            if at!=null:host.editor._add_at(host.editor.pending_kind,at)
        else:
            var previous: int=host.selected
            host.selected=host._pick(host.pointer)
            host._sync_panel()
            var id: String=host.objects[host.selected].data.id if host.selected>=0 else ""
            host.editor.dragging=at!=null and id!="" and host.selected==previous and id==host.editor.move_selection_id
            host.editor.move_selection_id=id
            if host.editor.dragging:
                host.editor.drag_press=event.position
                host.editor.drag_offset=host.objects[host.selected].node.position-at
                host.editor.drag_moved=false

func key_input(host: Control,event: InputEvent) -> void:
    if host.tank_session.active_editor!=null or not host.editing or not event is InputEventKey or not event.pressed or event.echo:return
    if event.ctrl_pressed:
        if event.keycode==KEY_Z:host._undo()
        if event.keycode==KEY_Y:host._redo()
        if event.keycode==KEY_S:host._save_layout()
        return
    if host.editor.pending_kind!="":
        if event.keycode in [KEY_Q,KEY_E] and host.editor.pending_kind in ["tank","bench","plinth"]:
            host.editor.pending_yaw+=deg_to_rad(15)*(-1 if event.keycode==KEY_Q else 1);host.editor._preview(host.editor._floor_hit(host.pointer))
        return
    if event.keycode==KEY_Q:host.editor._rotate_selected(-1)
    if event.keycode==KEY_E:host.editor._rotate_selected(1)
    if event.keycode==KEY_DELETE:host.editor._delete_selected()
