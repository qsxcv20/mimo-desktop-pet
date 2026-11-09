#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""filmgrid.py — 把精灵图某一行按指定帧号拼成网格大图，便于目视检查细节。

用法: python filmgrid.py <row> <out.png> [cols] [scale] [frames...]
     例: python filmgrid.py 1 out.png 4 2 0 4 8 12 16 20
"""
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SPRITE = r"D:\桌面宠物\build\mimo-witch"


def main():
    row = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    out = sys.argv[2] if len(sys.argv) > 2 else r"D:\桌面宠物\_mimo\filmgrid.png"
    cols = int(sys.argv[3]) if len(sys.argv) > 3 else 4
    scale = float(sys.argv[4]) if len(sys.argv) > 4 else 2.0
    frames = [int(x) for x in sys.argv[5:]] or list(range(0, 16, 2))

    with open(os.path.join(SPRITE, "manifest.json"), "r", encoding="utf-8") as f:
        mf = json.load(f)
    fw, fh = mf["frameWidth"], mf["frameHeight"]

    from PIL import Image
    im = Image.open(os.path.join(SPRITE, mf["spritesheet"])).convert("RGBA")

    cells = []
    for c in frames:
        fr = im.crop((c * fw, row * fh, (c + 1) * fw, (row + 1) * fh))
        if scale != 1.0:
            fr = fr.resize((int(fw * scale), int(fh * scale)), Image.LANCZOS)
        cells.append(fr)

    cw = max(c.width for c in cells)
    ch = max(c.height for c in cells)
    rows = (len(cells) + cols - 1) // cols
    pad = 6
    sheet = Image.new("RGBA", (cols * (cw + pad) + pad, rows * (ch + pad) + pad),
                      (240, 240, 240, 255))
    for i, c in enumerate(cells):
        r, col = divmod(i, cols)
        sheet.alpha_composite(c, (pad + col * (cw + pad), pad + r * (ch + pad)))
    sheet.convert("RGB").save(out)
    print("-> %s  %dx%d  row=%d frames=%s" % (out, sheet.width, sheet.height, row, frames))


if __name__ == "__main__":
    main()
