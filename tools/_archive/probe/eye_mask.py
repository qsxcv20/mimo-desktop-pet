#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""eye_mask.py — 把眼部分类掩膜染色叠回原图，肉眼核对掩膜对不对。

D=睫毛(红) W=眼白(蓝) O=虹膜(绿) S=皮肤(半透明灰)
用法: python eye_mask.py [expr] [EYE_L|EYE_R] [scale] [out.png]
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
    scale = float(sys.argv[3]) if len(sys.argv) > 3 else 3.0
    out = sys.argv[4] if len(sys.argv) > 4 else os.path.join(
        B.OUT, "eye-mask-%s-%s.png" % (expr, which))

    path = os.path.join(B.SRC, B.SOURCE_FILE[expr])
    arr = np.array(Image.open(path).convert("RGBA").crop(B.UNION_BBOX))
    x0, y0, x1, y1 = getattr(B, which)
    sub = np.ascontiguousarray(arr[y0:y1, x0:x1, :3])
    hsv = cv2.cvtColor(sub, cv2.COLOR_RGB2HSV)
    h, s, v = hsv[..., 0], hsv[..., 1], hsv[..., 2]
    dark = v < 150
    white = (s <= 16) & (v >= 246)
    orange = (h >= 8) & (h <= 42) & (s > 50) & (v > 110)

    vis = sub.astype(np.float32).copy()
    vis[white] = vis[white] * 0.35 + np.array([0, 90, 255]) * 0.65
    vis[orange] = vis[orange] * 0.35 + np.array([0, 230, 60]) * 0.65
    vis[dark] = vis[dark] * 0.30 + np.array([255, 0, 0]) * 0.70
    # 皮肤区整体压暗一点，方便区分
    skin = ~(white | orange | dark)
    vis[skin] = vis[skin] * 0.72

    img = Image.fromarray(np.clip(vis, 0, 255).astype(np.uint8))
    w, hgt = img.size
    img = img.resize((int(w * scale), int(hgt * scale)), Image.NEAREST)

    # 画 20px 网格（源像素）
    from PIL import ImageDraw
    d = ImageDraw.Draw(img)
    for gx in range(x0, x1, 20):
        px = (gx - x0) * scale
        d.line([(px, 0), (px, img.size[1])], fill=(255, 255, 0), width=1)
        d.text((px + 2, 2), str(gx), fill=(255, 255, 0))
    for gy in range(y0, y1, 20):
        py = (gy - y0) * scale
        d.line([(0, py), (img.size[0], py)], fill=(0, 255, 255), width=1)
        d.text((2, py + 2), str(gy), fill=(0, 255, 255))
    img.save(out)
    print("-> %s  %s" % (out, img.size))


if __name__ == "__main__":
    main()
