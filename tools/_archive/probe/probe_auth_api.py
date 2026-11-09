#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""probe_auth_api.py — 带 token 探测各本地服务端口。"""
import json
import os
import sys
import urllib.request
import urllib.error

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

api_path = os.path.join(os.environ["APPDATA"], "Xiaomi MiMo", "desktop-api.json")
with open(api_path, "r", encoding="utf-8") as f:
    api = json.load(f)
TOKEN, PORT = api["token"], api["port"]

TARGETS = [PORT, 51616, 51675, 8777, 8788, 55002]
PATHS = [
    "/", "/meta", "/api/meta", "/health", "/api/health", "/usage", "/api/usage",
    "/balance", "/api/balance", "/api/v1/usage", "/api/v1/balance",
    "/api/v1/tokenPlan/detail", "/api/v1/tokenPlan/usage",
    "/api/v1/userProfile", "/api/v1/user/createOrUpdateUser",
    "/user/usage", "/user/xiaomi/subscription/self", "/user/xiaomi/me",
    "/user/settings", "/api/accounts", "/accounts", "/api/plan", "/plan",
    "/api/quota", "/quota", "/credit", "/api/credit",
    "/v1/health", "/v1/sessions?limit=1", "/v1/usage", "/v1/balance",
    "/session/status", "/global/health", "/console/usage", "/console/balance",
]


def probe(port, path, timeout=2.5):
    url = "http://127.0.0.1:%d%s" % (port, path)
    hdrs = {"Authorization": "Bearer %s" % TOKEN,
            "Host": "127.0.0.1:%d" % port,
            "Accept": "application/json"}
    try:
        req = urllib.request.Request(url, headers=hdrs)
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
        if st is None or st in (401, 403, 404):
            continue
        if "not-found" in body or "not found" in body or body.strip() == "Unauthorized":
            continue
        hits += 1
        short = body if len(body) < 800 else body[:800] + " ...(截断)"
        print("\n  %-34s -> %s" % (path, st))
        print("      %s" % short.replace("\n", " ")[:800])
    if not hits:
        print("  (无有效响应)")
