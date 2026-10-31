extends RefCounted
## Editor chrome/view wiring. Commands and session ownership stay on host.

func _button(parent: Control,text: String,at: Vector2,width: float,callback: Callable) -> Button:
    var button := Button.new();button.text=text;button.position=at;button.custom_minimum_size=Vector2(width,40)
    button.focus_mode=Control.FOCUS_NONE;button.pressed.connect(callback);parent.add_child(button);return button

func _label(parent: Control,text: String,at: Vector2,size:=18) -> Label:
    var label := Label.new();label.text=text;label.position=at;label.add_theme_font_size_override("font_size",size);label.modulate=Color("d3e0d7");parent.add_child(label);return label

func build(host: Control) -> void:
    var header := ColorRect.new();header.name="HallHeader";header.color=Color("102a34");header.position=Vector2.ZERO;header.size=Vector2(1920,96);host.add_child(header)
    _label(header,"潮汐馆  /  可编辑 3D 大厅",Vector2(30,12),28)
    _label(header,"室内建造 · 地块扩建 / 展缸 / 隔墙 · 独立保存",Vector2(32,55),17)
    _label(header,"游客（本次逛馆）",Vector2(520,4),15)
    host.visitor_spin=SpinBox.new();host.visitor_spin.position=Vector2(520,30);host.visitor_spin.size=Vector2(125,36)
    host.visitor_spin.min_value=0;host.visitor_spin.max_value=200;host.visitor_spin.step=1;host.visitor_spin.value=24
    host.visitor_spin.value_changed.connect(func(value):if is_instance_valid(host.visitor_crowd):host.visitor_crowd.set_visitor_count(int(value)))
    header.add_child(host.visitor_spin)
    _button(header,"关闭",Vector2(657,26),90,func():host.visitor_spin.value=0)
    _button(header,"返回海岸",Vector2(1725,26),160,host._request_return)
    host.mode_button=_button(header,"切换逛馆  Tab",Vector2(1000,26),180,func():host._mode(not host.editing))
    _button(header,"展缸水体 / 近景",Vector2(780,26),200,host._open_water_panel)
    _button(header,"保存大厅",Vector2(1195,26),150,host._save_layout)
    _button(header,"读取大厅",Vector2(1360,26),150,func():host._load_layout(host.save_path))
    _button(header,"撤销",Vector2(1525,26),85,host._undo)
    _button(header,"重做",Vector2(1620,26),85,host._redo)
    host.side=ColorRect.new();host.side.color=Color("14313b");host.side.position=Vector2(1570,108);host.side.size=Vector2(330,866);host.add_child(host.side)
    _label(host.side,"大厅建造",Vector2(18,10),24)
    host.parcel_label=_label(host.side,"",Vector2(18,47),17)
    _button(host.side,"＋ 扩建相邻地块  6×7 m",Vector2(18,77),294,func():host._set_tool("parcel"))
    host.tank_size_choice=OptionButton.new();host.tank_size_choice.position=Vector2(18,127);host.tank_size_choice.size=Vector2(294,36)
    for label in ["小缸  3×1.5 m","中缸  3.9×1.95 m","标准缸  6×3 m"]:host.tank_size_choice.add_item(label)
    host.tank_size_choice.select(1);host.side.add_child(host.tank_size_choice)
    _button(host.side,"＋ 放置所选规格展缸",Vector2(18,169),294,func():host._set_tool("tank"))
    host.wall_choice=OptionButton.new();host.wall_choice.position=Vector2(18,218);host.wall_choice.size=Vector2(294,36);host.wall_choice.add_item("实心隔墙  高 3.2 m");host.wall_choice.add_item("门洞隔墙  通道宽 1.2 m")
    host.wall_choice.item_selected.connect(func(index):host.wall_with_door=index==1;host.wall_anchor=null);host.side.add_child(host.wall_choice)
    _button(host.side,"＋ 画隔墙  起点 → 终点",Vector2(18,260),294,func():host._set_tool("wall"))
    _button(host.side,"＋ 长凳",Vector2(18,309),142,func():host._set_tool("bench"))
    _button(host.side,"＋ 展示台",Vector2(170,309),142,func():host._set_tool("plinth"))
    _button(host.side,"选择 / 取消建造  Esc",Vector2(18,358),294,func():host._set_tool(""))
    host.tool_label=_label(host.side,"选择物件进行编辑",Vector2(18,403),17)
    host.detail=_label(host.side,"未选中物件",Vector2(18,434),18)
    _button(host.side,"Q  左转",Vector2(18,490),142,func():host._rotate_selected(-1))
    _button(host.side,"E  右转",Vector2(170,490),142,func():host._rotate_selected(1))
    _label(host.side,"物件倍率 / 隔墙长度（米）",Vector2(18,536),17)
    host.size_spin=SpinBox.new();host.size_spin.position=Vector2(18,562);host.size_spin.custom_minimum_size=Vector2(294,34);host.size_spin.min_value=.4;host.size_spin.max_value=1.3;host.size_spin.step=.05;host.size_spin.value=1
    host.size_spin.value_changed.connect(host._resize_selected);host.side.add_child(host.size_spin)
    _label(host.side,"展示海鱼数量（0～15）",Vector2(18,603),17)
    host.fish_spin=SpinBox.new();host.fish_spin.position=Vector2(18,629);host.fish_spin.custom_minimum_size=Vector2(294,34);host.fish_spin.max_value=15;host.fish_spin.step=1
    host.fish_spin.value_changed.connect(host._fish_count_changed);host.side.add_child(host.fish_spin)
    _button(host.side,"编辑选中缸内的沙子与摆件",Vector2(18,674),294,host._open_content_editor)
    _button(host.side,"删除选中物件",Vector2(18,720),294,host._delete_selected)
    _button(host.side,"更换地砖",Vector2(18,766),142,func():host._change_finish("floor_style"))
    _button(host.side,"更换墙色",Vector2(170,766),142,func():host._change_finish("wall_style"))
    _button(host.side,"俯视全馆",Vector2(18,812),142,func():host.pitch=1.30;host.yaw=.01;host._fit_hall())
    _button(host.side,"斜视全馆",Vector2(170,812),142,func():host.pitch=.83;host.yaw=.48;host._fit_hall())
    var footer := ColorRect.new();footer.color=Color("102a34");footer.position=Vector2(0,995);footer.size=Vector2(1920,85);host.add_child(footer)
    host.status=_label(footer,host.notice,Vector2(30,10),18)
    _label(footer,"编辑：右键环绕 · 中键平移 · 滚轮缩放 · Q/E 转向 · Esc 取消 · Delete 删除   |   Tab 逛馆：WASD 行走 · 右键看向 · Shift 加速",Vector2(30,45),16)
    host.water_panel=load("res://scripts/aquarium/TankWaterPanel.gd").new();host.add_child(host.water_panel);host.water_panel.hide()
    host.water_panel.changed.connect(host._water_changed);host.water_panel.preset_selected.connect(host._water_preset)
    host.water_panel.interaction_started.connect(func():if not host.water_drag:host._remember();host.water_drag=true)
    host.water_panel.interaction_ended.connect(func():host.water_drag=false)
    host.water_panel.inspect_requested.connect(host._start_inspection);host.water_panel.return_requested.connect(host._stop_inspection)
    host.water_panel.next_fish_requested.connect(func():host.inspection_fish+=1;host._start_inspection(false))
