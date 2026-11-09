#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""probe_quota2.py — 试验不同凭据组合下平台接口的行为。

用法: python probe_quota2.py
"""
import json
import sys
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, r"D:\桌面宠物\pet")

import mimo_quota as Q

PLATFORM = "https://platform.xiaomimimo.com"


def trial(tag, cred, path="/api/v1/usage"):
    opener, jar = Q._build_opener(cred)
    st, url, body = Q._get(opener, PLATFORM + path)
    print("\n--- %s ---" % tag)
    print("  HTTP %s" % st)
    print("  body(300): %s" % (body or "")[:300].replace("\n", " "))
    print("  jar now: %s" % [c.name for c in jar])
    return st, url, body, opener, jar


def main():
    cred = Q.load_cache()
    if not cred:
        print("无缓存凭据")
        return

    # 变体 1：只留 passToken / userId / cUserId，丢掉 platform_cookies
    c1 = {k: v for k, v in cred.items() if k != "platform_cookies"}
    st, url, body, opener, jar = trial("1) 只有账号 cookie，无平台票据", c1)
    if st == 401 and "loginUrl" in (body or ""):
        import json as J
        lu = J.loads(body).get("loginUrl")
        print("  loginUrl = %s" % lu[:200])
        st2, url2, body2 = Q._get(opener, lu)
        print("  SSO 之后 HTTP %s  url=%s" % (st2, url2))
        print("  SSO body(500): %s" % (body2 or "")[:500])
        print("  jar now: %s" % {c.name: str(c.value)[:14] for c in jar})
        # SSO 之后再打一次 usage
        st3, url3, body3 = Q._get(opener, PLATFORM + "/api/v1/usage")
        print("  复用同一 opener 打 usage -> HTTP %s" % st3)
        print("  body(400): %s" % (body3 or "")[:400])

    # 变体 2：完全不带 cookie 的 401 -> loginUrl 全链路
    print("\n\n===== 变体 2：完全无 cookie 走完整 SSO =====")
    import urllib.request as U
    opener3, jar3 = Q._build_opener({"passToken": "", "userId": "", "cUserId": ""})
    st, url, body = Q._get(opener3, PLATFORM + "/api/v1/usage")
    print("  第一步 HTTP %s" % st)
    lu = json.loads(body).get("loginUrl")
    print("  loginUrl = %s" % lu[:250])
    # SSO 时带上 passToken
    opener3, jar3 = Q._build_opener(c1)
    st2, url2, body2 = Q._get(opener3, lu)
    print("  第二步 HTTP %s" % st2)
    print("  final url = %s" % url2)
    print("  body(600): %s" % (body2 or "")[:600])
    print("  jar: %s" % {c.name: str(c.value)[:16] for c in jar3})


if __name__ == "__main__":
    main()
