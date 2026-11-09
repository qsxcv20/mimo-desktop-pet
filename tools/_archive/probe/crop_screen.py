#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""crop_screen.py — 抓桌面并裁剪指定区域（桌宠/气泡特写）。

用法: python crop_screen.py <x1> <y1> <x2> <y2> [输出文件]
"""
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

x1, y1, x2, y2 = (int(a) for a in sys.argv[1:5])
OUT = sys.argv[5] if len(sys.argv) > 5 else r"D:\桌面宠物\_mimo\pet-crop.png"

from PIL import ImageGrab

im = ImageGrab.grab(all_screens=True)
im = im.crop((x1, y1, x2, y2))
im.save(OUT)
print("已保存 %s (%dx%d)" % (OUT, im.width, im.height))
