#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""probe_engine_api2.py — 定点探测 MiMo / node 的本地服务。"""
import json
import sys
import urllib.request
import urllib.error

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

TARGETS = [51616, 51617, 51675, 8777, 8788, 55002]

PATHS = [
    "/", "/meta", "/api/meta", "/health", "/api/health",
    "/usage", "/api/usage", "/balance", "/api/balance",
    "/api/v1/usage", "/api/v1/balance", "/api/v1/tokenPlan/detail",
    "/api/v1/tokenPlan/usage", "/api/v1/userProfile",
    "/user/usage", "/user/xiaomi/subscription/self", "/user/xiaomi/me",
    "/api/accounts", "/accounts", "/api/plan", "/plan",
    "/api/v1/quota", "/quota", "/credit", "/api/credit",
    "/v1/health", "/v1/sessions?limit=1",
]


def probe(port, path, timeout=2.5):
    url = "http://127.0.0.1:%d%s" % (port, path)
    try:
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read(4000).decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read(2000).decode("utf-8", "replace")
    except Exception as e:
        return None, str(e)[:120]


for port in TARGETS:
    print("\n================ 端口 %d ================" % port)
    hits = 0
    for path in PATHS:
        st, body = probe(port, path)
        if st is None:
            continue
        if st == 404:
            continue
        if "not-found" in body or "not found" in body:
            continue
        hits += 1
        short = body if len(body) < 700 else body[:700] + " ...(截断)"
        print("\n  %-34s -> %s" % (path, st))
        print("      %s" % short.replace("\n", " ")[:700])
    if not hits:
        print("  (无有效响应)")
