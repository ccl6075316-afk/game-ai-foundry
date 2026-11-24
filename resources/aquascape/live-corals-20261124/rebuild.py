"""Model two meter-scale living reef colonies from the reviewed R2 six-direction sheets."""
import argparse
from hashlib import sha256
from pathlib import Path
import json
import sys

import numpy as np

release=Path(__file__).resolve().parent
root=release.parents[2]
batch=root/"resources/aquascape/reef-expansion-20261123/corals-c"
sys.path.insert(0,str(batch))
sys.path.insert(0,str(root/"resources/scripts/aquascape"))
import build_colonies as shared
from bake_reef_arch_six_view_art import texture_atlas
from forms import branch, join, oval
from validate_art_models import inspect

def living_elkhorn(grid):
    root_form=oval(grid,(.018,.072,-.008),(.272,.133,.24))
    rising=branch(grid,[((.018,.042,-.017),.145),((-.06,.29,-.018),.125),((-.087,.57,.016),.096),((-.155,.80,-.015),.086)])
    fronds=[
        [((-.05,.245,.02),.077),((-.20,.49,.065),.090),((-.35,.59,.102),.103),((-.499,.70,.14),.071)],
        [((-.27,.53,.083),.084),((-.34,.64,.25),.087),((-.435,.69,.369),.062)],
        [((-.074,.42,-.01),.075),((-.24,.67,-.135),.100),((-.432,.77,-.212),.075)],
        [((-.215,.64,-.111),.079),((-.235,.78,-.29),.095),((-.318,.82,-.418),.063)],
        [((-.115,.65,.007),.081),((-.17,.88,.013),.102),((-.228,.984,.101),.067)],
        [((-.167,.88,.026),.089),((-.041,.944,.11),.092),((.105,.995,.186),.053)],
        [((-.017,.18,-.025),.09),((.17,.34,-.109),.092),((.371,.43,-.135),.088),((.523,.53,-.080),.064)],
        [((.265,.39,-.126),.091),((.339,.55,-.281),.077),((.408,.61,-.402),.051)],
        [((-.067,.475,.012),.078),((.099,.659,.018),.093),((.26,.747,.102),.106),((.422,.798,.201),.074)],
        [((.201,.714,.082),.092),((.227,.754,.236),.088),((.211,.744,.386),.057)],
        [((.073,.197,.051),.101),((.09,.336,.211),.084),((.072,.38,.403),.061)],
        [((-.122,.406,-.037),.083),((-.084,.56,-.23),.087),((.011,.68,-.397),.063)],
    ]
    return join([root_form,rising,*[branch(grid, f, (1.0,.72,.94)) for f in fronds]])

def living_mass(grid):
    lobes=[
      ((-.03,.30,0),(.355,.37,.36)), ((-.205,.49,-.065),(.28,.34,.29)),
      ((-.04,.64,-.10),(.255,.34,.26)), ((.18,.48,.02),(.26,.34,.27)),
      ((.31,.28,-.158),(.19,.29,.234)), ((.14,.31,.261),(.25,.302,.245)),
      ((-.12,.36,.263),(.252,.31,.232)), ((-.322,.243,.168),(.205,.246,.254)),
      ((-.066,.26,-.293),(.291,.26,.211)), ((.09,.47,-.281),(.202,.278,.22)),
      ((-.28,.343,-.227),(.209,.25,.231)), ((.327,.25,.158),(.176,.23,.21)),
      ((.007,.092,.012),(.40,.14,.36)),
    ]
    field=join([oval(grid,c,r) for c,r in lobes])
    x,y,z=grid
    texture=.006*np.cos(42*x+3*np.sin(z*12))*np.cos(32*z+3*y)*np.cos(15*y)+.009*np.sin(15*x-11*z-3*y)
    return field+texture

# These volumes fit the accepted six-direction boards.
FORMS = {
    "live_elkhorn_colony": (living_elkhorn, 958),
    "live_massive_coral_colony": (living_mass, 858),
}
DEFAULT_BLENDER = Path.home() / ".gamefactory/toolchain/blender5/Blender.app/Contents/MacOS/Blender"


def rebuild(row, output, blender):
    key = row["id"]
    dims = row["size_m"]
    form, goal = FORMS[key]
    shared.FORMS[key] = form
    shared.blender = blender
    folder = output / key
    source = root / row["source_art"]
    if sha256(source.read_bytes()).hexdigest() != row["source_sha256"]:
        raise ValueError(f"{key}: six-face source image differs from the release")
    donors, _, spans, _ = shared.donors_from(source, folder, dims)
    vertices, faces, _ = shared.fit_surface(key, dims, goal)
    topology = shared.estimate_topology(vertices, faces)
    assert topology == row["topology"] and len(faces) == row["triangles"] <= row["hard_limit"]
    tris = vertices[faces]
    crosses = np.cross(tris[:,1]-tris[:,0], tris[:,2]-tris[:,0])
    smooth = np.zeros_like(vertices)
    for corner in range(3):
        np.add.at(smooth, faces[:,corner], crosses)
    smooth /= np.maximum(np.linalg.norm(smooth, axis=1, keepdims=True), 1e-10)
    normals = np.repeat(crosses / np.linalg.norm(crosses, axis=1, keepdims=True), 3, axis=0)
    texture, uv, _ = texture_atlas(faces, tris.reshape(-1,3), normals, faces.ravel(), donors, spans, 0., True)
    model = folder / (key + ".glb")
    shared.make_glb(model, row["name_zh"], vertices, faces, uv, texture, smooth)
    assert inspect(model)["ok"]
    if sha256(model.read_bytes()).hexdigest() != row["after_sha256"]:
        raise ValueError(f"{key}: rebuilt model differs from the accepted GLB")
    print(f"{key}: rebuilt GLB matches the release", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--blender", type=Path, default=DEFAULT_BLENDER)
    args = parser.parse_args()
    output = args.output.resolve()
    if output.is_relative_to(root / "projects/fishing-2d"):
        parser.error("Choose an output outside the game project")
    manifest = json.loads((release / "release.json").read_text(encoding="utf-8"))
    for row in manifest["items"]:
        rebuild(row, output, args.blender)


if __name__ == "__main__":
    main()
