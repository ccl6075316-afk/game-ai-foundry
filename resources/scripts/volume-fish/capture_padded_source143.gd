extends "capture_source_fins143.gd"
## Extra native pixels outside the original canvas expose translated tail edges.
## No rescaling or registration; original source x maps to x+200 in the proof.
const LEFT_PADDING=200
func original_image(species:String)->Image:return Image.load_from_file(source_specs[species].source)
func source_image_for_species(species:String)->Image:
    var original=original_image(species);var result=Image.create(original.get_width()+LEFT_PADDING,original.get_height(),false,Image.FORMAT_RGBA8);result.fill(Color.TRANSPARENT);result.blit_rect(original,Rect2i(Vector2i.ZERO,original.get_size()),Vector2i(LEFT_PADDING,0));return result
func source_camera(e:Dictionary,side:float=1.):
    var spec:Dictionary=source_specs[e.species];var image=original_image(e.species);var mapping:Dictionary=spec.get("pixel_mapping",{});var ppu:float=float(mapping.get("pixels_per_unit",image.get_width()));var cx:float=float(mapping.get("center_x",image.get_width()/2.));var cy:float=float(mapping.get("center_y",image.get_height()/2.));var center=Vector3((image.get_width()/2.-LEFT_PADDING/2.-cx)/ppu,(cy-image.get_height()/2.)/ppu,0.);var tr:Transform3D=e.model.global_transform;var scale:float=tr.basis.get_scale().x;hall.camera.projection=Camera3D.PROJECTION_ORTHOGONAL;hall.camera.size=image.get_height()/ppu*scale;hall.camera.near=.00001;hall.camera.global_position=tr*(center+Vector3(0,0,2.*image.get_width()/ppu*side));hall.camera.look_at(tr*center,tr.basis.orthonormalized()*Vector3.UP)
