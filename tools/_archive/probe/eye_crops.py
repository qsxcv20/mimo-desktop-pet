#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""eye_crops.py — 在精灵图带里自动找到橙色虹膜，裁出各档位的眼睛放大图。

用法: python eye_crops.py <strip.png> <out.png> [row] [scale]
"""
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import numpy as np
from PIL import Image

src, out = sys.argv[1], sys.argv[2]
row = int(sys.argv[3]) if len(sys.argv) > 3 else 0
scale = int(sys.argv[4]) if len(sys.argv) > 4 else 7

im = Image.open(src).convert("RGB")
W, H = im.size
cols = 6
fw = W // cols
arr = np.array(im)

# 找橙色虹膜：R>200, 100<G<210, B<110
mask = (arr[:, :, 0] > 200) & (arr[:, :, 1] > 100) & (arr[:, :, 1] < 215) \
    & (arr[:, :, 2] < 115)
ys, xs = np.nonzero(mask)
# 只取指定行区间
sel = (ys >= row * fw) & (ys < (row + 1) * fw)
ys, xs = ys[sel], xs[sel]
print("橙色像素 %d" % len(xs))

crops = []
for k in range(cols):
    x0 = k * fw
    m = (xs >= x0) & (xs < x0 + fw)
    if not m.any():
        crops.append(Image.new("RGB", (10, 10), (250, 250, 252)))
        continue
    cx = int(xs[m].mean())
    cy = int(ys[m].mean())
    ex = min(fw - 1, max(0, cx - 22))
    ey = min(row * fw + fw - 1, max(row * fw, cy - 16))
    ew = min(fw - ex, 46)
    eh = min((row + 1) * fw - ey, 38)
    c = im.crop((x0 + ex, ey, x0 + ex + ew, ey + eh))
    crops.append(c.resize((ew * scale, eh * scale), Image.LANCZOS))

w = max(c.width for c in crops)
h = max(c.height for c in crops)
sh = Image.new("RGB", (w * len(crops) + 4 * (len(crops) - 1), h), (250, 250, 252))
for i, c in enumerate(crops):
    sh.paste(c, (i * (w + 4), 0))
sh.save(out)
print("-> %s %dx%d" % (out, sh.width, sh.height))
