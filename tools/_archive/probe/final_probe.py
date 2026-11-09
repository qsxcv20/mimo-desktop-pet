#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""final_probe.py — 最后一轮：llm-server 配置 + region base + 平台路径。"""
import json
import os
import re
import socket
import sys
import urllib.request
import urllib.error

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

UD = os.path.join(os.environ["APPDATA"], "Xiaomi MiMo")

print("=== llm-server 配置 ===")
ls = os.path.join(UD, "mimocode", "llm-server")
for dp, dns, fns in os.walk(ls):
    for fn in fns:
        p = os.path.join(dp, fn)
        print("\n-- %s" % os.path.relpath(p, ls))
        print(open(p, "r", encoding="utf-8", errors="replace").read()[:900])

print("\n\n=== 主 bundle 里的 region -> base 映射 ===")
MAIN = os.path.join(UD, "runtime-res", "releases", "main", "main~DAq2tHkd.mjs")
s = open(MAIN, "r", encoding="utf-8", errors="replace").read()
for m in re.finditer(r'"CN"\s*:', s):
    a = max(0, m.start() - 500)
    b = min(len(s), m.end() + 500)
    seg = s[a:b]
    if "xiaomimimo" in seg or "http" in seg:
        print("\n--- @%d ---\n%s" % (m.start(), seg))
        break
for m in re.finditer(r'function sm\(', s):
    a = max(0, m.start() - 200)
    b = min(len(s), m.end() + 1500)
    print("\n--- sm() @%d ---\n%s" % (m.start(), s[a:b]))
    break

print("\n\n=== 探测 mimo-server-cn 上的 dn 路径 ===")
BASES = ["https://mimo-server-cn.xiaomimimo.com",
         "https://mimo-server-cn.xiaomimimo.com/v1"]
PATHS = ["/user/usage", "/v1/user/usage", "/api/v1/user/usage",
         "/user/xiaomi/subscription/self", "/api/v1/balance",
         "/api/v1/tokenPlan/detail", "/api/v1/tokenPlan/usage",
         "/api/v1/userProfile", "/api/v1/models", "/model/list"]
for base in BASES:
    for path in PATHS:
        url = base + path
        try:
            req = urllib.request.Request(url, headers={
                "Accept": "application/json",
                "X-Mimo-Source": "mimocode-desktop",
                "User-Agent": "MiMoDesktop/26.1102.21158"})
            with urllib.request.urlopen(req, timeout=6) as r:
                print("  %-58s -> %s  %s" % (url, r.status, r.read(300).decode("utf-8", "replace")[:200]))
        except urllib.error.HTTPError as e:
            body = e.read(300).decode("utf-8", "replace").replace("\n", " ")
            if e.code != 404:
                print("  %-58s -> %s  %s" % (url, e.code, body[:200]))
        except Exception as e:
            print("  %-58s -> ERR %s" % (url, str(e)[:80]))
