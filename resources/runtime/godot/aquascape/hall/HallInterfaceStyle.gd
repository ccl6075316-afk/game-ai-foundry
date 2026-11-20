extends RefCounted
## Shared native theme for the hall HUD, catalog and property controls.
const PAPER := Color("#f2f4ee")
const INK := Color("#173c40")
const MUTED := Color("#486264")
const TEAL := Color("#146659")

static func box(fill: Color, stroke: Color, radius: int, x: int, y: int) -> StyleBoxFlat:
    var s := StyleBoxFlat.new()
    s.bg_color=fill
    s.border_color=stroke
    s.set_border_width_all(1)
    s.set_corner_radius_all(radius)
    s.content_margin_left=x
    s.content_margin_right=x
    s.content_margin_top=y
    s.content_margin_bottom=y
    return s

static func create() -> Theme:
    var t := Theme.new()
    t.default_font_size=17
    var panel := box(PAPER, Color("#b2c5bb"), 14, 18, 14)
    panel.shadow_size=4
    panel.shadow_color=Color(0,0,0,.20)
    for type in ["Panel","PanelContainer","PopupMenu"]:
        t.set_stylebox("panel",type,panel)
    var normal := box(Color("#e2e9e2"),Color("#c2d1c7"),7,13,6)
    var hover := box(Color("#cbe7db"),Color("#87b9a7"),7,13,6)
    var active := box(TEAL,TEAL,7,13,6)
    var disabled := box(Color("#e9ede7"),Color("#d8e0d8"),7,13,6)
    for type in ["Button","OptionButton","MenuButton"]:
        for pair in [["normal",normal],["hover",hover],["pressed",active],["hover_pressed",active],["disabled",disabled]]:
            t.set_stylebox(pair[0],type,pair[1])
        for pair in [["font_color",INK],["font_hover_color",INK],["font_pressed_color",Color.WHITE],["font_hover_pressed_color",Color.WHITE],["font_disabled_color",Color("#697b77")]]:
            t.set_color(pair[0],type,pair[1])
    t.set_color("font_color","Label",INK)
    t.set_color("font_color","PopupMenu",INK)
    t.set_color("font_hover_color","PopupMenu",INK)
    t.set_stylebox("hover","PopupMenu",hover)
    t.set_constant("v_separation","PopupMenu",10)
    t.set_color("font_color","CheckBox",INK)
    t.set_color("font_hover_color","CheckBox",TEAL)
    t.set_color("font_pressed_color","CheckBox",TEAL)
    for type in ["LineEdit","TabBar"]:
        t.set_color("font_color",type,INK)
    t.set_color("caret_color","LineEdit",INK)
    t.set_color("font_placeholder_color","LineEdit",MUTED)
    t.set_stylebox("normal","LineEdit",box(Color("#ffffff"),Color("#bbcec4"),7,10,5))
    t.set_stylebox("tab_selected","TabBar",active)
    t.set_stylebox("tab_unselected","TabBar",box(PAPER,PAPER,7,13,6))
    t.set_stylebox("tab_hovered","TabBar",hover)
    t.set_color("font_selected_color","TabBar",Color.WHITE)
    t.set_color("font_unselected_color","TabBar",MUTED)
    t.set_color("font_hovered_color","TabBar",INK)
    t.set_stylebox("slider","HSlider",box(Color("#c5d4c9"),Color("#c5d4c9"),3,0,3))
    for key in ["grabber_area","grabber_area_highlight"]:
        t.set_stylebox(key,"HSlider",box(TEAL,TEAL,3,0,3))
    var knob := Image.create_empty(18,18,false,Image.FORMAT_RGBA8)
    for y in 18:
        for x in 18:
            var distance := Vector2(x-8.5,y-8.5).length()
            if distance<=8.5:
                knob.set_pixel(x,y,TEAL if distance>5.6 else PAPER)
    var grip := ImageTexture.create_from_image(knob)
    for key in ["grabber","grabber_highlight"]:
        t.set_icon(key,"HSlider",grip)
    return t

static func primary(button: Button) -> void:
    var style := box(TEAL,TEAL,8,16,7)
    button.add_theme_stylebox_override("normal",style)
    button.add_theme_color_override("font_color",Color.WHITE)
