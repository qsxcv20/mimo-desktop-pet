#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""scan_routes3.py — 找 desktop-api 路由表 + 凭据落盘位置。"""
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

MAIN = r"C:\Users\yang2\AppData\Roaming\Xiaomi MiMo\runtime-res\releases\main\main~DAq2tHkd.mjs"
s = open(MAIN, "r", encoding="utf-8", errors="replace").read()


def ctx(pat, radius=900, limit=3, label=""):
    print("\n########## %s ##########" % (label or pat))
    for i, m in enumerate(re.finditer(re.escape(pat), s)):
        a = max(0, m.start() - radius)
        b = min(len(s), m.end() + radius)
        print("\n--- #%d @%d ---\n%s" % (i, m.start(), s[a:b]))
        if i + 1 >= limit:
            break


ctx('"/health"', 1100, 2, "health 路由表")
ctx('"/sessions"', 1100, 2, "sessions 路由表")
ctx("getUserUsage", 900, 3, "getUserUsage IPC")
ctx("mimo:getUserUsage", 700, 2, "mimo:getUserUsage")
