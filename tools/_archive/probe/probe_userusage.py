#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""probe_userusage.py — 直接试 MiMo 桌面真正用的额度接口。

    GET https://mimo-server-cn.xiaomimimo.com/api/user/usage

用法: python probe_userusage.py
"""
import json
import sys
import urllib.request
import urllib.error

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, r"D:\桌面宠物\pet")

import mimo_quota as Q

HOSTS = [
    "https://mimo-server-cn.xiaomimimo.com/api/user/usage",
    "https://mimo-server-cn.xiaomimimo.com/api/user/xiaomi/subscription/self",
    "https://platform.xiaomimimo.com/api/v1/usage",
]


def try_url(url, cred, tag):
    opener, jar = Q._build_opener(cred)
    st, u, body = Q._get(opener, url)
    print("\n--- %s ---" % tag)
    print("  URL : %s" % url)
    print("  HTTP: %s" % st)
    print("  body: %s" % (body or "")[:700])
    return st, body


def main():
    cred = Q.load_cache()
    print("缓存: userId=%s  platform_cookies=%s"
          % (cred.get("userId"), list((cred.get("platform_cookies") or {}).keys())))

    # A: 只有账号 cookie
    c1 = {k: v for k, v in cred.items() if k != "platform_cookies"}
    # B: 全量
    c2 = dict(cred)

    for url in HOSTS:
        try_url(url, c1, "A 账号cookie: " + url.split("/api")[1])
        try_url(url, c2, "B 全量cookie: " + url.split("/api")[1])

    # C: 试试从 cookie 库里读 mimo-server 域的 cookie
    print("\n\n=== C: 读 cookie 库，找 mimo-server 相关 cookie ===")
    for p in Q.cookie_db_paths():
        try:
            ck = Q.read_cookie_db(p)
        except Exception as e:
            print("  %s -> 读不了: %s" % (p, e))
            continue
        hits = {k: (v[:18] + "...") for k, v in ck.items()}
        print("  %s -> %d 条" % (p, len(ck)))
        for k, v in sorted(hits.items())[:40]:
            print("      %-30s %s" % (k, v))


if __name__ == "__main__":
    main()
