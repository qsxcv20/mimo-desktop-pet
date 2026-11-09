#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""scan_zip.py — 在 zip（MiMo runtime seed 包）里搜索关键字。

用法: python scan_zip.py <zip> <keyword> [max_hits]
"""
import os
import sys
import zipfile

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

zp = sys.argv[1]
kw = sys.argv[2].encode("utf-8")
maxhits = int(sys.argv[3]) if len(sys.argv) > 3 else 8

z = zipfile.ZipFile(zp)
names = [n for n in z.namelist() if not n.endswith("/")]
print("zip entries: %d" % len(names))
hits = 0
for n in names:
    try:
        data = z.read(n)
    except Exception:
        continue
    idx = 0
    while hits < maxhits:
        i = data.find(kw, idx)
        if i < 0:
            break
        lo = max(0, i - 300)
        hi = min(len(data), i + 400)
        print("=== %s @%d (%d bytes) ===" % (n, i, len(data)))
        print(data[lo:hi].decode("utf-8", "replace").replace("\n", " "))
        print()
        hits += 1
        idx = i + len(kw)
    if hits >= maxhits:
        break
print("hits=%d" % hits)
