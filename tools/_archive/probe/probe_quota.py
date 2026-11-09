#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""probe_quota.py — 诊断平台接口返回 403 的原因。

用法: python probe_quota.py
"""
import json
import os
import sys
import time
import urllib.error
import urllib.request

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, r"D:\桌面宠物\pet")

import mimo_quota as Q

PLATFORM = "https://platform.xiaomimimo.com"


def show(tag, st, url, body):
    print("\n--- %s ---" % tag)
    print("  HTTP %s" % st)
    print("  final url: %s" % (url or "")[:220])
    print("  body(600): %s" % (body or "")[:600])


def main():
    cred = Q.load_cache()
    print("== 缓存凭据 ==")
    if not cred:
        print("  (无缓存)")
        return
    print("  captured_at = %s (%s)" % (
        cred.get("captured_at"),
        time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(cred.get("captured_at") or 0))))
    print("  userId      = %s" % cred.get("userId"))
    pt = cred.get("passToken") or ""
    print("  passToken   = %s... (len=%d)" % (pt[:14], len(pt)))
    print("  cUserId     = %s" % (cred.get("cUserId") or "")[:30])
    pc = cred.get("platform_cookies") or {}
    print("  platform_cookies: %s" % (list(pc.keys()) or "(无)"))
    for k, v in pc.items():
        print("      %-28s = %s... (len=%d)" % (k, str(v)[:16], len(str(v))))

    # 1) 裸请求：只带 passToken
    print("\n== A. 只带 passToken ==")
    opener, jar = Q._build_opener(cred)
    st, url, body = Q._get(opener, PLATFORM + "/api/v1/usage")
    show("A", st, url, body)

    # 2) 带缓存的 platform_cookies
    print("\n== B. 带缓存 platform_cookies ==")
    opener2, jar2 = Q._build_opener(cred)
    hdr = dict(Q.HDR)
    st, url, body = Q._get(opener2, PLATFORM + "/api/v1/usage")
    show("B", st, url, body)

    # 3) 不带任何 cookie
    print("\n== C. 不带 cookie ==")
    import urllib.request as U
    try:
        req = U.Request(PLATFORM + "/api/v1/usage", headers=Q.HDR)
        with U.urlopen(req, timeout=15) as r:
            show("C", r.status, r.geturl(), r.read(2000).decode("utf-8", "replace"))
    except urllib.error.HTTPError as e:
        show("C", e.code, e.url, e.read(2000).decode("utf-8", "replace"))
    except Exception as e:
        show("C", None, "", str(e))

    # 4) 直接走 fetch_platform 看错误
    print("\n== D. fetch_platform ==")
    data, err, newcred = Q.fetch_platform(cred)
    print("  err  = %s" % err)
    if data:
        print("  data keys = %s" % list(data.keys()))
        print(json.dumps(data, ensure_ascii=False, indent=2)[:1500])


if __name__ == "__main__":
    main()
