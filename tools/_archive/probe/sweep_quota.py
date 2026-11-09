#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""sweep_quota.py — base × path 组合扫描，只报非 404 响应。"""
import sys
import urllib.request
import urllib.error

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASES = [
    "https://api.xiaomimimo.com",
    "https://api.xiaomimimo.com/v1",
    "https://token-plan-cn.xiaomimimo.com",
    "https://token-plan-cn.xiaomimimo.com/v1",
    "https://mimo-server-cn.xiaomimimo.com",
    "https://mimo-server-cn.xiaomimimo.com/v1",
    "https://platform.xiaomimimo.com",
]
PATHS = [
    "/user/usage", "/user/xiaomi/subscription/self", "/user/xiaomi/me",
    "/api/v1/usage", "/api/v1/balance",
    "/api/v1/tokenPlan/detail", "/api/v1/tokenPlan/usage",
    "/api/v1/userProfile", "/api/v1/models", "/api/v1/model/list",
    "/v1/api/v1/usage", "/v1/user/usage",
    "/usage", "/balance", "/plan", "/quota",
]
HDR = {"Accept": "application/json",
       "X-Mimo-Source": "mimocode-desktop",
       "User-Agent": "MiMoDesktop/26.1102.21158",
       "Origin": "https://mimo.xiaomimimo.com"}

hits = 0
for base in BASES:
    for path in PATHS:
        url = base + path
        try:
            req = urllib.request.Request(url, headers=HDR)
            with urllib.request.urlopen(req, timeout=6) as r:
                body = r.read(600).decode("utf-8", "replace").replace("\n", " ")
                print("*** %-58s -> %s  %s" % (url, r.status, body[:260]))
                hits += 1
        except urllib.error.HTTPError as e:
            body = e.read(400).decode("utf-8", "replace").replace("\n", " ")
            if e.code not in (404,):
                print(">>> %-58s -> %s  %s" % (url, e.code, body[:260]))
                hits += 1
        except Exception:
            pass
print("\n非 404 响应数:", hits)
