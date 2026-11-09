#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""src_eyes.py — 把源图的眼睛区域裁出来对比用。

用法: python src_eyes.py <expr> <out.png> [scale]
     expr: idle / happy / think / tired
"""
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = r"D:\桌面宠物"
SRC = os.path.join(ROOT, "assets", "src")

# union 坐标里的眼睛框（见 build_anim_sheet.py）
EYE_L = (595, 962, 842, 1170)
EYE_R = (862, 958, 1207, 1170)


def main():
    expr = sys.argv[1] if len(sys.argv) > 1 else "happy"
    out = sys.argv[2] if len(sys.argv) > 2 else r"D:\桌面宠物\_mimo\src-eyes.png"
    scale = float(sys.argv[3]) if len(sys.argv) > 3 else 1.0

    from PIL import Image
    path = os.path.join(SRC, "mimo-%s-v2@2048.png" % expr)
    im = Image.open(path).convert("RGBA")
    print("source:", path, im.size)

    x0 = min(EYE_L[0], EYE_R[0])
    x1 = max(EYE_L[2], EYE_R[2])
    y0 = min(EYE_L[1], EYE_R[1])
    y1 = max(EYE_L[3], EYE_R[3])
    crop = im.crop((x0, y0, x1, y1))
    if scale != 1.0:
        crop = crop.resize((int(crop.width * scale), int(crop.height * scale)),
                           Image.LANCZOS)
    bg = Image.new("RGBA", crop.size, (255, 255, 255, 255))
    bg.alpha_composite(crop)
    bg.convert("RGB").save(out)
    print("-> %s  %dx%d  box=(%d,%d,%d,%d)" % (out, bg.width, bg.height, x0, y0, x1, y1))


if __name__ == "__main__":
    main()
