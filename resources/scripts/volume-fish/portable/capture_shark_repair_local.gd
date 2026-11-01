extends "ReviewCaptureBase.gd"
## Small actual-GLB local batch, before expensive full gates.
var plan: Dictionary
var destination: String
func _initialize() -> void:
	var a=OS.get_cmdline_user_args();assert(a.size()==2)
	plan=JSON.parse_string(FileAccess.get_file_as_string(a[0]));destination=a[1]
	assert(destination.is_absolute_path() and destination.contains("/experiments/"))
	DirAccess.make_dir_recursive_absolute(destination);root.hide();call_deferred("run")
func run() -> void:
	load_plan=plan
	var holder=SubViewportContainer.new();root.add_child(holder)
	var entry=super._load("local",holder);entries.append(entry)
	entry.view.mesh_lod_threshold=0.;entry.player.stop();entry.skeleton.reset_bone_poses();entry.carrier.transform=Transform3D.IDENTITY
	var views={"side":Vector3(0,0,1),"front":Vector3(1,0,0),"top":Vector3(0,1,.001),"bottom":Vector3(0,-1,.001),"oblique":Vector3(.8,.3,1),"under-oblique":Vector3(.6,-.6,1)}
	for head in [false,true]:
		var focus=Vector3(.645,-.02,0) if head else Vector3.ZERO
		var zoom=.45 if head else 1.8
		for view in views:
			entry.camera.keep_aspect=Camera3D.KEEP_WIDTH;entry.camera.size=zoom;entry.camera.position=focus+views[view].normalized()*2
			entry.camera.look_at(focus,Vector3.UP if absf(views[view].y)<.99 else Vector3(0,0,-1))
			for gray_view in [false,true]:
				_set_gray(gray_view)
				for i in 3:await process_frame;RenderingServer.force_draw(true)
				var label=("head-" if head else "whole-")+view+("-clay" if gray_view else "-texture")
				var path=destination.path_join(label+".png");assert(_view_image(entry).save_png(path)==OK)
				report.captures.append({"label":label,"path":path,"sha256":FileAccess.get_sha256(path)})
				if head and gray_view and plan.get("oral_contrast",false):
					var body: MeshInstance3D=entry.model.find_child(str(plan.body),true,false)
					var saved: Array=[]
					body.material_override=null
					for si in body.mesh.get_surface_count():
						saved.append(body.get_surface_override_material(si))
						var material:=StandardMaterial3D.new();material.albedo_color=Color(.12,.13,.14) if si==1 else Color(.65,.68,.7);material.roughness=1.;material.metallic_specular=0.;body.set_surface_override_material(si,material)
					for i in 3:await process_frame;RenderingServer.force_draw(true)
					var oral_path=destination.path_join("head-"+view+"-oral-clay.png");assert(_view_image(entry).save_png(oral_path)==OK)
					report.captures.append({"label":"head-"+view+"-oral-clay","path":oral_path,"sha256":FileAccess.get_sha256(oral_path),"diagnostic_materials_only":true,"source_skin_gray_oral_surfaces_dark":true})
					for si in saved.size():body.set_surface_override_material(si,saved[si])
	report.merge({"ok":true,"scope":"Local real exported GLB, fixed rest pose, six views each whole/head, texture and clay. No whole-fish acceptance.","model_sha256":plan.model_sha256,"runtime_static_build_calls":0})
	FileAccess.open(destination.path_join("local-capture.validation.json"),FileAccess.WRITE).store_string(JSON.stringify(report,"  ")+"\n");print("LOCAL_SHARK_CAPTURE_OK");quit()
