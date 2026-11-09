#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""blink_mask.py — 输出「眨眼改了哪些像素」的可视化。

红 = 被填成眼皮的区域，绿 = 被搬下来的睫毛带，蓝 = 原图本身。
一眼就能看出画错在哪。

用法: python blink_mask.py [expr] [EYE_L|EYE_R] [level] [out.png] [scale]
"""
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np
from PIL import Image

import build_anim_sheet as B  # noqa: E402


def main():
    expr = sys.argv[1] if len(sys.argv) > 1 else "idle"
    which = sys.argv[2] if len(sys.argv) > 2 else "EYE_L"
    lvl = float(sys.argv[3]) if len(sys.argv) > 3 else 0.6
    out = sys.argv[4] if len(sys.argv) > 4 else r"D:\桌面宠物\_mimo\blink-mask.png"
    scale = float(sys.argv[5]) if len(sys.argv) > 5 else 2.0

    path = os.path.join(B.SRC, B.SOURCE_FILE[expr])
    arr = np.array(Image.open(path).convert("RGBA").crop(B.UNION_BBOX))
    box = getattr(B, which)
    x0, y0, x1, y1 = box

    iris = B._find_iris(arr, box)
    if not iris:
        print("没有虹膜")
        return
    ix0, ix1, iy0, iy1, _ = iris
    cols = B._eye_structure(arr, box, ix0, ix1, iy0, iy1)
    mid = cols[len(cols) // 2]
    D = max(8, mid[5] - mid[2])
    d = int(round(lvl * D))

    vis = np.zeros(arr.shape[:2] + (3,), dtype=np.uint8)
    vis[..., 0] = arr[..., 0] // 3
    vis[..., 1] = arr[..., 1] // 3
    vis[..., 2] = arr[..., 2] // 3
    for (x, ltop, lbot, skin, lash, ebot) in cols:
        thick = lbot - ltop + 1
        nbot = min(lbot + d, ebot + 4)
        ntop = nbot - thick
        for y in range(max(0, ltop), max(0, ntop)):
            vis[y, x] = (255, 40, 40)
        for y in range(max(0, ntop), min(arr.shape[0], nbot)):
            vis[y, x] = (40, 255, 40)
    region = (x0 - 20, y0 - 30, x1 + 20, y1 + 10)
    img = Image.fromarray(vis[region[1]:region[3], region[0]:region[2]])
    img = img.resize((int(img.width * scale), int(img.height * scale)),
                     Image.NEAREST)
    img.save(out)
    print("-> %s  %dx%d   D=%d d=%d  列范围 %d..%d"
          % (out, img.width, img.height, D, d, cols[0][0], cols[-1][0]))


if __name__ == "__main__":
    main()
