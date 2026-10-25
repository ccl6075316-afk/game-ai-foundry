extends "capture_revision140.gd"
## Eye-only actual-runtime views; the ordinary whole-fish camera stays available.
func eye_region(e:Dictionary,r:Dictionary)->Dictionary:
    var points:Array[Vector3]=[]
    for node in e.model.find_children("*","MeshInstance3D",true,false):
        var label=String(node.name).to_lower()
        if not node.is_visible_in_tree() or not ("eye" in label or "iris" in label):continue
        var a=node.get_aabb()
        if a.size.length()<.0001:continue
        var tr=e.model.global_transform.affine_inverse()*node.global_transform
        for i in 8:points.append(tr*a.get_endpoint(i))
    if points.is_empty():return r
    var box=AABB(points[0],Vector3.ZERO)
    for p in points:box=box.expand(p)
    # Keep the center on the fish centerline, so opposite views use one focus.
    var center=box.get_center();center.z=0.
    var extent=maxf(box.size.x,box.size.y)*5.
    r.head=AABB(center-Vector3.ONE*extent*.5,Vector3.ONE*extent)
    r.extent_m=maxf(extent*e.model.global_transform.basis.get_scale().x,e.length_m*.025)
    return r
func run():
    var root_out=out;DirAccess.make_dir_recursive_absolute(out)
    hall=load("res://scripts/aquarium/VolumeFishExhibit.gd").new();root.add_child(hall)
    hall.set_process(false);hall.paused=true;hall.header.hide();hall.footer.hide()
    hall.viewport.size=Vector2i(800,600);hall.viewport.render_target_update_mode=SubViewport.UPDATE_ALWAYS
    ownership=JSON.parse_string(FileAccess.get_file_as_string("res://assets/models/fish/motion/surface-ownership.json")).profiles
    for node in hall.world.find_children("*","MeshInstance3D",true,false):intrinsic[node.get_instance_id()]=node.visible
    for node in hall.world.find_children("*","Label3D",true,false):node.hide()
    if requested.is_empty():requested=hall.SPECIES
    var bindings={}
    for dir in ["res://scripts/aquarium","res://assets/models/fish/motion"]:
        for path in runtime_files(dir):bindings[path]=FileAccess.get_sha256("res://"+path)
    var rows=[]
    for s in requested:
        out=root_out.path_join(s);DirAccess.make_dir_recursive_absolute(out);hall._select_display(s);var e:Dictionary=hall._selected()
        for tank in hall.tanks:tank.root.visible=tank.species==s
        for node in hall.world.find_children("*","MeshInstance3D",true,false):node.visible=e.model.is_ancestor_of(node) and intrinsic[node.get_instance_id()]
        e.controller.set_motion_controls({"body_amplitude":0.,"fin_amplitude":0.},true);assert(e.controller.set_action("Swim",true));e.controller.step(0.);e.controller.seek(0.)
        var broad=region(e);var close=eye_region(e,broad.duplicate(true));var stored=[];var files={}
        for node in e.model.find_children("*","MeshInstance3D",true,false):
            for si in node.mesh.get_surface_count():stored.append([node,si,node.get_surface_override_material(si),node.get_active_material(si)])
        var angles={"side":[0.,0.],"opposite":[PI,0.],"front":[PI/2.,0.],"top":[0.,1.4],"oblique":[.65,.2]}
        for view in angles:
            var a=angles[view]
            for mode in ["texture","clay"]:
                camera(e,close,true,a[0],a[1]);set_mode(e,stored,mode);var path=out+"/eye-%s-%s.png"%[view,mode];await shot(path);files[path]=FileAccess.get_sha256(path)
            set_mode(e,stored,"texture");camera(e,broad,true,a[0],a[1]);var path=out+"/head-%s-texture.png"%view;await shot(path);files[path]=FileAccess.get_sha256(path)
        for view in ["side","oblique"]:
            camera(e,broad,false,angles[view][0],angles[view][1]);var path=out+"/whole-%s.png"%view;await shot(path);files[path]=FileAccess.get_sha256(path)
        # A normal exhibit size view uses the real tank and normal framing.
        for node in hall.world.find_children("*","MeshInstance3D",true,false):node.visible=intrinsic[node.get_instance_id()]
        hall._focus_selected(true,2.6);var game=out+"/game.png";await shot(game);files[game]=FileAccess.get_sha256(game)
        for node in hall.world.find_children("*","MeshInstance3D",true,false):node.visible=e.model.is_ancestor_of(node) and intrinsic[node.get_instance_id()]
        e.controller.set_motion_controls({"body_amplitude":1.,"body_frequency":1.,"fin_amplitude":1.,"fin_frequency":1.},true)
        var actions=["Swim","Turn","Ascend","Dive"];var samples=[]
        for action in actions:
            assert(e.controller.set_action(action,true));e.controller.step(0.)
            for j in 4:
                e.controller.seek([0.,.35,.75,1.25][j]);camera(e,close,true,PI if j==3 else (.65 if j==1 else 0.),.12 if j==1 else 0.)
                var path=out+"/motion-%s-%d.png"%[action,j];await shot(path);files[path]=FileAccess.get_sha256(path);samples.append({"action":action,"time":[0.,.35,.75,1.25][j],"snapshot":e.controller.snapshot()})
        var transitions=[]
        for previous in actions:
            for next in actions:
                if previous==next:continue
                assert(e.controller.set_action(previous,true));e.controller.step(.35);assert(e.controller.set_action(next,false))
                for j in 6:e.controller.step(1./24.)
                assert(e.controller.snapshot().action==next);camera(e,close,true,.65,.2)
                var path=out+"/transition-%s-%s.png"%[previous,next];await shot(path);files[path]=FileAccess.get_sha256(path);transitions.append({"from":previous,"to":next,"snapshot":e.controller.snapshot()})
        rows.append({"species":s,"files":files,"actions":samples,"transitions":transitions,"model_sha256":FileAccess.get_sha256("res://assets/models/fish/"+s+".glb")})
        print("EYE_REVIEW150 ",s)
    for path in bindings:assert(FileAccess.get_sha256("res://"+path)==bindings[path])
    var f=FileAccess.open(root_out+"/capture.validation.json",FileAccess.WRITE);f.store_string(JSON.stringify({"ok":rows.size()==requested.size(),"rows":rows,"runtime_dependencies":bindings,"scope":"Actual game27-fish eye/whole views, four actions and12 directed transitions each; discrete visual evidence, not continuous-time proof or user acceptance."}));f.close()
    hall.queue_free();await process_frame;quit()
