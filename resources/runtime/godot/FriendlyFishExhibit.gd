extends "res://scripts/aquarium/VolumeFishExhibit.gd"
## Finite preview with replay; standard action controls remain available when behavior study is off.
var _friendly_config:Dictionary={}
var _friendly_species:=""
var _friendly_time:=0.0
var _friendly_anchor:=Vector3.ZERO
var _friendly_mode:CheckButton
var _friendly_label:Label
var _behavior=preload("res://scripts/aquarium/FriendlyFishPresentation.gd")
func _ready():
    super._ready()
    _friendly_config=JSON.parse_string(FileAccess.get_file_as_string("res://assets/models/fish/motion/presentation.json")).profiles
    for key in display_buttons:display_buttons[key].visible=_friendly_config.has(key)
    var row=HBoxContainer.new();row.position=Vector2(24,112);row.add_theme_constant_override("separation",12);add_child(row)
    _friendly_mode=CheckButton.new();_friendly_mode.text="亲近感行为试演";_friendly_mode.button_pressed=true;row.add_child(_friendly_mode)
    _friendly_mode.toggled.connect(_friendly_toggled)
    var replay=Button.new();replay.text="重播16秒";row.add_child(replay);replay.pressed.connect(_replay)
    _friendly_label=Label.new();row.add_child(_friendly_label)
    _select_display("crucian");distance=_selected().length_m*1.18;_update_camera()
func _friendly_toggled(enabled:bool):
    _friendly_time=0.;_friendly_species="";paused=false;pause_button.text="暂停"
    var entry:=_selected()
    if not enabled and not entry.is_empty():
        entry.controller.set_motion_controls({"body_amplitude":1.,"body_frequency":1.,"fin_amplitude":1.,"fin_frequency":1.},true)
        entry.controller.seek(0.)
        _friendly_label.text="四动作与滑杆可用 · 体态、眼部保留轻调"
func _process(delta:float):
    var entry:=_selected()
    if _friendly_mode==null or not _friendly_mode.button_pressed or overview or entry.is_empty() or not _friendly_config.has(display):
        super._process(delta);return
    if _friendly_species!=display:
        _friendly_species=display;_friendly_time=0.;_friendly_anchor=entry.origin
        entry.controller.set_action("Swim",true);entry.requested_action="Swim";entry.controller.step(0.)
        entry.controller.set_motion_controls({"body_amplitude":1.,"body_frequency":1.,"fin_amplitude":1.,"fin_frequency":1.},true)
        follow_selected=false;target=_friendly_anchor+Vector3(.075*entry.length_m,float(_friendly_config[display].height_tl)*entry.length_m,0.);yaw=.28;pitch=.1;distance=entry.length_m*1.18;_update_camera();_refresh_buttons()
    if paused:return
    if _friendly_time>=16.:
        _friendly_label.text="试演结束 · 可重播，或关闭试演查看四动作";return
    var state:Dictionary=_behavior.state(_friendly_time,_friendly_config[display],entry.length_m)
    entry.controller.set_motion_controls(state.controls)
    super._process(delta)
    entry.carrier.global_position=_friendly_anchor+state.offset;entry.carrier.rotation=Vector3(0.,state.yaw,0.)
    _friendly_time+=delta;_friendly_label.text=LABELS[display]+" · "+state.label
func _select_action(action:String):
    if _friendly_mode!=null and action!="Swim":
        _friendly_mode.set_pressed_no_signal(false);_friendly_toggled(false)
    super._select_action(action)
func _motion_changed(value:float,key:String):
    if _friendly_mode!=null:
        _friendly_mode.set_pressed_no_signal(false);_friendly_toggled(false)
    super._motion_changed(value,key)
func _motion_preset(preset:String):
    if _friendly_mode!=null:
        _friendly_mode.set_pressed_no_signal(false);_friendly_toggled(false)
    super._motion_preset(preset)
func _replay():
    if _friendly_mode!=null and _friendly_mode.button_pressed:
        _friendly_time=0.;_friendly_species="";paused=false;pause_button.text="暂停"
    else:super._replay()
