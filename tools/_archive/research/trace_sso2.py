#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""trace_sso2.py — 干净 opener 逐跳跟 SSO 链路（禁用默认重定向）。

用法: python trace_sso2.py
"""
import json
import sys
import urllib.error
import urllib.request

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, r"D:\桌面宠物\pet")

import mimo_quota as Q

PLATFORM = "https://platform.xiaomimimo.com"


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise urllib.error.HTTPError(req.full_url, code, "REDIRECT",
                                     headers, fp)


def chain(url, cred, maxd=10):
    import http.cookiejar
    jar = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(
        NoRedirect(), urllib.request.HTTPCookieProcessor(jar))
    # 预置账号 cookie
    for n in Q.ACCOUNT_COOKIES:
        v = cred.get(n)
        if v:
            jar.set_cookie(Q._RawCookie(n, v, ".xiaomi.com"))
    cur = url
    for i in range(maxd):
        print("\n[hop %d] GET %s" % (i, cur[:190]))
        req = urllib.request.Request(cur, headers=Q.HDR)
        try:
            with opener.open(req, timeout=20) as r:
                body = r.read(1200).decode("utf-8", "replace")
                print("   -> %s  final=%s" % (r.status, r.geturl()[:190]))
                print("   body: %s" % body[:400])
                return
        except urllib.error.HTTPError as e:
            body = e.read(1200).decode("utf-8", "replace")
            loc = e.headers.get("Location") if e.headers else None
            print("   -> HTTP %s" % e.code)
            print("   Location: %s" % (loc or "")[:190])
            sc = e.headers.get_all("Set-Cookie") if e.headers else None
            if sc:
                for c in sc:
                    print("   Set-Cookie: %s" % c[:170])
            print("   body: %s" % body[:400])
            if loc and e.code in (301, 302, 303, 307, 308):
                cur = urllib.request.urljoin(cur, loc)
                continue
            return
        except Exception as e:
            print("   -> EXC %s" % e)
            return
    print("\n(跳数超限)")


def main():
    cred = Q.load_cache()
    c1 = {k: v for k, v in cred.items() if k != "platform_cookies"}

    # 第一跳拿 loginUrl
    opener, jar = Q._build_opener(c1)
    st, url, body = Q._get(opener, PLATFORM + "/api/v1/usage")
    lu = json.loads(body).get("loginUrl")
    print("== 第一跳 %s -> loginUrl ==" % st)
    print(lu)
    print("\n== 逐跳 ==")
    chain(lu, c1)


if __name__ == "__main__":
    main()
