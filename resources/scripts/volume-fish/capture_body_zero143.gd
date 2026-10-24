extends "capture_body_albedo143.gd"
## Same actual bound mesh/material/compiler path, only new RGB restoration disabled.
func prepare_model(e:Dictionary,_species:String):
    var body=e.model.find_child("Closed_body",true,false) as MeshInstance3D;var original=body.get_active_material(0) as ShaderMaterial;assert(original.shader.code.contains("pectoral142_mask"))
    var mat=original.duplicate() as ShaderMaterial;var source=original.get_shader_parameter("pectoral142_mask")as Texture2D;var im=source.get_image().duplicate();im.fill(Color.BLACK);mat.set_shader_parameter("pectoral142_mask",ImageTexture.create_from_image(im));body.set_surface_override_material(0,mat)
