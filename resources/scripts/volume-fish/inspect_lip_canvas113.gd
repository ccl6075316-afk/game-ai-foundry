extends SceneTree
## Display current textured captures and their exact source texels at native zoom.
class Grid:
    extends Node2D
    var region: Rect2
    var factor: float
    func _draw() -> void:
        var font:=ThemeDB.fallback_font
        for x in range(ceili(region.position.x/10.)*10,int(region.end.x),10):
            var xx:float=(x-region.position.x)*factor
            draw_line(Vector2(xx,0),Vector2(xx,region.size.y*factor),Color(1,0,1,.3),1.)
            draw_string(font,Vector2(xx+2,20),str(x),HORIZONTAL_ALIGNMENT_LEFT,-1,16,Color.MAGENTA)
        for y in range(ceili(region.position.y/10.)*10,int(region.end.y),10):
            var yy:float=(y-region.position.y)*factor
            draw_line(Vector2(0,yy),Vector2(region.size.x*factor,yy),Color(1,0,1,.3),1.)
            draw_string(font,Vector2(2,yy-2),str(y),HORIZONTAL_ALIGNMENT_LEFT,-1,16,Color.MAGENTA)
func _initialize() -> void:
    call_deferred("run")
func run() -> void:
    root.size=Vector2i(1400,900)
    root.content_scale_mode=Window.CONTENT_SCALE_MODE_DISABLED
    root.content_scale_size=Vector2i.ZERO
    var args:=OS.get_cmdline_user_args()
    var image:=Image.new();assert(image.load(args[0])==OK)
    var sprite:=Sprite2D.new();sprite.texture=ImageTexture.create_from_image(image)
    sprite.centered=false;sprite.region_enabled=true
    sprite.region_rect=Rect2(float(args[2]),float(args[3]),float(args[4]),float(args[5]))
    sprite.texture_filter=CanvasItem.TEXTURE_FILTER_NEAREST
    var factor:=minf(1400./sprite.region_rect.size.x,900./sprite.region_rect.size.y)
    sprite.scale=Vector2.ONE*factor
    root.add_child(sprite)
    if "--grid" in args:
        var grid:=Grid.new();grid.region=sprite.region_rect;grid.factor=factor;root.add_child(grid)
    await process_frame;RenderingServer.force_draw()
    await process_frame;RenderingServer.force_draw()
    root.get_texture().get_image().save_png(args[1])
    quit()
