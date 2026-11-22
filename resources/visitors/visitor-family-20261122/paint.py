"""Fit each expression to the C face layout and extend the atlas with clothing."""
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent
BASE = ROOT / "face-layout.png"
PALETTES = {
    "man": ("3C3431", "654D3A", "4B3D33", "302B2C", "638B7B", "ABC2A4", "41665B", "536071", "86654E", "CEC0A3"),
    "child": ("713F2C", "9D6241", "865039", "623829", "E9AD53", "FFF0CA", "C58449", "63879B", "427988", "EDD9AF"),
    "elder": ("C6C7BD", "E8E7D9", "D8D9D0", "A6AA9F", "A47E91", "C5A8B3", "75596D", "685D65", "70514B", "B69B87"),
}

# Keep the eye, nose and mouth centers in the C layout. Each source has its own
# shapes and aspect ratios, including a raised brow and the child's open mouth.
# Each entry gives source bounds, UV center and target size in atlas pixels.
EXPRESSIONS = {
    "man": [
        ((69,269,690,392), (147,157), (112,21)), ((860,152,1453,377), (365,147), (108,36)),
        ((110,450,654,657), (147,232), (108,46)), ((877,450,1424,657), (365,232), (108,46)),
        ((689,602,843,755), (256,295), (41,33)), ((558,789,988,892), (258,355), (91,21)),
    ],
    "child": [
        ((388,117,633,246), (149,139), (66,34)), ((902,117,1142,246), (363,139), (66,34)),
        ((317,285,657,626), (149,230), (100,101)), ((865,285,1208,626), (363,230), (100,101)),
        ((694,536,826,622), (256,294), (39,25)), ((645,664,872,917), (256,355), (58,65)),
        ((312,645,460,758), (112,303), (42,33)), ((1064,643,1212,756), (400,303), (42,33)),
    ],
    "elder": [
        ((348,206,636,328), (148,157), (79,30)), ((901,206,1187,328), (364,157), (79,30)),
        ((324,390,644,522), (148,236), (83,32)), ((890,389,1208,521), (364,236), (83,32)),
        ((228,460,315,502), (68,244), (20,8)), ((1218,459,1307,500), (444,244), (20,8)),
        ((690,535,840,619), (256,293), (47,26)), ((544,653,984,895), (256,355), (111,51)),
    ],
}


def paint(name, palette):
    base = Image.open(BASE).convert("RGB")
    atlas = Image.new("RGB", (1024, 512))
    atlas.paste(base)
    atlas.paste(base.getpixel((256,30)), (0,0,512,480))
    source = Image.open(ROOT / "expressions" / (name + ".png")).convert("RGBA")
    for box, (cx,cy), (w,h) in EXPRESSIONS[name]:
        mark = source.crop(box).resize((w,h), Image.Resampling.LANCZOS)
        atlas.paste(mark, (cx-w//2,cy-h//2), mark.getchannel("A"))
    pen = ImageDraw.Draw(atlas)
    for slot, color in enumerate(palette, start=3):
        pen.rectangle((38*slot, 480, 38*slot+37, 511), fill="#" + color)
    shirt, trim, seam = ["#" + value for value in palette[4:7]]
    panel = Image.new("RGB", (512, 512), shirt)
    cloth = ImageDraw.Draw(panel)
    if name == "man":
        cloth.polygon([(185,0),(327,0),(256,93)],fill=seam)
        cloth.line([(256,49),(256,115)],fill=seam,width=6)
        cloth.polygon([(304,151),(360,151),(357,193),(333,206),(305,194)],fill=seam)
        cloth.line((308,155,355,155),fill=trim,width=5)
    elif name == "child":
        for y in (181,220):
            cloth.rectangle((0,y,511,y+15),fill=trim)
    else:
        cloth.polygon([(173,0),(339,0),(256,177)],fill="#EFE0C8")
        cloth.line([(174,0),(256,177),(338,0)],fill=seam,width=9)
        cloth.line((256,178,256,511),fill=seam,width=6)
        for y in (216,293,369,446):
            cloth.ellipse((251,y,260,y+9),fill="#DFC6AA")
        for left,right in ((85,210),(302,427)):
            pen.rounded_rectangle((left,194,right,278),radius=34,outline="#795E50",width=6)
        pen.arc((202,219,310,259),191,349,fill="#795E50",width=6)
    atlas.paste(panel,(512,0))
    atlas.save(ROOT / (name + ".png"), optimize=True)


if __name__ == "__main__":
    for visitor, palette in PALETTES.items():
        paint(visitor,palette)
