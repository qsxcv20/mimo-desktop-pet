#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""anim_metrics.py — 量化精灵图每一帧的姿态：alpha 包围盒（上下左右）、质心、面积。

用来检查动画首尾衔接是否平滑（例如 happy 弹跳最后���有没有落回待机高度，
切回 idle 时会不会突然「跳一下」）。
"""
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SPRITE = r"D:\桌面宠物\build\mimo-witch"


def main():
    with open(os.path.join(SPRITE, "manifest.json"), "r", encoding="utf-8") as f:
        mf = json.load(f)
    fw, fh = mf["frameWidth"], mf["frameHeight"]

    from PIL import Image
    import numpy as np
    im = Image.open(os.path.join(SPRITE, mf["spritesheet"])).convert("RGBA")
    a = np.asarray(im)

    names = {v["row"]: k for k, v in mf["animations"].items()}
    for row in sorted(names):
        print("\n=== row %d  %s ===" % (row, names[row]))
        print("  frame   top  bottom  left  right   height   area")
        prev = None
        for c in range(mf["columns"]):
            sub = a[row * fh:(row + 1) * fh, c * fw:(c + 1) * fw]
            alpha = sub[:, :, 3]
            ys, xs = np.nonzero(alpha > 16)
            if len(ys) == 0:
                print("  %5d  (empty)" % c)
                continue
            top, bot = int(ys.min()), int(ys.max())
            left, right = int(xs.min()), int(xs.max())
            h = bot - top + 1
            area = int((alpha > 16).sum())
            flag = ""
            if prev is not None and abs(top - prev) >= 3:
                flag = "  <-- 顶边跳变 %+d" % (top - prev)
            print("  %5d  %4d  %5d  %4d  %4d  %6d  %6d%s"
                  % (c, top, bot, left, right, h, area, flag))
            prev = top


if __name__ == "__main__":
    main()
