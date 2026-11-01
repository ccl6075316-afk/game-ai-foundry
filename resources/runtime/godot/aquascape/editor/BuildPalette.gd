extends PanelContainer
## Bottom asset browser only; selected-object tools belong to BuildInspector.
signal chosen(id: String)
signal drag_started(id: String)
signal drag_finished(placed: bool)
var scope := ""
var entries: Array=[]
var category: OptionButton
var tabs: TabBar
var search: LineEdit
var cards: HBoxContainer
var hint: Label
var selected_asset := ""

func setup(title_value: String,items: Array,scope_value: String) -> void:
    scope=scope_value;entries=items.duplicate(true)
    var compact := scope=="tank"
    var style := StyleBoxFlat.new();style.bg_color=Color("122e39");style.border_color=Color("355563");style.set_border_width_all(1)
    style.content_margin_left=14;style.content_margin_right=14;style.content_margin_top=8;style.content_margin_bottom=6;add_theme_stylebox_override("panel",style)
    var body := VBoxContainer.new();body.add_theme_constant_override("separation",5);add_child(body)
    var header := HBoxContainer.new();header.add_theme_constant_override("separation",16);body.add_child(header)
    var title := Label.new();title.text=title_value;title.add_theme_font_size_override("font_size",19 if compact else 22);header.add_child(title)
    category=OptionButton.new();category.add_item("全部");category.hide();header.add_child(category)
    tabs=TabBar.new();tabs.tab_alignment=TabBar.ALIGNMENT_LEFT;tabs.size_flags_horizontal=Control.SIZE_EXPAND_FILL
    tabs.add_theme_font_size_override("font_size",15 if compact else 17);tabs.add_tab("全部");header.add_child(tabs)
    var groups: Array=[]
    for item in entries:
        if item.category not in groups:groups.append(item.category);category.add_item(item.category);tabs.add_tab(item.category)
    tabs.tab_changed.connect(func(index):category.select(index);refresh())
    category.item_selected.connect(func(index):tabs.current_tab=index;refresh())
    search=LineEdit.new();search.placeholder_text="搜索物件";search.custom_minimum_size.x=200 if compact else 260
    header.add_child(search);search.text_changed.connect(func(_s):refresh())
    var scroll := ScrollContainer.new();scroll.size_flags_vertical=Control.SIZE_EXPAND_FILL;body.add_child(scroll)
    scroll.vertical_scroll_mode=ScrollContainer.SCROLL_MODE_DISABLED
    cards=HBoxContainer.new();cards.add_theme_constant_override("separation",9);scroll.add_child(cards)
    hint=Label.new();hint.text="拖出卡片放入场景，或点击卡片后放置。选中物件后，在右侧调整属性。"
    hint.add_theme_font_size_override("font_size",13 if compact else 15);body.add_child(hint)
    refresh()

func set_preview(id: String,texture: Texture2D) -> void:
    for item in entries:
        if item.id==id:item.preview=texture
    for card in cards.get_children():
        if card.asset.id==id:card.preview.texture=texture

func refresh() -> void:
    for child in cards.get_children():cards.remove_child(child);child.queue_free()
    for item in entries:
        if category.selected>0 and category.get_item_text(category.selected)!=item.category:continue
        if not search.text.is_empty() and not item.label.to_lower().contains(search.text.to_lower()):continue
        var b=preload("res://scripts/aquarium/editor/BuildAssetCard.gd").new()
        b.asset=item;b.owner_palette=self;b.setup_content(scope=="tank")
        b.tooltip_text=item.label+" · "+item.category+"\n拖入场景放置";b.focus_mode=Control.FOCUS_NONE
        b.toggle_mode=true;b.button_pressed=item.id==selected_asset
        b.pressed.connect(func():selected_asset=item.id;chosen.emit(item.id));cards.add_child(b)
