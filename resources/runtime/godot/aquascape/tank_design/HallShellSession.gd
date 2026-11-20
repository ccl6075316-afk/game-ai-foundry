extends RefCounted
## A transient scene preview. Only Apply writes to the layout document.
const Design=preload("ShellDesign.gd")
const PreviewMesh=preload("ShellMesh.gd")
const Finished=preload("FinishedShell.gd")
var hall: Control
var mode := ""
var draft: Dictionary={}
var source: Dictionary={}
var preview: MeshInstance3D
const Interior=preload("ShellInterior.gd")
var contents: Node3D
var last_mesh_data: Array=[]
var camera_before: Dictionary={}
var last_stroke_usec:=0
var brushing:=false
var previous_selection := -1

func _init(owner_hall: Control) -> void:
    hall=owner_hall

func begin(kind: String,data: Dictionary,existing: Dictionary={}) -> bool:
    if mode!="" or not hall.editor._valid_placement(data,hall.objects,data.id):return false
    previous_selection=hall.selected
    hall.editor._set_tool("")
    hall.editor.dragging=false
    hall.editor.move_selection_id=""
    mode=kind
    source=existing
    if not source.is_empty():source.node.hide()
    draft=data.duplicate(true)
    preview=MeshInstance3D.new()
    hall.world.add_child(preview)
    if mode=="shape":preview.material_override=PreviewMesh.material()
    if mode=="interior":
        contents=preload("ShellContentsView.gd").new()
        preview.add_child(contents)
        camera_before={"size":hall.view_size,"target":hall.camera_target}
        var box:AABB=hall._transform(draft)*Design.bounds(draft.design)
        hall.view_size=maxf(2.0,box.size.length()*1.08)
        hall.camera_target=box.get_center()+hall.editor_camera.global_basis.x*hall.view_size*.09
        hall._camera()
    refresh()
    hall.notice="调整后保存缸形，Esc 取消。" if mode=="shape" else "完成布置后保存内部，Esc 取消。"
    return true

func preview_row() -> Dictionary:
    return {"node":preview,"data":draft} if mode!="" else {}

func refresh() -> void:
    preview.transform=hall._transform(draft)
    if mode=="shape":preview.mesh=PreviewMesh.build(Design.contour(draft.design),draft.design.height)
    else:
        var bed:Dictionary=draft.get("interior",Finished.DEFAULT_BED)
        var mesh_data:=[draft.design,bed.substrate,bed.depth_cm,bed.get("heights",[])]
        if mesh_data!=last_mesh_data:
            preview.mesh=Finished.build(draft)
            last_mesh_data=mesh_data
        contents.sync(draft,bed)

func change(patch: Dictionary) -> bool:
    if mode=="":return false
    var proposal:=draft.duplicate()
    proposal.merge(patch,true)
    if not Design.valid(proposal.design) or not Finished.valid_interior(proposal.get("interior",Finished.DEFAULT_BED)):return false
    if not Interior.fits(proposal.design,proposal.get("interior",Finished.DEFAULT_BED)):return false
    if mode=="shape" and not hall.editor._valid_placement(proposal,hall.objects,proposal.id):return false
    draft=proposal
    refresh()
    return true

func save() -> bool:
    if mode=="":return false
    var id: String=draft.id
    var ok:=true
    if source.is_empty():
        ok=hall._execute_build("add",{"object":draft})
    else:
        var patch: Dictionary={}
        var keys:=["design","at"] if mode=="shape" else ["interior"]
        for key in keys:
            if draft.has(key) and draft[key]!=source.data.get(key):patch[key]=draft[key]
        if not patch.is_empty():ok=hall._execute_build("patch",{"id":id,"patch":patch})
    if not ok:return false
    var message:="缸形已保存。" if mode=="shape" else "缸内布置已保存。"
    close()
    for i in hall.objects.size():
        if hall.objects[i].data.id==id:hall.selected=i;break
    hall._sync_panel()
    hall.notice=message
    return true

func cancel() -> void:
    if mode=="":return
    close()
    hall.selected=previous_selection
    hall._sync_panel()
    hall.notice="已取消本次编辑。"

func close() -> void:
    hall.build_editor.shells.handles.reset()
    if not source.is_empty() and is_instance_valid(source.node):source.node.show()
    if not camera_before.is_empty():
        hall.view_size=camera_before.size
        hall.camera_target=camera_before.target
        camera_before={}
        hall._camera()
    last_mesh_data=[]
    last_stroke_usec=0
    brushing=false
    contents=null
    preview.hide();preview.queue_free()
    preview=null;mode="";draft={};source={}

