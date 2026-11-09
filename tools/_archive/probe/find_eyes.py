#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
find_eyes.py — 在 MiMo 立绘里程序化定位双眼（金琥珀色高饱和小色块），
供动画生成器做眨眼用。只做分析，不改素材。
"""
import sys, os
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import numpy as np
from PIL import Image

SRC = r"D:\桌面宠物\assets\src"


def analyse(fn):
    p = os.path.join(SRC, fn)
    img = Image.open(p).convert("RGBA")
    a = np.array(img)
    rgb = a[:, :, :3].astype(np.int16)
    al = a[:, :, 3]
    R, G, B = rgb[:, :, 0], rgb[:, :, 1], rgb[:, :, 2]

    # 金琥珀色：R 高、G 中高、B 中低，且有一定饱和度
    mask = (al > 200) & (R > 195) & (G > 140) & (G < 225) & (B > 70) & (B < 175) \
        & ((R - B) > 60) & ((G - B) > 25)

    ys, xs = np.nonzero(mask)
    if len(xs) == 0:
        print("  %s: 没找到金色像素" % fn)
        return None
    # 只看脸部高度范围（图像上部 15%~50%）
    H = img.height
    sel = (ys > H * 0.12) & (ys < H * 0.50)
    ys, xs = ys[sel], xs[sel]
    print("  %-26s 金色像素 %d 个（在脸高范围内）" % (fn, len(xs)))

    # 简易聚类：按 x 分组（双眼在两侧）
    if len(xs) == 0:
        return None
    order = np.argsort(xs)
    xs, ys = xs[order], ys[order]
    groups = []
    cur = [0]
    for i in range(1, len(xs)):
        if xs[i] - xs[i - 1] > 25:
            groups.append(cur); cur = []
        cur.append(i)
    groups.append(cur)
    groups = [g for g in groups if len(g) >= 25]
    groups.sort(key=len, reverse=True)
    print("     候选簇(按像素数): %s" %
          [("%d 个, x=%d..%d, y=%d..%d" % (len(g), xs[g].min(), xs[g].max(),
                                           ys[g].min(), ys[g].max())) for g in groups[:6]])
    if len(groups) >= 2:
        g1, g2 = groups[0], groups[1]
        # 左眼 = 中心靠左的那个
        if xs[g1].mean() > xs[g2].mean():
            g1, g2 = g2, g1
        for tag, g in (("左眼", g1), ("右眼", g2)):
            print("     %s bbox = (x %d..%d, y %d..%d)  中心=(%.0f,%.0f)  宽%d 高%d"
                  % (tag, xs[g].min(), xs[g].max(), ys[g].min(), ys[g].max(),
                     (xs[g].min() + xs[g].max()) / 2, (ys[g].min() + ys[g].max()) / 2,
                     xs[g].max() - xs[g].min(), ys[g].max() - ys[g].min()))
    return groups


for fn in ["mimo-idle-v2@2048.png", "mimo-happy-v2@2048.png",
           "mimo-think-v2@2048.png", "mimo-tired-v2@2048.png"]:
    analyse(fn)
    print()
