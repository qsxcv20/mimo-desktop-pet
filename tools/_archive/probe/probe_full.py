#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""probe_full.py — 打印 SSO 全量 Location + mimo-server 401 响应头。

用法: python probe_full.py
"""
import json
import sys
import urllib.error
import urllib.request
import http.cookiejar

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, r"D:\桌面宠物\pet")

import mimo_quota as Q


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise urllib.error.HTTPError(req.full_url, code, "REDIRECT", headers, fp)


def main():
    cred = Q.load_cache() or {}
    c1 = {k: v for k, v in cred.items() if k != "platform_cookies"}

    # ---- 1. mimo-server 的 401 响应头 ----
    print("=== 1. mimo-server-cn 401 响应头 ===")
    for url in ("https://mimo-server-cn.xiaomimimo.com/api/user/usage",
                "https://platform.xiaomimimo.com/api/user/usage",
                "https://platform.xiaomimimo.com/api/user/xiaomi/me"):
        req = urllib.request.Request(url, headers=Q.HDR)
        try:
            with urllib.request.urlopen(req, timeout=15) as r:
                print("  %s -> %s" % (url, r.status))
        except urllib.error.HTTPError as e:
            print("  %s -> %s" % (url, e.code))
            for k, v in (e.headers or {}).items():
                print("       %-24s %s" % (k, v[:150]))
        except Exception as e:
            print("  %s -> EXC %s" % (url, e))

    # ---- 2. SSO 完整 Location ----
    print("\n=== 2. SSO 完整链路 URL ===")
    opener, jar = Q._build_opener({"passToken": "", "userId": "", "cUserId": ""})
    st, url, body = Q._get(opener, "https://platform.xiaomimimo.com/api/v1/usage")
    lu = json.loads(body).get("loginUrl")

    jar2 = http.cookiejar.CookieJar()
    op = urllib.request.build_opener(NoRedirect(),
                                     urllib.request.HTTPCookieProcessor(jar2))
    for n in Q.ACCOUNT_COOKIES:
        v = c1.get(n)
        if v:
            jar2.set_cookie(Q._RawCookie(n, v, ".xiaomi.com"))

    cur = lu
    for i in range(6):
        req = urllib.request.Request(cur, headers=Q.HDR)
        try:
            with op.open(req, timeout=20) as r:
                print("  [%d] %s -> %s" % (i, cur[:120], r.status))
                break
        except urllib.error.HTTPError as e:
            print("  [%d] status=%s" % (i, e.code))
            loc = e.headers.get("Location") if e.headers else None
            if loc:
                print("      Location(完整): %s" % loc)
                cur = urllib.request.urljoin(cur, loc)
                continue
            print("      body: %s" % (e.read() or b"")[:200])
            break

    print("\n=== 3. jar 最终 cookie ===")
    for c in jar2:
        print("   %-30s domain=%-28s %s" % (c.name, c.domain, str(c.value)[:24]))


if __name__ == "__main__":
    main()
