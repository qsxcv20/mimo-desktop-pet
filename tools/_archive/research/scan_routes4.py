#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""scan_routes4.py — 列出 main bundle 里所有像 API 路径的字符串。"""
import os
import re
import sys
from collections import Counter

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

MAIN = r"C:\Users\yang2\AppData\Roaming\Xiaomi MiMo\runtime-res\releases\main\main~DAq2tHkd.mjs"
s = open(MAIN, "r", encoding="utf-8", errors="replace").read()

pat = re.compile(r'["\'`](/[A-Za-z0-9_\-/:.?=&{}<>\[\]%$,]*)["\'`]')
c = Counter(pat.findall(s))
print("=== 含关键字的路径 ===")
keys = ("usage", "balance", "subscription", "session", "turn", "event", "health",
        "api-key", "token", "user", "quota", "credit", "plan", "account", "me")
for p, n in sorted(c.items()):
    if any(k in p.lower() for k in keys):
        print("  %-60s x%d" % (p, n))

print("\n=== 全部 /v1* 风格路径 ===")
for p, n in sorted(c.items()):
    if p.startswith("/v1"):
        print("  %-60s x%d" % (p, n))

print("\n=== 路由注册处上下文 (health) ===")
for m in list(re.finditer(r"health", s))[:6]:
    a = max(0, m.start() - 500)
    b = min(len(s), m.end() + 500)
    seg = s[a:b]
    if "api" in seg and ("session" in seg or "route" in seg or "method" in seg):
        print("\n--- @%d ---\n%s" % (m.start(), seg))
