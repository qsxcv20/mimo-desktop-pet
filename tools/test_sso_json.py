#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""test_sso_json.py — 用 MiMo 同款 serviceLogin(_json=true) 换票。

逆向自 MiMo 主进程 SSO SDK：
    GET https://account.xiaomi.com/pass/serviceLogin
        ?_locale=zh_CN&_snsNone=true&sid=<sid>&_json=true
    Cookie: passToken=...; userId=...; cUserId=...
    -> JSON: {code, loc, ssecurity, nonce, ...}
    跟随 loc -> /sts -> Set-Cookie 下发 serviceToken

用法: python test_sso_json.py [sid]
"""
import json
import sys
import urllib.error
import urllib.parse
import urllib.request

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass  # pythonw.exe 下 sys.stdout 是 None
sys.path.insert(0, r"D:\桌面宠物\pet")

import mimo_quota as Q

ACC = "https://account.xiaomi.com/pass/serviceLogin"
UA = ("miNative PC/Normal Windows_NT/10.0.26200 SDKV/1.0.0 DEVT/PC "
      "DEVS/Windows APP/miaccount_desktop APPV/0.1.0")


def phase1(sid, pass_token, user_id, c_user_id):
    q = urllib.parse.urlencode({"_locale": "zh_CN", "_snsNone": "true",
                                "sid": sid, "_json": "true"})
    url = ACC + "?" + q
    hdr = {"User-Agent": UA, "Accept": "application/json",
           "Cookie": "passToken=%s; userId=%s; cUserId=%s"
                     % (pass_token, user_id, c_user_id)}
    req = urllib.request.Request(url, headers=hdr)
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return r.status, r.read(8000).decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read(4000).decode("utf-8", "replace")
    except Exception as e:
        return None, str(e)


def main():
    sid = sys.argv[1] if len(sys.argv) > 1 else "api-platform"
    cred = Q.load_cache() or {}
    pt = cred.get("passToken") or ""
    uid = cred.get("userId") or "3113399232"
    cid = cred.get("cUserId") or ""
    print("sid=%s userId=%s passToken=%s..." % (sid, uid, pt[:14]))

    st, body = phase1(sid, pt, uid, cid)
    print("\n== Phase 1 HTTP %s ==" % st)
    print(body[:1200])

    try:
        j = json.loads(body)
    except Exception:
        print("\n不是 JSON")
        return
    loc = j.get("loc")
    print("\nloc = %s" % (loc or "")[:300])
    if not loc:
        return

    # 跟随 loc 拿票据
    opener, jar = Q._build_opener({})
    hdr = {"User-Agent": UA,
           "Cookie": "passToken=%s; userId=%s; cUserId=%s" % (pt, uid, cid)}
    req = urllib.request.Request(loc, headers=hdr)
    try:
        with opener.open(req, timeout=25) as r:
            b = r.read(3000).decode("utf-8", "replace")
            print("\n== 跟随 loc: HTTP %s  final=%s ==" % (r.status, r.geturl()))
            print(b[:800])
    except urllib.error.HTTPError as e:
        print("\n== 跟随 loc: HTTP %s ==" % e.code)
        print(e.read(800).decode("utf-8", "replace")[:800])
    except Exception as e:
        print("\n跟随 loc 异常: %s" % e)

    print("\n== jar ==")
    for c in jar:
        print("   %-30s domain=%-28s %s" % (c.name, c.domain, str(c.value)[:30]))


if __name__ == "__main__":
    main()
