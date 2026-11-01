extends Button
var asset: Dictionary={}
var owner_palette: Control
var payload: Dictionary={}
var preview: TextureRect

func setup_content(compact: bool) -> void:
    custom_minimum_size=Vector2(136,98) if compact else Vector2(164,130)
    var body := VBoxContainer.new();body.mouse_filter=Control.MOUSE_FILTER_IGNORE
    add_child(body);body.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
    body.offset_left=7;body.offset_right=-7;body.offset_top=6;body.offset_bottom=-5
    preview=TextureRect.new();preview.custom_minimum_size.y=62 if compact else 90
    preview.expand_mode=TextureRect.EXPAND_IGNORE_SIZE;preview.stretch_mode=TextureRect.STRETCH_KEEP_ASPECT_CENTERED
    preview.texture_filter=CanvasItem.TEXTURE_FILTER_NEAREST;preview.mouse_filter=Control.MOUSE_FILTER_IGNORE
    preview.texture=asset.get("preview");body.add_child(preview)
    var label := Label.new();label.text=asset.label;label.horizontal_alignment=HORIZONTAL_ALIGNMENT_CENTER
    label.text_overrun_behavior=TextServer.OVERRUN_TRIM_ELLIPSIS;label.add_theme_font_size_override("font_size",14 if compact else 16)
    label.mouse_filter=Control.MOUSE_FILTER_IGNORE;body.add_child(label)

func _get_drag_data(_at: Vector2) -> Variant:
    var drag_preview := VBoxContainer.new()
    var picture := TextureRect.new();picture.texture=preview.texture;picture.custom_minimum_size=Vector2(120,82)
    picture.expand_mode=TextureRect.EXPAND_IGNORE_SIZE;picture.stretch_mode=TextureRect.STRETCH_KEEP_ASPECT_CENTERED;drag_preview.add_child(picture)
    var label := Label.new();label.text="＋ "+str(asset.label);drag_preview.add_child(label);set_drag_preview(drag_preview)
    payload={"build_asset":asset.id,"scope":owner_palette.scope,"placed":false}
    owner_palette.drag_started.emit(asset.id)
    return payload

func _notification(what: int) -> void:
    if what==NOTIFICATION_DRAG_END and is_instance_valid(owner_palette) and not payload.is_empty():
        owner_palette.drag_finished.emit(payload.get("placed",false));payload={}
