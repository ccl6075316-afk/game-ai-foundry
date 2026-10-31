extends "res://scripts/aquarium/AquascapeCatalogLab.gd"
## Current low-poly stones, wood and artificial decorations, one large object.

func _catalog_entries() -> Array:
    var result: Array=[]
    for path in ["res://assets/aquascape-v5/catalog.json","res://assets/aquascape-decor-v1/catalog.json"]:
        for row in JSON.parse_string(FileAccess.get_file_as_string(path)).assets:
            if row.get("animated",false):continue
            row["animated"]=false
            if not row.has("category"):row["category"]="decor"
            result.append(row)
    return result

func _ready() -> void:
    super._ready()
    DisplayServer.window_set_title("当前低面造景 · 石头、沉木与人工摆件 · 逐件查看")
    _focus(0)
    for i in entries.size():
        if entries[i].id=="dragon_stone":_focus(i);break
    for arg in OS.get_cmdline_user_args():
        if arg.begins_with("--viewer-capture-dir="):call_deferred("_viewer_capture",arg.trim_prefix("--viewer-capture-dir="))

func _build() -> void:
    super._build()
    # Match the material binding actually used inside the tank, including
    # radial jar mapping and the coconut's rear donor.
    for row in entries:
        var paint := ShaderMaterial.new();paint.shader=load("res://scripts/aquarium/DecorThreeViewArtwork.gdshader")
        for view in ["front","right","top"]:paint.set_shader_parameter(view+"_art",load(row.material_dir+"/"+row.id+"-"+view+".png"))
        var box: Dictionary=row.projection_bounds;paint.set_shader_parameter("projection_size",Vector3(box.width,box.height,box.depth));paint.set_shader_parameter("radial_jar",row.id=="terracotta_jar");paint.set_shader_parameter("right_art_on_rear",row.id=="coconut_shelter")
        for mesh in art_nodes[row.id].find_children("*","MeshInstance3D",true,false):
            var originals: Array=[]
            for surface in mesh.mesh.get_surface_count():mesh.set_surface_override_material(surface,paint);originals.append(paint)
            art_originals[mesh]=originals

func _ui() -> void:
    super._ui()
    flow_button.hide()
    for label in find_children("*","Label",true,false):
        if label.text.begins_with("A Q U A S C A P E"):label.text="当前低面造景 · 点击右侧名称，逐件放大查看"
        if label.text.begins_with("拖动旋转"):label.text="拖动旋转 · 滚轮缩放 · ← → 上一件/下一件 · 空格自动旋转 · 1贴图 2灰模 4俯视 5背面"
    for button in find_children("*","Button",true,false):
        if button.text=="水草":button.text="石头与沉木"
        elif button.text=="石木":button.text="人工摆件"
    _mode(0)

func _overview(value: int) -> void:
    selected=-1;page=value
    var shown: int=entries.filter(func(r):return value==0 or (value==1 and r.category!="decor") or (value==2 and r.category=="decor")).size()
    var rows: int=ceili(shown/5.0)
    var visible_index := 0
    for row in entries:
        var visible_row: bool=value==0 or (value==1 and row.category!="decor") or (value==2 and row.category=="decor")
        prop_scales[row.id]=1.0;art_nodes[row.id].scale=Vector3.ONE;art_nodes[row.id].visible=visible_row;labels[row.id].visible=visible_row
        if visible_row:
            art_nodes[row.id].position=Vector3((visible_index%5-2)*.62,.009-bounds[row.id].position.y,(float(visible_index/5)-(rows-1)*.5)*.57)
            labels[row.id].position=art_nodes[row.id].position+Vector3(0,-.004,.22);visible_index+=1
    yaw=.07;pitch=1.02;view_size=maxf(2.85,rows*.63);target=Vector3(.3,.13,0);_camera()
    if is_instance_valid(selection_label):selection_label.text="共%d件：%d种石头、%d种沉木、%d种人工摆件 · 点击右侧逐件看大图" % [entries.size(),entries.filter(func(r):return r.category=="rock").size(),entries.filter(func(r):return r.category=="wood").size(),entries.filter(func(r):return r.category=="decor").size()]

func _focus(index: int) -> void:
    super._focus(index)
    view_size*=.85;_camera()
    var row: Dictionary=entries[selected];var triangles := 0
    for mesh in art_nodes[row.id].find_children("*","MeshInstance3D",true,false):
        for s in mesh.mesh.get_surface_count():
            var arrays: Array=mesh.mesh.surface_get_arrays(s)
            triangles+=(arrays[Mesh.ARRAY_INDEX].size() if arrays[Mesh.ARRAY_INDEX]!=null else arrays[Mesh.ARRAY_VERTEX].size())/3
    selection_label.text="%02d / %02d   %s   ·   %d 三角面   ·   ← → 切换" % [selected+1,entries.size(),row.name_zh,triangles]

func _mode(value: int) -> void:
    super._mode(value)
    if is_instance_valid(mode_label):mode_label.text=["当前模型原画贴图","当前模型灰模","当前模型UV格纹"][value]+" · 1贴图 2灰模 4俯视 5背面"

func _viewer_capture(directory: String) -> void:
    DirAccess.make_dir_recursive_absolute(directory)
    var outputs: Array=[]
    var ids: Array=["rock","shipwreck","terracotta_jar","stone_lantern"]
    if "--capture-all" in OS.get_cmdline_user_args():ids=entries.map(func(r):return r.id)
    if "--capture-new" in OS.get_cmdline_user_args():ids=entries.filter(func(r):return r.get("geometry_revision","")=="budget-first-v11").map(func(r):return r.id)
    for id in ids:
        for i in entries.size():
            if entries[i].id==id:_focus(i);break
        var views: Array=["front","right","back","top","gray"] if "--capture-multiview" in OS.get_cmdline_user_args() else ["front"]
        for view in views:
            _focus(selected);_mode(1 if view=="gray" else 0)
            if view=="right":yaw=PI/2;pitch=.12
            if view=="back":yaw=PI+.25
            if view=="top":yaw=0;pitch=1.49
            _camera()
            for i in 4:await get_tree().process_frame
            await RenderingServer.frame_post_draw
            var path: String=directory+"/"+id+("-"+view if views.size()>1 else "")+".png";get_viewport().get_texture().get_image().save_png(path);outputs.append(path)
    var file := FileAccess.open(directory+"/viewer.validation.json",FileAccess.WRITE);file.store_string(JSON.stringify({"command":"aquascape.current-object-viewer","ok":not outputs.is_empty(),"status":"done","next_action":"human_review","outputs":outputs,"entries":entries.size(),"default":"one large selected object","failures":[]},"  "));file.close();get_tree().quit()
