#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""eye_stats.py — 统计每帧眼睛区域的像素特征，定位被眨眼逻辑改坏的帧。

特征：
    orange   橙色虹膜像素（V>150 的橙）—— 睁眼时多，闭眼时应该≈0
    dark     深棕睫毛/睑缘像素
    skin     肤色像素
happy 源图本来就是闭着的笑眼，所以「orange 应该一直≈0」；
如果某些帧 orange 突然变高，说明眨眼逻辑把闭眼重新画成了睁眼。
"""
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SPRITE = r"D:\桌面宠物\build\mimo-witch"

# 256 帧里的眼睛区域（目测 grid-happy2.png 得到）
BOX = (78, 130, 180, 190)


def main():
    with open(os.path.join(SPRITE, "manifest.json"), "r", encoding="utf-8") as f:
        mf = json.load(f)
    fw, fh = mf["frameWidth"], mf["frameHeight"]

    from PIL import Image
    import numpy as np
    im = Image.open(os.path.join(SPRITE, mf["spritesheet"])).convert("RGBA")
    a = np.asarray(im)

    x0, y0, x1, y1 = BOX
    print("box =", BOX)
    print(" row  frame   orange   dark   skin   |  与帧0的差异像素")
    for row in range(4):
        base = None
        print("--- row %d ---" % row)
        for c in range(mf["columns"]):
            sub = a[row * fh + y0:row * fh + y1, c * fw + x0:c * fw + x1]
            rgb = sub[:, :, :3].astype(np.int16)
            r, g, b = rgb[:, :, 0], rgb[:, :, 1], rgb[:, :, 2]
            orange = int(((r > 200) & (g > 120) & (g < 215) & (b < 190) &
                          (r - b > 60)).sum())
            dark = int(((r < 130) & (g < 110) & (b < 100)).sum())
            skin = int(((r > 235) & (g > 200) & (b > 190)).sum())
            if base is None:
                base = sub.astype(np.int16)
                diff = 0
            else:
                diff = int((np.abs(sub.astype(np.int16) - base).max(axis=2) > 30).sum())
            mark = "  <<< 橙色突增" if orange > 60 else ""
            print("  %3d  %5d  %7d  %5d  %5d  |  %6d%s"
                  % (row, c, orange, dark, skin, diff, mark))


if __name__ == "__main__":
    main()
