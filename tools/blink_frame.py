#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""blink_frame.py — 存出 256px 精灵帧（可指定档位），用于定位问题出在哪一步。

用法: python blink_frame.py [expr] [level] [out.png] [--nowarp]
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


def main():
    expr = sys.argv[1] if len(sys.argv) > 1 else "idle"
    level = float(sys.argv[2]) if len(sys.argv) > 2 else 0.6
    out = sys.argv[3] if len(sys.argv) > 3 else \
        r"D:\桌面宠物\_mimo\frame-%s-%s.png" % (expr, level)
    nowarp = "--nowarp" in sys.argv

    path = os.path.join(B.SRC, B.SOURCE_FILE[expr])
    arr_full = np.array(Image.open(path).convert("RGBA").crop(B.UNION_BBOX))
    bl = B.make_blink(arr_full.copy(), B.EYE_L, level)

    W0f, H0f = B.W0, B.H0
    w1, h1 = int(W0f * B.RES), int(H0f * B.RES)
    a = np.array(Image.fromarray(bl).resize((w1, h1), Image.LANCZOS))
    if not nowarp:
        dx, dy = B.build_field(h1, w1, expr, 0.0, s=B.RES)
        a = B.warp(a, dx, dy)
    pm = B.place_into_frame(a, FRAME, MARGIN)
    pm = pm.convert("RGBA")
    bg = Image.new("RGBA", pm.size, (238, 238, 242, 255))
    bg.alpha_composite(pm)
    bg = bg.convert("RGB").resize((FRAME * 4, FRAME * 4), Image.NEAREST)
    bg.save(out)
    print("-> %s  %s" % (out, bg.size))


if __name__ == "__main__":
    main()
