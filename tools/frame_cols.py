#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""frame_cols.py — 打印 256px 最终帧眼部的逐列色块剖面（可多档位并排）。

用法: python frame_cols.py [expr] [lvlA,lvlB,...] [--nowarp]
"""
import os
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass  # pythonw.exe 下 sys.stdout 是 None
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
from PIL import Image

import build_anim_sheet as B  # noqa: E402

FRAME = 256
MARGIN = max(4, FRAME // 32)


def cls(r, g, b):
    mx, mn = max(r, g, b), min(r, g, b)
    v = mx
    s = 0 if mx == 0 else (mx - mn) * 255 // mx
    if v < 80:
        return "#"
    if s < 22 and v >= 243:
        return "W"
    if s < 40 and v >= 232:
        return "w"
    if s < 75 and v >= 215:
        return "."
    if r > 200 and g > 120 and b < 140:
        return "O"
    if r > g > b and r - b > 50:
        return "o"
    return "?"


def render(arr_full, expr, nowarp):
    w1, h1 = int(B.W0 * B.RES), int(B.H0 * B.RES)
    a = np.array(Image.fromarray(arr_full).resize((w1, h1), Image.LANCZOS))
    if not nowarp:
        dx, dy = B.build_field(h1, w1, expr, 0.0, s=B.RES)
        a = B.warp(a, dx, dy)
    pm = B.place_into_frame(a, FRAME, MARGIN).convert("RGBA")
    bg = Image.new("RGBA", pm.size, (238, 238, 242, 255))
    bg.alpha_composite(pm)
    return bg.convert("RGB")


def runs(arr, x, y0, y1):
    out = []
    prev, st = None, y0
    for y in range(y0, y1):
        c = cls(int(arr[y, x, 0]), int(arr[y, x, 1]), int(arr[y, x, 2]))
        if c != prev:
            if prev is not None:
                out.append("%s%d-%d" % (prev, st, y - 1))
            prev, st = c, y
    out.append("%s%d-%d" % (prev, st, y1 - 1))
    return " ".join(out)


def main():
    expr = sys.argv[1] if len(sys.argv) > 1 else "think"
    levels = [float(v) for v in (sys.argv[2] if len(sys.argv) > 2 else "0.0,0.6").split(",")]
    nowarp = "--nowarp" in sys.argv

    path = os.path.join(B.SRC, B.SOURCE_FILE[expr])
    base = np.array(Image.open(path).convert("RGBA").crop(B.UNION_BBOX))

    imgs = [np.array(render(B.make_blink(base.copy(), B.EYE_L, lv), expr, nowarp))
            for lv in levels]

    s = min((FRAME - 2 * MARGIN) / float(B.W0), (FRAME - 2 * MARGIN) / float(B.H0))
    nw, nh = int(round(B.W0 * s)), int(round(B.H0 * s))
    ox = (FRAME - nw) // 2
    oy = FRAME - MARGIN - nh
    x0, y0, x1, y1 = B.EYE_L
    fx0 = max(0, ox + int(x0 * s))
    fx1 = min(FRAME, ox + int(x1 * s))
    fy0 = max(0, oy + int(y0 * s))
    fy1 = min(FRAME, oy + int(y1 * s))
    print("expr=%s  frame rect=(%d,%d)-(%d,%d)  levels=%s" % (
        expr, fx0, fy0, fx1, fy1, levels))
    for x in range(fx0, fx1):
        print("x=%3d | %s" % (x, " | ".join(runs(im, x, fy0, fy1) for im in imgs)))


if __name__ == "__main__":
    main()
