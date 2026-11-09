#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""find_eyes2.py — 在统一裁剪框里自动定位两只眼睛，供眨眼动画使用。"""
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import numpy as np
from PIL import Image

SRC = r"D:\桌面宠物\assets\src"
EXPRS = ["idle", "happy", "think", "tired"]


def load_all():
    imgs = {}
    for n in EXPRS:
        im = Image.open(os.path.join(SRC, "mimo-%s-v2@2048.png" % n)).convert("RGBA")
        imgs[n] = im
    boxes = [imgs[n].getchannel("A").getbbox() for n in EXPRS]
    union = (min(b[0] for b in boxes), min(b[1] for b in boxes),
             max(b[2] for b in boxes), max(b[3] for b in boxes))
    print("各表情 bbox:", dict(zip(EXPRS, boxes)))
    print("union bbox :", union, "-> size", (union[2] - union[0], union[3] - union[1]))
    out = {}
    for n in EXPRS:
        out[n] = imgs[n].crop(union)
    return out, union


def srgb_dist(a, b):
    return np.sqrt(np.sum((a.astype(np.float32) - b.astype(np.float32)) ** 2, axis=-1))


def find_eyes(img):
    arr = np.array(img).astype(np.float32)
    H, W = arr.shape[:2]
    R, G, B, A = arr[..., 0], arr[..., 1], arr[..., 2], arr[..., 3]
    # 琥珀/橙色虹膜：红高、绿中、蓝低
    mask = (R > 185) & (G > 85) & (G < 205) & (B < 135) & (A > 200)
    # 只看脸部区域
    u = np.arange(W)[None, :] / float(W)
    v = np.arange(H)[:, None] / float(H)
    face = (u > 0.24) & (u < 0.78) & (v > 0.44) & (v < 0.72)
    mask = mask & face
    ys, xs = np.nonzero(mask)
    print("候选像素:", len(xs))
    if len(xs) == 0:
        return None

    # 连通域（简易 BFS）
    pts = set(zip(xs.tolist(), ys.tolist()))
    clusters = []
    while pts:
        seed = pts.pop()
        stack = [seed]
        comp = [seed]
        while stack:
            x, y = stack.pop()
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    q = (x + dx, y + dy)
                    if q in pts:
                        pts.discard(q)
                        stack.append(q)
                        comp.append(q)
        clusters.append(comp)
    clusters.sort(key=len, reverse=True)
    out = []
    for comp in clusters[:6]:
        cx = [p[0] for p in comp]
        cy = [p[1] for p in comp]
        out.append((len(comp), min(cx), min(cy), max(cx), max(cy)))
        print("  簇 size=%-6d bbox=(%d,%d,%d,%d)" % out[-1])
    # 取面积最大的两个簇且都够大
    big = [c for c in out if c[0] > 1500][:2]
    if len(big) == 2:
        big.sort(key=lambda c: c[1])
        return big
    return out


imgs, union = load_all()
print("\n=== idle 眼睛检测 ===")
res = find_eyes(imgs["idle"])
print("\n=== happy 眼睛检测 ===")
find_eyes(imgs["happy"])
print("\n=== think 眼睛检测 ===")
find_eyes(imgs["think"])
print("\n=== tired 眼睛检测 ===")
find_eyes(imgs["tired"])

print("\n=== 采样眼睛中心颜色 ===")
for n in EXPRS:
    a = np.array(imgs[n])
    if res and len(res) == 2:
        for tag, c in zip("LR", res):
            x0, y0, x1, y1 = c[1], c[2], c[3], c[4]
            cx, cy = (x0 + x1) // 2, (y0 + y1) // 2
            print("  %-6s %s center(%d,%d) rgba=%s" % (n, tag, cx, cy, a[cy, cx]))
