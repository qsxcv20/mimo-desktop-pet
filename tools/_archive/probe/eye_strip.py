#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""eye_strip.py — 把精灵图某一行里每帧的眼睛区域裁出来放大拼成一条，方便检查眨眼/表情。

用法: python eye_strip.py <row> <out.png> [scale]
"""
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SPRITE = r"D:\桌面宠物\build\mimo-witch"

# 眼睛区域（256x256 帧内的相对坐标），从 happy 帧目测得到
EYE_BOX = (70, 138, 186, 200)


def main():
    row = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    out = sys.argv[2] if len(sys.argv) > 2 else r"D:\桌面宠物\_mimo\eyes.png"
    scale = float(sys.argv[3]) if len(sys.argv) > 3 else 3.0
    global EYE_BOX
    if len(sys.argv) > 7:
        EYE_BOX = tuple(int(x) for x in sys.argv[4:8])

    with open(os.path.join(SPRITE, "manifest.json"), "r", encoding="utf-8") as f:
        mf = json.load(f)
    fw, fh = mf["frameWidth"], mf["frameHeight"]
    cols = mf["columns"]

    from PIL import Image
    im = Image.open(os.path.join(SPRITE, mf["spritesheet"])).convert("RGBA")
    x0, y0, x1, y1 = EYE_BOX
    cw, ch = int((x1 - x0) * scale), int((y1 - y0) * scale)
    strip = Image.new("RGBA", (cw * cols, ch), (250, 250, 250, 255))
    for c in range(cols):
        fr = im.crop((c * fw + x0, row * fh + y0, c * fw + x1, row * fh + y1))
        fr = fr.resize((cw, ch), Image.LANCZOS)
        strip.alpha_composite(fr, (c * cw, 0))
    strip.convert("RGB").save(out)
    print("-> %s  %dx%d  row=%d  %d frames" % (out, strip.width, strip.height, row, cols))


if __name__ == "__main__":
    main()
