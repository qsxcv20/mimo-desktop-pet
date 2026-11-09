#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""probe_platform2.py — 带 /v1 前缀探测小米平台。"""
import json
import sys
import urllib.request
import urllib.error

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASES = [
    "https://api.xiaomimimo.com/v1",
    "https://token-plan-cn.xiaomimimo.com/v1",
    "https://platform.xiaomimimo.com/v1",
]
PATHS = ["/user/usage", "/user/xiaomi/subscription/self", "/user/xiaomi/me",
         "/model/list", "/user/settings"]

HDR = {"Accept": "application/json",
       "User-Agent": "MiMoDesktop/26.1102.21158",
       "X-Mimo-Source": "mimocode-desktop"}


def probe(base, path, extra=None):
    url = base + path
    h = dict(HDR)
    if extra:
        h.update(extra)
    try:
        req = urllib.request.Request(url, headers=h)
        with urllib.request.urlopen(req, timeout=8) as r:
            return r.status, r.read(900).decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read(900).decode("utf-8", "replace")
    except Exception as e:
        return None, str(e)[:150]


for base in BASES:
    print("\n############ %s ############" % base)
    for path in PATHS:
        st, body = probe(base, path)
        print("  %-34s -> %s" % (path, st))
        if body:
            print("      %s" % body[:400].replace("\n", " "))
