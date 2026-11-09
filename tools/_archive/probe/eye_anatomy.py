#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""eye_anatomy.py — 眼部解剖：放大图 + 逐列结构表。

用法: python eye_anatomy.py [expr] [EYE_L|EYE_R]
"""
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
from PIL import Image

import build_anim_sheet as B  # noqa: E402

OUT_DIR = r"D:\桌面宠物\_mimo"


def save_zoom(expr, which, out, zoom=3, pad=30):
    path = os.path.join(B.SRC, B.SOURCE_FILE[expr])
    img = Image.open(path).convert("RGBA").crop(B.UNION_BBOX)
    x0, y0, x1, y1 = getattr(B, which)
    crop = img.crop((max(0, x0 - pad), max(0, y0 - pad),
                     min(img.width, x1 + pad), min(img.height, y1 + pad)))
    crop = crop.resize((crop.width * zoom, crop.height * zoom), Image.LANCZOS)
    bg = Image.new("RGBA", crop.size, (235, 235, 238, 255))
    bg.alpha_composite(crop)
    bg.convert("RGB").save(out)
    print("zoom -> %s (%dx%d)" % (out, bg.width, bg.height))


def analyze(expr, which):
    import cv2
    path = os.path.join(B.SRC, B.SOURCE_FILE[expr])
    arr = np.array(Image.open(path).convert("RGBA").crop(B.UNION_BBOX))
    x0, y0, x1, y1 = getattr(B, which)
    sub = np.ascontiguousarray(arr[y0:y1, x0:x1, :3])
    hsv = cv2.cvtColor(sub, cv2.COLOR_RGB2HSV)
    h, s, v = hsv[..., 0], hsv[..., 1], hsv[..., 2]

    orange = (h >= 8) & (h <= 42) & (s > 50) & (v > 110)
    white = (s <= 16) & (v >= 246)
    m = (orange | white).astype(np.uint8)

    iris = B._find_iris(arr, (x0, y0, x1, y1))
    print("\n=== %s / %s ===" % (expr, which))
    print("box=%s  iris=%s" % ((x0, y0, x1, y1),
                               (iris[:4] if iris else None)))
    if iris is None:
        # 没有虹膜：happy 的闭眼笑眼
        print("  (无虹膜，跳过结构表)")
        return

    ix0, ix1, iy0, iy1 = iris[0], iris[1], iris[2], iris[3]
    n, lab, stats, _ = cv2.connectedComponentsWithStats(m, 8)
    reg = lab[iy0 - y0:iy1 - y0, ix0 - x0:ix1 - x0]
    vals, cnts = np.unique(reg[reg > 0], return_counts=True)
    best = int(vals[int(np.argmax(cnts))])
    comp = (lab == best)

    print("  眼球连通域 = #%d  面积=%d" % (best, int(comp.sum())))
    print("   x    eyeball_top  eyeball_bot   lash_top  lash_bot  lash_th  skin")
    for x in range(x0, x1, 6):
        c = comp[:, x - x0]
        ys = np.nonzero(c)[0]
        if len(ys) == 0:
            continue
        et = int(ys.min()) + y0
        eb = int(ys.max()) + y0
        # 睫毛带：从 eyeball_top-1 往上找暗段
        lb = et - 1
        lt = lb
        while lt - 1 >= y0 and int(v[lt - 1 - y0, x - x0]) < 140:
            lt -= 1
        # 皮肤色：睫毛带正上方 8 行
        sa = max(y0, lt - 10)
        sb = max(sa + 1, lt - 2)
        skin = np.median(arr[sa:sb, x, :3].astype(np.float32), axis=0)
        print("%5d   %5d       %5d       %5d    %5d    %4d   %s" % (
            x, et, eb, lt, lb, lb - lt + 1,
            tuple(int(q) for q in skin)))


if __name__ == "__main__":
    expr = sys.argv[1] if len(sys.argv) > 1 else "idle"
    which = sys.argv[2] if len(sys.argv) > 2 else "EYE_L"
    os.makedirs(OUT_DIR, exist_ok=True)
    save_zoom(expr, which, os.path.join(OUT_DIR, "eye_%s_%s.png" % (expr, which)))
    analyze(expr, which)
