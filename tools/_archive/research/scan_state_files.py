#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""scan_state_files.py — 列出主 bundle 里所有 *.json 字符串字面量。"""
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

MAIN = r"C:\Users\yang2\AppData\Roaming\Xiaomi MiMo\runtime-res\releases\main\main~DAq2tHkd.mjs"
s = open(MAIN, "r", encoding="utf-8", errors="replace").read()

names = sorted(set(re.findall(r'"([A-Za-z0-9_\-]{2,40}\.json)"', s)))
print("=== *.json 字面量 (%d) ===" % len(names))
for n in names:
    print("   ", n)

print("\n=== 与状态/凭据相关的路径拼接 ===")
for pat in (r'"[a-z\-]{3,30}-state"', r'"[a-z\-]{3,30}\.state"',
            r'"[a-z\-]{3,30}-store"', r'"auth[a-z\-]*"'):
    hits = sorted(set(re.findall(pat, s)))
    print(" ", pat, "->", hits[:30])

print("\n=== 'xiaomi' 附近的 store 字段 ===")
for m in list(re.finditer(r'xiaomi:', s))[:8]:
    a = max(0, m.start() - 320)
    b = min(len(s), m.end() + 320)
    print("\n--- @%d ---\n%s" % (m.start(), s[a:b]))
