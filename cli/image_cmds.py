"""Image processing subcommands for gamefactory CLI."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import click
import cv2
import numpy as np


from matting_config import (
    KEY_SCOPE_EXTERIOR,
    KEY_SCOPE_GLOBAL,
    KEY_SCOPES,
    resolve_color_key_settings,
    resolve_trim_settings,
    resolve_validate_edges_settings,
)


def refine_alpha_mask(
    alpha: np.ndarray,
    *,
    morph_erode: int = 0,
    morph_dilate: int = 0,
    despeckle: int = 0,
) -> np.ndarray:
    """Morphological cleanup on alpha — remove edge halos / stray white specks."""
    if morph_erode == 0 and morph_dilate == 0 and despeckle == 0:
        return alpha

    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    result = alpha.copy()
    if despeckle > 0:
        for _ in range(despeckle):
            result = cv2.morphologyEx(result, cv2.MORPH_OPEN, kernel)
    if morph_erode > 0:
        result = cv2.erode(result, kernel, iterations=morph_erode)
    if morph_dilate > 0:
        result = cv2.dilate(result, kernel, iterations=morph_dilate)
    return result


def _sample_corner_bg_color(img_bgr: np.ndarray, block: int = 4) -> np.ndarray:
    """Average RGB from corner blocks (BGR order)."""
    b = min(block, img_bgr.shape[0] // 4, img_bgr.shape[1] // 4)
    corners = np.concatenate(
        [
            img_bgr[:b, :b].reshape(-1, 3),
            img_bgr[:b, -b:].reshape(-1, 3),
            img_bgr[-b:, :b].reshape(-1, 3),
            img_bgr[-b:, -b:].reshape(-1, 3),
        ],
        axis=0,
    )
    return corners.mean(axis=0)


def _background_candidate_mask(
    gray: np.ndarray,
    diff: np.ndarray,
    *,
    threshold: int,
    fuzz: float,
) -> np.ndarray:
    """Pixels that look like studio background by brightness / color."""
    return (gray >= threshold) | (diff <= fuzz)


def _exterior_background_mask(candidate: np.ndarray) -> np.ndarray:
    """Background pixels connected to the image border (PS magic-wand exterior only).

    Interior whites/highlights that do not touch the canvas edge stay opaque.
    """
    h, w = candidate.shape
    exterior = np.zeros((h, w), dtype=bool)
    if not candidate.any():
        return exterior

    from collections import deque

    visited = np.zeros((h, w), dtype=bool)
    queue: deque[tuple[int, int]] = deque()

    for x in range(w):
        for y in (0, h - 1):
            if candidate[y, x] and not visited[y, x]:
                visited[y, x] = True
                queue.append((y, x))
    for y in range(h):
        for x in (0, w - 1):
            if candidate[y, x] and not visited[y, x]:
                visited[y, x] = True
                queue.append((y, x))

    while queue:
        y, x = queue.popleft()
        exterior[y, x] = True
        for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            ny, nx = y + dy, x + dx
            if (
                0 <= ny < h
                and 0 <= nx < w
                and candidate[ny, nx]
                and not visited[ny, nx]
            ):
                visited[ny, nx] = True
                queue.append((ny, nx))

    return exterior


def _matting_masks(
    img_bgr: np.ndarray,
    *,
    threshold: int,
    fuzz: float,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Return gray, diff-to-bg, exterior background, foreground masks."""
    bg_bgr = _sample_corner_bg_color(img_bgr)
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY).astype(np.float32)
    diff = np.linalg.norm(img_bgr.astype(np.float32) - bg_bgr, axis=2)
    candidate = _background_candidate_mask(gray, diff, threshold=threshold, fuzz=fuzz)
    exterior = _exterior_background_mask(candidate)
    foreground = ~exterior
    return gray, diff, exterior, foreground


