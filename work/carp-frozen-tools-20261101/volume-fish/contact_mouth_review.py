"""Make labelled review sheets from unchanged, equal-size Godot captures."""
import argparse
from pathlib import Path
from PIL import Image, ImageDraw


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    folders = sorted(x for x in a.input.iterdir() if x.is_dir())
    a.output.mkdir(parents=True, exist_ok=True)
    for batch in range(0, len(folders), 5):
        sheet = Image.new('RGB', (1600, 5 * 292), '#14232c')
        draw = ImageDraw.Draw(sheet)
        for row, folder in enumerate(folders[batch:batch + 5]):
            draw.text((8, row * 292 + 3), folder.name, fill='white')
            for col, view in enumerate(['head-side', 'head-oblique', 'head-front', 'head-top']):
                file = folder / (view + '-clay.png')
                if file.exists():
                    im = Image.open(file).convert('RGB')
                    assert im.size == (1200, 800)
                    sheet.paste(im.resize((400, 267), Image.Resampling.LANCZOS), (col * 400, row * 292 + 25))
        sheet.save(a.output / f'clay-{batch//5 + 1:02}.jpg', quality=94)


if __name__ == '__main__':
    main()
