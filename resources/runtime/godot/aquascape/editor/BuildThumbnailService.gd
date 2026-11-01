extends Node
## Existing hall geometry rendered once to memory; never edits layout or assets.
signal preview_ready(id: String,texture: Texture2D)
var complete := false

static func tool_icon(id: String) -> Texture2D:
    var image := Image.create(64,48,false,Image.FORMAT_RGBA8);image.fill(Color("193b46"))
    for y in 48:
        for x in 64:
            var mark := false
            match id:
                "pour":mark=(y>20 and y<41 and abs(x-32)<(y-18)) or (abs(x-32)<2 and y>5 and y<15)
                "remove":mark=(abs(y-15)<2 and abs(x-32)<13) or (y>28 and y<37 and x>15 and x<49)
                "smooth":mark=x>10 and x<54 and (abs(y-15)<2 or abs(y-25)<2 or abs(y-35)<2)
                "paint":mark=(abs(x+y-56)<6 and x>18 and x<44) or (y>34 and y<40 and x>10 and x<54)
                _:mark=x>23 and x<38 and y>7 and y<37 and x-23<(y-5)*.6
            if mark:image.set_pixel(x,y,Color("a8d3d5"))
    return ImageTexture.create_from_image(image)

func generate(host: Control,items: Array) -> void:
    var view := SubViewport.new();view.size=Vector2i(224,144);view.own_world_3d=true;view.render_target_update_mode=SubViewport.UPDATE_ALWAYS;add_child(view)
    var world := Node3D.new();view.add_child(world)
    var lighting=preload("res://scripts/aquarium/HallLighting.gd").new();world.add_child(lighting)
    lighting.environment.environment.background_color=Color("173b48");lighting.environment.environment.ambient_light_energy=.8
    var projection=preload("res://scripts/aquarium/hall/HallSceneProjection.gd").new(world,host.layout_rules,host._surface,lighting)
    projection.wall_paint=host.wall_paint
    var camera := Camera3D.new();camera.projection=Camera3D.PROJECTION_ORTHOGONAL;camera.near=.02;camera.far=80;world.add_child(camera)
    for item in items:
        var data: Dictionary;var node: Node3D;var bounds: AABB
        if item.id=="parcel":
            node=Node3D.new();world.add_child(node);projection._box(node,Vector3(0,-.1,0),Vector3(6,.2,7),host.floor_paint)
            bounds=AABB(Vector3(-3,-.2,-3.5),Vector3(6,.2,7))
        else:
            var kind: String="tank" if item.id.begins_with("tank_") else ("wall" if item.id in ["wall","door"] else item.id)
            data={"id":"thumbnail-"+item.id,"kind":kind,"name":"预览","at":[0.0,0.0],"yaw":0.0,"scale":1.0}
            if kind=="tank":data.scale=[.5,.65,1.0][int(item.id.trim_prefix("tank_"))];data.fish_count=0;data.content={}
            if kind=="wall":data.length=4.0;data.door=item.id=="door"
            var row: Dictionary=projection._create(data);node=row.node;bounds=host._transform(data)*host._bounds(data)
        var center := bounds.get_center();camera.size=maxf(bounds.size.x,bounds.size.y)*1.5+1
        camera.position=center+Vector3(9,7,11);camera.look_at(center)
        for i in 3:await get_tree().process_frame
        await RenderingServer.frame_post_draw
        preview_ready.emit(item.id,ImageTexture.create_from_image(view.get_texture().get_image()))
        node.hide();node.queue_free()
    complete=true;view.queue_free()
