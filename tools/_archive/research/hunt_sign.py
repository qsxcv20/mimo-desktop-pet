#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""hunt_sign.py — 在 MiMo bundle 里找平台接口的签名头实现。

用法: python hunt_sign.py <关键字> [起始目录]
"""
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = r"C:\Users\yang2\AppData\Roaming\Xiaomi MiMo\runtime-res\releases"
if len(sys.argv) > 2:
    ROOT = sys.argv[2]
KEY = sys.argv[1] if len(sys.argv) > 1 else "xiaomimimo.com"

pat = re.compile(KEY.encode("utf-8"), re.I)
hits = 0
for dirpath, dirnames, filenames in os.walk(ROOT):
    for fn in filenames:
        if not fn.endswith((".mjs", ".js", ".json", ".cjs")):
            continue
        p = os.path.join(dirpath, fn)
        try:
            size = os.path.getsize(p)
            if size > 80 * 1024 * 1024:
                continue
            with open(p, "rb") as f:
                data = f.read()
        except Exception:
            continue
        for m in pat.finditer(data):
            i = m.start()
            lo = max(0, i - 700)
            hi = min(len(data), i + 700)
            frag = data[lo:hi].decode("utf-8", "replace")
            hits += 1
            print("=" * 100)
            print("%s   (@%d, size=%d)" % (p, i, size))
            print(frag)
            if hits >= 12:
                print("\n(达到上限，停止)")
                sys.exit(0)
if not hits:
    print("未找到关键字:", KEY)
