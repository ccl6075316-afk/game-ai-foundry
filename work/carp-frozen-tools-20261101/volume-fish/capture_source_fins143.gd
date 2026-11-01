extends "capture_source_fins141.gd"
## Generic exact native source mapping, including historical pixel/unit models.
var source_specs:Dictionary={}
func _initialize():
    var args=OS.get_cmdline_user_args();out=args[0];var scope=JSON.parse_string(FileAccess.get_file_as_string(args[1]))
    for row in scope.records:source_specs[row.species]=row
    requested=Array(args.slice(2)) if args.size()>2 else scope.get("audit_species",source_specs.keys())
    call_deferred("run")
func source_image_for_species(species:String)->Image:
    var p:Dictionary=source_specs[species];assert(FileAccess.get_sha256(p.source)==p.source_sha256);return Image.load_from_file(p.source)
func body_texture_override_for_species(species:String)->String:
    var p:Dictionary=source_specs[species]
    var candidate:Dictionary=p.get("body_texture_override",{})
    if candidate.is_empty():return ""
    assert(FileAccess.get_sha256(candidate.path)==candidate.sha256)
    return String(candidate.path)
func source_camera(e:Dictionary,side:float=1.):
    var spec:Dictionary=source_specs[e.species];var image=source_image_for_species(e.species);var mapping:Dictionary=spec.get("pixel_mapping",{});var ppu:float=float(mapping.get("pixels_per_unit",image.get_width()));var cx:float=float(mapping.get("center_x",image.get_width()/2.));var cy:float=float(mapping.get("center_y",image.get_height()/2.));var center=Vector3((image.get_width()/2.-cx)/ppu,(cy-image.get_height()/2.)/ppu,0.);var tr:Transform3D=e.model.global_transform;var scale:float=tr.basis.get_scale().x
    hall.camera.projection=Camera3D.PROJECTION_ORTHOGONAL;hall.camera.size=image.get_height()/ppu*scale;hall.camera.near=.00001;hall.camera.global_position=tr*(center+Vector3(0,0,2.*image.get_width()/ppu*side));hall.camera.look_at(tr*center,tr.basis.orthonormalized()*Vector3.UP)
