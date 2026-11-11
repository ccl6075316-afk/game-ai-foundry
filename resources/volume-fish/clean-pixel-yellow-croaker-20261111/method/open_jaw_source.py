"""Open the original Croaker lower jaw in its existing closed skinned mesh."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

import bpy
import numpy as np

WORK = Path(__file__).resolve().parent
ROOT = WORK.parents[1]
sys.path[:0] = [str(ROOT/"resources/scripts/volume-fish"), str(ROOT/"resources/scripts/volume-fish/portable")]
from export_ordinary_source_owned import export_source
from restore_fin_source_normals import EXACT_NORMAL_ATTRIBUTE, geometry_signature, normal_attribute_signature

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def smooth(t):
    u = np.clip(t,0,1)
    return u*u*(3-2*u)

def deformation(points, amplitude):
    # Coordinates in the editable Blender mesh: X forward, Z dorsal.
    x, _, z = points.T
    # Actual lower and upper welded oral-boundary stations, both sides.
    stations = [.428,.4434,.450,.45829,.46822,.47815,.48845,.498]
    floor = np.interp(x,stations,[-.043,-.03848,-.03606,-.03302,-.02756,-.02160,-.02160,-.02545])
    roof = np.interp(x,stations,[-.041,-.03649,-.03297,-.02855,-.02309,-.01713,-.01042,-.0069])
    lower = 1-smooth((z-floor-.00015)/np.maximum(.001,roof-floor-.00065))
    corner = smooth((x-.429)/.064)
    chin = .80+.20*smooth((z+.077)/.03)
    move = lower*corner*chin
    result=points.copy()
    result[:,0] -= amplitude*.0065*move
    result[:,2] -= amplitude*.0150*move
    return result

def main():
    p=argparse.ArgumentParser()
    p.add_argument("output",type=Path)
    p.add_argument("--amount",type=float,default=1.)
    a=p.parse_args(sys.argv[sys.argv.index("--")+1:])
    out=a.output.resolve()
    assert out.is_relative_to(WORK) and not out.exists()
    source=WORK/"source-r2/fish.blend"
    assert sha(source)=="10a96867faccdbd63bdc96b025fff56e45abb49b708a2ff227026ffbb7bed0ee"
    bpy.ops.wm.open_mainfile(filepath=str(source))
    obj=bpy.data.objects["Closed_body"]
    mesh=obj.data
    attr=mesh.attributes[EXACT_NORMAL_ATTRIBUTE]
    assert geometry_signature(obj)==mesh["foundry_normal_geometry_sha256"]
    assert normal_attribute_signature(obj)==mesh["foundry_exact_normal_sha256"]
    original=np.array([list(v.co) for v in mesh.vertices])
    new=deformation(original,a.amount)
    moved=np.any(new!=original,axis=1)
    assert moved.sum()>20 and np.min(original[moved,0])>.429
    normal_gltf=np.array([list(row.vector) for row in attr.data])
    loop_vid=np.array([loop.vertex_index for loop in mesh.loops])
    affected=moved[loop_vid]
    eps=2.e-6
    ids=loop_vid[affected]
    p=original[ids]
    jacobian=np.stack([(deformation(p+eps*delta,a.amount)-deformation(p-eps*delta,a.amount))/(2*eps)
                       for delta in np.eye(3)],axis=2)
    n=normal_gltf[affected][:,[0,2,1]]*np.array([1,-1,1])
    transformed=np.linalg.solve(jacobian.transpose(0,2,1),n[:,:,None])[:,:,0]
    transformed/=np.linalg.norm(transformed,axis=1)[:,None]
    assert np.isfinite(transformed).all() and np.min(np.linalg.det(jacobian))>.3
    for index in np.flatnonzero(moved):
        mesh.vertices[int(index)].co=new[index]
    normal_gltf[affected]=transformed[:,[0,2,1]]*np.array([1,1,-1])
    mesh.update()
    mesh.normals_split_custom_set((normal_gltf[:,[0,2,1]]*np.array([1,-1,1])).tolist())
    for index in np.flatnonzero(affected):
        attr.data[int(index)].vector=normal_gltf[index]
    mesh.update()
    mesh["foundry_normal_geometry_sha256"]=geometry_signature(obj)
    mesh["foundry_exact_normal_sha256"]=normal_attribute_signature(obj)
    mesh["foundry_normal_provenance_sha256"]=sha(Path(__file__))
    out.mkdir()
    bpy.context.preferences.filepaths.save_version=0
    bpy.ops.wm.save_as_mainfile(filepath=str(out/"fish.blend"))
    result=export_source(out/"fish.glb")
    result.update(input_source_sha256=sha(source),source_sha256=sha(out/"fish.blend"),
      amount=a.amount,moved_vertices=int(moved.sum()),updated_corner_normals=int(affected.sum()),
      minimum_changed_x=float(original[moved,0].min()),maximum_displacement_native=float(np.linalg.norm(new-original,axis=1).max()),
      minimum_jacobian_determinant=float(np.min(np.linalg.det(jacobian))),
      retained="Existing integrated lower jaw and oral floor; fixed upper jaw, actual mouth corners and non-mouth meshes. No material, UV, triangle or rig edits.")
    (out/"source-authoring.validation.json").write_text(json.dumps(result,indent=2)+"\n")

if __name__=="__main__":
    main()
