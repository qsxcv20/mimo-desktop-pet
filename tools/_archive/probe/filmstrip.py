#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""filmstrip.py — 把精灵图的某一行动画渲染成横向帧条，便于目视检查。

用法: python filmstrip.py <row> <out.png> [scale]
     row: 0=idle 1=happy 2=think 3=tired
"""
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SPRITE = r"D:\桌面宠物\build\mimo-witch"


def main():
    row = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    out = sys.argv[2] if len(sys.argv) > 2 else r"D:\桌面宠物\_mimo\filmstrip.png"
    scale = float(sys.argv[3]) if len(sys.argv) > 3 else 1.0

    with open(os.path.join(SPRITE, "manifest.json"), "r", encoding="utf-8") as f:
        mf = json.load(f)
    fw, fh = mf["frameWidth"], mf["frameHeight"]
    cols = mf["columns"]

    from PIL import Image
    im = Image.open(os.path.join(SPRITE, mf["spritesheet"])).convert("RGBA")
    print("sheet:", im.size)

    frames = []
    for c in range(cols):
        box = (c * fw, row * fh, (c + 1) * fw, (row + 1) * fh)
        fr = im.crop(box)
        if scale != 1.0:
            fr = fr.resize((int(fw * scale), int(fh * scale)), Image.LANCZOS)
        frames.append(fr)

    w = sum(f.width for f in frames)
    h = max(f.height for f in frames)
    strip = Image.new("RGBA", (w, h), (245, 245, 245, 255))
    x = 0
    for f in frames:
        strip.alpha_composite(f, (x, 0))
        x += f.width
    strip.convert("RGB").save(out)
    print("-> %s  %dx%d  (row=%d, %d frames)" % (out, strip.width, strip.height, row, cols))


if __name__ == "__main__":
    main()
