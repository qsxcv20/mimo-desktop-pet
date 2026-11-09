#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""scan_base.py — 找 base URL 合成函数与 region 映射。"""
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

MAIN = r"C:\Users\yang2\AppData\Roaming\Xiaomi MiMo\runtime-res\releases\main\main~DAq2tHkd.mjs"
s = open(MAIN, "r", encoding="utf-8", errors="replace").read()


def ctx(pat, radius=1500, limit=2, label=None):
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


ctx("token-plan-cn", 1600, 2, "token-plan-cn")
ctx("api.xiaomimimo.com/v1", 1800, 2, "api.xiaomimimo.com/v1")
ctx("function xn(", 900, 3, "xn()")
