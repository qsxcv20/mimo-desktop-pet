"""Combine pet cut-outs into a 2x2 contact sheet at a given cell size.

Usage:
    python preview_sheet.py --out sheet.png cell.png [cell.png ...]
"""

import argparse
import os

from PIL import Image

LABELS = {"mimo-idle-v2": "idle", "mimo-happy-v2": "happy",
          "mimo-think-v2": "think", "mimo-tired-v2": "tired"}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--out", required=True)
    p.add_argument("--cell", type=int, default=320)
    p.add_argument("inputs", nargs="+")
    a = p.parse_args()

    cell = a.cell
    cols = 2
    rows = (len(a.inputs) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * cell, rows * cell), "#ffffff")

    for i, path in enumerate(a.inputs):
        img = Image.open(path).convert("RGBA")
        small = img.resize((cell, cell), Image.LANCZOS)
        tile = Image.new("RGBA", (cell, cell), (255, 255, 255, 255))
        tile.alpha_composite(small)
        sheet.paste(tile.convert("RGB"), ((i % cols) * cell, (i // cols) * cell))

    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    sheet.save(a.out, "PNG")
    print(a.out)


if __name__ == "__main__":
    main()
