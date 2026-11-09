#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""scan_secure.py — 找 secureStorage 落盘位置。"""
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

UD = os.path.join(os.environ["APPDATA"], "Xiaomi MiMo")
MAIN = os.path.join(UD, "runtime-res", "releases", "main", "main~DAq2tHkd.mjs")
s = open(MAIN, "r", encoding="utf-8", errors="replace").read()

for pat in ("secureStorage", "Pw=", "safeStorage", "isEncryptionAvailable"):
    idxs = [m.start() for m in re.finditer(re.escape(pat), s)]
    print("\n######## %s  x%d ########" % (pat, len(idxs)))
    for i in idxs[:3]:
        a = max(0, i - 800)
        b = min(len(s), i + 1000)
        print("\n--- @%d ---\n%s" % (i, s[a:b]))
