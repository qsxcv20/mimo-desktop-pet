#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""frame_eye_zoom.py — 在**最终 256px 精灵帧**上放大眼部，并扫描亮像素。

用法: python frame_eye_zoom.py [expr] [level] [out.png] [--nowarp] [--zoom N]
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
    W0f, H0f = B.W0, B.H0
    w1, h1 = int(W0f * B.RES), int(H0f * B.RES)
    a = np.array(Image.fromarray(arr_full).resize((w1, h1), Image.LANCZOS))
    if not nowarp:
        dx, dy = B.build_field(h1, w1, expr, 0.0, s=B.RES)
        a = B.warp(a, dx, dy)
    pm = B.place_into_frame(a, FRAME, MARGIN).convert("RGBA")
    bg = Image.new("RGBA", pm.size, (238, 238, 242, 255))
    bg.alpha_composite(pm)
    return bg.convert("RGB")


def main():
    expr = sys.argv[1] if len(sys.argv) > 1 else "idle"
    level = float(sys.argv[2]) if len(sys.argv) > 2 else 0.6
    out = sys.argv[3] if len(sys.argv) > 3 else \
        r"D:\桌面宠物\_mimo\fz-%s-%s.png" % (expr, level)
    nowarp = "--nowarp" in sys.argv
    zoom = 12
    for i, a in enumerate(sys.argv):
        if a == "--zoom" and i + 1 < len(sys.argv):
            zoom = int(sys.argv[i + 1])

    path = os.path.join(B.SRC, B.SOURCE_FILE[expr])
    arr_full = np.array(Image.open(path).convert("RGBA").crop(B.UNION_BBOX))
    bl = B.make_blink(arr_full.copy(), B.EYE_L, level)
    img = render(bl, expr, nowarp)

    # --- 眼部区域裁剪（256px 帧坐标） ---
    s = min((FRAME - 2 * MARGIN) / float(B.W0), (FRAME - 2 * MARGIN) / float(B.H0))
    nw, nh = int(round(B.W0 * s)), int(round(B.H0 * s))
    ox = (FRAME - nw) // 2
    oy = FRAME - MARGIN - nh
    x0, y0, x1, y1 = B.EYE_L
    fx0 = max(0, ox + int(x0 * s) - 6)
    fy0 = max(0, oy + int(y0 * s) - 6)
    fx1 = min(FRAME, ox + int(x1 * s) + 6)
    fy1 = min(FRAME, oy + int(y1 * s) + 6)
    crop = img.crop((fx0, fy0, fx1, fy1))
    crop.resize((crop.width * zoom, crop.height * zoom), Image.NEAREST).save(out)

    # --- 亮像素扫描 ---
    a = np.array(crop).astype(np.int16)
    R, G, Bl = a[:, :, 0], a[:, :, 1], a[:, :, 2]
    V = np.max(a, axis=2)
    # 纯白：高亮且低色散（皮肤 254,234,221 的色散=33，会被滤掉）
    spread = np.max(a, axis=2) - np.min(a, axis=2)
    bright = (R >= 244) & (G >= 241) & (Bl >= 236) & (spread <= 22)
    print("-> %s  crop=%s zoom=%d" % (out, (fx0, fy0, fx1, fy1), zoom))
    print("bright px total = %d" % int(bright.sum()))
    cols = []
    for c in range(bright.shape[1]):
        n = int(bright[:, c].sum())
        if n:
            rows = np.where(bright[:, c])[0]
            cols.append((c, n, int(rows.min()), int(rows.max())))
    if cols:
        print("col(裁剪内)  n  yTop  yBot   [源x ≈ ox + x0*s + col/s]")
        for c, n, r0, r1 in cols:
            sx = ox + x0 * s + c / s
            print("  c=%3d n=%2d  y=%3d..%3d   srcX~%.0f" % (c, n, r0, r1, sx))


if __name__ == "__main__":
    main()
