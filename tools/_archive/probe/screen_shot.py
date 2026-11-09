#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""screen_shot.py — 全屏截图。

用法: python screen_shot.py [输出文件]
"""
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

OUT = sys.argv[1] if len(sys.argv) > 1 else r"D:\桌面宠物\_mimo\screen-now.png"

from PIL import ImageGrab

im = ImageGrab.grab(all_screens=True)
im.save(OUT)
print("已保存 %s (%dx%d)" % (OUT, im.width, im.height))
