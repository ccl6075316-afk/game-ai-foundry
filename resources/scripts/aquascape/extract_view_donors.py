"""Native-resolution crops from a visually inspected generated material sheet."""
import argparse
import json
from pathlib import Path
from PIL import Image


def main():
    p=argparse.ArgumentParser();p.add_argument('--input',type=Path,required=True);p.add_argument('--review',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    report=json.loads(a.review.read_text(encoding='utf-8'));im=Image.open(a.input)
    a.output.mkdir(exist_ok=True,parents=True)
    for region in report['regions']:
        x0,y0,x1,y1=region['bbox'];pad=4
        box=(max(0,x0-pad),max(0,y0-pad),min(im.width,x1+pad),min(im.height,y1+pad))
        path=a.output/(region['candidate_view']+'.png');im.crop(box).save(path)
        print(path)


if __name__=='__main__':main()
