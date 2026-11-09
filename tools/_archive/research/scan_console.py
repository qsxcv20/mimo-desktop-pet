#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""scan_console.py — 在开放平台 JS 里挖签名实现。

用法: python scan_console.py <关键字> [最大命中]
"""
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

JS = r"D:\桌面宠物\_mimo\console\main.dd4c96b8f4cc7ba6.chunk.js"
KEY = sys.argv[1] if len(sys.argv) > 1 else "SIGN_KEY_MISSING"
MAX = int(sys.argv[2]) if len(sys.argv) > 2 else 6
PAD = 700

data = open(JS, "r", encoding="utf-8", errors="replace").read()
pat = re.compile(re.escape(KEY))
hits = 0
for m in pat.finditer(data):
    i = m.start()
    hits += 1
    print("=" * 100)
    print("HIT %d @%d / %d" % (hits, i, len(data)))
    print(data[max(0, i - PAD):i + PAD].replace("\n", " "))
    if hits >= MAX:
        break
if not hits:
    print("未命中:", KEY)
