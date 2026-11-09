#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""eye_contour_probe.py — 探测眼睛的「眼球轮廓」（眼白 + 虹膜）。

原画的眼白是纯白 (255,255,255)，皮肤是 (255,237,225)，
用 HSV 饱和度就能把两者分开：眼白 S≈0，皮肤 S≈30。

用法: python eye_contour_probe.py [expr] [EYE_L|EYE_R]
"""
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
from PIL import Image

import build_anim_sheet as B  # noqa: E402


def main():
    expr = sys.argv[1] if len(sys.argv) > 1 else "idle"
    which = sys.argv[2] if len(sys.argv) > 2 else "EYE_L"

    path = os.path.join(B.SRC, B.SOURCE_FILE[expr])
    arr = np.array(Image.open(path).convert("RGBA").crop(B.UNION_BBOX))
    box = getattr(B, which)
    x0, y0, x1, y1 = box

    import cv2
    sub = np.ascontiguousarray(arr[y0:y1, x0:x1, :3])
    hsv = cv2.cvtColor(sub, cv2.COLOR_RGB2HSV)
    h, s, v = hsv[..., 0], hsv[..., 1], hsv[..., 2]

    orange = (h >= 8) & (h <= 42) & (s > 50) & (v > 140)
    white = (s <= 12) & (v >= 245)
    eyeball = orange | white

    print("box=%s  eyeball px=%d" % (box, int(eyeball.sum())))
    print()
    print("  x   eye_top  eye_bot   (abs y)     orange?  white?")
    for x in range(x0, x1, 6):
        col = eyeball[:, x - x0]
        ys = np.nonzero(col)[0]
        if len(ys) == 0:
            print("%5d   ----    ----" % x)
            continue
        # 取最长连续段
        runs = []
        s0 = ys[0]
        prev = ys[0]
        for y in ys[1:]:
            if y != prev + 1:
                runs.append((s0, prev))
                s0 = y
            prev = y
        runs.append((s0, prev))
        runs.sort(key=lambda r: r[1] - r[0], reverse=True)
        a, b = runs[0]
        no = int(orange[:, x - x0].sum())
        nw = int(white[:, x - x0].sum())
        print("%5d   %5d   %5d   (%5d..%5d)   %5d  %5d" % (
            x, a + y0, b + y0, a + y0, b + y0, no, nw))

    # ASCII 预览
    print("\n--- 框内结构 ASCII (每 4px 一列, 每 6px 一行) ---")
    print("    " + "".join("|" if (x - x0) % 24 == 0 else " " for x in range(x0, x1, 4)))
    for y in range(y0, y1, 6):
        row = ""
        for x in range(x0, x1, 4):
            blk = eyeball[y - y0:y - y0 + 6, x - x0:x - x0 + 4]
            o = orange[y - y0:y - y0 + 6, x - x0:x - x0 + 4].sum()
            w = white[y - y0:y - y0 + 6, x - x0:x - x0 + 4].sum()
            if o > 4:
                row += "O"
            elif w > 4:
                row += "."
            else:
                vv = v[y - y0:y - y0 + 6, x - x0:x - x0 + 4].mean()
                row += "#" if vv < 150 else " "
        print("%4d%s" % (y, row))


if __name__ == "__main__":
    main()
