#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""probe_sso.py — 走小米 SSO serviceLogin -> /sts 换票链取额度。"""
import http.cookiejar
import json
import sys
import urllib.error
import urllib.request

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, r"D:\桌面宠物\pet")
import mimo_quota as Q

cred = Q.load_cache()
print("userId:", cred.get("userId"), "passToken:", cred.get("passToken")[:14], "...")

jar = http.cookiejar.CookieJar()


class RawCookie(http.cookiejar.Cookie):
    def __init__(self, name, value, domain, path="/"):
        self.name = name
        self.value = value
        self.domain = domain
        self.domain_specified = True
        self.domain_initial_dot = domain.startswith(".")
        self.path = path
        self.path_specified = True
        self.port = None
        self.port_specified = False
        self.secure = False
        self.expires = None
        self.discard = True
        self.comment = None
        self.comment_url = None
        self.rest = {"HttpOnly": None}
        self.version = 0


for n, v in (("passToken", cred["passToken"]), ("userId", cred["userId"]),
             ("cUserId", cred.get("cUserId") or "")):
    if v:
        jar.set_cookie(RawCookie(n, v, ".xiaomi.com"))

opener = urllib.request.build_opener(
    urllib.request.HTTPCookieProcessor(jar),
    urllib.request.HTTPRedirectHandler())

UA = ("miNative PC/Normal Windows_NT/10.0 SDKV/1.0.0 DEVT/PC DEVS/Windows "
      "APP/miaccount_desktop APPV/0.1.0")
HDR = {"Accept": "application/json", "User-Agent": UA,
       "X-Mimo-Source": "mimocode-desktop"}


def get(url, headers=None):
    h = dict(HDR)
    if headers:
        h.update(headers)
    req = urllib.request.Request(url, headers=h)
    try:
        with opener.open(req, timeout=15) as r:
            return r.status, r.geturl(), r.read(2000).decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, url, e.read(2000).decode("utf-8", "replace")
    except Exception as e:
        return None, url, str(e)


TARGET = Q.PLATFORM + "/api/v1/usage"
st, url, body = get(TARGET)
print("\n[1] 直连 %s -> %s" % (TARGET, st))
print("    %s" % body[:400])

login_url = None
try:
    j = json.loads(body)
    login_url = j.get("loginUrl")
except Exception:
    pass
print("    loginUrl:", (login_url or "")[:220])

if login_url:
    print("\n[2] 走 SSO 链：%s" % login_url[:160])
    st2, url2, body2 = get(login_url)
    print("    -> %s  final=%s" % (st2, url2[:160]))
    print("    body: %s" % body2[:900])
    print("\n    cookie jar:")
    for c in jar:
        print("      %s=%s...  (%s)" % (c.name, c.value[:18], c.domain))

    print("\n[3] 带上换来的票据再取各接口")
    for key, path in Q.API_PATHS.items():
        st3, u3, b3 = get(Q.PLATFORM + path)
        print("   %-12s -> %s  %s" % (key, st3, b3[:220].replace("\n", " ")))
