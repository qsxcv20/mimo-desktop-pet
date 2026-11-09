#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""scan_bundle.py — 在 MiMo 安装目录里搜索关键字（ripgrep 会把大 bundle 当二进制跳过）。

用法: python scan_bundle.py <keyword> [max_hits]
"""
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "Xiaomi MiMo")
kw = sys.argv[1].encode("utf-8")
maxhits = int(sys.argv[2]) if len(sys.argv) > 2 else 12

hits = 0
scanned = 0
for dirpath, dirnames, filenames in os.walk(ROOT):
    dirnames[:] = [d for d in dirnames
                   if d not in ("locales", "swiftshader", "resources.pak")]
    for fn in filenames:
        if not fn.endswith((".js", ".mjs", ".cjs", ".json", ".asar")):
            continue
        p = os.path.join(dirpath, fn)
        try:
            sz = os.path.getsize(p)
        except OSError:
            continue
        if sz > 200 * 1024 * 1024:
            continue
        try:
            data = open(p, "rb").read()
        except OSError:
            continue
        scanned += 1
        idx = 0
        while hits < maxhits:
            i = data.find(kw, idx)
            if i < 0:
                break
            lo = max(0, i - 220)
            hi = min(len(data), i + 260)
            frag = data[lo:hi].decode("utf-8", "replace")
            print("=== %s @%d ===" % (os.path.relpath(p, ROOT), i))
            print(frag.replace("\n", " "))
            print()
            hits += 1
            idx = i + len(kw)
print("scanned %d files, %d hits" % (scanned, hits))
