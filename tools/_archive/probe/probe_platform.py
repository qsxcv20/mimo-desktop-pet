#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""probe_platform.py — 定位平台 base 并探测额度端点。"""
import json
import os
import re
import sys
import urllib.request
import urllib.error

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

MAIN = r"C:\Users\yang2\AppData\Roaming\Xiaomi MiMo\runtime-res\releases\main\main~DAq2tHkd.mjs"
s = open(MAIN, "r", encoding="utf-8", errors="replace").read()

print("=== 主 bundle 里的 mimo-server / xiaomimimo base ===")
for pat in (r'https?://[a-z0-9\.\-]*xiaomimimo\.com[^\s"\',)]*',
            r'https?://[a-z0-9\.\-]*mimo-server[^\s"\',)]*'):
    hits = sorted(set(re.findall(pat, s)))
    for h in hits[:25]:
        print("   ", h)

print("\n=== region -> base 映射（om 表）===")
m = re.search(r'om\s*=\s*\{', s)
if m:
    a = m.start()
    seg = s[a:a + 1200]
    print(seg)

print("\n=== 探测额度端点 ===")
BASES = [
    "http://mimo-server-cn.xiaomimimo.com",
    "https://mimo-server-cn.xiaomimimo.com",
    "http://api.xiaomimimo.com",
    "https://api.xiaomimimo.com",
]
PATHS = ["/user/usage", "/api/v1/usage", "/user/xiaomi/subscription/self",
         "/api/v1/balance", "/api/v1/userProfile"]


def probe(base, path):
    url = base + path
    try:
        req = urllib.request.Request(url, headers={
            "Accept": "application/json",
            "User-Agent": "MiMoDesktop/26.1102.21158",
            "X-Mimo-Source": "mimocode-desktop",
            "Origin": "https://mimo.xiaomimimo.com",
        })
        with urllib.request.urlopen(req, timeout=8) as r:
            return r.status, r.read(900).decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read(900).decode("utf-8", "replace")
    except Exception as e:
        return None, str(e)[:150]


for base in BASES:
    for path in PATHS:
        st, body = probe(base, path)
        if st is None:
            print("  %-42s %-34s -> ERR %s" % (base, path, body[:60]))
        else:
            print("  %-42s %-34s -> %s  %s" % (base, path, st, body[:220].replace("\n", " ")))
