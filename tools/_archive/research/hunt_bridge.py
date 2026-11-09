#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""hunt_bridge.py — 找 window.mimo 的调用方法名。

用法: python hunt_bridge.py
"""
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = (r"C:\Users\yang2\AppData\Roaming\Xiaomi MiMo\runtime-res\releases")
PAT = re.compile(r"window\.mimo\.(\w+)|mimo\.invoke\(|\.invoke\(\s*[\"']mimo:")


def main():
    seen = {}
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
                for m in PAT.finditer(d):
                    k = m.group(0)
                    if k not in seen:
                        seen[k] = (f, d[max(0, m.start() - 160):m.start() + 200]
                                   .replace("\n", " "))
    for k, (f, ctx) in list(seen.items())[:16]:
        print("%-30s  (%s)" % (k, f))
        print("    " + ctx[:320])
        print()


if __name__ == "__main__":
    main()
