#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""eye_debug.py — 把「眼球上下沿 / 睫毛带 / 有效性」的逐列原始值全打出来。

用法: python eye_debug.py [expr] [EYE_L|EYE_R]
"""
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__))))

import cv2
import numpy as np
from PIL import Image

import build_anim_sheet as B  # noqa: E402


def main():
    expr = sys.argv[1] if len(sys.argv) > 1 else "idle"
    which = sys.argv[2] if len(sys.argv) > 2 else "EYE_L"

    path = os.path.join(B.SRC, B.SOURCE_FILE[expr])
    arr = np.array(Image.open(path).convert("RGBA").crop(B.UNION_BBOX))
    x0, y0, x1, y1 = getattr(B, which)
    H, W = arr.shape[:2]

    R = arr[:, :, 0].astype(np.int16)
    Bc = arr[:, :, 2].astype(np.int16)
    Vm = arr[:, :, :3].max(axis=2)
    warm = ((R - Bc) > 0.55 * R) & (Vm < 165)

    disc = B._iris_disc(arr, (x0, y0, x1, y1))
    if disc is None:
        print("disc = None")
        return
    hsv = cv2.cvtColor(np.ascontiguousarray(arr[y0:y1, x0:x1, :3]),
                       cv2.COLOR_RGB2HSV)
    white = np.zeros((H, W), np.uint8)
    white[y0:y1, x0:x1] = ((hsv[..., 1] <= 16) & (hsv[..., 2] >= 246)).astype(np.uint8)
    white = cv2.morphologyEx(
        white, cv2.MORPH_OPEN,
        cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))).astype(bool)

    eyeball = np.zeros((H, W), bool)
    eyeball[y0:y1, x0:x1] = disc.astype(bool)
    eyeball |= white

    print("expr=%s %s box=%s" % (expr, which, (x0, y0, x1, y1)))
    print("  x   openT openB  lashT lashB  gap  有效")
    for i in range(disc.shape[1]):
        x = i + x0
        ys = np.nonzero(eyeball[:, x])[0]
        if len(ys) == 0:
            continue
        ot, ob = int(ys.min()), int(ys.max())
        lt = lb = -1
        y = y0
        while y < ot:
            if warm[y, x]:
                s = y
                while y < ot and warm[y, x]:
                    y += 1
                if y - s >= 3:
                    lt, lb = s, y - 1
                    break
            else:
                y += 1
        gap = ot - lb
        ok = (lt >= 0) and (lb <= ot - 1) and (gap <= 45) and (ob - ot >= 5)
        print("%5d %6d %5d %6d %5d %5d  %s" %
              (x, ot, ob, lt, lb, gap, "Y" if ok else "."))


if __name__ == "__main__":
    main()
