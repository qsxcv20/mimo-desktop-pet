#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""scan_api_srv.py — 定位 desktop-api 服务器实现与它的路由表。"""
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

MAIN = r"C:\Users\yang2\AppData\Roaming\Xiaomi MiMo\runtime-res\releases\main\main~DAq2tHkd.mjs"
s = open(MAIN, "r", encoding="utf-8", errors="replace").read()


def show(pat, radius=1400, limit=2, label=None):
    print("\n########## %s ##########" % (label or pat))
    n = 0
    for m in re.finditer(re.escape(pat), s):
        a = max(0, m.start() - radius)
        b = min(len(s), m.end() + radius)
        print("\n--- @%d ---\n%s" % (m.start(), s[a:b]))
        n += 1
        if n >= limit:
            break
    if n == 0:
        print("  (无命中)")


show("desktop-api", 1500, 2, "desktop-api")
show('"turns"', 1500, 2, 'turns 路由')
show("authFetch", 1200, 3, "authFetch")
