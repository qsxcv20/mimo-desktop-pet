"""Trim a transparent PNG to its alpha bounding box and fit it into a square canvas.

Aligns with the dsh-whale-widget pet asset spec (610x610 RGBA cut-out, bottom anchored).

Usage:
    python export_pet.py --src in.png --out out.png [--size 610] [--preview prev.png]
"""

import argparse
import os

from PIL import Image


def alpha_bbox(img: Image.Image, threshold: int = 10):
    """Bounding box of pixels whose alpha exceeds the threshold."""
    alpha = img.getchannel("A")
    mask = alpha.point(lambda a: 255 if a > threshold else 0)
    return mask.getbbox()


def export(src_path: str, out_path: str, size: int = 610, preview_path: str = None,
           pad_ratio: float = 0.02) -> str:
    img = Image.open(src_path).convert("RGBA")
    box = alpha_bbox(img)
    if box is None:
        raise SystemExit(f"no visible pixels in {src_path}")

    left, top, right, bottom = box
    width, height = right - left, bottom - top
    pad = int(max(width, height) * pad_ratio)
    left = max(0, left - pad)
    top = max(0, top - pad)
    right = min(img.width, right + pad)
    bottom = min(img.height, bottom + pad)

    cropped = img.crop((left, top, right, bottom))
    scale = min(size / cropped.width, size / cropped.height)
    new_w = max(1, int(round(cropped.width * scale)))
    new_h = max(1, int(round(cropped.height * scale)))
    resized = cropped.resize((new_w, new_h), Image.LANCZOS)

    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    canvas.paste(resized, ((size - new_w) // 2, size - new_h), resized)

    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    canvas.save(out_path, "PNG")
    info = f"{os.path.basename(out_path)}  content {width}x{height} -> {new_w}x{new_h}"

    if preview_path:
        preview = Image.new("RGBA", (160, 160), (255, 255, 255, 255))
        small = canvas.resize((160, 160), Image.LANCZOS)
        preview.alpha_composite(small)
        preview.convert("RGB").save(preview_path, "PNG")
        info += "  (+160px preview)"

    return info


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--src", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--size", type=int, default=610)
    parser.add_argument("--preview")
    args = parser.parse_args()
    print(export(args.src, args.out, args.size, args.preview))


if __name__ == "__main__":
    main()
