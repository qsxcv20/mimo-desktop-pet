#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""hunt_channels.py — 在 preload 里筛出「额度/用量」相关的 mimo: IPC 通道名。

用法: python hunt_channels.py [子串]
"""
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = r"C:\Users\yang2\AppData\Roaming\Xiaomi MiMo\runtime-res\releases"
KEY = (sys.argv[1] if len(sys.argv) > 1 else "").lower()

pat = re.compile(rb'"(mimo:[A-Za-z0-9_\-.:]+)"')
seen = {}
for dirpath, dirnames, filenames in os.walk(ROOT):
    for fn in filenames:
        if not fn.endswith((".mjs", ".js", ".cjs")):
            continue
        p = os.path.join(dirpath, fn)
        try:
            if os.path.getsize(p) > 80 * 1024 * 1024:
                continue
            with open(p, "rb") as f:
                data = f.read()
        except Exception:
            continue
        for m in pat.finditer(data):
            name = m.group(1).decode("utf-8", "replace")
            low = name.lower()
            if KEY and KEY not in low:
                continue
            seen.setdefault(name, []).append(os.path.basename(p))

print("命中 %d 条通道（关键字=%r）" % (len(seen), KEY))
for name in sorted(seen):
    print("  %-52s  <- %s" % (name, ", ".join(sorted(set(seen[name]))[:3])))
