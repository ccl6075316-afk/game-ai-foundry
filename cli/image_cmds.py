"""Image processing subcommands for gamefactory CLI."""

from __future__ import annotations

import sys
from pathlib import Path

import click
import cv2
import numpy as np


def _remove_bg(img_bytes: bytes) -> bytes:
    """Lazy-import rembg to avoid loading the model at CLI startup."""
    from rembg import remove
    return remove(img_bytes)


@click.command("slice")
@click.option("--input", "input_path", required=True, type=click.Path(exists=True, path_type=Path),
              help="Source image file.")
@click.option("--mode", type=click.Choice(["grid", "auto"]), default="auto",
              help="Slicing strategy.")
@click.option("--rows", type=int, default=4, help="Grid rows (grid mode only).")
@click.option("--cols", type=int, default=4, help="Grid columns (grid mode only).")
@click.option("--output-dir", type=click.Path(path_type=Path), default=None,
              help="Output directory (default: same as input).")
def slice_cmd(input_path: Path, mode: str, rows: int, cols: int, output_dir: Path | None) -> None:
    """Slice an image into individual sprites."""
    img = cv2.imread(str(input_path))
    if img is None:
        click.echo(f"Error: cannot read image {input_path}", err=True)
        sys.exit(1)

    out_dir = output_dir or input_path.parent
    out_dir.mkdir(parents=True, exist_ok=True)
    base = input_path.stem

    if mode == "grid":
        h, w = img.shape[:2]
        tile_h, tile_w = h // rows, w // cols
        count = 0
        for r in range(rows):
            for c in range(cols):
                tile = img[r * tile_h:(r + 1) * tile_h, c * tile_w:(c + 1) * tile_w]
                out_path = out_dir / f"{base}_{count}.png"
                cv2.imwrite(str(out_path), tile)
                click.echo(str(out_path.resolve()))
                count += 1
    else:  # auto
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        _, thresh = cv2.threshold(gray, 240, 255, cv2.THRESH_BINARY_INV)
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        # Filter tiny contours (noise) and sort left-to-right, top-to-bottom
        contours = [c for c in contours if cv2.contourArea(c) > 50]
        contours = sorted(contours, key=lambda c: (cv2.boundingRect(c)[1] // 50, cv2.boundingRect(c)[0]))

        for i, cnt in enumerate(contours):
            x, y, w, h = cv2.boundingRect(cnt)
            # Add small padding
            pad = 2
            x = max(0, x - pad)
            y = max(0, y - pad)
            w = min(img.shape[1] - x, w + pad * 2)
            h = min(img.shape[0] - y, h + pad * 2)
            sprite = img[y:y + h, x:x + w]
            out_path = out_dir / f"{base}_{i}.png"
            cv2.imwrite(str(out_path), sprite)
            click.echo(str(out_path.resolve()))


@click.command("remove-bg")
@click.option("--input", "input_path", required=True, type=click.Path(exists=True, path_type=Path),
              help="Source image file.")
@click.option("--output", "output_path", required=True, type=click.Path(path_type=Path),
              help="Output file path.")
def remove_bg_cmd(input_path: Path, output_path: Path) -> None:
    """Remove background from an image."""
    try:
        img = input_path.read_bytes()
        result = _remove_bg(img)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(result)
        click.echo(str(output_path.resolve()))
    except Exception as e:
        click.echo(f"Error removing background: {e}", err=True)
        sys.exit(1)


@click.command("resize")
@click.option("--input", "input_path", required=True, type=click.Path(exists=True, path_type=Path),
              help="Source image or directory.")
@click.option("--width", type=int, required=True, help="Target width.")
@click.option("--height", type=int, required=True, help="Target height.")
@click.option("--output-dir", type=click.Path(path_type=Path), default=None,
              help="Output directory (default: same as input).")
def resize_cmd(input_path: Path, width: int, height: int, output_dir: Path | None) -> None:
    """Resize image(s) to target dimensions."""
    files: list[Path] = []
    if input_path.is_dir():
        files = sorted(input_path.glob("*.png")) + sorted(input_path.glob("*.jpg"))
    else:
        files = [input_path]

    out_dir = output_dir or (input_path if input_path.is_dir() else input_path.parent)
    out_dir.mkdir(parents=True, exist_ok=True)

    for f in files:
        img = cv2.imread(str(f))
        if img is None:
            click.echo(f"Warning: cannot read {f}, skipping", err=True)
            continue
        resized = cv2.resize(img, (width, height), interpolation=cv2.INTER_AREA)
        out_path = out_dir / f"{f.stem}_{width}x{height}{f.suffix}"
        cv2.imwrite(str(out_path), resized)
        click.echo(str(out_path.resolve()))
