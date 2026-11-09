#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""hunt_ctx.py — 把 bundle 里某个关键字的所有命中点连同上下文导出来。

用法: python hunt_ctx.py <关键字> [文件路径]
"""
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

KEY = sys.argv[1]
PATH = sys.argv[2] if len(sys.argv) > 2 else \
    r"C:\Users\yang2\AppData\Roaming\Xiaomi MiMo\runtime-res\releases\main\main~DAq2tHkd.mjs"
PAD = int(sys.argv[3]) if len(sys.argv) > 3 else 2500
CASE = os.environ.get("HUNT_CASE", "0") == "1"

data = open(PATH, "rb").read()
pat = re.compile(KEY.encode("utf-8"), 0 if CASE else re.I)
n = 0
for m in pat.finditer(data):
    i = m.start()
    lo = max(0, i - PAD)
    hi = min(len(data), i + PAD)
    n += 1
    print("=" * 110)
    print("HIT #%d  @%d / %d   in %s" % (n, i, len(data), os.path.basename(PATH)))
    print("-" * 110)
    print(data[lo:hi].decode("utf-8", "replace"))
    if n >= 6:
        break
if not n:
    print("未命中")
