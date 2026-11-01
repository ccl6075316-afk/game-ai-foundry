extends "capture_revision140.gd"
## Audit actual final body/eye arrays, rather than pre-repair GLB support.
func jvec(v:Vector3)->Array:return [v.x,v.y,v.z]
func export_part(node:MeshInstance3D,si:int,source_bones:Array)->Dictionary:
    var a=node.mesh.surface_get_arrays(si);var v=[];var n=[];var uv=[];var joints=[];var weights=[]
    var sk=node.get_node(node.skeleton) as Skeleton3D;assert(sk!=null and node.skin!=null)
    var remap=[]
    for bind in node.skin.get_bind_count():
        var name=String(node.skin.get_bind_name(bind))
        if name.is_empty():name=sk.get_bone_name(node.skin.get_bind_bone(bind))
        var index=source_bones.find(name)
        if index<0 and name.ends_with("_2"):index=source_bones.find(name.trim_suffix("_2"))
        remap.append(index)
    for i in a[Mesh.ARRAY_VERTEX].size():
        v.append(jvec(a[Mesh.ARRAY_VERTEX][i]));n.append(jvec(a[Mesh.ARRAY_NORMAL][i]));uv.append([a[Mesh.ARRAY_TEX_UV][i].x,a[Mesh.ARRAY_TEX_UV][i].y])
        var jj=[];var ww=[]
        for k in 4:
            var b=int(a[Mesh.ARRAY_BONES][i*4+k]);var w=float(a[Mesh.ARRAY_WEIGHTS][i*4+k]);assert(remap[b]>=0 or w<.00000001,"Unknown actual skin bone")
            jj.append(maxi(remap[b],0));ww.append(w)
        joints.append(jj);weights.append(ww)
    return {"name":str(node.name)+"/"+str(si),"source_surface":si,"vertices":v,"normals":n,"uv":uv,"joints":joints,"weights":weights,"triangles":Array(a[Mesh.ARRAY_INDEX])}
func run():
    var plan=JSON.parse_string(FileAccess.get_file_as_string(out));out=plan.output;DirAccess.make_dir_recursive_absolute(out)
    hall=load("res://scripts/aquarium/VolumeFishExhibit.gd").new();root.add_child(hall);hall.set_process(false);hall.paused=true;hall.header.hide();hall.footer.hide()
    hall.viewport.size=Vector2i(800,600);hall.viewport.render_target_update_mode=SubViewport.UPDATE_ALWAYS
    ownership=JSON.parse_string(FileAccess.get_file_as_string("res://assets/models/fish/motion/surface-ownership.json")).profiles
    for node in hall.world.find_children("*","MeshInstance3D",true,false):intrinsic[node.get_instance_id()]=node.visible
    var rows=[];var root_out=out
    for spec in plan.species:
        var s:String=spec.species;out=root_out.path_join(s);DirAccess.make_dir_recursive_absolute(out);hall._select_display(s);var e:Dictionary=hall._selected()
        for node in hall.world.find_children("*","MeshInstance3D",true,false):node.visible=e.model.is_ancestor_of(node) and intrinsic.get(node.get_instance_id(),false)
        for node in hall.world.find_children("*","Label3D",true,false):node.hide()
        e.controller.set_motion_controls({"body_amplitude":0.,"fin_amplitude":0.},true);e.controller.set_action("Swim",true);e.controller.step(0.);e.controller.seek(0.)
        var body=e.model.find_child(spec.body,true,false) as MeshInstance3D;assert(body!=null)
        var parts=[]
        for si in body.mesh.get_surface_count():parts.append(export_part(body,si,spec.bones))
        var f=FileAccess.open(out+"/body.json",FileAccess.WRITE);f.store_string(JSON.stringify({"parts":parts,"bones":spec.bones,"body_node":spec.body,"model_sha256":spec.model_sha256}));f.close()
        if spec.has("support_meshes"):
            var support_parts=parts.duplicate()
            for name in spec.support_meshes:
                var overlay=e.model.find_child(name,true,false) as MeshInstance3D;assert(overlay!=null and overlay.transform==body.transform,"Eye support transform differs")
                for si in overlay.mesh.get_surface_count():
                    var material=overlay.get_active_material(si)
                    var alpha:float=material.albedo_color.a if material is StandardMaterial3D else material.get_shader_parameter("tint").a
                    if alpha<=0.:continue # An invisible blend layer is not eye support.
                    var extra=export_part(overlay,si,spec.bones);extra["support_only"]=true;extra["support_alpha"]=alpha;support_parts.append(extra)
            f=FileAccess.open(out+"/support.json",FileAccess.WRITE);f.store_string(JSON.stringify({"parts":support_parts,"bones":spec.bones,"scope":"Actual composed eye support; overlays do not replace the separately closed physical body."}));f.close()
        var eye_nodes=[]
        for node in e.model.find_children("*","MeshInstance3D",true,false):
            if not ("eye"in str(node.name).to_lower()or "iris"in str(node.name).to_lower()or "pupil"in str(node.name).to_lower()):continue
            var a=node.mesh.surface_get_arrays(0);var mat=node.get_active_material(0);var info={"name":str(node.name),"visible":intrinsic[node.get_instance_id()],"aabb_position":jvec(node.get_aabb().position),"aabb_size":jvec(node.get_aabb().size),"vertices":a[Mesh.ARRAY_VERTEX].size(),"transform":var_to_str(node.transform)}
            eye_nodes.append(info)
            if mat is StandardMaterial3D and mat.albedo_texture:
                var im=mat.albedo_texture.get_image();if im.is_compressed():assert(im.decompress()==OK)
                var path=out+"/eye-source.png";assert(im.save_png(path)==OK)
                info["texture_size"]=[im.get_width(),im.get_height()];info["rgba_sha256"]=im.get_data().hex_encode().sha256_text()
        var raw=body.get_active_material(0)
        if raw is ShaderMaterial:
            var tex=raw.get_shader_parameter("source_texture") as Texture2D
            if tex:
                var im=tex.get_image();if im.is_compressed():assert(im.decompress()==OK)
                assert(im.save_png(out+"/body-source.png")==OK)
        var r=region(e);var stored=[]
        for node in e.model.find_children("*","MeshInstance3D",true,false):
            for si in node.mesh.get_surface_count():var mat=node.get_active_material(si);stored.append([node,si,mat,mat])
        for view in {"side":[0.,0.],"oblique":[.65,.2],"front":[PI/2.,0.]}:
            var angles={"side":[0.,0.],"oblique":[.65,.2],"front":[PI/2.,0.]}[view];camera(e,r,true,angles[0],angles[1])
            for mode in ["texture","clay"]:
                set_mode(e,stored,mode);await shot(out+"/head-"+view+"-"+mode+".png")
        set_mode(e,stored,"texture")
        rows.append({"species":s,"body_sha256":FileAccess.get_sha256(out+"/body.json"),"eye_nodes":eye_nodes,"model_sha256":spec.model_sha256,"fin_state":load("res://scripts/aquarium/MouthRepair139.gd").new().fin_state(e.model,s)})
        print("EYE_AUDIT150 ",s," eyes=",eye_nodes.size())
    var f=FileAccess.open(root_out+"/audit.validation.json",FileAccess.WRITE);f.store_string(JSON.stringify({"ok":rows.size()==plan.species.size(),"rows":rows,"scope":"Actual current body and old eye audit; not candidate or user acceptance."}));f.close();hall.queue_free();await process_frame;quit()
