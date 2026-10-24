extends "res://scripts/aquarium/DecorPlacementLab.gd"
signal apply_requested(state: Dictionary)
signal cancel_requested
var initial_state: Dictionary={}

func _ready() -> void:
    super._ready()
    # The standalone lab assumes a 1440x900 local canvas. Embed that exact
    # workspace, scaled uniformly inside the hall, without resizing its window.
    get_window().content_scale_size=Vector2i(1920,1080)
    size=Vector2(1440,900);position=Vector2(96,0);scale=Vector2.ONE*1.2
    for row in JSON.parse_string(FileAccess.get_file_as_string("res://assets/aquascape-v5/catalog.json")).assets:
        if not row.animated:rock_specs[row.id]=row
    if not initial_state.is_empty():_restore(initial_state)
    # The hall owns persistence. Reuse sculpt/placement behavior, with explicit
    # Apply/Cancel instead of writing the standalone trial save accidentally.
    for b in find_children("*","Button",true,false):
        if b.text in ["保存实验","读取实验"]:b.hide()
    _button(self,"应用并回大厅",Vector2(1148,810),264,func():apply_requested.emit(_state()))
    _button(self,"取消本次修改",Vector2(1148,858),264,func():cancel_requested.emit())
    notice="正在编辑这个展缸 · 应用后回到大厅 · 尺度为大缸的 1/5 工作空间"

func _save_user() -> void:apply_requested.emit(_state())
func _load_user() -> void:notice="由大厅统一保存；取消可放弃本次缸内修改。"

# The parent lab sees process-wide capture arguments; the hall review owns
# capture, so embedded editors must not launch a second review or quit the game.
func _capture(_directory: String) -> void:pass
