#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""test_login_variants.py — 试各种 cookie 组合，看哪个能让 account 自动登录。

用法: python test_login_variants.py
"""
import http.cookiejar
import json
import sys
import urllib.error
import urllib.request

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass  # pythonw.exe 下 sys.stdout 是 None
sys.path.insert(0, r"D:\桌面宠物\pet")

import mimo_quota as Q

PLATFORM = "https://platform.xiaomimimo.com"
UA = ("miNative PC/Normal Windows_NT/10.0 SDKV/1.0.0 DEVT/PC DEVS/Windows "
      "APP/miaccount_desktop APPV/0.1.0")


def mk_opener(cookies):
    jar = http.cookiejar.CookieJar()
    for name, value, domain in cookies:
        jar.set_cookie(Q._RawCookie(name, value, domain))
    return urllib.request.build_opener(
        urllib.request.HTTPCookieProcessor(jar),
        urllib.request.HTTPRedirectHandler()), jar


def attempt(label, cookies, extra_headers=None):
    opener, jar = mk_opener(cookies)
    hdr = {"Accept": "application/json", "User-Agent": UA,
           "X-Mimo-Source": "mimocode-desktop"}
    if extra_headers:
        hdr.update(extra_headers)
    req = urllib.request.Request(PLATFORM + "/api/v1/usage", headers=hdr)
    try:
        with opener.open(req, timeout=20) as r:
            body = r.read(1500).decode("utf-8", "replace")
            print("  [%s] HTTP %s  %s" % (label, r.status, body[:110]))
            return jar, body
    except urllib.error.HTTPError as e:
        body = e.read(1500).decode("utf-8", "replace")
        print("  [%s] HTTP %s  %s" % (label, e.code, body[:110]))
        try:
            lu = json.loads(body).get("loginUrl")
        except Exception:
            lu = None
        if not lu:
            return jar, body
        req2 = urllib.request.Request(lu, headers=hdr)
        try:
            with opener.open(req2, timeout=25) as r2:
                b2 = r2.read(400).decode("utf-8", "replace")
                ok = "passInfo" in str([c.name for c in jar])
                print("       -> SSO 后 HTTP %s  url=%s"
                      % (r2.status, r2.geturl()[:120]))
                print("       -> 票据: %s" % [c.name for c in jar])
                if "login-end" in b2 or "passInfo" in str([c.name for c in jar]):
                    print("       ★★ 自动登录成功")
                else:
                    print("       xx 需要交互登录 (最终 %s)"
                          % r2.geturl()[:90])
        except urllib.error.HTTPError as e2:
            print("       -> SSO HTTP %s" % e2.code)
        except Exception as e2:
            print("       -> SSO EXC %s" % e2)
        return jar, body


def main():
    cred = Q.load_cache() or {}
    pt = cred.get("passToken") or ""
    uid = cred.get("userId") or "3113399232"
    cid = cred.get("cUserId") or ""

    variants = [
        ("A 全部 .xiaomi.com",
         [("passToken", pt, ".xiaomi.com"), ("userId", uid, ".xiaomi.com"),
          ("cUserId", cid, ".xiaomi.com")]),
        ("B 按DB原始域",
         [("passToken", pt, ".account.xiaomi.com"),
          ("cUserId", cid, ".account.xiaomi.com"),
          ("userId", uid, ".account.xiaomi.com"),
          ("passToken", pt, ".xiaomi.com"),
          ("cUserId", cid, ".xiaomi.com"),
          ("uLocale", "zh_CN", ".xiaomi.com")]),
        ("C 只 .account.xiaomi.com",
         [("passToken", pt, ".account.xiaomi.com"),
          ("cUserId", cid, ".account.xiaomi.com"),
          ("userId", uid, ".account.xiaomi.com")]),
        ("D B + Referer",
         [("passToken", pt, ".account.xiaomi.com"),
          ("cUserId", cid, ".account.xiaomi.com"),
          ("userId", uid, ".account.xiaomi.com"),
          ("passToken", pt, ".xiaomi.com"),
          ("cUserId", cid, ".xiaomi.com"),
          ("uLocale", "zh_CN", ".xiaomi.com")]),
    ]

    for label, ck in variants:
        extra = None
        if label.endswith("Referer"):
            extra = {"Referer": "https://platform.xiaomimimo.com/",
                     "Origin": "https://platform.xiaomimimo.com"}
        print("\n===== %s =====" % label)
        attempt(label, ck, extra)


if __name__ == "__main__":
    main()
