"""Validate captured production ShellContentsView TIME frames."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

ROOT=Path(__file__).resolve().parents[4]
BATCH=Path(__file__).parent
GAME=ROOT/"projects/fishing-2d/game"
PHASES=["real-time-a","real-time-b","held-a","held-b","resumed"]

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def pixels(first,second):
    return int(np.count_nonzero(np.any(first!=second,axis=2)))

def run(folder,log,expected):
    report=json.loads((folder/"game-review.json").read_text())
    assert report["ok"],report["failures"]
    log_errors=[line for line in log.read_text().splitlines() if "ERROR" in line]
    assert not log_errors,log_errors
    assert sum(r["rooted"] for r in report["rows"])==expected,report
    contact=Image.new("RGB",(1200,154*len(report["rows"])),"#253840")
    captions=ImageDraw.Draw(contact)
    for index,row in enumerate(report["rows"]):
        key=row["id"]
        frames=[Image.open(folder/f"{key}-{pose}.png").convert("RGB") for pose in PHASES]
        a,b,c,d,e=map(np.asarray,frames)
        row["time_phase_changed_pixels"]=pixels(a,b)
        row["disabled_material_changed_pixels"]=pixels(c,d)
        row["resume_changed_pixels"]=pixels(d,e)
        row["shader_pixel_repeat_after_resume"]=pixels(a,e)
        row["rendered_image_wh_px"]=list(frames[0].size)
        row["model_sha256"]=sha(GAME/row["model"].removeprefix("res://"))
        if row["rooted"]:
            assert row["time_phase_changed_pixels"]>0 and row["resume_changed_pixels"]>0,row
            assert row["native_mount_vertices"]>0 and row["native_max_mount_sway_weight"]==0 and row["native_max_tip_sway_weight"]>0,row
        else:
            assert not row["time_phase_changed_pixels"] and not row["resume_changed_pixels"],row
        assert row["disabled_material_changed_pixels"]==0,row
        for j,(name,image_index) in enumerate([("TIME A",0),("TIME B",1),("SWAY OFF",2),("SWAY RESTORED",4)]):
            frame=frames[image_index]
            frame.thumbnail((300,120))
            contact.paste(frame,(j*300+(300-frame.width)//2,index*154+4))
            captions.text((j*300+15,index*154+128),f"{key} / {name}",fill="#f0f5f4")
    reference=BATCH/"game-rooted-current.jpg"
    contact.save(reference,quality=92)
    report.update(ok=True,visual_scope="Actual Godot production catalogue and ShellContentsView. Centered test shell and isolated viewing camera, with no fish or player save.",
        shader_compiler_log_errors=log_errors,
        contact_sheet=str(reference.relative_to(ROOT)),
        shader_sha256=sha(GAME/report["shader_path"].removeprefix("res://")),
        shader_include_sha256=sha(GAME/"scripts/aquarium/PlantSwayMotion.gdshaderinc"),
        user_acceptance="pending")
    report_path=BATCH/"game-rooted-current.validation.json"
    report_path.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
    print(json.dumps({"ok":True,"rooted":expected,"catalog_count":report["catalog_count"]}))
    return report

if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("captures",type=Path)
    parser.add_argument("log",type=Path)
    parser.add_argument("--expected-rooted",type=int,required=True)
    args=parser.parse_args()
    run(args.captures,args.log,args.expected_rooted)