def _transparent_mask(
    gray: np.ndarray,
    diff: np.ndarray,
    candidate: np.ndarray,
    *,
    key_scope: str,
    threshold: int,
    fuzz: float,
) -> np.ndarray:
    """Pixels that should become transparent."""
    if key_scope == KEY_SCOPE_GLOBAL:
        transparent = candidate.copy()
        spill = (~candidate) & (gray >= threshold - 35) & (diff <= fuzz + 20)
        transparent |= spill
        return transparent
    return _exterior_background_mask(candidate)


def _foreground_mask(
    img_bgr: np.ndarray,
    *,
    threshold: int,
    fuzz: float,
    key_scope: str = KEY_SCOPE_EXTERIOR,
) -> np.ndarray:
    gray, diff, _, _ = _matting_masks(img_bgr, threshold=threshold, fuzz=fuzz)
    candidate = _background_candidate_mask(gray, diff, threshold=threshold, fuzz=fuzz)
    transparent = _transparent_mask(
        gray, diff, candidate, key_scope=key_scope, threshold=threshold, fuzz=fuzz
    )
    return ~transparent


def remove_bg_color_key(
    img: np.ndarray,
    *,
    threshold: int = 240,
    fuzz: float = 18.0,
    key_scope: str = KEY_SCOPE_EXTERIOR,
    morph_erode: int = 0,
    morph_dilate: int = 0,
    despeckle: int = 0,
) -> np.ndarray:
    """Make white studio background transparent.

    key_scope:
      exterior — only background connected to canvas edge (default; keeps interior whites)
      global   — all white/near-white pixels become transparent
    """
    if key_scope not in KEY_SCOPES:
        key_scope = KEY_SCOPE_EXTERIOR

    if img.ndim == 2:
        img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
    elif img.shape[2] == 4:
        img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)

    gray, diff, exterior, foreground = _matting_masks(
        img, threshold=threshold, fuzz=fuzz
    )
    candidate = _background_candidate_mask(gray, diff, threshold=threshold, fuzz=fuzz)
    transparent = _transparent_mask(
        gray, diff, candidate, key_scope=key_scope, threshold=threshold, fuzz=fuzz
    )
    alpha = np.where(transparent, 0, 255).astype(np.uint8)

    if key_scope == KEY_SCOPE_EXTERIOR:
        # Edge halo: bright pixels touching exterior background only
        kernel = np.ones((3, 3), np.uint8)
        touch_exterior = cv2.dilate(exterior.astype(np.uint8), kernel) > 0
        edge_halo = (
            foreground
            & touch_exterior
            & (gray >= threshold - 35)
            & (diff <= fuzz + 20)
        )
        alpha[edge_halo] = 0

    refined = refine_alpha_mask(
        alpha,
        morph_erode=morph_erode,
        morph_dilate=morph_dilate,
        despeckle=despeckle,
    )
    refined = np.where(refined >= 128, 255, 0).astype(np.uint8)

    out = cv2.cvtColor(img, cv2.COLOR_BGR2BGRA)
    out[:, :, 3] = refined
    out[:, :, :3] = np.where(refined[..., None] == 0, 0, out[:, :, :3])
    return out


def _remove_bg_ai(img_bytes: bytes) -> bytes:
    """Optional rembg path (MIT). Requires: pip install \"rembg[cpu]\"."""
    from rembg import remove

    return remove(img_bytes)


def trim_content_bbox(
    img: np.ndarray,
    *,
    threshold: int = 240,
    fuzz: float = 18.0,
    key_scope: str = KEY_SCOPE_EXTERIOR,
    padding: int = 2,
    use_alpha: bool = False,
) -> tuple[np.ndarray, dict[str, int]]:
    """Crop to the union bounding box of non-background pixels."""
    if img is None or img.size == 0:
        raise ValueError("empty image")

    h, w = img.shape[:2]
    if use_alpha and img.shape[2] == 4:
        mask = img[:, :, 3] > 0
    else:
        bgr = img if img.shape[2] == 3 else cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
        mask = _foreground_mask(
            bgr, threshold=threshold, fuzz=fuzz, key_scope=key_scope
        )

    if not mask.any():
        raise ValueError("no foreground pixels found for trim")

    ys, xs = np.where(mask)
    y0 = max(0, int(ys.min()) - padding)
    x0 = max(0, int(xs.min()) - padding)
    y1 = min(h, int(ys.max()) + 1 + padding)
    x1 = min(w, int(xs.max()) + 1 + padding)
    cropped = img[y0:y1, x0:x1]
    meta = {
        "x": x0,
        "y": y0,
        "width": x1 - x0,
        "height": y1 - y0,
        "source_width": w,
        "source_height": h,
    }
    return cropped, meta


