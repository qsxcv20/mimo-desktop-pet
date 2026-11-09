#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""probe_platform_user.py — 验证 platform.xiaomimimo.com/api/user/* + 票据。

用法: python probe_platform_user.py
"""
import json
import sys
import urllib.request
import urllib.error

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, r"D:\桌面宠物\pet")

import mimo_quota as Q

PLATFORM = "https://platform.xiaomimimo.com"
PATHS = [
    "/api/user/usage",
    "/api/user/xiaomi/subscription/self",
    "/api/user/xiaomi/me",
]


def hit(url, cred, tag, extra_headers=None):
    opener, jar = Q._build_opener(cred)
    hdr = dict(Q.HDR)
    hdr["X-Client-Version"] = "26.1102.21158"
    if extra_headers:
        hdr.update(extra_headers)
    req = urllib.request.Request(url, headers=hdr)
    try:
        with opener.open(req, timeout=20) as r:
            body = r.read(4000).decode("utf-8", "replace")
            print("\n--- %s ---" % tag)
            print("  HTTP %s  %s" % (r.status, url))
            print("  body: %s" % body[:900])
            return r.status, body
    except urllib.error.HTTPError as e:
        body = e.read(2000).decode("utf-8", "replace")
        print("\n--- %s ---" % tag)
        print("  HTTP %s  %s" % (e.code, url))
        print("  body: %s" % body[:500])
        return e.code, body
    except Exception as e:
        print("\n--- %s ---" % tag)
        print("  EXC %s" % e)
        return None, ""


def main():
    cred = Q.load_cache() or {}

    print("########## 1. 完全无 cookie ##########")
    for p in PATHS:
        hit(PLATFORM + p, {"passToken": "", "userId": "", "cUserId": ""},
            "无cookie " + p)

    print("\n\n########## 2. 只有账号 cookie ##########")
    c1 = {k: v for k, v in cred.items() if k != "platform_cookies"}
    for p in PATHS:
        hit(PLATFORM + p, c1, "账号cookie " + p)

    print("\n\n########## 3. 账号 cookie + 平台票据 ##########")
    for p in PATHS:
        hit(PLATFORM + p, cred, "全量 " + p)


if __name__ == "__main__":
    main()
