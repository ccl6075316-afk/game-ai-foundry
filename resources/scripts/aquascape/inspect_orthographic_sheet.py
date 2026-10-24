"""Measure three generated view regions; camera/identity still require visual review."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
from PIL import Image
from scipy import ndimage as ndi


def main():
    p=argparse.ArgumentParser();p.add_argument('--input',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--layout',choices=['row','single'],default='row');a=p.parse_args()
    image=Image.open(a.input).convert('RGB');rgb=np.asarray(image);h,w=rgb.shape[:2]
    mask=(rgb.min(2)<215)
    if a.layout=='row':mask[:round(h*.17)]=False
    labels,n=ndi.label(mask)
    objects=[]
    for i,box in enumerate(ndi.find_objects(labels),1):
        if box is None:continue
        yy,xx=box;area=int((labels[box]==i).sum())
        if area>w*h*.002:
            objects.append({'bbox':[xx.start,yy.start,xx.stop,yy.stop],'area':area,'width':xx.stop-xx.start,'height':yy.stop-yy.start,'cx':(xx.stop+xx.start)/2})
    expected=3 if a.layout=='row' else 1
    objects=sorted(sorted(objects,key=lambda b:b['area'],reverse=True)[:expected],key=lambda b:b['cx'])
    metrics={}
    if len(objects)==3:
        front,right,top=objects
        metrics={'front_top_length_ratio':top['width']/front['width'],'front_right_height_ratio':right['height']/front['height'],'side_top_depth_ratio':top['height']/right['width']}
        side_scale=front['height']/right['height']
        top_scale=front['width']/top['width']
        d_side=right['width']*side_scale/front['width']
        d_top=top['height']*top_scale/front['width']
        metrics['uniform_scale_to_front']={'front':1.0,'right':side_scale,'top':top_scale}
        metrics['depth_in_front_length_units']={'from_right':d_side,'from_top':d_top}
        metrics['normalized_depth_disagreement']=abs(d_side-d_top)/max(d_side,d_top)
        metrics['note']='Uniform per-view print-scale calibration only. Residual depth disagreement remains independent; no image warp or geometric approval.'
        for row,name in zip(objects,['front','right','top']):row['candidate_view']=name
    data={'command':'aquascape.inspect-orthographic-sheet','status':'done','next_action':'human_review','ok':len(objects)==expected,'input':str(a.input),'sha256':hashlib.sha256(a.input.read_bytes()).hexdigest(),'image_size':[w,h],'regions':objects,'metrics':metrics,'scope':'Region and printed-scale diagnostics only; these do not certify a true camera or consistent object geometry. No image resize or warping.','camera_visual_review':'pending','object_identity_visual_review':'pending','user_acceptance':'pending','failures':[] if len(objects)==expected else ['Could not isolate the expected major connected view regions; inspect manually.']}
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(data,ensure_ascii=False))


if __name__=='__main__':main()