@click.command("trim")
@click.option("--input", "input_path", required=True, type=click.Path(exists=True, path_type=Path),
              help="Source image file.")
@click.option("--output", "output_path", required=True, type=click.Path(path_type=Path),
              help="Trimmed output file path.")
@click.option("--padding", type=int, default=None,
              help="Pixels around content bbox (config: matting.trim.padding, default 2).")
@click.option("--threshold", type=int, default=None,
              help="White background threshold (config: matting.trim.threshold, default 240).")
@click.option(
    "--key-scope",
    type=click.Choice(list(KEY_SCOPES)),
    default=None,
    help="Foreground mask scope (config: matting.color_key.key_scope).",
)
@click.option("--alpha", "use_alpha", is_flag=True,
              help="Trim using alpha channel instead of white-background detection.")
@click.option("--json", "as_json", is_flag=True, help="Print crop metadata as JSON.")
@click.pass_context
def trim_cmd(
    ctx: click.Context,
    input_path: Path,
    output_path: Path,
    padding: int | None,
    threshold: int | None,
    key_scope: str | None,
    use_alpha: bool,
    as_json: bool,
) -> None:
    """Trim excess white borders by content bounding box (切图 / tight crop)."""
    config = ctx.obj.get("config", {}) if ctx.obj else {}
    trim_cfg = resolve_trim_settings(config, threshold=threshold, padding=padding)
    key_cfg = resolve_color_key_settings(config, key_scope=key_scope)

    img = cv2.imread(str(input_path), cv2.IMREAD_UNCHANGED)
    if img is None:
        click.echo(f"Error: cannot read image {input_path}", err=True)
        sys.exit(1)

    try:
        cropped, meta = trim_content_bbox(
            img,
            threshold=trim_cfg["threshold"],
            fuzz=float(key_cfg["fuzz"]),
            key_scope=str(key_cfg["key_scope"]),
            padding=trim_cfg["padding"],
            use_alpha=use_alpha,
        )
    except ValueError as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(output_path), cropped)
    if as_json:
        meta["output"] = str(output_path.resolve())
        click.echo(json.dumps(meta, indent=2))
    else:
        click.echo(str(output_path.resolve()))


@click.command("slice")
@click.option("--input", "input_path", required=True, type=click.Path(exists=True, path_type=Path),
              help="Source image file.")
@click.option("--mode", type=click.Choice(["grid"]), default="grid",
              help="Grid-split an icon kit into tiles (not white-border trim).")
@click.option("--rows", type=int, default=4, help="Grid rows.")
@click.option("--cols", type=int, default=4, help="Grid columns.")
@click.option("--output-dir", type=click.Path(path_type=Path), default=None,
              help="Output directory (default: same as input).")
def slice_cmd(input_path: Path, mode: str, rows: int, cols: int, output_dir: Path | None) -> None:
    """Grid-split an icon kit image into tiles. Use `image trim` to crop white borders."""
    img = cv2.imread(str(input_path))
    if img is None:
        click.echo(f"Error: cannot read image {input_path}", err=True)
        sys.exit(1)

    out_dir = output_dir or input_path.parent
    out_dir.mkdir(parents=True, exist_ok=True)
    base = input_path.stem

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


@click.command("remove-bg")
@click.option("--input", "input_path", required=True, type=click.Path(exists=True, path_type=Path),
              help="Source image file.")
@click.option("--output", "output_path", required=True, type=click.Path(path_type=Path),
              help="Output PNG with transparency.")
