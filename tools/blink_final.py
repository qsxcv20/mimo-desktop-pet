#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""blink_final.py — 按**精灵图最终分辨率**预览眨眼效果。

这是验收视图：走完整流水线（2048 原画 -> 55% -> 256px 帧），
再把眼部区域用 NEAREST 放大，看的就是用户真正看到的像素。

用法: python blink_final.py [expr] [EYE_L|EYE_R] [out.png]
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

LEVELS = [0.0, 0.20, 0.40, 0.60, 0.80, 1.0]
FRAME = 256
MARGIN = max(4, FRAME // 32)
ZOOM = 7


def frame_eye(arr_full, expr, box):
    """走完整流水线，返回 256px 帧里的眼部裁剪（已放大）。"""
    W0f, H0f = B.W0, B.H0
    w1, h1 = int(W0f * B.RES), int(H0f * B.RES)
    a = np.array(Image.fromarray(arr_full).resize((w1, h1), Image.LANCZOS))
    dx, dy = B.build_field(h1, w1, expr, 0.0, s=B.RES)
    a = B.warp(a, dx, dy)
    pm = B.place_into_frame(a, FRAME, MARGIN)

    s = min((FRAME - 2 * MARGIN) / float(W0f),
            (FRAME - 2 * MARGIN) / float(H0f))
    nw, nh = int(round(W0f * s)), int(round(H0f * s))
    ox = (FRAME - nw) // 2
    oy = FRAME - MARGIN - nh
    x0, y0, x1, y1 = box
    fx0 = ox + int(x0 * s) - 8
    fy0 = oy + int(y0 * s) - 6
    fx1 = ox + int(x1 * s) + 8
    fy1 = oy + int(y1 * s) + 6
    crop = pm.crop((max(0, fx0), max(0, fy0), min(FRAME, fx1), min(FRAME, fy1)))
    bg = Image.new("RGBA", crop.size, (238, 238, 242, 255))
    bg.alpha_composite(crop)
    return bg.convert("RGB").resize((crop.width * ZOOM, crop.height * ZOOM),
                                     Image.NEAREST)


def main():
    expr = sys.argv[1] if len(sys.argv) > 1 else "idle"
    which = sys.argv[2] if len(sys.argv) > 2 else "EYE_L"
    out = sys.argv[3] if len(sys.argv) > 3 else r"D:\桌面宠物\_mimo\blink-final-%s.png" % which

    path = os.path.join(B.SRC, B.SOURCE_FILE[expr])
    arr_full = np.array(Image.open(path).convert("RGBA").crop(B.UNION_BBOX))
    box = getattr(B, which)

    crops = []
    for lvl in LEVELS:
        bl = B.make_blink(arr_full.copy(), box, lvl)
        crops.append(frame_eye(bl, expr, box))

    w = max(c.width for c in crops)
    h = sum(c.height for c in crops) + 6 * (len(crops) - 1)
    sheet = Image.new("RGB", (w, h), (250, 250, 252))
    y = 0
    for lvl, c in zip(LEVELS, crops):
        sheet.paste(c, (0, y))
        y += c.height + 6
    sheet.save(out)
    print("-> %s  %dx%d  levels=%s" % (out, sheet.width, sheet.height, LEVELS))


if __name__ == "__main__":
    main()