func frame_height() -> void:
    var box:AABB=preview.transform*Design.bounds(draft.design)
    if box.size.y<=hall.view_size*.45:return
    hall.view_size=maxf(hall.view_size,box.size.length()*2)
    hall.camera_target=box.get_center()-hall.editor_camera.global_basis.y*(hall.view_size*.1)
    hall._camera()

func update_bed(fields: Dictionary) -> void:
    if mode!="interior":return
    var bed:Dictionary=draft.get("interior",Finished.DEFAULT_BED).duplicate()
    bed.merge(fields,true)
    if not change({"interior":bed}):
        hall.build_editor.shell_inspector.bound_data={}
        hall.build_editor.shell_inspector.interior_tools.status.text="现有鱼只需要更多水深。"

func available_fish() -> Dictionary:
    var options:Dictionary={}
    if not hall.warehouse_linked:
        for species in Interior.Fish.SPECIES:options[species]=[]
        return options
    var used:Dictionary={}
    for row in hall.objects:
        var data:Dictionary=draft if row.data.id==draft.id else row.data
        for item in data.get("interior",{}).get("fish",[]):used[item.get("stock","")]=true
    for id in hall.warehouse:
        if used.has(id):continue
        var species:String=hall.warehouse[id]
        if not options.has(species):options[species]=[]
        options[species].append(id)
    return options

func interior_input(event: InputEvent) -> bool:
    var panel:Control=hall.build_editor.shell_inspector.interior_tools
    if event is InputEventMouseButton:
        if event.button_index!=MOUSE_BUTTON_LEFT:return false
        brushing=event.pressed and panel.tool in ["raise","lower"]
        if not event.pressed:return true
    elif event is InputEventMouseMotion:
        if not event.button_mask&MOUSE_BUTTON_MASK_LEFT or panel.tool not in ["raise","lower"]:return false
        if Time.get_ticks_usec()-last_stroke_usec<45000:return true
    else:return false
    apply_pointer(event.position)
    return true

func tick_brush() -> void:
    if not brushing or Time.get_ticks_usec()-last_stroke_usec<80000:return
    if not Input.is_mouse_button_pressed(MOUSE_BUTTON_LEFT):
        brushing=false
        return
    if hall.get_viewport().gui_get_hovered_control()==hall.canvas:apply_pointer(hall.canvas.get_local_mouse_position())

func apply_pointer(point: Vector2) -> void:
    var panel:Control=hall.build_editor.shell_inspector.interior_tools
    if panel.tool in ["fish_idle",""]:return
    var screen:Vector2=point*Vector2(hall.viewport.size)/hall.canvas.size
    var camera:Camera3D=hall.editor_camera
    if panel.tool in ["remove_prop","remove_fish"]:
        var fish:bool=panel.tool=="remove_fish"
        var entries:Array=contents.swimmers if fish else contents.props
        var best:=INF
        var nearest:=-1
        for i in entries.size():
            var e:Dictionary=entries[i]
            var center:Vector3=e.root.global_position
            var extent:float=e.length*.65 if fish else e.root.scale.x*.6
            if not fish:center+=Vector3.UP*extent*.5
            var pixel:=camera.unproject_position(center)
            var side:=camera.unproject_position(center+camera.global_basis.x*extent)
            var distance:=screen.distance_to(pixel)
            if distance<=maxf(18,pixel.distance_to(side)) and distance<best:
                nearest=i
                best=distance
        if nearest>=0:
            var key:="fish" if fish else "props"
            var rows:Array=draft.interior[key].duplicate()
            rows.remove_at(nearest)
            update_bed({key:rows})
            panel.set_tool(panel.tool)
        else:panel.status.text="请点要收回的鱼。" if fish else "请点要移除的布景。"
        return
    var local_inverse:=preview.global_transform.affine_inverse()
    var eye:=local_inverse*camera.project_ray_origin(screen)
    var direction:=local_inverse.basis*camera.project_ray_normal(screen)
    if direction.y>=-.00001:return
    var bed:Dictionary=draft.get("interior",Finished.DEFAULT_BED)
    var box:=Interior.bounds(draft.design)
    var plane_y:=float(bed.depth_cm)*.01
    var hit:=Vector3.ZERO
    for i in 4:
        hit=eye+direction*((plane_y-eye.y)/direction.y)
        plane_y=Interior.floor_y((Vector2(hit.x,hit.z)-box.position)/box.size,bed,draft.design.height)
    panel.use_at(Vector2(hit.x,hit.z))
    last_stroke_usec=Time.get_ticks_usec()
