#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""hunt_schema.py — 找 usage 的 zod schema 字段。

用法: python hunt_schema.py
"""
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
P = (r"C:\Users\yang2\AppData\Roaming\Xiaomi MiMo\runtime-res\releases"
     r"\renderer\assets\index~OePpplEX.js")

d = open(P, encoding="utf-8", errors="replace").read()
print("file len", len(d))

for m in re.finditer(r"resetDate", d):
    i = m.start()
    print("=" * 90)
    print("@%d" % i)
    print(d[max(0, i - 700):i + 500].replace("\n", " "))
    break
