extends SceneTree
func _initialize():call_deferred("run")
func run():
	var args:=OS.get_cmdline_user_args()
	var vp:=SubViewport.new();vp.size=Vector2i(1536,512);vp.own_world_3d=true;vp.render_target_update_mode=SubViewport.UPDATE_ALWAYS;root.add_child(vp)
	var env:=WorldEnvironment.new();env.environment=Environment.new();env.environment.background_mode=Environment.BG_COLOR;env.environment.background_color=Color.BLACK;vp.add_child(env)
	var doc:=GLTFDocument.new();var state:=GLTFState.new();assert(doc.append_from_file(args[0],state)==OK);var model:=doc.generate_scene(state);vp.add_child(model)
	for ob in model.find_children("*","MeshInstance3D",true,false):
		ob.visible=ob.name=="Reference_head_body"
		if not ob.visible:continue
		for si in ob.mesh.get_surface_count():
			var old:StandardMaterial3D=ob.mesh.surface_get_material(si)
			if old.albedo_texture:
				var sh:=Shader.new();sh.code="shader_type spatial; render_mode unshaded; uniform sampler2D skin:source_color,filter_nearest; varying vec3 p; void vertex(){p=VERTEX;} void fragment(){vec3 c=texture(skin,UV).rgb; float f=smoothstep(.82,1.0,p.x)*(1.-smoothstep(-.23,-.14,p.y)); ALBEDO=mix(c,vec3(.73,.73,.68),f); }"
				var mat:=ShaderMaterial.new();mat.shader=sh;mat.set_shader_parameter("skin",old.albedo_texture);ob.set_surface_override_material(si,mat)
			else:
				var mat:=StandardMaterial3D.new();mat.shading_mode=BaseMaterial3D.SHADING_MODE_UNSHADED;mat.albedo_color=Color(.73,.73,.68);ob.set_surface_override_material(si,mat)
	var cam:=Camera3D.new();cam.projection=Camera3D.PROJECTION_ORTHOGONAL;cam.keep_aspect=Camera3D.KEEP_WIDTH;cam.size=3.5;cam.current=true;vp.add_child(cam)
	var plate:=Image.create(1536,1536,false,Image.FORMAT_RGBA8)
	var views=[]
	for i in range(3):
		var focus:=Vector3(0,-.10,0);var direction:Vector3=[Vector3(0,0,1),Vector3(0,1,0),Vector3(0,-1,0)][i]
		cam.position=focus+direction*5.;cam.look_at(focus,Vector3(0,0,-1) if i>0 else Vector3.UP)
		await process_frame;await RenderingServer.frame_post_draw
		plate.blit_rect(vp.get_texture().get_image(),Rect2i(0,0,1536,512),Vector2i(0,i*512))
		views.append({"name":["side","dorsal","ventral"][i],"focus":[focus.x,focus.y,focus.z],"right":[cam.global_basis.x.x,cam.global_basis.x.y,cam.global_basis.x.z],"up":[cam.global_basis.y.x,cam.global_basis.y.y,cam.global_basis.y.z],"width":3.5,"height":3.5/3.})
	assert(plate.save_png(args[1])==OK)
	FileAccess.open(args[1]+".json",FileAccess.WRITE).store_string(JSON.stringify({"views":views,"model_sha256":FileAccess.get_sha256(args[0]),"purpose":"Full unshaded body color projection guide; all fins/eyes hidden; old oral marks excluded only in reference render. Actual candidate geometry untouched."},"  "))
	quit()
