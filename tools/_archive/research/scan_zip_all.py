#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""scan_zip_all.py — 列出 zip 内所有关键字出现位置（过滤文档区）。

用法: python scan_zip_all.py <zip> <keyword> [skip_first_n]
"""
import sys
import zipfile

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

zp = sys.argv[1]
kw = sys.argv[2].encode("utf-8")
skip = int(sys.argv[3]) if len(sys.argv) > 3 else 0

z = zipfile.ZipFile(zp)
for n in z.namelist():
    if n.endswith("/"):
        continue
    try:
        data = z.read(n)
    except Exception:
        continue
    idx = 0
    k = 0
    while True:
        i = data.find(kw, idx)
        if i < 0:
            break
        k += 1
        if k > skip:
            lo = max(0, i - 260)
            hi = min(len(data), i + 320)
            print("=== %s @%d ===" % (n, i))
            print(data[lo:hi].decode("utf-8", "replace").replace("\n", " "))
            print()
        idx = i + len(kw)
    if k:
        print("### %s : %d hits" % (n, k))
