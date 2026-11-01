extends SceneTree
var p:Dictionary
const PORTABLE=preload("../../runtime/godot/mouth-repair-139/PortableMaterial139.gd")
func read(path:String):return JSON.parse_string(FileAccess.get_file_as_string(path))
func texture(path:String)->ImageTexture:return ImageTexture.create_from_image(Image.load_from_file(path))
func key(v:Vector3)->String:return "%d,%d,%d"%[roundi(v.x*1e6),roundi(v.y*1e6),roundi(v.z*1e6)]
func save_json(path:String,value):
    var f=FileAccess.open(path,FileAccess.WRITE);f.store_string(JSON.stringify(value));f.close()
func _initialize():p=read(OS.get_cmdline_user_args()[0]);call_deferred("run")
func run():
    DirAccess.make_dir_recursive_absolute(p.output)
    var hall=load("res://scripts/aquarium/VolumeFishExhibit.gd").new();root.add_child(hall);hall.set_process(false);hall.paused=true
    hall._select_display(p.species);var e=hall._selected();var body=e.model.find_child("Closed_body",true,false) as MeshInstance3D
    assert(FileAccess.get_sha256(e.model.scene_file_path)==p.model_sha256)
    var before=preload("res://scripts/aquarium/RestSurface114.gd").new().snapshot(body)
    var source_names=read(p.joints);var mapping=[];var actual_names=[]
    for i in body.skin.get_bind_count():
        var name=String(body.skin.get_bind_name(i))
        if name.is_empty():name=e.skeleton.get_bone_name(body.skin.get_bind_bone(i))
        actual_names.append(name)
    for name in source_names:
        var found=-1
        for i in actual_names.size():
            if actual_names[i]==name or actual_names[i]==name+"_2":assert(found<0);found=i
        assert(found>=0);mapping.append(found)
    var raw=read(p.body);var records=read(p.records);var bins={}
    var native_materials=[]
    for si in body.mesh.get_surface_count():native_materials.append(body.get_active_material(si))
    var aligned=ArrayMesh.new()
    for part in raw.parts:
        var aa=[];aa.resize(Mesh.ARRAY_MAX);var vv=PackedVector3Array();var nn=PackedVector3Array();var uv=PackedVector2Array();var jj=PackedInt32Array();var ww=PackedFloat32Array()
        for v in part.vertices:vv.append(Vector3(v[0],v[1],v[2]))
        for v in part.normals:nn.append(Vector3(v[0],v[1],v[2]))
        for v in part.uv:uv.append(Vector2(v[0],v[1]))
        for i in part.joints.size():
            for k in 4:jj.append(mapping[int(part.joints[i][k])]);ww.append(part.weights[i][k])
        aa[Mesh.ARRAY_VERTEX]=vv;aa[Mesh.ARRAY_NORMAL]=nn;aa[Mesh.ARRAY_TEX_UV]=uv;aa[Mesh.ARRAY_BONES]=jj;aa[Mesh.ARRAY_WEIGHTS]=ww;aa[Mesh.ARRAY_INDEX]=PackedInt32Array(part.triangles)
        aligned.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES,aa);aligned.surface_set_material(aligned.get_surface_count()-1,native_materials[int(part.source_surface)])
    body.mesh=aligned
    for si in aligned.get_surface_count():
        body.set_surface_override_material(si,native_materials[si])
        var active=native_materials[si]
        if active is ShaderMaterial and active.shader.code.contains("rest114_vertex_begin"):preload("res://scripts/aquarium/RestSurface114.gd").new().bind(e.model,body,si,active)
    for i in raw.parts[0].vertices.size():
        var v=raw.parts[0].vertices[i];var k=key(Vector3(v[0],v[1],v[2]))
        if not bins.has(k):bins[k]=[]
        bins[k].append(i)
    var a=body.mesh.surface_get_arrays(0);var width=256;var height=ceili(a[Mesh.ARRAY_VERTEX].size()/256.);var im=Image.create(width,height,false,Image.FORMAT_RGBAF);var mapped=0
    for i in a[Mesh.ARRAY_VERTEX].size():
        var v:Vector3=a[Mesh.ARRAY_VERTEX][i];var uv:Vector2=a[Mesh.ARRAY_TEX_UV][i];var choices=bins.get(key(v),[]);var best=-1;var error=INF
        for idx in choices:
            var q=raw.parts[0].uv[idx];var err=uv.distance_to(Vector2(q[0],q[1]))
            if err<error:error=err;best=idx
        assert(best>=0 and error<.00001,"Imported body material correspondence missing")
        var rec=records[best];im.set_pixel(i%width,i/width,Color(rec[0],rec[1],rec[2],rec[3]));mapped+=int(rec[2]>0)
    var mat=body.get_active_material(0).duplicate() as ShaderMaterial;var code:String=mat.shader.code
    assert(not code.contains("mouth146_records"),"Resource builder requires original runtime material, not a previously installed mouth candidate")
    var decl="uniform sampler2D mouth146_records:filter_nearest,repeat_disable;\nuniform sampler2D mouth146_skin:source_color,filter_nearest,repeat_disable;\nuniform ivec2 mouth146_size;\nvarying vec4 mouth146_chart;\n"
    var start=code.find("{",code.find("void vertex()"));code=code.insert(start+1,"mouth146_chart=texelFetch(mouth146_records,ivec2(VERTEX_ID%mouth146_size.x,VERTEX_ID/mouth146_size.x),0);")
    code=code.replace("void vertex()",decl+"void vertex()")
    var parser=load("res://scripts/aquarium/FishEyeOwnership.gd").new();var fragment=parser._stage_braces(code,"fragment")
    code=code.insert(fragment.close,"\nALBEDO=mix(ALBEDO,texture(mouth146_skin,mouth146_chart.xy).rgb,clamp(mouth146_chart.z,0.,1.));\n")
    var shader=Shader.new();shader.code=code;mat.shader=shader;mat.set_shader_parameter("mouth146_records",ImageTexture.create_from_image(im));mat.set_shader_parameter("mouth146_size",Vector2i(width,height));mat.set_shader_parameter("mouth146_skin",texture(p.atlases.skin))
    var next=body.mesh.duplicate() as ArrayMesh
    var frozen={"parts":[]};var binding_names=actual_names
    for si in next.get_surface_count():
        next.surface_set_material(si,PORTABLE.freeze(mat if si==0 else body.get_active_material(si)))
        var aa=next.surface_get_arrays(si);var part={"source_surface":si,"vertices":[],"triangles":Array(aa[Mesh.ARRAY_INDEX]),"joints":[],"weights":[]}
        for i in aa[Mesh.ARRAY_VERTEX].size():
            var v:Vector3=aa[Mesh.ARRAY_VERTEX][i];part.vertices.append([v.x,v.y,v.z]);var jj=[];var ww=[]
            for k in 4:jj.append(aa[Mesh.ARRAY_BONES][i*4+k]);ww.append(aa[Mesh.ARRAY_WEIGHTS][i*4+k])
            part.joints.append(jj);part.weights.append(ww)
        frozen.parts.append(part)
    assert(ResourceSaver.save(next,p.output+"/body.res",ResourceSaver.FLAG_BUNDLE_RESOURCES)==OK)
    body.mesh=next
    save_json(p.output+"/body.frozen.json",frozen);save_json(p.output+"/skinning.validation.json",{"ok":true,"summary":{"skin_joint_names":binding_names,"body_geometry_unchanged_from_frozen_candidate":true,"source_geometry":p.body,"source_geometry_sha256":FileAccess.get_sha256(p.body)}})
    var lips=ArrayMesh.new();var data=read(p.lips)
    for part in data.parts:
        var arrays=[];arrays.resize(Mesh.ARRAY_MAX)
        var vv=PackedVector3Array();var nn=PackedVector3Array();var uv=PackedVector2Array();var uv2=PackedVector2Array();var cc=PackedColorArray();var jj=PackedInt32Array();var ww=PackedFloat32Array()
        for v in part.vertices:vv.append(Vector3(v[0],v[1],v[2]))
        for v in part.normals:nn.append(Vector3(v[0],v[1],v[2]))
        for v in part.uv:uv.append(Vector2(v[0],v[1]))
        for v in part.uv2:uv2.append(Vector2(v[0],v[1]))
        for v in part.colors:cc.append(Color(v[0],v[1],v[2],v[3]))
        for i in part.joints.size():
            for k in 4:jj.append(mapping[int(part.joints[i][k])]);ww.append(part.weights[i][k])
        arrays[Mesh.ARRAY_VERTEX]=vv;arrays[Mesh.ARRAY_NORMAL]=nn;arrays[Mesh.ARRAY_TEX_UV]=uv;arrays[Mesh.ARRAY_TEX_UV2]=uv2;arrays[Mesh.ARRAY_COLOR]=cc;arrays[Mesh.ARRAY_BONES]=jj;arrays[Mesh.ARRAY_WEIGHTS]=ww;arrays[Mesh.ARRAY_INDEX]=PackedInt32Array(part.triangles)
        lips.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES,arrays)
        var lm=ShaderMaterial.new();lm.shader=load(p.shader);lm.set_shader_parameter("original_source",texture(p.source));lm.set_shader_parameter("original_opaque",texture(p.opaque));lm.set_shader_parameter("continuation",texture(p.atlases[part.name]));lips.surface_set_material(lips.get_surface_count()-1,PORTABLE.freeze(lm))
    assert(ResourceSaver.save(lips,p.output+"/lips.res",ResourceSaver.FLAG_BUNDLE_RESOURCES)==OK)
    save_json(p.output+"/build.validation.json",{"ok":true,"original_body_snapshot":before,"mapped_skin_vertices":mapped,"skin_bind_names":actual_names,"native_source_joint_mapping":mapping,"lips_sha256":FileAccess.get_sha256(p.output+"/lips.res"),"body_sha256":FileAccess.get_sha256(p.output+"/body.res"),"scope":"Localized source-aperture body candidate and native raised bands, measured135 continuity, source-only chart skin. Original fin/rig arrays retained; new body geometry, GPU, whole triangle lip contact and visual acceptance checked separately."})
    hall.queue_free();await process_frame;quit()
