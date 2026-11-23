"""Finalize native evidence and publish only already rendered and reviewed assets."""
import argparse
import hashlib
import math
from pathlib import Path
import json
import numpy as np
from PIL import Image, ImageDraw

folder=Path(__file__).resolve().parent
work=folder.parents[4]/"work/reef-expansion-20261123/freshwater-e/fern-mat"
p=argparse.ArgumentParser(description=__doc__)
p.add_argument("keys",nargs="+")
args=p.parse_args()
paths=folder/"candidates"
rows={}
out=folder/"candidate-catalog.json"
if out.exists():
    rows={r["id"]:r for r in json.loads(out.read_text())["assets"]}
notes={
    "riverwort_moss_mat":"实看较低且分层，俯视自然分枝。下方附着面连续，单层无枝尖微摆；低端支撑、贴石形态与正背视大致对应。侧面少数三角投影有低面拉伸。",
    "laceleaf_rosette":"原样透孔判定采用叶片材质的 .5 阈值及封闭双壳。实际能看穿，所有叶片跟随各自叶柄，低面近看边缘带像素台阶。",
    "bolbitis_fern_clump":"低横走根茎承接前后分开的羽状叶；每片羽片都有厚度，透过真实片间空隙可见背景。"
}
for key in args.keys:
    base=paths/key
    entry=json.loads((base/"catalog-entry.json").read_text())
    report_path=base/"validation.json"
    report=json.loads(report_path.read_text())
    views=["angle","front","right","rear","left","top","bottom","oblique"]
    cw,ch=183,164
    evidence=Image.new("RGB",(cw*len(views),2*ch+36),(36,57,66))
    draw=ImageDraw.Draw(evidence)
    draw.text((10,9),f"{key} | {entry['triangles']} triangles | Godot actual cold recovery",fill="white")
    for j,style in enumerate(("material","gray")):
        for i,angle in enumerate(views):
            matching=work/"captures"/f"{key}-{style}-{angle}.png"
            im=Image.open(matching).convert("RGB")
            im.thumbnail((cw,ch-24))
            x,y=i*cw+int((cw-im.width)*.5),36+ch*j
            evidence.paste(im,(x,y+16))
            draw.text((i*cw+6,y),f"{style} / {angle}",fill="white")
    path=base/"godot-native-review.jpg"
    evidence.save(path,quality=92,optimize=True)
    entry["native_review"]=str(path)
    rows[key]=entry
    report["native_review"]={"engine":"Godot macOS 4.7.1 Compatibility", "views":views,"static_image":path.name,"observations":notes[key],"filter":"nearest"}
    if "rooted_current" in entry:
        pics={}
        motion=Image.new("RGB",(1280,420),(36,57,66))
        for i,heading in enumerate(("active-0","active-1","hold-0","hold-1")):
            source=work/"captures"/f"{key}-current-{heading}.png"
            im=Image.open(source).convert("RGB")
            pics[heading]=np.array(im)
            im.thumbnail((320,391))
            motion.paste(im,((i*320)+((320-im.width)//2),29))
            ImageDraw.Draw(motion).text((i*320+10,9),heading,fill="white")
        moving=int(np.any(pics["active-0"]!=pics["active-1"],axis=2).sum())
        held=int(np.any(pics["hold-0"]!=pics["hold-1"],axis=2).sum())
        if moving == 0 or held != 0:
            raise ValueError(f"Live motion not shown {key} {moving=} {held=}")
        photo=base/"godot-current-review.jpg"
        motion.save(photo,quality=93,optimize=True)
        report["shader_tests"]["native_runtime"]= {"moving_pixel_count":moving,"held_pixel_count":held,
            "evidence":photo.name,"matches_runtime_shader":True,
            "note":"实际展缸 RootedCurrent 同版 shader，在独立原生场景以 enabled=1/0 对比活动与固定姿态。"}
    report["status"]="native_candidate_pending_user"
    report_path.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
out.write_text(json.dumps({"schema_version":1,"assets":list(rows.values())},ensure_ascii=False,indent=2)+"\n")
print(f"{len(rows)} entries in {out}")
