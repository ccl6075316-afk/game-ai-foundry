extends RefCounted
func button(parent: Control,text_value: String,at: Vector2,width: float,callback: Callable) -> Button:
    var b := Button.new();b.text=text_value;b.position=at;b.custom_minimum_size=Vector2(width,38);b.focus_mode=Control.FOCUS_NONE;b.pressed.connect(callback);parent.add_child(b);return b

func label(parent: Control,text_value: String,at: Vector2,size_value:=17) -> Label:
    var l := Label.new();l.text=text_value;l.position=at;l.add_theme_font_size_override("font_size",size_value);parent.add_child(l);return l

func number(parent: Control,at: Vector2,lo: float,hi: float,value: float,callback: Callable) -> SpinBox:
    var n := SpinBox.new();n.position=at;n.size=Vector2(278,36);n.min_value=lo;n.max_value=hi;n.step=.1;n.value=value;n.value_changed.connect(callback);parent.add_child(n);return n

func build(host: Control) -> void:
    var top := ColorRect.new();top.color=Color("102a38");top.size=Vector2(1920,92);host.add_child(top)
    label(top,"潮汐馆  /  透明通道试建",Vector2(26,13),29)
    label(top,"画路线 · 拖控制点 · 调标高 · 自动生成玻璃外壳",Vector2(28,55),17)
    host.mode_button=button(top,"进入通道  Tab",Vector2(650,25),200,host.toggle_mode)
    button(top,"俯视画路线",Vector2(866,25),160,func():host.set_edit_view(true))
    button(top,"立体看外形",Vector2(1040,25),160,func():host.set_edit_view(false))
    button(top,"回到入口  R",Vector2(1215,25),175,host.spawn_player)
    button(top,"保存试建",Vector2(1405,25),150,host.save_route)
    button(top,"读取试建",Vector2(1570,25),150,host.load_route)
    button(top,"重置示例",Vector2(1735,25),150,host.reset_route)
    host.side=ColorRect.new();host.side.position=Vector2(1580,106);host.side.size=Vector2(320,866);host.side.color=Color("153341");host.add_child(host.side)
    var panel: Control=host.side
    label(panel,"通道设计",Vector2(20,13),26)
    button(panel,"画新路线",Vector2(20,61),133,host.start_drawing)
    button(panel,"完成路线",Vector2(165,61),133,host.finish_drawing)
    label(panel,"截面形状",Vector2(20,115))
    host.section_choice=OptionButton.new();host.section_choice.position=Vector2(20,145);host.section_choice.size=Vector2(278,36)
    host.section_choice.add_item("圆筒 · 平整步行面");host.section_choice.add_item("直墙 + 圆拱顶")
    host.section_choice.item_selected.connect(host.section_changed);panel.add_child(host.section_choice)
    label(panel,"步行宽度（米）",Vector2(20,197))
    host.width_spin=number(panel,Vector2(20,226),2,3.6,2.6,host.width_changed)
    label(panel,"地板到顶部净高（米）",Vector2(20,278))
    host.height_spin=number(panel,Vector2(20,307),2.4,3.6,2.8,host.height_changed)
    host.point_label=label(panel,"控制点",Vector2(20,362),19)
    label(panel,"标高 Y（米，连续高度）",Vector2(20,400))
    host.y_spin=number(panel,Vector2(20,429),0,4,1.3,host.point_height_changed)
    label(panel,"位置 X（米）",Vector2(20,481))
    host.x_spin=number(panel,Vector2(20,510),-14,14,-2,host.point_x_changed)
    label(panel,"位置 Z（米）",Vector2(20,562))
    host.z_spin=number(panel,Vector2(20,591),-4,4,1.5,host.point_z_changed)
    button(panel,"插入中间点",Vector2(20,647),133,host.insert_point)
    button(panel,"删除控制点",Vector2(165,647),133,host.delete_point)
    button(panel,"撤销",Vector2(20,698),133,host.undo)
    button(panel,"重做",Vector2(165,698),133,host.redo)
    label(panel,"新路线：两端分别放到缸左右\n的平台区（X ≤－11 / X ≥11）。\n选点拖动改变方向，Y 框调高低。\n绿色可建，红色显示原因。",Vector2(20,754),16)
    var footer := ColorRect.new();footer.position=Vector2(0,991);footer.size=Vector2(1920,89);footer.color=Color("102a38");host.add_child(footer)
    host.status_label=label(footer,"",Vector2(25,12),19)
    label(footer,"编辑：左键选点/拖动，右键环绕，滚轮缩放，Esc 取消草稿  |  行走：WASD，右键看向，Shift 加速，Tab 返回编辑",Vector2(25,51),16)
