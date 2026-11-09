#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""trace_sso.py — 逐跳跟踪 SSO 链路，看 403 到底出在哪一跳。

用法: python trace_sso.py
"""
import json
import sys
import urllib.request
import urllib.error

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, r"D:\桌面宠物\pet")

import mimo_quota as Q

PLATFORM = "https://platform.xiaomimimo.com"


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise urllib.error.HTTPError(req.full_url, code, "REDIRECT->" + newurl,
                                     headers, fp)


def trace(opener, url, label, depth=0, maxd=8):
    ind = "  " * depth
    print("%s[%s] GET %s" % (ind, label, url[:150]))
    req = urllib.request.Request(url, headers=Q.HDR)
    try:
        with opener.open(req, timeout=20) as r:
            body = r.read(600).decode("utf-8", "replace")
            print("%s  -> %s (final=%s)" % (ind, r.status, r.geturl()[:150]))
            print("%s  body: %s" % (ind, body[:300]))
            return r.status, r.geturl(), body
    except urllib.error.HTTPError as e:
        body = e.read(600).decode("utf-8", "replace")
        loc = e.headers.get("Location") if e.headers else None
        print("%s  -> HTTP %s  location=%s" % (ind, e.code, (loc or "")[:150]))
        print("%s  body: %s" % (ind, body[:300]))
        if loc and depth < maxd:
            return trace(opener, urllib.request.urljoin(url, loc),
                        "redirect", depth + 1, maxd)
        return e.code, url, body
    except Exception as e:
        print("%s  -> EXC %s" % (ind, e))
        return None, url, str(e)


def main():
    cred = Q.load_cache()
    c1 = {k: v for k, v in cred.items() if k != "platform_cookies"}
    opener, jar = Q._build_opener(c1)

    # 1) 先拿 loginUrl
    st, url, body = Q._get(opener, PLATFORM + "/api/v1/usage")
    print("== 第一跳 HTTP %s ==" % st)
    lu = json.loads(body).get("loginUrl")
    print("loginUrl = %s\n" % lu)

    # 2) 用禁止自动重定向的 opener 逐跳跟
    print("== 逐跳跟踪 ==")
    op2, jar2 = Q._build_opener(c1)
    op2.add_handler(NoRedirect())
    trace(op2, lu, "serviceLogin")

    print("\n== jar 最终 ==")
    for c in jar2:
        print("  %-30s %s" % (c.name, str(c.value)[:40]))


if __name__ == "__main__":
    main()
