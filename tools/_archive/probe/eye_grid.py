#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""eye_grid.py — 把精灵图某一行指定帧的眼睛区域放大拼成网格。

用法: python eye_grid.py <row> <out.png> <scale> <x0> <y0> <x1> <y1> [frames...]
"""
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SPRITE = r"D:\桌面宠物\build\mimo-witch"


def main():
    row = int(sys.argv[1])
    out = sys.argv[2]
    scale = float(sys.argv[3])
    x0, y0, x1, y1 = [int(x) for x in sys.argv[4:8]]
    frames = [int(x) for x in sys.argv[8:]] or list(range(24))
    cols = 4

    with open(os.path.join(SPRITE, "manifest.json"), "r", encoding="utf-8") as f:
        mf = json.load(f)
    fw, fh = mf["frameWidth"], mf["frameHeight"]

    from PIL import Image
    im = Image.open(os.path.join(SPRITE, mf["spritesheet"])).convert("RGBA")

    cw, ch = int((x1 - x0) * scale), int((y1 - y0) * scale)
    rows = (len(frames) + cols - 1) // cols
    pad = 4
    sheet = Image.new("RGB", (cols * (cw + pad) + pad, rows * (ch + pad) + pad),
                      (255, 255, 255))
    for i, c in enumerate(frames):
        fr = im.crop((c * fw + x0, row * fh + y0, c * fw + x1, row * fh + y1))
        fr = fr.resize((cw, ch), Image.LANCZOS)
        bg = Image.new("RGBA", fr.size, (255, 255, 255, 255))
        bg.alpha_composite(fr)
        r, col = divmod(i, cols)
        sheet.paste(bg.convert("RGB"), (pad + col * (cw + pad), pad + r * (ch + pad)))
    sheet.save(out)
    print("-> %s  %dx%d  row=%d frames=%s" % (out, sheet.width, sheet.height, row, frames))


if __name__ == "__main__":
    main()
