#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""blink_measure.py — 在最终 256px 帧里量一下填充区的实际颜色。

用法: python blink_measure.py [expr] [EYE_L|EYE_R]
"""
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
from PIL import Image

import build_anim_sheet as B  # noqa: E402

FRAME = 256
MARGIN = FRAME // 32


def frame_rgb(arr_full, expr, box):
    W0f, H0f = B.W0, B.H0
    w1, h1 = int(W0f * B.RES), int(H0f * B.RES)
    a = np.array(Image.fromarray(arr_full).resize((w1, h1), Image.LANCZOS))
    dx, dy = B.build_field(h1, w1, expr, 0.0, s=B.RES)
    a = B.warp(a, dx, dy)
    pm = B.place_into_frame(a, FRAME, MARGIN)
    s = min((FRAME - 2 * MARGIN) / float(W0f), (FRAME - 2 * MARGIN) / float(H0f))
    nw, nh = int(round(W0f * s)), int(round(H0f * s))
    ox, oy = (FRAME - nw) // 2, FRAME - MARGIN - nh
    return np.array(pm.convert("RGB")), ox, oy, s


def main():
    expr = sys.argv[1] if len(sys.argv) > 1 else "idle"
    which = sys.argv[2] if len(sys.argv) > 2 else "EYE_L"
    path = os.path.join(B.SRC, B.SOURCE_FILE[expr])
    arr_full = np.array(Image.open(path).convert("RGBA").crop(B.UNION_BBOX))
    box = getattr(B, which)
    geo = B._eye_geometry(arr_full, box)
    xs = geo["xs"]
    k = len(xs) // 2
    x = int(xs[k])
    lid = int(round(geo["top"][k]))
    lt = int(round(geo["bandT"][k]))

    for lvl in (0.0, 0.4, 1.0):
        bl = B.make_blink(arr_full.copy(), box, lvl)
        px, ox, oy, s = frame_rgb(bl, expr, box)
        print("--- level %.1f ---" % lvl)
        # 填充区中心（2048 坐标）
        d = int(round(lvl * (geo["bot"][k] - geo["top"][k])))
        mid = lt + max(0, d // 2)
        for label, ux, uy in (
                ("填充区中心", x, mid),
                ("填充区上边", x, lt + 2),
                ("睑缘下 6px", x, lid + d + 6),
                ("眼睛左侧皮肤", x - 45, lid + 20),
                ("眼睛上方皮肤", x, lid - 40),
                ("眼睛下方皮肤", x, lid + 150)):
            fx = ox + int(ux * s)
            fy = oy + int(uy * s)
            if 0 <= fy < FRAME and 0 <= fx < FRAME:
                print("   %-12s union(%4d,%4d) frame(%3d,%3d) = %s" % (
                    label, ux, uy, fx, fy,
                    tuple(int(q) for q in px[fy, fx])))


if __name__ == "__main__":
    main()
