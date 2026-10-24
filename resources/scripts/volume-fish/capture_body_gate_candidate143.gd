extends "capture_body_albedo143.gd"
## Preview a single RGB candidate without mutating current frozen configurations.
func prepare_model(e:Dictionary,species:String):
    assert(species=="yellow_croaker");var path=OS.get_environment("FOUNDRY_BODY_GATE143_CANDIDATE");assert(not path.is_empty());var mesh=load(path) as ArrayMesh;assert(mesh!=null);var body=e.model.find_child("Closed_body",true,false) as MeshInstance3D;body.mesh=mesh
    for si in mesh.get_surface_count():body.set_surface_override_material(si,null)
