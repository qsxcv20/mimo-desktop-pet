#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""hunt_api.py — 在 preload 里找某个 window.mimo.* 方法的定义。

用法: python hunt_api.py <apiName>
"""
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = (r"C:\Users\yang2\AppData\Roaming\Xiaomi MiMo\runtime-res\releases")
NAME = sys.argv[1] if len(sys.argv) > 1 else "getUserUsage"


def main():
    hits = 0
    for sub in ("preload", "renderer"):
        for dp, dn, fn in os.walk(os.path.join(ROOT, sub)):
            for f in fn:
                if not f.endswith((".js", ".mjs")):
                    continue
                p = os.path.join(dp, f)
                try:
                    d = open(p, encoding="utf-8", errors="replace").read()
                except Exception:
                    continue
                pat = re.compile(r'.{160}' + re.escape(NAME) + r'.{240}')
                for m in pat.finditer(d):
                    i = m.start()
                    print("--- %s @%d" % (f, i))
                    print("   " + d[i:i + 420].replace("\n", " "))
                    hits += 1
                    if hits >= 8:
                        return
    if not hits:
        print("未找到", NAME)


if __name__ == "__main__":
    main()
