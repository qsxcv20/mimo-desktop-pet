#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""blink_strip.py — 按精灵图最终 256px 拼一条眨眼动画带（这就是用户看到的）。

用法: python blink_strip.py [expr] [out.png] [--nowarp] [--scale N]
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
LEVELS = [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]


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


def main():
    expr = sys.argv[1] if len(sys.argv) > 1 else "idle"
    out = sys.argv[2] if len(sys.argv) > 2 else \
        r"D:\桌面宠物\_mimo\strip-%s.png" % expr
    nowarp = "--nowarp" in sys.argv
    scale = 2
    for i, a in enumerate(sys.argv):
        if a == "--scale" and i + 1 < len(sys.argv):
            scale = int(sys.argv[i + 1])

    path = os.path.join(B.SRC, B.SOURCE_FILE[expr])
    base = np.array(Image.open(path).convert("RGBA").crop(B.UNION_BBOX))
    imgs = [render(B.make_blink(base.copy(), B.EYE_L, lv), expr, nowarp)
            for lv in LEVELS]
    imgs += [render(B.make_blink(base.copy(), B.EYE_R, lv), expr, nowarp)
             for lv in LEVELS]

    w = FRAME * scale
    h = FRAME * scale
    sheet = Image.new("RGB", (w * 6, h * 2), (250, 250, 252))
    for i, im in enumerate(imgs):
        r, c = divmod(i, 6)
        sheet.paste(im.resize((w, h), Image.LANCZOS), (c * w, r * h))
    sheet.save(out)
    print("-> %s  %dx%d  (上排左眼 下排右眼, level=%s)" % (
        out, sheet.width, sheet.height, LEVELS))


if __name__ == "__main__":
    main()
