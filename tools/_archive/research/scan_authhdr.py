#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""scan_authhdr.py — 看 sessionFetch / ru 怎么带凭据。"""
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

UD = os.path.join(os.environ["APPDATA"], "Xiaomi MiMo")
MAIN = os.path.join(UD, "runtime-res", "releases", "main", "main~DAq2tHkd.mjs")
s = open(MAIN, "r", encoding="utf-8", errors="replace").read()

for pat in ("function ru(", "sessionFetch", "serviceToken", "userServiceToken",
            "account.xiaomi.com", "Authorization"):
    idxs = [m.start() for m in re.finditer(re.escape(pat), s)]
    print("\n######## %s  x%d ########" % (pat, len(idxs)))
    for i in idxs[:3]:
        a = max(0, i - 700)
        b = min(len(s), i + 900)
        print("\n--- @%d ---\n%s" % (i, s[a:b]))
