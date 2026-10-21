#!/usr/bin/env python3
"""Freeze reviewed eye masks and optional RGB-only native mirrored skin copies."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import numpy as np
from PIL import Image, ImageDraw
ROOT = Path(__file__).resolve().parents[3]
def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
def rgba(path: Path) -> np.ndarray:
    with Image.open(path) as image:
        return np.array(image.convert("RGBA"))
def binary_mask(spec: dict, size: tuple[int,int]) -> Image.Image:
    path = ROOT / spec["path"]
    if sha(path) != spec["sha256"]:
        raise ValueError("Frozen mask SHA mismatch")
    with Image.open(path) as image:
        result = image.convert("L")
    if result.size != size or set(result.tobytes()) != {0,255}:
        raise ValueError("Mask must be nonempty binary at native size")
    return result
def color_copy(original: np.ndarray, mask: np.ndarray, rect: list[float]) -> tuple[np.ndarray,dict]:
    height,width=mask.shape
    x0,y0=np.floor(np.array(rect[:2])*[width,height]).astype(int)
    x1,y1=np.ceil(np.array(rect[2:])*[width,height]).astype(int)
    if not (0<=x0<x1<=width and 0<=y0<y1<=height):
        raise ValueError("Donor rectangle outside original source")
    if mask[y0:y1,x0:x1].any() or (original[y0:y1,x0:x1,3]<243).any():
        raise ValueError("Donor rect must be opaque and outside old-eye cleaning region")
    result=original.copy();ys,xs=np.nonzero(mask);w=x1-x0;h=y1-y0
    xx=(xs-x0)%(2*w);yy=(ys-y0)%(2*h)
    dx=x0+np.where(xx<w,xx,2*w-1-xx);dy=y0+np.where(yy<h,yy,2*h-1-yy)
    result[ys,xs,:3]=original[dy,dx,:3]
    outside_equal=bool(np.array_equal(result[~mask],original[~mask]))
    alpha_equal=bool(np.array_equal(result[:,:,3],original[:,:,3]))
    if not outside_equal or not alpha_equal:
        raise ValueError("RGB copy violated outside-RGBA/whole-alpha identity")
    report={"native_donor_bounds_xyxy_exclusive":[int(x0),int(y0),int(x1),int(y1)],"mask_pixels":int(mask.sum()),
            "changed_rgb_pixels":int(np.any(result[:,:,:3]!=original[:,:,:3],axis=2).sum()),
            "outside_mask_all_rgba_equal":outside_equal,"all_pixels_alpha_equal":alpha_equal,
            "original_decoded_rgba_sha256":hashlib.sha256(original.tobytes()).hexdigest(),
            "copy_decoded_rgba_sha256":hashlib.sha256(result.tobytes()).hexdigest(),
            "method":"native integer mirror repeat, x/y phase relative to donor origin, RGB only"}
    return result,report
def freeze(input_path: Path, output: Path) -> dict:
    profile=json.loads(input_path.read_text(encoding="utf-8"))
    modes=profile.get("allowed_modes")
    if profile.get("schema_version")!=1 or modes != [0,1,2]:
        raise ValueError("Current helper requires schema1 modes [0,1,2]; deprecated [0,2] profiles require their archived helper")
    source=ROOT/profile["source_path"];model=ROOT/profile["model_path"]
    if sha(source)!=profile["source_sha256"] or sha(model)!=profile["model_sha256"]:
        raise ValueError("Frozen source/model SHA mismatch")
    original=rgba(source);size=(original.shape[1],original.shape[0])
    if list(size)!=profile["source_size"]:
        raise ValueError("Source dimensions mismatch")
    polygon=profile["source_polygon"]
    if len(polygon)<3 or any(len(p)!=2 or any(not isinstance(v,int) for v in p) or not(0<=p[0]<size[0] and 0<=p[1]<size[1]) for p in polygon):
        raise ValueError("Reviewed polygon requires native integer coordinates")
    mask=Image.new("L",size,0);ImageDraw.Draw(mask).polygon([tuple(p) for p in polygon],fill=255)
    independent=profile.get("projection",{}).get("kind")=="rest_xy"
    eye=None;opaque=None;copies={};copy_reports={}
    if independent:
        mask=binary_mask(profile["cleaning_mask"],size);eye=binary_mask(profile["eye_layer_mask"],size)
    if 1 in modes:
        if not independent or profile.get("repair",{}).get("kind")!="mirrored_source_rect_rgb":
            raise ValueError("Mode1 requires reviewed independent projection and RGB-only mirror donor")
        opaque_path=model.parents[3]/profile["opaque_skin"]["path"].removeprefix("res://")
        if sha(opaque_path)!=profile["opaque_skin"]["sha256"]:
            raise ValueError("Frozen opaque donor SHA mismatch")
        opaque=rgba(opaque_path)
        if opaque.shape!=original.shape:
            raise ValueError("Opaque dimensions mismatch")
        selected=np.array(mask)==255
        for channel,image in [("source",original),("opaque",opaque)]:
            copies[channel],copy_reports[channel]=color_copy(image,selected,profile["repair"]["donor_rect"])
    count=mask.histogram()[255]
    if count<1:raise ValueError("Empty source cleaning region")
    # All inputs and RGB identities are validated before writing any output.
    output.mkdir(parents=True,exist_ok=True);runtime_dir=profile["runtime_data_directory"].rstrip("/")
    frozen_source=output/"source-runtime.png";mask_path=output/"source-eye-mask.png"
    shutil.copyfile(source,frozen_source);mask.save(mask_path)
    frozen={key:profile[key] for key in ["model_sha256","source_embedded_sha256","source_size","mesh","surface","surface0_vertices","vertex_order_sha256","centers","radii","fade_q","allowed_modes"]}
    frozen.update({"model_path":profile["runtime_model_path"],"source":{"path":runtime_dir+"/source-runtime.png","sha256":sha(frozen_source),"decoded_rgba_sha256":hashlib.sha256(original.tobytes()).hexdigest()},
                   "source_eye_mask":{"path":runtime_dir+"/source-eye-mask.png","sha256":sha(mask_path),"pixels":count},
                   "input_profile_sha256":sha(input_path),"shader_origin":"res://scripts/aquarium/FishBodyOpaque.gdshader"})
    outputs=[frozen_source,mask_path]
    if independent:
        eye_path=output/"eye-layer-mask.png";fallback_mask=output/"fallback-eye-mask.png"
        eye.save(eye_path);shutil.copyfile(mask_path,fallback_mask);outputs += [eye_path,fallback_mask]
        frozen.update({"projection":profile["projection"],"retired_lod":profile["retired_lod"],"opaque_skin":profile["opaque_skin"],
                       "eye_layer_mask":{"path":runtime_dir+"/eye-layer-mask.png","sha256":sha(eye_path),"pixels":eye.histogram()[255]},
                       "fallback_eye_mask":{"path":runtime_dir+"/fallback-eye-mask.png","sha256":sha(fallback_mask),"pixels":count}})
    if copies:
        frozen["repair"]=profile["repair"]
        for channel,image in copies.items():
            path=output/f"clean-{channel}.png";Image.fromarray(image).save(path);outputs.append(path)
            frozen[f"clean_{channel}"]={"path":runtime_dir+f"/clean-{channel}.png","sha256":sha(path)}
            copy_reports[channel]["copy_png_sha256"]=sha(path)
        proof=output/"color-copies.validation.json"
        proof.write_text(json.dumps({"schema_version":1,"ok":True,"command":"fish.eye106-freeze-rgb-copies","stage":"validate","status":"done","next_action":"human_review","inputs":{"source_sha256":sha(source),"opaque_sha256":profile["opaque_skin"]["sha256"],"cleaning_mask_sha256":sha(mask_path)},"outputs":[],"summary":{"source_and_opaque":copy_reports,"accepted":False,"original_files_modified":False},"failures":[]},ensure_ascii=False,indent=2)+"\n")
        outputs.append(proof)
    config_path=output/"eye-ownership-106.json"
    config_path.write_text(json.dumps({"schema_version":1,"profiles":{profile["species"]:frozen}},ensure_ascii=False,indent=2)+"\n");outputs.append(config_path)
    result={"schema_version":1,"ok":True,"command":"fish.freeze-eye-features","stage":"implement","status":"done","next_action":"human_review","inputs":{"profile":str(input_path),"profile_sha256":sha(input_path)},"outputs":[str(p) for p in outputs],
            "summary":{"species":profile["species"],"source_mask_pixels":count,"allowed_modes":modes,"color_repair_created":bool(copies),"accepted":False,"model_sha256":profile["model_sha256"],"source_sha256":sha(frozen_source),"source_eye_mask_sha256":sha(mask_path),"config_sha256":sha(config_path),"rgb_copy_checks":copy_reports},"failures":[]}
    (output/"freeze.validation.json").write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n")
    return result
def main() -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input",required=True,type=Path,help="Reviewed per-species profile JSON")
    parser.add_argument("--output",required=True,type=Path,help="Output directory for frozen copies/masks/metadata")
    args=parser.parse_args()
    try:result=freeze(args.input.resolve(),args.output.resolve())
    except (ValueError,KeyError,OSError,TypeError) as exc:
        result={"schema_version":1,"ok":False,"command":"fish.freeze-eye-features","stage":"implement","status":"failed","next_action":"fix_input","inputs":{"input":str(args.input),"output":str(args.output)},"outputs":[],"summary":{},"failures":[{"kind":"validation","code":"invalid_eye_profile","message":str(exc)}]}
    print(json.dumps(result,ensure_ascii=False,indent=2));return 0 if result["ok"] else 1
if __name__=="__main__":raise SystemExit(main())
