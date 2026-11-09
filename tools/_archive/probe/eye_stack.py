#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""eye_stack.py — 把眼睛区域逐列做「纵向色块剖面」，看清真实结构。

用法: python eye_stack.py [expr] [EYE_L|EYE_R] [step]

分类（按原画实测的语义）：
  D = 深棕睫毛   V < 150
  W = 纯白眼白   S<=16 & V>=246
  O = 橙色虹膜   H in [8,42] & S>50 & V>110
  S = 皮肤/其它
输出是 run-length 编码： y0..y1 区间内的连续同色段。
"""
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__))))

import cv2
import numpy as np
from PIL import Image

import build_anim_sheet as B  # noqa: E402


def classify(arr, box):
    x0, y0, x1, y1 = box
    sub = np.ascontiguousarray(arr[y0:y1, x0:x1, :3])
    hsv = cv2.cvtColor(sub, cv2.COLOR_RGB2HSV)
    h, s, v = hsv[..., 0], hsv[..., 1], hsv[..., 2]
    dark = v < 150
    white = (s <= 16) & (v >= 246)
    orange = (h >= 8) & (h <= 42) & (s > 50) & (v > 110)
    cls = np.full(sub.shape[:2], "S", dtype="<U1")
    cls[orange] = "O"
    cls[white] = "W"
    cls[dark] = "D"
    return cls


def main():
    expr = sys.argv[1] if len(sys.argv) > 1 else "idle"
    which = sys.argv[2] if len(sys.argv) > 2 else "EYE_L"
    step = int(sys.argv[3]) if len(sys.argv) > 3 else 10

    path = os.path.join(B.SRC, B.SOURCE_FILE[expr])
    arr = np.array(Image.open(path).convert("RGBA").crop(B.UNION_BBOX))
    box = getattr(B, which)
    x0, y0, x1, y1 = box
    cls = classify(arr, box)

    iris = B._find_iris(arr, box)
    print("expr=%s %s box=%s" % (expr, which, box))
    print("iris =", iris)
    print()

    hdr = "x    "
    for x in range(x0, x1, step):
        hdr += "%-14d" % x
    print(hdr)
    for x in range(x0, x1, step):
        col = cls[:, x - x0]
        runs = []
        cur = col[0]
        s = 0
        for i in range(1, len(col)):
            if col[i] != cur:
                runs.append("%s%d-%d" % (cur, s + y0, i - 1 + y0))
                cur = col[i]
                s = i
        runs.append("%s%d-%d" % (cur, s + y0, len(col) - 1 + y0))
        print("x=%-4d %s" % (x, " ".join(runs)))


if __name__ == "__main__":
    main()
