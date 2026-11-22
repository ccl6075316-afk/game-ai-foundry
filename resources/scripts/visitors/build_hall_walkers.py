"""Build the current instanced visitor mesh and atlas for the hall."""
import argparse
import json
import subprocess
import tempfile
from pathlib import Path

import numpy as np
from hall_guest_paint import paint_guest_atlas
from hall_guest_sculpt import HallGuest


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--godot",required=True)
    parser.add_argument("--adult-study", action="store_true",
                        help=argparse.SUPPRESS)
    args=parser.parse_args()
    root=Path(__file__).resolve().parents[3]
    game=root/"projects/fishing-2d/game"
    directory = "visitors-v4"
    out=game/"assets"/directory
    out.mkdir(exist_ok=True)
    profile=json.loads((root/"resources/visitors/visitors-v2.profile.json").read_text())
    rects, size = paint_guest_atlas(profile, out)
    archetype = "adult_male"
    base,second,third=[HallGuest(archetype,i,profile,rects,size).build() for i in range(3)]
    if not (base.parts == second.parts == third.parts):
        raise ValueError("Appearance variants must share the same component topology")
    xyz=np.array(base.positions)
    def delta(form):
        return np.column_stack((np.array(form.positions)-xyz,np.zeros(len(xyz))))
    arrays=dict(vertices=xyz,normals=base.normals,uv=base.uv,uv2=second.uv,
            custom0=base.rig,custom1=delta(second),custom2=delta(third),
            custom3=np.column_stack((third.uv,base.weights,base.regions)))
    # Keep seams, morphs and skinning attributes when sharing GPU vertices.
    stream = np.column_stack(list(arrays.values())).astype(np.float32)
    _, first, indices = np.unique(stream,axis=0,return_index=True,return_inverse=True)
    arrays = {name:np.asarray(values)[first] for name,values in arrays.items()}
    arrays["indices"] = indices
    data={archetype:{key:np.ravel(value).tolist() for key,value in arrays.items()}}
    data[archetype]["contact_shadow"] = "res://scripts/aquarium/visitors/GuestContactShadow.gdshader"
    with tempfile.TemporaryDirectory() as staging:
        path=Path(staging)/"meshes.json"
        path.write_text(json.dumps(data,separators=(",",":")))
        subprocess.run([args.godot,"--headless","--path",str(game),"--script",
                        str(Path(__file__).with_name("save_visitor_meshes_v2.gd")),"--",
                        f"res://assets/{directory}",str(path),
                        "res://scripts/aquarium/visitors/VisitorMaterialV4.gdshader"],check=True)


if __name__=="__main__":
    main()
