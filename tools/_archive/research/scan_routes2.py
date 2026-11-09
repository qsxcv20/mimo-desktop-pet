#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""scan_routes2.py — 从 Electron 主 bundle 里挖完整路由表与上下文。"""
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

p = r"C:\Users\yang2\AppData\Roaming\Xiaomi MiMo\runtime-res\releases\main\main~DAq2tHkd.mjs"
s = open(p, "r", encoding="utf-8", errors="replace").read()


def ctx(pat, radius=420, limit=6):
    out = []
    for m in re.finditer(re.escape(pat), s):
        a = max(0, m.start() - radius)
        b = min(len(s), m.end() + radius)
        out.append(s[a:b])
        if len(out) >= limit:
            break
    return out


print("############ /v1/usage 上下文 ############")
for i, c in enumerate(ctx("/v1/usage", 500, 3)):
    print("\n--- #%d ---\n%s" % (i, c))

print("\n\n############ /v1/balance 上下文 ############")
for i, c in enumerate(ctx("/v1/balance", 500, 2)):
    print("\n--- #%d ---\n%s" % (i, c))

print("\n\n############ user/usage 上下文 ############")
for i, c in enumerate(ctx("user/usage", 700, 3)):
    print("\n--- #%d ---\n%s" % (i, c))

print("\n\n############ desktop-api 路由表候选 ############")
for m in re.finditer(r'"(/v1/[a-zA-Z0-9_\-/:{}<>]*)"', s):
    pass
routes = sorted(set(re.findall(r'"(/v1[a-zA-Z0-9_\-/:{}<>\.]*)"', s)))
print(len(routes))
for r in routes:
    print("  ", r)
