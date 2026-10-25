extends PanelContainer
signal changed(key: String,value: Variant)
signal preset_selected(index: int)
signal interaction_started
signal interaction_ended
signal inspect_requested
signal next_fish_requested
signal return_requested
const Profile=preload("res://scripts/aquarium/TankWaterProfile.gd")
var sliders: Dictionary={}
var labels: Dictionary={}
var enabled_box: CheckBox
var tint_button: ColorPickerButton
var title: Label
var syncing := false

func _ready() -> void:
    position=Vector2(24,130);size=Vector2(310,650)
    var style := StyleBoxFlat.new();style.bg_color=Color("102734");style.border_color=Color("36596d");style.set_border_width_all(1);style.content_margin_left=16;style.content_margin_right=16;style.content_margin_top=14;style.content_margin_bottom=14
    add_theme_stylebox_override("panel",style)
    var list := VBoxContainer.new();list.add_theme_constant_override("separation",9);add_child(list)
    title=Label.new();title.add_theme_font_size_override("font_size",20);list.add_child(title)
    var hint := Label.new();hint.text="逐缸调节 · 保存到大厅布局";hint.add_theme_font_size_override("font_size",14);list.add_child(hint)
    enabled_box=CheckBox.new();enabled_box.text="启用水体效果";list.add_child(enabled_box)
    enabled_box.toggled.connect(func(v):if not syncing:changed.emit("enabled",v))
    var presets := OptionButton.new();presets.add_item("选择水体预设…")
    for preset in Profile.PRESETS:presets.add_item(preset.name)
    list.add_child(presets);presets.item_selected.connect(func(i):
        if i>0:preset_selected.emit(i-1);presets.select(0))
    var tint_row := HBoxContainer.new();list.add_child(tint_row)
    var tint_label := Label.new();tint_label.text="水色";tint_label.size_flags_horizontal=Control.SIZE_EXPAND_FILL;tint_row.add_child(tint_label)
    tint_button=ColorPickerButton.new();tint_button.custom_minimum_size=Vector2(140,30);tint_button.edit_alpha=false;tint_row.add_child(tint_button)
    tint_button.pressed.connect(func():interaction_started.emit())
    tint_button.popup_closed.connect(func():interaction_ended.emit())
    tint_button.color_changed.connect(func(c):if not syncing:changed.emit("tint",c.to_html(false)))
    for row in [["visibility_m","可见距离（米）"],["strength","水色与距离衰减"],["reflection","水面反光"],["ripple","水面微波"],["caustics","水波光纹"]]:
        var key: String=row[0]
        var label := Label.new();labels[key]=label;list.add_child(label)
        label.set_meta("caption",row[1])
        var slider := HSlider.new();slider.min_value=Profile.LIMITS[key][0];slider.max_value=Profile.LIMITS[key][1];slider.step=.5 if key=="visibility_m" else .01;slider.custom_minimum_size.y=22;slider.focus_mode=Control.FOCUS_NONE;list.add_child(slider);sliders[key]=slider
        slider.drag_started.connect(func():interaction_started.emit());slider.drag_ended.connect(func(_v):interaction_ended.emit())
        slider.value_changed.connect(func(value):
            _value_label(key,value)
            if not syncing:changed.emit(key,value))
    for row in [["近景观察选中缸",inspect_requested],["观察下一条鱼",next_fish_requested],["返回大厅视角",return_requested]]:
        var button := Button.new();button.text=row[0];button.custom_minimum_size.y=34;button.focus_mode=Control.FOCUS_NONE;list.add_child(button);button.pressed.connect(func():row[1].emit())
    var help := Label.new();help.text="近景：滚轮推近 / 拉远\n按住右键环绕 · Esc 返回\n仅调整外观，不改变养殖水质";help.add_theme_font_size_override("font_size",14);list.add_child(help)
    var close := Button.new();close.text="收起水体面板";list.add_child(close);close.pressed.connect(hide)

func _value_label(key: String,value: float) -> void:
    labels[key].text="%s  %s" % [labels[key].get_meta("caption"),("%.1f" % value) if key=="visibility_m" else ("%d%%" % roundi(value*100))]

func bind(config: Dictionary,name: String) -> void:
    syncing=true;title.text=name+" · 水体";enabled_box.set_pressed_no_signal(config.enabled);tint_button.color=Color(config.tint)
    for key in sliders:sliders[key].set_value_no_signal(config[key]);_value_label(key,float(config[key]))
    syncing=false
