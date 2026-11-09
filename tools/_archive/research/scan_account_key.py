#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""scan_account_key.py — 找 accountKey / authFetch 的来源。"""
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

MAIN = r"C:\Users\yang2\AppData\Roaming\Xiaomi MiMo\runtime-res\releases\main\main~DAq2tHkd.mjs"
s = open(MAIN, "r", encoding="utf-8", errors="replace").read()

for m in list(re.finditer(r"accountKey", s))[:6]:
    a = max(0, m.start() - 800)
    b = min(len(s), m.end() + 800)
    print("\n===== accountKey @%d =====\n%s" % (m.start(), s[a:b]))

print("\n\n===== authFetch: 定义处 =====")
for m in list(re.finditer(r"authFetch\s*[:=]", s))[:8]:
    a = max(0, m.start() - 900)
    b = min(len(s), m.end() + 900)
    seg = s[a:b]
    print("\n--- @%d ---\n%s" % (m.start(), seg))
