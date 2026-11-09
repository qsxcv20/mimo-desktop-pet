#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""scan_engine_call.py — 看主进程怎么调 engine 本地 API（POST 形状）。"""
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

MAIN = r"C:\Users\yang2\AppData\Roaming\Xiaomi MiMo\runtime-res\releases\main\main~DAq2tHkd.mjs"
s = open(MAIN, "r", encoding="utf-8", errors="replace").read()


def show(pat, radius=1100, limit=2):
    print("\n########## %s ##########" % pat)
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


show('"/api/meta"', 1200, 2)
show('"/api/v1/balance"', 1300, 2)
