#!/usr/bin/env python3
"""Measure horizontal mesh sweep using the current shader's limb equations.

Uses saved model build inputs, samples all vertices over 720 phases and 9 blend
levels. A 5 mm margin is added to the discrete maximum for runtime navigation.
It is a conservative engineering bound for this animation, not visual approval.
"""
import argparse
import importlib.util
import json
import math
import re
from pathlib import Path

import numpy as np


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--assets",type=Path,required=True)
    parser.add_argument("--shader",type=Path,required=True)
    parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args()
    spec=importlib.util.spec_from_file_location("visitor_builder",Path(__file__).with_name("build_visitors.py"))
    builder=importlib.util.module_from_spec(spec); spec.loader.exec_module(builder)
    shader=args.shader.read_text()
    match=re.search(r"limb < 2\.5 \? (-?[\d.]+) : ([\d.]+)",shader)
    arm,leg=map(float,match.groups())
    knee=float(re.search(r"float bend = max\(0\.0, -swing\) \* blend \* ([\d.]+)",shader).group(1))
    manifest=json.loads((args.assets / "build_manifest.json").read_text())
    assert manifest["builder_sha256"] == builder.digest(Path(__file__).with_name("build_visitors.py")), "Rebuild modified builder before sweep validation"
    assert manifest["shader_sha256"] == builder.digest(args.shader), "Rebuild modified shader before sweep validation"
    measurements={}
    for name,gender,child in [("male","male",False),("female","female",False),("boy","male",True),("girl","female",True)]:
        assert manifest["meshes"][name]["sha256"] == builder.digest(args.assets / f"visitor_{name}.res"), "Saved mesh differs from build manifest"
        mesh=builder.Mesh(gender,manifest["atlas_rects"]).build(child)
        vertices=np.array(mesh["vertices"]).reshape(-1,3)
        ids=np.array(mesh["uv2s"]).reshape(-1,2)[:,0]
        pivots=np.array(mesh["pivots"]).reshape(-1,4)[:,:3]
        maximum=float(np.linalg.norm(vertices[:,[0,2]],axis=1).max())
        worst={"phase":0,"blend":0}
        for phase in np.linspace(0,2*math.pi,720,endpoint=False):
            for blend in np.linspace(0,1,9):
                pos=vertices.copy()
                for limb in range(1,5):
                    selected=ids==limb
                    p=pos[selected].copy(); pivot=pivots[selected]
                    swing=math.sin(phase)*(1 if limb in [1,3] else -1)
                    angle=swing*blend*(arm if limb<3 else leg)
                    if limb>=3:
                        knee_y=pivot[:,1]*.51
                        lower=p[:,1]<knee_y
                        kp=pivot[lower].copy(); kp[:,1]=knee_y[lower]
                        p[lower]=rotate_x(p[lower]-kp,max(0,-swing)*blend*knee)+kp
                    p=rotate_x(p-pivot,angle)+pivot
                    pos[selected]=p
                radius=float(np.linalg.norm(pos[:,[0,2]],axis=1).max())
                if radius>maximum:
                    maximum=radius; worst={"phase":float(phase),"blend":float(blend)}
        # Head yaw pivots xz=(0,0), so it preserves each vertex's horizontal radius.
        measurements[name]={"max_horizontal_radius_m":maximum,"worst_pose":worst,"mesh_sha256":manifest["meshes"][name]["sha256"]}
    maximum=max(v["max_horizontal_radius_m"] for v in measurements.values())
    report={"ok":True,"status":"done","next_action":"human_review","method":"all vertices, shader-equivalent limb transforms, 720 phases x 9 blends; head yaw preserves xz radius",
            "shader_sha256":builder.digest(args.shader),"builder_sha256":builder.digest(Path(__file__).with_name("build_visitors.py")),
            "animation_radians":{"arm":arm,"hip":leg,"knee":knee},"models":measurements,
            "sampled_maximum_m":maximum,"recommended_nav_radius_m":math.ceil((maximum+.005)*100)/100,
            "sampling_margin_m":.005,"failures":[]}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps(report))


def rotate_x(points,angle):
    c,s=math.cos(angle),math.sin(angle)
    out=points.copy()
    out[:,1]=c*points[:,1]-s*points[:,2]
    out[:,2]=s*points[:,1]+c*points[:,2]
    return out


if __name__=="__main__":
    main()
