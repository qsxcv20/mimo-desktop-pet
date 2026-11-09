#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""scan_acct.py — 提取账号状态附近的完整内容。"""
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

LS = os.path.join(os.environ["APPDATA"], "Xiaomi MiMo", "Local Storage", "leveldb")
PATS = [b"mimo-pro", b"V5gi3saeo", b"user_unique", b"tokens_%"]

for fn in sorted(os.listdir(LS)):
    p = os.path.join(LS, fn)
    if not os.path.isfile(p):
        continue
    with open(p, "rb") as f:
        data = f.read()
    for pat in PATS:
        for m in list(re.finditer(re.escape(pat), data))[:3]:
            a = max(0, m.start() - 400)
            b = min(len(data), m.end() + 600)
            seg = data[a:b]
            # 只打印可读部分
            txt = "".join(chr(c) if 32 <= c < 127 else ("\n" if c == 10 else ".") for c in seg)
            print("\n--- %s @ %s ---\n%s" % (fn, pat.decode(), txt))
