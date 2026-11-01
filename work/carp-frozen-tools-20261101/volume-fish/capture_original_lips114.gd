extends SceneTree
## Original source PNG canvas only: no game shaders, cleaning or replacement UV.
class SourcePanel:
    extends Node2D
    var image: Texture2D
    var points: PackedVector2Array
    var crop: Rect2
    func _draw() -> void:
        var font:=ThemeDB.fallback_font
        draw_rect(Rect2(0,0,1800,1000),Color("18212a"))
        var original:=Rect2(25,150,750,750*image.get_height()/image.get_width())
        draw_texture_rect(image,original,false)
        draw_string(font,Vector2(25,65),"Original source PNG (unchanged)",HORIZONTAL_ALIGNMENT_LEFT,-1,30,Color.WHITE)
        draw_string(font,Vector2(820,65),"Lower lip line on original material",HORIZONTAL_ALIGNMENT_LEFT,-1,30,Color.WHITE)
        draw_string(font,Vector2(820,105),"Green: visible lower lip ink edge",HORIZONTAL_ALIGNMENT_LEFT,-1,24,Color.GREEN)
        var factor:=minf(940./crop.size.x,780./crop.size.y)
        var detail:=Rect2(820,150,crop.size.x*factor,crop.size.y*factor)
        draw_texture_rect_region(image,detail,crop)
        var whole_points:=PackedVector2Array()
        var detail_points:=PackedVector2Array()
        for p in points:
            whole_points.append(original.position+p*(original.size.x/image.get_width()))
            detail_points.append(detail.position+(p-crop.position)*factor)
        draw_polyline(whole_points,Color.GREEN,2.,false)
        draw_polyline(detail_points,Color.GREEN,3.,false)
        for i in points.size():
            var p: Vector2=detail_points[i]
            draw_circle(p,3.,Color.GREEN)
            if i%3==0:
                draw_string(font,p+Vector2(0,30 if i%2==0 else -12),"%d,%d"%[points[i].x,points[i].y],HORIZONTAL_ALIGNMENT_LEFT,-1,16,Color.GREEN)
        draw_string(font,Vector2(25,900),"No clean-source, no runtime material, no geometric cut.",HORIZONTAL_ALIGNMENT_LEFT,-1,24,Color.WHITE)
func _initialize() -> void:call_deferred("run")
func run() -> void:
    root.size=Vector2i(1800,1000);root.content_scale_size=Vector2i.ZERO;root.content_scale_mode=Window.CONTENT_SCALE_MODE_DISABLED
    var args:=OS.get_cmdline_user_args()
    var plan: Dictionary=JSON.parse_string(FileAccess.get_file_as_string(args[0]))
    var out: String=args[1];DirAccess.make_dir_recursive_absolute(out)
    var records: Array=[]
    for p in plan.items:
        assert(FileAccess.get_sha256(p.original_image)==p.original_sha256,"Original source changed")
        var image:=Image.new();assert(image.load_png_from_buffer(FileAccess.get_file_as_bytes(p.original_image))==OK)
        var canvas:=SourcePanel.new();canvas.image=ImageTexture.create_from_image(image)
        canvas.texture_filter=CanvasItem.TEXTURE_FILTER_NEAREST
        var points:=PackedVector2Array()
        for point in p.lower_lip_source_px:points.append(Vector2(point[0],point[1]))
        canvas.points=points
        var r: Array=p.mouth_roi;canvas.crop=Rect2(r[0],r[1],r[2],r[3])
        root.add_child(canvas)
        await process_frame;RenderingServer.force_draw();await process_frame;RenderingServer.force_draw()
        var target: String=out+"/"+p.species+"-original-material-lower-lip.png"
        assert(root.get_texture().get_image().save_png(target)==OK)
        records.append({"species":p.species,"original_source":p.original_image,"original_sha256":p.original_sha256,"output":target,"output_sha256":FileAccess.get_sha256(target),"source_size":[image.get_width(),image.get_height()],"line_source_px":p.lower_lip_source_px})
        root.remove_child(canvas);canvas.queue_free();await process_frame
    var f:=FileAccess.open(out+"/original-lip-annotation.validation.json",FileAccess.WRITE)
    f.store_string(JSON.stringify({"schema_version":1,"ok":true,"command":"fish.review114.original-material-lip-lines","status":"done","next_action":"human_review","items":records,"source_modified":false,"production_model_modified":false,"runtime_material_used":false,"script_sha256":FileAccess.get_sha256(get_script().resource_path)},"  ")+"\n")
    quit()
