"""Author the reef arch's four dimensioned orthographic construction drawings."""

import argparse
import json
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont


def draw_view(spec, key, out):
    raw = spec["profile"]
    side = key in {"left", "right"}
    top = key == "top"
    width, height = 1100, 780
    scale = 164
    center_x, center_y = width // 2, 419
    im = Image.new("RGB", (width, height), "#f2f3ef")
    pen = ImageDraw.Draw(im)
    system_fonts = Path("/System/Library/Fonts/Supplemental")
    def font(name, size):
        path = system_fonts / name
        return ImageFont.truetype(str(path), size) if path.is_file() else ImageFont.load_default(size)

    large = font("Arial Bold.ttf", 35)
    normal = font("Arial.ttf", 20)
    small = font("Arial.ttf", 16)

    def xy(x, y):
        y0 = 645 if side else center_y
        return (round(center_x + x * scale), round(y0 - y * scale))

    def projected(x, y, z):
        if side:
            return xy(-z if key == "right" else z, y)
        return xy(x, -z if top else z)

    extents = [-1.25, 1.25] if side else [-2.5, 2.5]
    for j in range(-5, 6):
        x = xy(j / 2, 0)[0]
        if extents[0] <= j / 2 <= extents[1]:
            pen.line((x, 145, x, 655), fill="#dce1df", width=1)
    for j in range(7) if side else range(-2, 3):
        y = xy(0, j / 2)[1]
        pen.line((xy(extents[0], 0)[0], y, xy(extents[1], 0)[0], y), fill="#dce1df", width=1)
    if side:
        pen.line((xy(-1.55, 0), xy(1.55, 0)), fill="#63757b", width=2)

    strips = []
    for index, a in enumerate(raw):
        b = raw[(index + 1) % len(raw)]
        p = [projected(*a[:3]), projected(a[0], a[1], a[3]),
             projected(b[0], b[1], b[3]), projected(*b[:3])]
        value = (a[0] + b[0]) / 2 if side else (a[1] + b[1]) / 2
        if key in {"left", "bottom"}:
            value *= -1
        strips.append((value, index, p))
    mask = Image.new("1", im.size)
    mask_pen = ImageDraw.Draw(mask)
    for depth, index, polygon in sorted(strips):
        tone = min(208, max(91, int(165 + depth * 11)))
        if (raw[index][1] == 0 and raw[(index + 1) % len(raw)][1] == 0):
            tone = 116 if key == "bottom" else tone
        pen.polygon(polygon, fill=(tone, tone + 6, tone + 8))
        mask_pen.polygon(polygon, fill=1)
    # Outline the full projected shape, with the high ridge and foot locations marked.
    mask = mask.convert("L")
    contour = ImageChops.subtract(mask.filter(ImageFilter.MaxFilter(5)), mask.filter(ImageFilter.MinFilter(3)))
    im.paste("#495b61", (0, 0, width, height), contour)
    if side:
        z_right = "REAR / −Z" if key == "right" else "FRONT / +Z"
        z_left = "FRONT / +Z" if key == "right" else "REAR / −Z"
        pen.text((270, 670), z_left, fill="#42585c", font=small)
        pen.text((730, 670), z_right, fill="#42585c", font=small)
        pen.text((705, 569), "Ground Y = 0", fill="#42585c", font=small)
    else:
        pen.text((302, 187), "REAR / −Z" if top else "FRONT / +Z", fill="#42585c", font=small)
        pen.text((302, 630), "FRONT / +Z" if top else "REAR / −Z", fill="#42585c", font=small)
        if not top:
            for indices, label in [
                (spec["location"]["left_ground_points"], "LEFT FOOT"),
                (spec["location"]["right_ground_points"], "RIGHT FOOT"),
            ]:
                a, b, c = (raw[i] for i in indices)
                poly = [projected(p[0], 0, p[z]) for p, z in [(a, 2), (b, 2), (c, 2), (c, 3), (b, 3), (a, 3)]]
                pen.polygon(poly, fill="#61777e", outline="#354c54", width=3)
                mid = sum(p[0] for p in poly) // len(poly)
                pen.text((mid - 40, 411), label, fill="white", font=small)
            for y in range(276, 566, 18):
                pen.line((center_x, y, center_x, y + 9), fill="#385e68", width=3)
            pen.text((center_x - 88, 591), "Passage axis (+Z / −Z)", fill="#42585c", font=small)

    view_names = {"left": "Left elevation", "right": "Right elevation", "top": "Top plan", "bottom": "Underside"}
    pos = {"left": "−X", "right": "+X", "top": "+Y", "bottom": "−Y"}
    pen.text((43, 37), f"Reef arch  /  {view_names[key]}", fill="#213439", font=large)
    pen.text((44, 91), f"Orthographic · view from {pos[key]} · common meter scale", fill="#475b60", font=normal)
    bar_x, bar_y = 44, 713
    pen.line((bar_x, bar_y, bar_x + scale, bar_y), fill="#344c51", width=3)
    for x in [bar_x, bar_x + scale]:
        pen.line((x, bar_y - 6, x, bar_y + 6), fill="#344c51", width=2)
    pen.text((bar_x, bar_y + 14), "1 m", fill="#42585c", font=small)
    im.save(out / f"arch-{key}.png")
    mask.save(out / f"{key}-outline.png")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("design", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    spec = json.loads(args.design.read_text())
    for view in ("left", "right", "top", "bottom"):
        draw_view(spec, view, args.output)


if __name__ == "__main__":
    main()