@click.option(
    "--mode",
    type=click.Choice(["color", "ai"]),
    default="color",
    show_default=True,
    help="color = corner key for white studio BG (default); ai = rembg U2Net.",
)
@click.option("--threshold", type=int, default=None,
              help="Background threshold (config: matting.color_key.threshold).")
@click.option("--fuzz", type=float, default=None,
              help="Color distance tolerance (config: matting.color_key.fuzz).")
@click.option("--erode", "morph_erode", type=int, default=None,
              help="Erode alpha mask N px — eats edge white halos (config: morph_erode).")
@click.option("--dilate", "morph_dilate", type=int, default=None,
              help="Dilate alpha mask N px — fills small holes (config: morph_dilate).")
@click.option("--despeckle", type=int, default=None,
              help="Morph open passes — removes stray white specks (config: despeckle).")
@click.option(
    "--key-scope",
    type=click.Choice(list(KEY_SCOPES)),
    default=None,
    help="exterior = only border-connected white (default); global = all white → transparent.",
)
@click.option("--validate-edges/--no-validate-edges", default=True,
              help="After remove-bg, check 1–2px edge band for white fringes.")
@click.pass_context
def remove_bg_cmd(
    ctx: click.Context,
    input_path: Path,
    output_path: Path,
    mode: str,
    threshold: int | None,
    fuzz: float | None,
    morph_erode: int | None,
    morph_dilate: int | None,
    despeckle: int | None,
    key_scope: str | None,
    validate_edges: bool,
) -> None:
    """Remove background → transparent PNG. Default: color key for white sprites."""
    config = ctx.obj.get("config", {}) if ctx.obj else {}
    key_cfg = resolve_color_key_settings(
        config,
        threshold=threshold,
        fuzz=fuzz,
        key_scope=key_scope,
        morph_erode=morph_erode,
        morph_dilate=morph_dilate,
        despeckle=despeckle,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        if mode == "ai":
            result = _remove_bg_ai(input_path.read_bytes())
            output_path.write_bytes(result)
        else:
            img = cv2.imread(str(input_path), cv2.IMREAD_UNCHANGED)
            if img is None:
                raise ValueError(f"cannot read image {input_path}")
            rgba = remove_bg_color_key(img, **key_cfg)
            if not cv2.imwrite(str(output_path), rgba):
                raise ValueError(f"failed to write {output_path}")
    except Exception as e:
        click.echo(f"Error removing background: {e}", err=True)
        sys.exit(1)

    if validate_edges and mode == "color":
        from matting_validate import validate_matting_edges

        vcfg = resolve_validate_edges_settings(config)
        result = validate_matting_edges(output_path, **vcfg)
        click.echo(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))
        if not result.ok:
            sys.exit(2)

    click.echo(str(output_path.resolve()))


@click.command("validate-matting")
@click.option("--input", "input_path", required=True, type=click.Path(exists=True, path_type=Path),
              help="RGBA PNG after remove-bg.")
@click.option("--edge-width", type=int, default=None, help="Edge band width in pixels (default 2).")
@click.option("--threshold", "brightness_threshold", type=int, default=None,
              help="Brightness ≥ this counts as white on edge.")
@click.option("--max-ratio", "max_white_ratio", type=float, default=None,
              help="Max ratio of bright pixels in edge band.")
@click.pass_context
def validate_matting_cmd(
    ctx: click.Context,
    input_path: Path,
    edge_width: int | None,
    brightness_threshold: int | None,
    max_white_ratio: float | None,
) -> None:
    """Validate transparent sprite edges for white fringes (1–2px band)."""
    from matting_validate import validate_matting_edges

    config = ctx.obj.get("config", {}) if ctx.obj else {}
    vcfg = resolve_validate_edges_settings(
        config,
        edge_width=edge_width,
        brightness_threshold=brightness_threshold,
        max_white_ratio=max_white_ratio,
    )
    result = validate_matting_edges(input_path, **vcfg)
    click.echo(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))
    if not result.ok:
        sys.exit(2)


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
