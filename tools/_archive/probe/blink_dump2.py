#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""blink_dump2.py — 打印 256px 最终帧眼部区域的 RGB 网格。

用法: python blink_dump2.py [expr] [level] [--nowarp]
"""
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
from PIL import Image

import build_anim_sheet as B  # noqa: E402

FRAME = 256
MARGIN = max(4, FRAME // 32)


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


def classify(r, g, b):
    mx, mn = max(r, g, b), min(r, g, b)
    v = mx
    s = 0 if mx == 0 else (mx - mn) * 255 // mx
    if v < 70:
        return "#"        # 深棕/黑：睫毛
    if s < 25 and v >= 244:
        return "W"        # 纯白：高光/眼白
    if s < 30 and v >= 235:
        return "w"        # 浅灰
    if s < 60 and v >= 225:
        return "."        # 皮肤
    if r > g and g >= b:
        return "O"        # 橙
    return "?"


def main():
    expr = sys.argv[1] if len(sys.argv) > 1 else "idle"
    level = float(sys.argv[2]) if len(sys.argv) > 2 else 0.6
    nowarp = "--nowarp" in sys.argv

    path = os.path.join(B.SRC, B.SOURCE_FILE[expr])
    base = np.array(Image.open(path).convert("RGBA").crop(B.UNION_BBOX))
    img = render(B.make_blink(base.copy(), B.EYE_L, level), expr, nowarp)

    s = min((FRAME - 2 * MARGIN) / float(B.W0), (FRAME - 2 * MARGIN) / float(B.H0))
    nw, nh = int(round(B.W0 * s)), int(round(B.H0 * s))
    ox = (FRAME - nw) // 2
    oy = FRAME - MARGIN - nh
    x0, y0, x1, y1 = B.EYE_L
    fx0 = max(0, ox + int(x0 * s) - 4)
    fy0 = max(0, oy + int(y0 * s) - 4)
    fx1 = min(FRAME, ox + int(x1 * s) + 4)
    fy1 = min(FRAME, oy + int(y1 * s) + 4)
    crop = np.array(img.crop((fx0, fy0, fx1, fy1))).astype(np.int16)

    print("expr=%s level=%s crop=(%d,%d)-(%d,%d)  s=%.5f" % (
        expr, level, fx0, fy0, fx1, fy1, s))
    print("字符图: #=深棕  W=纯白  w=浅灰  .=皮肤  O=橙  ?=其它")
    print("      " + "".join(str((fx0 + c) % 10) for c in range(crop.shape[1])))
    for r in range(crop.shape[0]):
        row = []
        for c in range(crop.shape[1]):
            row.append(classify(int(crop[r, c, 0]), int(crop[r, c, 1]),
                                int(crop[r, c, 2])))
        print("y%3d  %s" % (fy0 + r, "".join(row)))

    # 打印几列的原始 RGB
    print("\n选定列 RGB：")
    for c in range(crop.shape[1]):
        px = [tuple(int(v) for v in crop[r, c]) for r in range(crop.shape[0])]
        if any(p[0] > 245 and p[1] > 240 and p[2] > 235 for p in px):
            print("  x=%d (frame) 纯白行: %s" % (
                fx0 + c,
                [(fy0 + r, px[r]) for r in range(len(px))
                 if px[r][0] > 245 and px[r][1] > 240 and px[r][2] > 235]))


if __name__ == "__main__":
    main()
