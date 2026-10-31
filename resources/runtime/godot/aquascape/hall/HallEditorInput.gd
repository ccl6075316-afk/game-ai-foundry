extends RefCounted
## Build-mode input adapter. Issues host commands; owns no scene or persistence.

func canvas_input(host: Control,event: InputEvent) -> void:
    if event is InputEventMouseMotion:
        host.pointer=event.position*Vector2(host.viewport.size)/host.canvas.size
        if host.panning:
            var right: Vector3=host.editor_camera.global_basis.x
            var forward := Vector3(right.z,0,-right.x)
            host.camera_target+=(-right*event.relative.x+forward*event.relative.y)*host.view_size/1080;host._camera()
        if host.orbiting:host.yaw-=event.relative.x*.005;host.pitch=clampf(host.pitch+event.relative.y*.004,.4,1.35);host._camera()
        if host.dragging and host.selected>=0:
            var at: Variant=host._floor_hit(host.pointer)
            if at!=null:host._move_selected(at+host.drag_offset)
        host._preview(host._floor_hit(host.pointer))
    if not event is InputEventMouseButton:return
    host.pointer=event.position*Vector2(host.viewport.size)/host.canvas.size
    if event.button_index==MOUSE_BUTTON_RIGHT:host.orbiting=event.pressed
    if event.button_index==MOUSE_BUTTON_MIDDLE:host.panning=event.pressed
    if event.pressed and event.button_index in [MOUSE_BUTTON_WHEEL_UP,MOUSE_BUTTON_WHEEL_DOWN]:
        host.view_size=clampf(host.view_size*(.9 if event.button_index==MOUSE_BUTTON_WHEEL_UP else 1.1),10,65);host._camera();host._preview(host._floor_hit(host.pointer))
    if event.button_index==MOUSE_BUTTON_LEFT:
        if not event.pressed:host.dragging=false;return
        var at: Variant=host._floor_hit(host.pointer)
        if host.pending_kind=="parcel":
            if at!=null:host._expand_at(at);host._preview(host._floor_hit(host.pointer))
        elif host.pending_kind=="wall":
            if at!=null:
                if host.wall_anchor==null:
                    var marker := AABB(Vector3(at.x-.01,0,at.z-.01),Vector3(.02,.1,.02))
                    if host.Footprint.contains(host.parcels,marker):host.wall_anchor=at;host.notice="已选起点，点击终点建墙；Esc 取消。"
                    else:host.notice="起点需要在已扩建地基内。"
                else:host._commit_wall(host.wall_anchor,at)
                host._preview(at)
        elif host.pending_kind!="":
            if at!=null:host._add_at(host.pending_kind,at)
        else:
            host.selected=host._pick(host.pointer);host._sync_panel()
            if host.selected>=0 and at!=null:host._remember();host.drag_offset=host.objects[host.selected].node.position-at;host.dragging=true

func key_input(host: Control,event: InputEvent) -> void:
    if host.active_editor!=null or not host.editing or not event is InputEventKey or not event.pressed or event.echo:return
    if event.ctrl_pressed:
        if event.keycode==KEY_Z:host._undo()
        if event.keycode==KEY_Y:host._redo()
        if event.keycode==KEY_S:host._save_layout()
        return
    if host.pending_kind!="":
        if event.keycode in [KEY_Q,KEY_E] and host.pending_kind in ["tank","bench","plinth"]:
            host.pending_yaw+=deg_to_rad(15)*(-1 if event.keycode==KEY_Q else 1);host._preview(host._floor_hit(host.pointer))
        return
    if event.keycode==KEY_Q:host._rotate_selected(-1)
    if event.keycode==KEY_E:host._rotate_selected(1)
    if event.keycode==KEY_DELETE:host._delete_selected()
