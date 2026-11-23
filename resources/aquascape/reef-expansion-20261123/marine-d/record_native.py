"""Record already viewed native GPU captures and measure phase deltas."""
import argparse
from pathlib import Path
import hashlib
import json

import numpy as np
from PIL import Image,ImageDraw

ROOT=Path(__file__).resolve().parents[4]
BATCH=Path(__file__).parent
CAMERAS=["front","right","back","left","top","bottom","oblique","rear_oblique"]

def pixels(folder,asset,phase):
    return np.asarray(Image.open(folder/f"{asset}-flow-{phase}.png").convert("RGB"))

def delta(a,b):
    return int(np.count_nonzero(np.any(a!=b,axis=2)))

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def dump(path,data):
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n")

def collect(item,gray,material):
    final=BATCH/item
    asset_path=final/"candidate.json"
    proof_path=final/"asset.validation.json"
    row=json.loads(asset_path.read_text())
    proof=json.loads(proof_path.read_text())
    swatches=Image.new("RGB",(1400,832),"#25383c")
    label=ImageDraw.Draw(swatches)
    for ri,source in enumerate([gray,material]):
        for ci,cam in enumerate(CAMERAS):
            file=source/f"{item}-{cam}.png"
            frame=Image.open(file).convert("RGB")
            frame.thumbnail((350,191))
            x,y=ci%4*350,(2*ri+ci//4)*208
            swatches.paste(frame,(x,y))
            label.text((x+14,y+190),("GRAY" if ri==0 else "MATERIAL")+"  "+cam.upper(),fill="white")
    output=final/"godot-views.jpg"
    swatches.save(output,quality=94)
    proof["native"]=dict(version="Godot 4.7.1 stable mono, OpenGL compatibility Apple M4",
                          result="agent reviewed native orthographic + oblique gray and nearest material",
                          contact_sheet=str(output.relative_to(ROOT)),
                          contact_sheet_sha256=sha(output),user_acceptance="pending")
    if "rooted_current" in row:
        zero,quarter,hold,half,end=[pixels(material,item,t) for t in ("0.0","2.5","2.5-repeat","5.0","10.0")]
        quarter_change=delta(zero,quarter)
        pause_change=delta(quarter,hold)
        resume_change=delta(quarter,half)
        loop_change=delta(zero,end)
        assert quarter_change>0 and pause_change==0 and resume_change>0 and loop_change<=20, (quarter_change,pause_change,resume_change,loop_change)
        proof["native"]["multimesh_current"]={"instances":3,"custom_phases":[0,.31,.62],"phase_change_pixels":quarter_change,
                    "held_phase_change_pixels":pause_change,"subsequent_phase_change_pixels":resume_change,
                    "loop_endpoint_change_pixels":loop_change,"fixed_root_validated_in_cpu_sampling":True}
    row["visual_review"]="native candidate viewed; user approval pending"
    row["native_views"]=str(output.relative_to(ROOT))
    dump(asset_path,row)
    dump(proof_path,proof)
    return row

if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gray",required=True,type=Path)
    parser.add_argument("--material",required=True,type=Path)
    parser.add_argument("assets",nargs="+")
    args=parser.parse_args()
    for item in args.assets:
        row=collect(item,args.gray,args.material)
        print(f"{item}: {row['triangles']} triangles, native reviewed")
    candidates=[json.loads(p.read_text()) for p in sorted(BATCH.glob("*/candidate.json"))]
    dump(BATCH/"candidate-catalog.json",{"assets":candidates,"user_acceptance":"pending"})
