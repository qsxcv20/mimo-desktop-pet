#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""blink_diff.py — 对比两个眨眼档位在 256px 最终帧上的像素差异。

用法: python blink_diff.py [expr] [levelA] [levelB] [out.png] [--nowarp] [--zoom N]
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


def eye_rect():
    s = min((FRAME - 2 * MARGIN) / float(B.W0), (FRAME - 2 * MARGIN) / float(B.H0))
    nw, nh = int(round(B.W0 * s)), int(round(B.H0 * s))
    ox = (FRAME - nw) // 2
    oy = FRAME - MARGIN - nh
    x0, y0, x1, y1 = B.EYE_L
    return (max(0, ox + int(x0 * s) - 4), max(0, oy + int(y0 * s) - 4),
            min(FRAME, ox + int(x1 * s) + 4), min(FRAME, oy + int(y1 * s) + 4))


def main():
    expr = sys.argv[1] if len(sys.argv) > 1 else "idle"
    la = float(sys.argv[2]) if len(sys.argv) > 2 else 0.0
    lb = float(sys.argv[3]) if len(sys.argv) > 3 else 0.6
    out = sys.argv[4] if len(sys.argv) > 4 else \
        r"D:\桌面宠物\_mimo\diff-%s-%s.png" % (expr, lb)
    nowarp = "--nowarp" in sys.argv
    zoom = 16
    for i, a in enumerate(sys.argv):
        if a == "--zoom" and i + 1 < len(sys.argv):
            zoom = int(sys.argv[i + 1])

    path = os.path.join(B.SRC, B.SOURCE_FILE[expr])
    base = np.array(Image.open(path).convert("RGBA").crop(B.UNION_BBOX))

    ia = render(B.make_blink(base.copy(), B.EYE_L, la), expr, nowarp)
    ib = render(B.make_blink(base.copy(), B.EYE_L, lb), expr, nowarp)
    r = eye_rect()
    ca = ia.crop(r)
    cb = ib.crop(r)

    A = np.array(ca).astype(np.int16)
    C = np.array(cb).astype(np.int16)
    diff = np.abs(A - C).sum(axis=2)
    mask = Image.fromarray((diff > 24).astype(np.uint8) * 255)
    mask = mask.convert("RGB")

    w = ca.width * zoom
    h = ca.height * zoom
    sheet = Image.new("RGB", (w * 3 + 16, h), (255, 255, 255))
    sheet.paste(ca.resize((w, h), Image.NEAREST), (0, 0))
    sheet.paste(cb.resize((w, h), Image.NEAREST), (w + 8, 0))
    sheet.paste(mask.resize((w, h), Image.NEAREST), (w * 2 + 16, 0))
    sheet.save(out)
    print("-> %s  rect=%s zoom=%d  左=level%s 中=level%s 右=差异掩膜" % (
        out, r, zoom, la, lb))
    ys, xs = np.nonzero(diff > 24)
    if len(xs):
        print("差异像素 %d 个，裁剪内 x %d..%d, y %d..%d" % (
            len(xs), xs.min(), xs.max(), ys.min(), ys.max()))
    else:
        print("无差异")


if __name__ == "__main__":
    main()
